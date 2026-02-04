from pydantic import BaseModel, Field
from typing import List
from backend.models.city import ParkingZone

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
    zones: List[ParkingZone]               # A List of all zones to be optimized simultaneously 
    settings: OptimizationSettings              # the NSGA-III algorithm settings

#  OUTPUT SCHEMAS (Data sent back to Frontend) 

class OptimizedZoneResult(BaseModel):
    """
    The result for a single zone (part of a scenario).
    """
    id: int
    new_fee: float
    predicted_occupancy: float # New estimated occupancy
    predicted_revenue: float   # New estimated revenue

class PricingScenario(BaseModel):
    """
    A solution on the Pareto Front. Contains current_fees for ALL zones.
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

class WeightSelectionRequest(BaseModel):
    """
    Request for selecting the best solution from optimization results based on user preferences.
    """
    optimization_response: OptimizationResponse
    weights: dict = Field(..., description="Weights for each objective (revenue, occupancy, drop, fairness)")