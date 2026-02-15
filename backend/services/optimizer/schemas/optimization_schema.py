from pydantic import BaseModel, Field
from typing import List, Union
from backend.services.models.city import City, ParkingZone
from backend.services.settings.optimizations_settings import OptimizationSettings, AgentBasedSettings
from backend.services.settings.data_source_settings import DataSourceSettings

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
    
