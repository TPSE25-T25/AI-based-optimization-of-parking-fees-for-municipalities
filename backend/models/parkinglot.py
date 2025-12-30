"""
ParkingLot model for parking simulation
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Tuple
from decimal import Decimal


class ParkingLot(BaseModel):
    """
    ParkingLot model for parking simulation.
    Represents a parking facility with capacity and pricing information.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "CenterLot001",
                "price": "2.50",
                "position": [52.5170, 13.4003],
                "maximum_capacity": 150,
                "current_capacity": 10
            }
        }
    )
    
    # Unique identification
    id: int = Field(..., description="Unique parking lot identifier")
    pseudonym: str = Field(..., min_length=1, description="Parking lot's pseudonym for simulation")
    
    # Pricing
    price: Decimal = Field(..., ge=0, description="Hourly parking price")
    
    # Location data (latitude, longitude)
    position: Tuple[float, float] = Field(..., description="Parking lot position (latitude, longitude)")
    
    # Capacity management
    maximum_capacity: int = Field(..., gt=0, description="Maximum number of parking spots")
    current_capacity: int = Field(..., ge=0, description="Currently occupied parking spots")
    
    @model_validator(mode='after')
    def current_capacity_not_exceed_maximum(self):
        """Validate that current capacity doesn't exceed maximum capacity."""
        if self.current_capacity > self.maximum_capacity:
            raise ValueError('Current capacity cannot exceed maximum capacity')
        return self
    
    def available_spots(self) -> int:
        """Calculate number of available parking spots."""
        return self.maximum_capacity - self.current_capacity
    
    def occupancy_rate(self) -> float:
        """Calculate occupancy rate as a percentage (0.0 to 1.0)."""
        return self.current_capacity / self.maximum_capacity
    
    def is_full(self) -> bool:
        """Check if parking lot is at full capacity."""
        return self.current_capacity >= self.maximum_capacity
    
    def can_accommodate(self, spots_needed: int = 1) -> bool:
        """Check if parking lot can accommodate the requested number of spots."""
        return self.available_spots() >= spots_needed
    
    def distance_to_point(self, point: Tuple[float, float]) -> float:
        """
        Calculate approximate euclidean distance to a given point.
        Uses simple Euclidean distance (suitable for simulation heuristics).
        """
        lat_diff = point[0] - self.position[0]
        lon_diff = point[1] - self.position[1]
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5