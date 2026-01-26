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
                "from_parking_zone_id": 1,
                "to_parking_zone_id": 2,
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
    from_parking_zone_id: Optional[int] = Field(None, description="Starting parking lot ID (if applicable)")
    to_parking_zone_id: Optional[int] = Field(None, description="Ending parking lot ID (if applicable)")
    
    # Street characteristics - Cost of traversal
    speed_limit: float = Field(..., gt=0, description="Maximum travel speed (km/h or arbitrary units)")
    
    def length(self) -> float:
        """Calculate the euclidean length between from_position and to_position."""
        lat_diff = self.to_position[0] - self.from_position[0]
        lon_diff = self.to_position[1] - self.from_position[1]
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5
    
    def travel_cost(self) -> float:
        """Calculate travel cost as length divided by speed limit."""
        return self.length() / self.speed_limit


class ParkingZone(BaseModel):
    """
    ParkingZone model for parking simulation.
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
    City model representing a real geographic area.
    Contains parking lots, streets, and points of interest for driver navigation.
    Uses real latitude/longitude coordinates.
    """

    # Unique identification
    id: int = Field(..., description="Unique city identifier")
    pseudonym: str = Field(..., min_length=1, description="City's pseudonym for simulation")

    # Geographic bounds (bounding box)
    min_latitude: float = Field(..., ge=-90, le=90, description="Minimum latitude of city bounds")
    max_latitude: float = Field(..., ge=-90, le=90, description="Maximum latitude of city bounds")
    min_longitude: float = Field(..., ge=-180, le=180, description="Minimum longitude of city bounds")
    max_longitude: float = Field(..., ge=-180, le=180, description="Maximum longitude of city bounds")

    # City components
    parking_zones: List[ParkingZone] = Field(default_factory=list, description="List of parking lots in the city")
    point_of_interests: List[PointOfInterest] = Field(
        default_factory=list,
        description="List of points of interest in the city"
    )
    streets: List[Street] = Field(default_factory=list, description="List of streets connecting locations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "pseudonym": "Berlin_Mitte",
                "min_latitude": 52.5000,
                "max_latitude": 52.5300,
                "min_longitude": 13.3800,
                "max_longitude": 13.4200,
                "parking_zones": [
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
                        "from_parking_zone_id": None,
                        "to_parking_zone_id": 1,
                        "speed_limit": 50.0
                    }
                ]
            }
        }
    )

    @model_validator(mode='after')
    def validate_bounds(self):
        """Validate that geographic bounds are consistent."""
        if self.min_latitude >= self.max_latitude:
            raise ValueError('min_latitude must be less than max_latitude')
        if self.min_longitude >= self.max_longitude:
            raise ValueError('min_longitude must be less than max_longitude')
        return self

    @model_validator(mode='after')
    def validate_positions(self):
        """Validate that all parking lots and POIs are within geographic bounds."""
        # Validate parking lot positions
        for lot in self.parking_zones:
            lat, lon = lot.position
            if not (self.min_latitude <= lat <= self.max_latitude):
                raise ValueError(
                    f'Parking lot {lot.id} latitude {lat} is outside city bounds '
                    f'[{self.min_latitude}, {self.max_latitude}]'
                )
            if not (self.min_longitude <= lon <= self.max_longitude):
                raise ValueError(
                    f'Parking lot {lot.id} longitude {lon} is outside city bounds '
                    f'[{self.min_longitude}, {self.max_longitude}]'
                )

        # Validate point of interest positions
        for poi in self.point_of_interests:
            lat, lon = poi.position
            if not (self.min_latitude <= lat <= self.max_latitude):
                raise ValueError(
                    f'Point of interest {poi.id} latitude {lat} is outside city bounds '
                    f'[{self.min_latitude}, {self.max_latitude}]'
                )
            if not (self.min_longitude <= lon <= self.max_longitude):
                raise ValueError(
                    f'Point of interest {poi.id} longitude {lon} is outside city bounds '
                    f'[{self.min_longitude}, {self.max_longitude}]'
                )

        return self
    
    def get_parking_zone_by_id(self, lot_id: int) -> Optional[ParkingZone]:
        """Find parking lot by ID."""
        for lot in self.parking_zones:
            if lot.id == lot_id:
                return lot
        return None
    
    def add_parking_zone(self, parking_zone: ParkingZone) -> None:
        """Add a parking lot to the city."""
        # Validate position is within geographic bounds
        lat, lon = parking_zone.position
        if not (self.min_latitude <= lat <= self.max_latitude):
            raise ValueError(
                f'Parking lot latitude {lat} is outside city bounds '
                f'[{self.min_latitude}, {self.max_latitude}]'
            )
        if not (self.min_longitude <= lon <= self.max_longitude):
            raise ValueError(
                f'Parking lot longitude {lon} is outside city bounds '
                f'[{self.min_longitude}, {self.max_longitude}]'
            )

        # Check for duplicate IDs
        if any(lot.id == parking_zone.id for lot in self.parking_zones):
            raise ValueError(f'Parking lot with ID {parking_zone.id} already exists')

        self.parking_zones.append(parking_zone)

    def add_point_of_interest(self, point_of_interest: PointOfInterest) -> None:
        """Add a point of interest to the city."""
        lat, lon = point_of_interest.position
        if not (self.min_latitude <= lat <= self.max_latitude):
            raise ValueError(
                f'Point of interest latitude {lat} is outside city bounds '
                f'[{self.min_latitude}, {self.max_latitude}]'
            )
        if not (self.min_longitude <= lon <= self.max_longitude):
            raise ValueError(
                f'Point of interest longitude {lon} is outside city bounds '
                f'[{self.min_longitude}, {self.max_longitude}]'
            )

        # Check for duplicate IDs
        if any(poi.id == point_of_interest.id for poi in self.point_of_interests):
            raise ValueError(f'Point of interest with ID {point_of_interest.id} already exists')

        self.point_of_interests.append(point_of_interest)

    def add_street(self, street: Street) -> None:
        """Add a street to the city."""
        # Validate positions are within geographic bounds
        for pos_name, pos in [('from', street.from_position), ('to', street.to_position)]:
            lat, lon = pos
            if not (self.min_latitude <= lat <= self.max_latitude):
                raise ValueError(
                    f'Street {pos_name}_position latitude {lat} is outside city bounds '
                    f'[{self.min_latitude}, {self.max_latitude}]'
                )
            if not (self.min_longitude <= lon <= self.max_longitude):
                raise ValueError(
                    f'Street {pos_name}_position longitude {lon} is outside city bounds '
                    f'[{self.min_longitude}, {self.max_longitude}]'
                )

        # Check for duplicate IDs
        if any(s.id == street.id for s in self.streets):
            raise ValueError(f'Street with ID {street.id} already exists')

        self.streets.append(street)
    
    def total_parking_capacity(self) -> int:
        """Calculate total parking capacity across all lots."""
        return sum(lot.maximum_capacity for lot in self.parking_zones)
    
    def total_occupied_spots(self) -> int:
        """Calculate total occupied spots across all lots."""
        return sum(lot.current_capacity for lot in self.parking_zones)
    
    def total_available_spots(self) -> int:
        """Calculate total available spots across all lots."""
        return sum(lot.available_spots() for lot in self.parking_zones)
    
    def city_occupancy_rate(self) -> float:
        """Calculate overall city occupancy rate."""
        total_capacity = self.total_parking_capacity()
        if total_capacity == 0:
            return 0.0
        return self.total_occupied_spots() / total_capacity
    
    def find_nearest_parking_zone(self, position: Tuple[float, float]) -> Optional[ParkingZone]:
        """Find the nearest parking lot to a given position."""
        if not self.parking_zones:
            return None
        
        min_distance = float('inf')
        nearest_lot = None
        
        for lot in self.parking_zones:
            distance = lot.distance_to_point(position)
            if distance < min_distance:
                min_distance = distance
                nearest_lot = lot
        
        return nearest_lot
    
    def find_available_parking_zones(self) -> List[ParkingZone]:
        """Find all parking lots with available spots."""
        return [lot for lot in self.parking_zones if not lot.is_full()]
    
    def get_streets_from_parking_zone(self, lot_id: int) -> List[Street]:
        """Get all streets that start from a specific parking lot."""
        return [street for street in self.streets if street.from_parking_zone_id == lot_id]
    
    def get_streets_to_parking_zone(self, lot_id: int) -> List[Street]:
        """Get all streets that lead to a specific parking lot."""
        return [street for street in self.streets if street.to_parking_zone_id == lot_id]

