from pydantic import BaseModel, Field
from typing import List

#  INPUT SCHEMAS (Data coming from Frontend) 

# This class defines the input schema for a single parking zone.
# It validates the raw data received from the city before optimization. (capacity, current fee, occupancy, constraints, user behavior)
# logical constraints (e.g., no negative prices) rquired by the NSGA-III algorithm.

class ParkingZoneInput(BaseModel):
    """
    Describes a single parking zone to be optimized.
    Validates input data and constraints before simulation.
    """
    zone_id: int = Field(..., description="Unique ID of the zone")
    name: str = Field(..., description="Name of the zone, e.g., 'Station'")
    
    # syntax: '...' means required field, 'gt=0' means Greater Than 0
    capacity: int = Field(..., gt=0, description="Total number of parking spots")
    
    # Current Status (Crucial for Before/After comparison)
    current_fee: float = Field(..., ge=0, description="Current hourly fee")
    current_occupancy: float = Field(..., ge=0, le=1.0, description="Current occupancy rate (0.0 - 1.0)")
    
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
    The result for a single zone (part of a scenario).
    """
    zone_id: int
    new_fee: float
    predicted_occupancy: float # New estimated occupancy
    predicted_revenue: float   # New estimated revenue

class PricingScenario(BaseModel):
    """
    A solution on the Pareto Front. Contains prices for ALL zones.
    Each scenario is a compromise between the 4 objectives.
    """
    scenario_id: int
    zones: List[OptimizedZoneResult]
    
    #The 4 objective values calculated by NSGA-III
    score_revenue: float        # f1: Revenue (maximize)
    score_occupancy_gap: float  # f2: Avoid overload/vacancy (minimize)
    score_demand_drop: float    # f3: Demand drop (minimize)
    score_user_balance: float   # f4: User group balance (maximize)
    
class OptimizationResponse(BaseModel):
    """
    The API response: A list of optimal scenarios (Pareto Front).
    """
    scenarios: List[PricingScenario]