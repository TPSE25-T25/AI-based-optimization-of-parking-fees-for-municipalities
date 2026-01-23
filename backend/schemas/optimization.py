from pydantic import BaseModel, Field
from typing import List, Optional

#  INPUT SCHEMAS (Data coming from Frontend) 

# This class defines the input schema for a single parking zone.
# It validates the raw data received from the city before optimization. (capacity, current fee, occupancy, constraints, user behavior)
# logical constraints (e.g., no negative prices) rquired by the NSGA-III algorithm.

class ParkingZoneInput(BaseModel):
    """
    Describes a single parking zone to be optimized.
    """
    zone_id: int = Field(..., description="Unique ID of the zone")
    # Das Cluster-Feld (wird automatisch befüllt)
    cluster_group_id: int = Field(default=0, description="Zones with same ID get same price.")
    
    name: str = Field(..., description="Name of the zone")
    
    
    lat: float = Field(default=0.0, description="Latitude")
    lon: float = Field(default=0.0, description="Longitude")
    
    capacity: int = Field(..., gt=0, description="Total number of parking spots")
    current_fee: float = Field(..., ge=0, description="Current hourly fee")
    current_occupancy: float = Field(..., ge=0, le=1.0, description="Current occupancy rate")
    min_fee: float = Field(..., ge=0, description="Legal minimum fee")
    max_fee: float = Field(..., description="Legal maximum fee")
    elasticity: float = Field(default=-0.5, le=0, description="Price elasticity")
    short_term_share: float = Field(default=0.5, ge=0, le=1.0, description="Share of short-term parkers")

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