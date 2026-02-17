# Defines the configuration parameters for the NSGA-III algorithm.
from pydantic import BaseModel, Field
from typing import Literal


class OptimizationSettings(BaseModel):
    """
    Settings for the NSGA-III algorithm itself.
    """
    optimizer_type: Literal["elasticity"] = "elasticity"
    random_seed: int = Field(default=1, description="Seed for reproducibility")    
    population_size: int = Field(default=200, ge=10, description="Number of solutions per generation")
    generations: int = Field(default=50, ge=1, description="Number of generations (iterations)")
    target_occupancy: float = Field(default=0.85, ge=0, le=1.0, description="Desired target occupancy rate")
    min_fee : float = Field(default=0.0, ge=0, description="Minimum allowable parking fee")
    max_fee : float = Field(default=10.0, ge=0, description="Maximum allowable parking fee")
    fee_increment: float = Field(default=0.25, gt=0, description="Increment step for parking fee adjustments")


class AgentBasedSettings(OptimizationSettings):
    """
    Extended configuration for agent-based simulation optimizers.
    Inherits from the base Configuration and adds specific parameters.
    """
    optimizer_type: Literal["agent"] = "agent"
    drivers_per_zone_capacity: float = Field(default=2.0, gt=0, description="Multiplier for driver generation (e.g., 2.0 = 200% of capacity)")
    simulation_runs: int = Field(default=3, ge=1, description="Number of simulation runs per evaluation for averaging")
    
    # Driver Decision Weights
    driver_fee_weight: float = Field(default=1.5, ge=0, description="Driver's fee sensitivity weight")
    driver_distance_to_lot_weight: float = Field(default=0.8, ge=0, description="Driver's driving distance sensitivity")
    driver_walking_distance_weight: float = Field(default=2.0, ge=0, description="Driver's walking distance sensitivity")
    driver_availability_weight: float = Field(default=0.5, ge=0, description="Driver's lot availability sensitivity")
