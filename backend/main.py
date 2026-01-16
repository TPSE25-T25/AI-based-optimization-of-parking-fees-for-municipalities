from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from schemas.optimization import ParkingZoneInput, OptimizationSettings, OptimizationRequest, OptimizationResponse
from services.nsga3_optimizer import NSGA3Optimizer


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
    current_fee: float
    occupancy_rate: float
    suggested_fee: float

class FeeOptimizationRequest(BaseModel):
    zone_id: int
    target_occupancy: float

# Sample data
parking_zones = [
    ParkingZone(id=1, name="Downtown", current_fee=2.5, occupancy_rate=0.85, suggested_fee=3.0),
    ParkingZone(id=2, name="Shopping District", current_fee=1.5, occupancy_rate=0.95, suggested_fee=2.0),
    ParkingZone(id=3, name="Residential", current_fee=1.0, occupancy_rate=0.60, suggested_fee=0.8),
]

@app.get("/")
async def root():
    return {"message": "Parking Fee Optimization API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/zones", response_model=List[ParkingZone])
async def get_parking_zones():
    """Get all parking zones with current fees and optimization suggestions"""
    return parking_zones

@app.get("/zones/{zone_id}", response_model=ParkingZone)
async def get_parking_zone(zone_id: int):
    """Get a specific parking zone by ID"""
    for zone in parking_zones:
        if zone.id == zone_id:
            return zone
    return {"error": "Zone not found"}

@app.post("/optimize", response_model=OptimizationResponse)
async def optimize_fee(request: OptimizationRequest):
    """
    Endpoint to execute the NSGA-III optimization algorithm.
    """
    #Create an instance of the NSGA3Optimizer
    optimizer = NSGA3Optimizer()
    
    #Call the optimize method and return the result
    return optimizer.optimize(request)





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)