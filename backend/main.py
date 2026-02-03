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
from typing import List, Optional
from services.data.karlsruhe_loader import KarlsruheLoader
from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest, OptimizationResponse, PricingScenario, WeightSelectionRequest
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased

app = FastAPI(title="Parking Fee Optimization API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ParkingZone(BaseModel):
    id: int
    name: str
    current_fee: Optional[float] = None
    occupancy_rate: Optional[float] = None
    suggested_fee: Optional[float] = None
    lat: float = 0.0
    lon: float = 0.0
    capacity: Optional[int] = None
    is_placeholder: bool = True  # Flag so UI/clients know data is synthetic
# Config 
source = "mobidata" # or "mobidata"
limit = 3000  # Max limit for MobiData API

# Cache for loaded Karlsruhe parking zones
parking_zones: List[ParkingZone] = []
loader = KarlsruheLoader(source=source)
agent_optimizer = NSGA3OptimizerAgentBased()
elasticity_optimizer = NSGA3OptimizerElasticity()

@app.get("/")
async def root():
    return {"message": "Parking Fee Optimization API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/zones", response_model=List[ParkingZone])
async def get_parking_zones():
    """Get all parking zones with current fees and optimization suggestions"""
    global parking_zones

    # Serve cached data if already loaded
    if parking_zones:
        return parking_zones

    try:
        # Load city model which contains parking zones
        city = loader.load_city(limit=limit)

        parking_zones = [
            ParkingZone(
                id=z.id,
                name=z.pseudonym,
                current_fee=float(z.price) if hasattr(z, 'price') else None,
                occupancy_rate=z.current_capacity / z.maximum_capacity if hasattr(z, 'maximum_capacity') and z.maximum_capacity > 0 else None,
                suggested_fee=None,  # synthetic / to be generated
                lat=z.position[0],
                lon=z.position[1],
                capacity=z.maximum_capacity if hasattr(z, 'maximum_capacity') else None,
                is_placeholder=False
            )
            for z in city.parking_zones
        ]
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
    """
    Endpoint to execute the NSGA-III optimization algorithm.
    """
    #Create an instance of the NSGA3Optimizer
    
    #Call the optimize method and return the result
    return elasticity_optimizer.optimize(request)


@app.post("/optimize_agent", response_model=OptimizationResponse)
async def optimize_fee_agent(request: OptimizationRequest):
    """
    Endpoint to execute the NSGA-III optimization algorithm.
    """
    #Create an instance of the NSGA3Optimizer
    
    #Call the optimize method and return the result
    return agent_optimizer.optimize(request, loader=loader)

@app.post("/select_best_solution_elasticity", response_model=PricingScenario)
async def select_elasticity_best_solution_by_weights(request: WeightSelectionRequest) -> PricingScenario:
    return elasticity_optimizer.select_best_solution_by_weights(request.optimization_response, request.weights)

@app.post("/select_best_solution_agent", response_model=PricingScenario)
async def select_agent_best_solution_by_weights(request: WeightSelectionRequest) -> PricingScenario:
    return agent_optimizer.select_best_solution_by_weights(request.optimization_response, request.weights)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)