"""
Driver model for parking simulation
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Tuple
from decimal import Decimal


class Driver(BaseModel):
    """
    Driver model for parking simulation.
    Represents an individual seeking parking with specific preferences and constraints.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "SimUser001",
                "max_parking_price": "5.00",
                "starting_position": [52.5200, 13.4050],
                "destination": [52.5170, 13.4003],
                "desired_parking_time": 120
            }
        }
    )
    
    # Unique identification
    id: int = Field(..., description="Unique driver identifier")
    pseudonym: str = Field(..., min_length=1, description="Driver's pseudonym for simulation")
    
    # Financial constraint
    max_parking_price: Decimal = Field(..., ge=0, description="Maximum price driver is willing to pay for parking (per hour)")
    
    # Location data (latitude, longitude)
    starting_position: Tuple[float, float] = Field(..., description="Starting position (latitude, longitude)")
    destination: Tuple[float, float] = Field(..., description="Destination coordinates (latitude, longitude)")
    
    # Time preference
    desired_parking_time: int = Field(..., gt=0, description="Desired parking duration in minutes")
    
    def distance_to_travel(self) -> float:
        """
        Calculate approximate euclydian distance between starting position and destination.
        Uses simple Euclidean distance (not precise for real-world use, but suitable for simulation heuristics).
        """
        lat_diff = self.destination[0] - self.starting_position[0]
        lon_diff = self.destination[1] - self.starting_position[1]
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5
    
    def hourly_budget(self) -> Decimal:
        """
        Calculate total budget based on desired parking time and max price per hour.
        """
        hours = Decimal(self.desired_parking_time) / Decimal(60)
        return self.max_parking_price * hours