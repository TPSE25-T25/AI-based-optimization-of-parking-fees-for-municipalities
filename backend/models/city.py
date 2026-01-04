"""
City and Street models for parking simulation
"""

from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Tuple, Optional


class PointOfInterest(BaseModel):
    """
    Point of Interest model representing important locations in the city.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "CityHall",
                "position": [52.5200, 13.4050]
            }
        }
    )
    
    # Unique identification
    id: int = Field(..., description="Unique point of interest identifier")
    pseudonym: str = Field(..., min_length=1, description="Point of interest's pseudonym for simulation")
    
    # Location
    position: Tuple[float, float] = Field(..., description="Position (latitude, longitude)")
    
    def distance_to_point(self, point: Tuple[float, float]) -> float:
        """
        Calculate approximate euclidean distance to a given point.
        Uses simple Euclidean distance (suitable for simulation heuristics).
        """
        lat_diff = point[0] - self.position[0]
        lon_diff = point[1] - self.position[1]
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5


class Street(BaseModel):
    """
    Street model representing a connection between parking lots.
    Defines the cost/distance of driving between two points.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "MainStreet_A_B",
                "from_position": [100.0, 200.0],
                "to_position": [300.0, 450.0],
                "from_parking_lot_id": 1,
                "to_parking_lot_id": 2,
                "speed_limit": 2.0
            }
        }
    )
    
    # Connection identification
    id: int = Field(..., description="Unique street identifier")
    pseudonym: str = Field(..., min_length=1, description="Street's pseudonym for simulation")
    
    # Connection points
    from_position: Tuple[float, float] = Field(..., description="Starting position (latitude, longitude)")
    to_position: Tuple[float, float] = Field(..., description="Ending position (latitude, longitude)")
    
    # Optional parking lot connections
    from_parking_lot_id: Optional[int] = Field(None, description="Starting parking lot ID (if applicable)")
    to_parking_lot_id: Optional[int] = Field(None, description="Ending parking lot ID (if applicable)")
    
    # Street characteristics
    speed_limit: float = Field(..., gt=0, description="Maximum travel speed in pixels per unit time")
    
    def length(self) -> float:
        """Calculate the euclidean length between from_position and to_position."""
        lat_diff = self.to_position[0] - self.from_position[0]
        lon_diff = self.to_position[1] - self.from_position[1]
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5
    
    def travel_cost(self) -> float:
        """Calculate travel cost as length divided by speed limit."""
        return self.length() / self.speed_limit


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
   

