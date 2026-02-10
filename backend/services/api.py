from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select

from backend.services.datasources.city_data_loader import CityDataLoader
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased
from backend.services.optimizer.solution_selector import SolutionSelector
from backend.services.settings.data_source_settings import DataSourceSettings
from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource
from backend.services.payloads.weight_selection_payload import WeightSelectionRequest, WeightSelectionResponse
from backend.services.payloads.load_city_payload import LoadCityRequest, LoadCityResponse, ReverseGeoLocationRequest, ReverseGeoLocationResponse
from backend.services.payloads.optimization_payload import OptimizationResponse, OptimizationRequest, OptimizationSettingsResponse
from backend.services.payloads.results_payload import SaveResultRequest
from backend.services.database.init_db import init_db
from backend.services.database.database import SessionLocal
from backend.services.database.models import SimulationResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Parking Fee Optimization API", version="1.0.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Parking Fee Optimization API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/optimization-settings", response_model=OptimizationSettingsResponse)
async def get_optimization_settings() -> OptimizationSettingsResponse:
    return OptimizationSettingsResponse()

@app.post("/reverse-geocode", response_model=ReverseGeoLocationResponse)
async def reverse_geocode(request: ReverseGeoLocationRequest) -> ReverseGeoLocationResponse:
    """
    Reverse geocode coordinates to get location information.
    
    Uses OSMnx loader's static method to convert lat/lon to city name.
    """
    try:
        result = OSMnxDataSource.reverse_geocode(request.center_lat, request.center_lon)
        return ReverseGeoLocationResponse(geo_info=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reverse geocoding failed: {str(e)}")


@app.post("/load_city", response_model=LoadCityResponse)
async def load_city(request: LoadCityRequest) -> LoadCityResponse:
    """Load city data including parking zones and POIs from specified datasource (osmnx, mobidata, or generated)."""
    try:
        # Build datasource settings from request
        datasource_settings = DataSourceSettings(
            data_source=request.data_source,
            limit=request.limit,
            city_name=request.city_name,
            center_coords=(request.center_lat, request.center_lon),
            random_seed=request.seed,
            poi_limit=request.poi_limit,
            default_elasticity=request.default_elasticity,
            search_radius=request.search_radius,
            default_current_fee=request.default_current_fee,
            tariffs=request.tariffs
        )
        
        # Load city data using the specified datasource
        loader = CityDataLoader(datasource=datasource_settings)
        city = loader.load_city()
        
        if not city.parking_zones:
            raise HTTPException(
                status_code=502, 
                detail=f"No parking data returned from {request.data_source} datasource"
            )
        
        return LoadCityResponse(city=city)
    except Exception as exc:
        import traceback
        error_details = traceback.format_exc()
        print(f"{request.data_source} datasource load failed: {exc}")
        print(f"Full traceback:\n{error_details}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to load data from {request.data_source}: {str(exc)}"
        )


@app.post("/optimize", response_model=OptimizationResponse)
async def optimize(request: OptimizationRequest) -> OptimizationResponse:
    """Run NSGA-III optimization and return Pareto scenarios."""
    # Create optimizer with settings from request
    if request.optimizer_settings.optimizer_type == 'elasticity':
        optimizer = NSGA3OptimizerElasticity(request.optimizer_settings)
    elif request.optimizer_settings.optimizer_type == 'agent':
        optimizer = NSGA3OptimizerAgentBased(request.optimizer_settings)
    else:
        raise HTTPException(status_code=400, detail="Invalid optimizer type specified")
    
    scenarios = optimizer.optimize(request.city)
    return OptimizationResponse(scenarios=scenarios)


@app.post("/select_best_solution_by_weight", response_model=WeightSelectionResponse)
async def select_best_solution_by_weight(request: WeightSelectionRequest) -> WeightSelectionResponse:
    """Select the best scenario using user weights."""
    return WeightSelectionResponse(scenario=SolutionSelector.select_best_by_weights(request.scenarios, request.weights))


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