from pydantic import BaseModel, Field
from typing import List
from backend.models.city import ParkingZone

#  INPUT SCHEMAS (Data coming from Frontend)

# This class defines the input schema for a single parking zone.
# It validates the raw data received from the city before optimization. (capacity, current fee, occupancy, constraints, user behavior)
# logical constraints (e.g., no negative prices) rquired by the NSGA-III algorithm.

class ParkingZoneInput(ParkingZone):
    """
    Describes a single parking zone to be optimized.
    Inherits from ParkingZone and adds optimization-specific constraints and behavior parameters.

    Inherited fields from ParkingZone:
    - id: Unique parking lot identifier
    - pseudonym: Parking lot name
    - price: Current hourly parking price
    - position: Parking lot position (latitude, longitude)
    - maximum_capacity: Total number of parking spots
    - current_capacity: Currently occupied parking spots
    """

    # [cite_start]Rules (Hard Constraints) [cite: 175]
    min_fee: float = Field(..., ge=0, description="Legal minimum fee")
    max_fee: float = Field(..., description="Legal maximum fee")

    # Simulation Data: How do users behave?
    # Important for Objective 3: Demand drop
    # syntax: 'le=0' (Less or Equal 0) because elasticity is usually negative
    elasticity: float = Field(default=-0.5, le=0, description="Price elasticity (How strongly does demand drop with price increase?)")

    # [cite_start]Important for Objective 4: User groups [cite: 167, 173]
    # syntax: 'ge=0' and 'le=1.0' ensures a valid percentage between 0% and 100%
    short_term_share: float = Field(default=0.5, ge=0, le=1.0, description="Share of short-term parkers (0.0 - 1.0)")

# Defines the configuration parameters for the NSGA-III algorithm.
class OptimizationSettings(BaseModel):
    """
    Settings for the NSGA-III algorithm itself.
    """
    population_size: int = Field(default=200, ge=10, description="Number of solutions per generation")
    generations: int = Field(default=50, ge=1, description="Number of generations (iterations)")
    target_occupancy: float = Field(default=0.85, ge=0, le=1.0, description="Desired target occupancy") # for Objective 2   # Avoid overload/vacancy -> 85% occupancy is ideal

class OptimizationRequest(BaseModel):
    """
    The complete payload sent to the API for optimization.
    It acts as a container building the "what" (zones) and the "how" (settings).
    """
    zones: List[ParkingZoneInput]               # A List of all zones to be optimized simultaneously
    settings: OptimizationSettings              # the NSGA-III algorithm settings

#  OUTPUT SCHEMAS (Data sent back to Frontend)

class OptimizedZoneResult(BaseModel):
    """
    Result for a single parking zone after optimization.
    Contains both old and new values for comparison.
    """
    zone_id: int
    new_fee: float                    # Optimized price determined by NSGA-III
    predicted_occupancy: float        # Expected utilization rate under the new price
    predicted_revenue: float          # Expected revenue (fee * occupied spots)

class PricingScenario(BaseModel):
    """
    One complete Pareto-optimal solution from NSGA-III.
    Represents one point on the Pareto Front with its zone-specific fee recommendations.
    """
    scenario_id: int                                    # Internal ID (1, 2, 3, ...)
    zones: List[OptimizedZoneResult]                    # Per-zone results (fees + predictions)

    # Objective function scores (for decision support / dashboard visualization)
    score_revenue: float                                # f1: Total city revenue
    score_occupancy_gap: float                          # f2: Deviation from target occupancy (85%)
    score_demand_drop: float                            # f3: How much demand was lost?
    score_user_balance: float                           # f4: Fairness metric

class OptimizationResponse(BaseModel):
    """
    The full response returned by the optimization API.
    Contains all Pareto-optimal scenarios for decision-making.
    """
    scenarios: List[PricingScenario]                    # Usually 9-15 optimal scenarios
    computation_time_seconds: float                     # How long did the algorithm run?
