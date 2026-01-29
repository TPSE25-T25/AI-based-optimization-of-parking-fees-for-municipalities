from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ✅ Admin router
from backend.services.admin.api import router as admin_router

# ✅ Admin config access for other modules
from backend.services.admin.config_repository import ConfigRepository
from backend.services.admin.config_service import ConfigService
from backend.services.io.file_manager import FileManager

# ✅ Optimization schemas (you created backend/models/optimization_schemas.py)
from backend.models.optimization_schemas import (
    OptimizationRequest,
    OptimizationResponse,
    PricingScenario,
    OptimizedZoneResult,
)

# ----------------------------------------
# FastAPI app MUST be defined before routes
# ----------------------------------------
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

# Register admin endpoints (e.g. /admin/config)
app.include_router(admin_router)

# ----------------------------------------
# Admin config service (used by optimize endpoints)
# ----------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]  # repo_root/backend/main.py -> parents[1] = repo_root
ADMIN_CONFIG_PATH = REPO_ROOT / "backend" / "data" / "config" / "admin_config.json"
_admin_service = ConfigService(ConfigRepository(FileManager(), config_path=str(ADMIN_CONFIG_PATH)))


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


# -----------------------
# Basic endpoints
# -----------------------
@app.get("/")
async def root():
    return {"message": "Parking Fee Optimization API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/zones", response_model=List[ParkingZone])
async def get_parking_zones():
    return parking_zones


@app.get("/zones/{zone_id}", response_model=ParkingZone)
async def get_parking_zone(zone_id: int):
    for zone in parking_zones:
        if zone.id == zone_id:
            return zone
    raise HTTPException(status_code=404, detail="Zone not found")


# -----------------------
# Demo optimize endpoint (kept)
# -----------------------
@app.post("/optimize")
async def optimize_fee(request: FeeOptimizationRequest):
    """
    Simple demo optimization endpoint (old).
    """
    for zone in parking_zones:
        if zone.id == request.zone_id:
            current_occupancy = zone.occupancy_rate
            target = request.target_occupancy

            if target <= 0:
                raise HTTPException(status_code=400, detail="target_occupancy must be > 0")

            if current_occupancy > target:
                optimized_fee = zone.current_fee * (current_occupancy / target)
            else:
                optimized_fee = zone.current_fee / (target / max(current_occupancy, 1e-9))

            zone.suggested_fee = round(float(optimized_fee), 2)

            return {
                "zone_id": zone.id,
                "current_fee": zone.current_fee,
                "suggested_fee": zone.suggested_fee,
                "current_occupancy": current_occupancy,
                "target_occupancy": target,
                "message": f"Fee optimization completed for {zone.name}",
            }

    raise HTTPException(status_code=404, detail="Zone not found")


# -----------------------
# Real-ish optimize endpoint using your schemas + Admin config
# -----------------------
@app.post("/optimize/nsga", response_model=OptimizationResponse)
async def optimize_nsga(req: OptimizationRequest) -> OptimizationResponse:
    """
    Prototype optimization endpoint:
    - Load AdminConfig (saved via /admin/config)
    - Apply admin constraints (min/max per zone)
    - Return a placeholder scenario (later replace with NSGA-III)
    """
    cfg = _admin_service.get_active_config()
    if cfg is None:
        raise HTTPException(status_code=400, detail="No active admin config set. Please PUT /admin/config first.")

    # Build quick lookup: zone_id(str) -> rule
    rules_by_zone = {r.zone_id: r for r in cfg.price_rules}

    results: list[OptimizedZoneResult] = []

    for z in req.zones:
        rule = rules_by_zone.get(str(z.zone_id))

        # Apply admin min/max if rule exists; otherwise use what came in
        min_fee = float(rule.min_price_eur_per_hour) if rule else float(z.min_fee)
        max_fee = float(rule.max_price_eur_per_hour) if rule else float(z.max_fee)

        target = float(req.settings.target_occupancy)
        current_fee = float(z.current_fee)
        occ = float(z.current_occupancy)

        # placeholder optimization
        if occ > target:
            new_fee = current_fee * (occ / max(target, 1e-9))
        else:
            new_fee = current_fee / (target / max(occ, 1e-9))

        # clamp to legal min/max
        new_fee = max(min_fee, min(max_fee, new_fee))
        new_fee = round(float(new_fee), 2)

        # predict occupancy with elasticity (prototype)
        if current_fee <= 0:
            predicted_occ = occ
        else:
            demand_mult = (new_fee / current_fee) ** float(z.elasticity)
            predicted_occ = max(0.0, min(1.0, occ * demand_mult))

        predicted_occ = round(float(predicted_occ), 3)

        # revenue estimate (prototype)
        predicted_revenue = round(predicted_occ * float(z.capacity) * new_fee, 2)

        results.append(
            OptimizedZoneResult(
                zone_id=z.zone_id,
                new_fee=new_fee,
                predicted_occupancy=predicted_occ,
                predicted_revenue=predicted_revenue,
            )
        )

    scenario = PricingScenario(
        scenario_id=1,
        zones=results,
        score_revenue=sum(r.predicted_revenue for r in results),
        score_occupancy_gap=sum(abs(r.predicted_occupancy - req.settings.target_occupancy) for r in results),
        score_demand_drop=0.0,
        score_user_balance=0.0,
    )

    return OptimizationResponse(scenarios=[scenario])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
