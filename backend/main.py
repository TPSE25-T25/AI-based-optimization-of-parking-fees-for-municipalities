import sys
from pathlib import Path

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Add the project root directory to sys.path
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

from sqlalchemy import select
from services.data.karlsruhe_loader import KarlsruheLoader
from backend.services.optimizer.schemas.optimization_schema import ParkingZone
from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest, OptimizationResponse, PricingScenario, WeightSelectionRequest, OptimizationSettings
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased
from db.init_db import init_db
from db.database import SessionLocal
from db.models import SimulationResult

app = FastAPI(title="Parking Fee Optimization API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Config 
source = "mobidata" # or "mobidata"
limit = 3000  # Max limit for MobiData API

# Cache for loaded Karlsruhe parking zones
parking_zones: List[ParkingZone] = []
loader = KarlsruheLoader(source=source)
agent_optimizer = NSGA3OptimizerAgentBased()
elasticity_optimizer = NSGA3OptimizerElasticity()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


class SaveResultRequest(BaseModel):
    parameters: Dict
    map_config: Optional[Dict] = None
    map_snapshot: Optional[List[Dict]] = None
    map_path: Optional[str] = None
    csv_path: Optional[str] = None
    best_scenario: Optional[Dict] = None

@app.get("/")
async def root():
    return {"message": "Parking Fee Optimization API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# frontend now pulls the settings metadata dynamically from 
# a new backend endpoint and uses it for defaults, min/max, 
#and descriptions
@app.get("/optimization-settings")
async def get_optimization_settings():
    """Expose optimization settings defaults/limits for the frontend ConfigurationPanel."""
    fields = getattr(OptimizationSettings, "model_fields", None) or OptimizationSettings.__fields__

    def serialize_field(field):
        info = getattr(field, "field_info", None)
        return {
            "default": getattr(info, "default", None) if info else getattr(field, "default", None),
            "min": getattr(info, "ge", None),
            "max": getattr(info, "le", None),
            "description": getattr(info, "description", None),
        }

    return {name: serialize_field(field) for name, field in fields.items()}

@app.get("/zones", response_model=List[ParkingZone])
async def get_parking_zones():
    """Return all parking zones for the map (used on initial frontend load)."""
    global parking_zones

    # Serve cached data if already loaded
    if parking_zones:
        return parking_zones

    try:
        # Load city model which contains parking zones
        city = loader.load_city(limit=limit)
        parking_zones = city.parking_zones
        
        if not parking_zones:
            raise HTTPException(status_code=502, detail="No parking data returned for Karlsruhe")

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        error_details = traceback.format_exc()
        print(f"Load failed with error: {exc}")
        print(f"Full traceback:\n{error_details}")
        raise HTTPException(status_code=502, detail=f"Load failed for Karlsruhe: {str(exc)}")

    return parking_zones

@app.get("/zones/{zone_id}", response_model=ParkingZone)
async def get_parking_zone(zone_id: int):
    """Get a specific parking zone by ID"""
    for zone in parking_zones:
        if zone.id == zone_id:
            return zone
    return {"error": "Zone not found"}

@app.post("/optimize_elasticity", response_model=OptimizationResponse)
async def optimize_fee_elasticity(request: OptimizationRequest):
    """Run NSGA-III optimization (elasticity model) and return Pareto scenarios."""
    #Create an instance of the NSGA3Optimizer
    
    #Call the optimize method and return the result
    return elasticity_optimizer.optimize(request)


@app.post("/optimize_agent", response_model=OptimizationResponse)
async def optimize_fee_agent(request: OptimizationRequest):
    """Run NSGA-III optimization (agent-based model) and return Pareto scenarios."""
    #Create an instance of the NSGA3Optimizer
    
    #Call the optimize method and return the result
    return agent_optimizer.optimize(request, loader=loader)

@app.post("/select_best_solution_elasticity", response_model=PricingScenario)
async def select_elasticity_best_solution_by_weights(request: WeightSelectionRequest) -> PricingScenario:
    """Select the best scenario using user weights (elasticity results)."""
    return elasticity_optimizer.select_best_solution_by_weights(request.optimization_response, request.weights)

@app.post("/select_best_solution_agent", response_model=PricingScenario)
async def select_agent_best_solution_by_weights(request: WeightSelectionRequest) -> PricingScenario:
    """Select the best scenario using user weights (agent-based results)."""
    return agent_optimizer.select_best_solution_by_weights(request.optimization_response, request.weights)


@app.post("/results")
async def save_result(request: SaveResultRequest):
    """Persist a simulation result and optional map configuration to the database."""
    session = SessionLocal()
    try:
        result = SimulationResult(
            parameters=request.parameters,
            map_config=request.map_config,
            map_snapshot=request.map_snapshot,
            map_path=request.map_path,
            csv_path=request.csv_path,
            best_scenario=request.best_scenario,
        )
        session.add(result)
        session.commit()
        session.refresh(result)
        return {"id": result.id, "created_at": result.created_at}
    finally:
        session.close()


@app.get("/results")
async def list_results():
    """List stored results without heavy payloads."""
    session = SessionLocal()
    try:
        stmt = select(SimulationResult).order_by(SimulationResult.created_at.desc())
        results = session.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at,
                "parameters": r.parameters,
            }
            for r in results
        ]
    finally:
        session.close()


@app.get("/results/{result_id}")
async def get_result(result_id: int):
    """Fetch a stored result including map snapshot and config."""
    session = SessionLocal()
    try:
        result = session.get(SimulationResult, result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        return {
            "id": result.id,
            "created_at": result.created_at,
            "parameters": result.parameters,
            "map_config": result.map_config,
            "map_snapshot": result.map_snapshot,
            "map_path": result.map_path,
            "csv_path": result.csv_path,
            "best_scenario": result.best_scenario,
        }
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)