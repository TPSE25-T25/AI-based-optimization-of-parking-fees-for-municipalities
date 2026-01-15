from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ✅ Admin router (make sure backend/services/admin/api.py defines `router`)
from backend.services.admin.api import router as admin_router

app = FastAPI(
    title="Parking Fee Optimization API",
    version="1.0.0",
    description="API for parking fee optimization",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register admin endpoints (e.g. /admin/config)
app.include_router(admin_router)


# -----------------------
# Pydantic models (demo)
# -----------------------
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
    # ✅ response_model expects ParkingZone; raise proper 404
    raise HTTPException(status_code=404, detail="Zone not found")


@app.post("/optimize")
async def optimize_fee(request: FeeOptimizationRequest):
    """Optimize parking fee for a specific zone based on target occupancy"""
    for zone in parking_zones:
        if zone.id == request.zone_id:
            current_occupancy = zone.occupancy_rate
            target = request.target_occupancy

            if target <= 0:
                raise HTTPException(status_code=400, detail="target_occupancy must be > 0")

            # Simple optimization algorithm (demo)
            if current_occupancy > target:
                optimization_factor = current_occupancy / target
                optimized_fee = zone.current_fee * optimization_factor
            else:
                optimization_factor = target / max(current_occupancy, 1e-9)
                optimized_fee = zone.current_fee / optimization_factor

            zone.suggested_fee = round(optimized_fee, 2)

            return {
                "zone_id": zone.id,
                "current_fee": zone.current_fee,
                "suggested_fee": zone.suggested_fee,
                "current_occupancy": current_occupancy,
                "target_occupancy": target,
                "message": f"Fee optimization completed for {zone.name}",
            }

    raise HTTPException(status_code=404, detail="Zone not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
