from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from services.data.osmnx_loader import OSMnxParkingLoader

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

# Cache for loaded Karlsruhe parking zones
parking_zones: List[ParkingZone] = []

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
        # Load real parking areas from OSM (amenity=parking)
        loader = OSMnxParkingLoader(
            place_name="Karlsruhe, Germany",
            center_coords=(49.0069, 8.4037)
        )
        raw_zones = loader.load_zones(limit=60)

        parking_zones = [
            ParkingZone(
                id=z.zone_id,
                name=z.name,
                current_fee=getattr(z, "current_fee", None),
                occupancy_rate=getattr(z, "current_occupancy", None),
                suggested_fee=None,  # synthetic / to be generated
                lat=z.lat,
                lon=z.lon,
                capacity=getattr(z, "capacity", None),
                is_placeholder=False
            )
            for z in raw_zones
        ]
        if not parking_zones:
            raise HTTPException(status_code=502, detail="OSM returned no parking data for Karlsruhe")

    except Exception as exc:
        print(f"OSM load failed: {exc}")
        raise HTTPException(status_code=502, detail="OSM load failed for Karlsruhe")

    return parking_zones

@app.get("/zones/{zone_id}", response_model=ParkingZone)
async def get_parking_zone(zone_id: int):
    """Get a specific parking zone by ID"""
    for zone in parking_zones:
        if zone.id == zone_id:
            return zone
    return {"error": "Zone not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)