class City(BaseModel):
    """
    City model representing a 2D simulation environment.
    Contains parking lots, streets, and points of interest for driver navigation.
    """
    
    # Unique identification
    id: int = Field(..., description="Unique city identifier")
    pseudonym: str = Field(..., min_length=1, description="City's pseudonym for simulation")
    
    # Canvas/Map dimensions
    canvas: Tuple[float, float] = Field(..., description="Canvas size (width, height) in coordinate units")
    
    # City components
    parking_lots: List[ParkingLot] = Field(default_factory=list, description="List of parking lots in the city")
    point_of_interests: List[PointOfInterest] = Field(
        default_factory=list, 
        description="List of points of interest in the city"
    )
    streets: List[Street] = Field(default_factory=list, description="List of streets connecting locations")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "SimCity_Downtown",
                "canvas": [1000.0, 1000.0],
                "parking_lots": [
                    {
                        "id": 1,
                        "pseudonym": "CenterLot001",
                        "price": "2.50",
                        "position": [52.5170, 13.4003],
                        "maximum_capacity": 150,
                        "current_capacity": 75
                    }
                ],
                "point_of_interests": [
                    {
                        "id": 1,
                        "pseudonym": "CityHall",
                        "position": [52.5200, 13.4050]
                    },
                    {
                        "id": 2,
                        "pseudonym": "MainStation",
                        "position": [52.5180, 13.4020]
                    }
                ],
                "streets": [
                    {
                        "id": 1,
                        "pseudonym": "MainStreet_A_B",
                        "from_position": [52.5200, 13.4050],
                        "to_position": [52.5170, 13.4003],
                        "driving_cost": "0.50",
                        "distance": 500.0,
                        "travel_time": 2.5
                    }
                ]
            }
        }
    )
    
    @field_validator('canvas')
    @classmethod
    def canvas_positive_dimensions(cls, v):
        """Validate that canvas dimensions are positive."""
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError('Canvas dimensions must be positive')
        return v
    
    @model_validator(mode='after')
    def validate_positions(self):
        """Validate that all parking lots and POIs are within canvas bounds."""
        canvas_width, canvas_height = self.canvas
        
        # Validate parking lot positions
        for lot in self.parking_lots:
            lat, lon = lot.position
            if not (0 <= lat <= canvas_width and 0 <= lon <= canvas_height):
                raise ValueError(f'Parking lot {lot.id} position {lot.position} is outside canvas bounds')
        
        # Validate point of interest positions
        for poi in self.point_of_interests:
            lat, lon = poi.position
            if not (0 <= lat <= canvas_width and 0 <= lon <= canvas_height):
                raise ValueError(f'Point of interest {poi.id} at position {poi.position} is outside canvas bounds')
        
        return self
    
    def get_parking_lot_by_id(self, lot_id: int) -> Optional[ParkingLot]:
        """Find parking lot by ID."""
        for lot in self.parking_lots:
            if lot.id == lot_id:
                return lot
        return None
    
    def add_parking_lot(self, parking_lot: ParkingLot) -> None:
        """Add a parking lot to the city."""
        # Validate position is within canvas
        lat, lon = parking_lot.position
        if not (0 <= lat <= self.canvas[0] and 0 <= lon <= self.canvas[1]):
            raise ValueError(f'Parking lot position {parking_lot.position} is outside canvas bounds')
        
        # Check for duplicate IDs
        if any(lot.id == parking_lot.id for lot in self.parking_lots):
            raise ValueError(f'Parking lot with ID {parking_lot.id} already exists')
        
        self.parking_lots.append(parking_lot)
    
    def add_point_of_interest(self, point_of_interest: PointOfInterest) -> None:
        """Add a point of interest to the city."""
        lat, lon = point_of_interest.position
        if not (0 <= lat <= self.canvas[0] and 0 <= lon <= self.canvas[1]):
            raise ValueError(f'Point of interest position {point_of_interest.position} is outside canvas bounds')
        
        # Check for duplicate IDs
        if any(poi.id == point_of_interest.id for poi in self.point_of_interests):
            raise ValueError(f'Point of interest with ID {point_of_interest.id} already exists')
        
        self.point_of_interests.append(point_of_interest)
    
    def add_street(self, street: Street) -> None:
        """Add a street to the city."""
        # Validate positions are within canvas
        for pos in [street.from_position, street.to_position]:
            lat, lon = pos
            if not (0 <= lat <= self.canvas[0] and 0 <= lon <= self.canvas[1]):
                raise ValueError(f'Street position {pos} is outside canvas bounds')
        
        # Check for duplicate IDs
        if any(s.id == street.id for s in self.streets):
            raise ValueError(f'Street with ID {street.id} already exists')
        
        self.streets.append(street)
    
    def total_parking_capacity(self) -> int:
        """Calculate total parking capacity across all lots."""
        return sum(lot.maximum_capacity for lot in self.parking_lots)
    
    def total_occupied_spots(self) -> int:
        """Calculate total occupied spots across all lots."""
        return sum(lot.current_capacity for lot in self.parking_lots)
    
    def total_available_spots(self) -> int:
        """Calculate total available spots across all lots."""
        return sum(lot.available_spots() for lot in self.parking_lots)
    
    def city_occupancy_rate(self) -> float:
        """Calculate overall city occupancy rate."""
        total_capacity = self.total_parking_capacity()
        if total_capacity == 0:
            return 0.0
        return self.total_occupied_spots() / total_capacity
    
    def find_nearest_parking_lot(self, position: Tuple[float, float]) -> Optional[ParkingLot]:
        """Find the nearest parking lot to a given position."""
        if not self.parking_lots:
            return None
        
        min_distance = float('inf')
        nearest_lot = None
        
        for lot in self.parking_lots:
            distance = lot.distance_to_point(position)
            if distance < min_distance:
                min_distance = distance
                nearest_lot = lot
        
        return nearest_lot
    
    def find_available_parking_lots(self) -> List[ParkingLot]:
        """Find all parking lots with available spots."""
        return [lot for lot in self.parking_lots if not lot.is_full()]
    
    def get_streets_from_parking_lot(self, lot_id: int) -> List[Street]:
        """Get all streets that start from a specific parking lot."""
        return [street for street in self.streets if street.from_parking_lot_id == lot_id]
    
    def get_streets_to_parking_lot(self, lot_id: int) -> List[Street]:
        """Get all streets that lead to a specific parking lot."""
        return [street for street in self.streets if street.to_parking_lot_id == lot_id]

