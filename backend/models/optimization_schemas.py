from pydantic import BaseModel, Field
from typing import List


# -------------------------
# INPUT SCHEMAS
# -------------------------

class ParkingZoneInput(BaseModel):
    """
    Describes a single parking zone to be optimized.
    Validates input data and constraints before simulation.
    """
    zone_id: int = Field(..., description="Unique ID of the zone")
    name: str = Field(..., description="Name of the zone, e.g., 'Station'")

    capacity: int = Field(..., gt=0, description="Total number of parking spots")

    current_fee: float = Field(..., ge=0, description="Current hourly fee")
    current_occupancy: float = Field(..., ge=0, le=1.0, description="Current occupancy rate (0.0 - 1.0)")

    min_fee: float = Field(..., ge=0, description="Legal minimum fee")
    max_fee: float = Field(..., ge=0, description="Legal maximum fee")

    elasticity: float = Field(default=-0.5, le=0, description="Price elasticity (usually negative)")
    short_term_share: float = Field(default=0.5, ge=0, le=1.0, description="Share of short-term parkers (0.0 - 1.0)")


class OptimizationSettings(BaseModel):
    """
    Settings for the NSGA-III algorithm itself.
    """
    population_size: int = Field(default=100, ge=10, description="Number of solutions per generation")
    generations: int = Field(default=50, ge=1, description="Number of generations (iterations)")
    target_occupancy: float = Field(default=0.85, ge=0, le=1.0, description="Desired target occupancy")


class OptimizationRequest(BaseModel):
    """
    Payload sent to the API for optimization.
    """
    zones: List[ParkingZoneInput]
    settings: OptimizationSettings


# -------------------------
# OUTPUT SCHEMAS
# -------------------------

class OptimizedZoneResult(BaseModel):
    """
    Result for a single zone (part of a scenario).
    """
    zone_id: int
    new_fee: float
    predicted_occupancy: float
    predicted_revenue: float


class PricingScenario(BaseModel):
    """
    One solution on the Pareto Front. Contains prices for ALL zones.
    """
    scenario_id: int
    zones: List[OptimizedZoneResult]

    score_revenue: float
    score_occupancy_gap: float
    score_demand_drop: float
    score_user_balance: float


class OptimizationResponse(BaseModel):
    """
    API response: list of optimal scenarios (Pareto Front).
    """
    scenarios: List[PricingScenario]
