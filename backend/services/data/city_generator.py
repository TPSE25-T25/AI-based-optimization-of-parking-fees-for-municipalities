"""
City and parking lot generation utilities for simulation testing.
"""

import random
import math
from typing import List, Tuple, Optional
from decimal import Decimal

from backend.models.city import City, PointOfInterest, Street, ParkingZone


class ParkingZoneGenerator:
    """
    Generates parking lots with various configurations.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize parking lot generator.
        
        Args:
            seed: Random seed for reproducibility (None for random)
        """
        if seed is not None:
            random.seed(seed)
    
    def generate_random_parking_zones(
        self,
        count: int,
        lat_range: Tuple[float, float],
        lon_range: Tuple[float, float],
        price_range: Tuple[Decimal, Decimal] = (Decimal('1.0'), Decimal('10.0')),
        capacity_range: Tuple[int, int] = (50, 300),
        initial_occupancy: float = 0.0
    ) -> List[ParkingZone]:
        """
        Generate random parking lots within geographic bounds.

        Args:
            count: Number of parking lots to generate
            lat_range: (min_lat, max_lat) latitude bounds
            lon_range: (min_lon, max_lon) longitude bounds
            price_range: (min, max) hourly parking price
            capacity_range: (min, max) parking capacity
            initial_occupancy: Initial occupancy rate (0.0 to 1.0)

        Returns:
            List of generated parking lots
        """
        lots = []

        for i in range(count):
            lat = random.uniform(lat_range[0], lat_range[1])
            lon = random.uniform(lon_range[0], lon_range[1])

            price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            max_capacity = random.randint(capacity_range[0], capacity_range[1])
            current_capacity = int(max_capacity * initial_occupancy)

            lot = ParkingZone(
                id=i + 1,
                pseudonym=f"ParkingZone_{i+1:03d}",
                price=price,
                position=(lat, lon),
                maximum_capacity=max_capacity,
                current_capacity=current_capacity
            )

            lots.append(lot)

        return lots
    
    def generate_clustered_parking_zones(
        self,
        count: int,
        cluster_centers: List[Tuple[float, float]],
        cluster_radius_deg: float = 0.01,
        lat_range: Optional[Tuple[float, float]] = None,
        lon_range: Optional[Tuple[float, float]] = None,
        price_range: Tuple[Decimal, Decimal] = (Decimal('2.0'), Decimal('8.0')),
        capacity_range: Tuple[int, int] = (50, 200)
    ) -> List[ParkingZone]:
        """
        Generate parking lots clustered around specific points.

        Args:
            count: Number of parking lots to generate
            cluster_centers: List of (lat, lon) positions to cluster around
            cluster_radius_deg: Maximum distance from cluster center in degrees
            lat_range: Optional (min_lat, max_lat) to clamp results
            lon_range: Optional (min_lon, max_lon) to clamp results
            price_range: (min, max) hourly parking price
            capacity_range: (min, max) parking capacity

        Returns:
            List of generated parking lots
        """
        if not cluster_centers:
            raise ValueError("Must provide at least one cluster center")

        lots = []

        for i in range(count):
            # Pick random cluster center
            center_lat, center_lon = random.choice(cluster_centers)

            # Generate position near cluster center
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, cluster_radius_deg)
            lat = center_lat + distance * math.cos(angle)
            lon = center_lon + distance * math.sin(angle)

            # Clamp to bounds if provided
            if lat_range:
                lat = max(lat_range[0], min(lat_range[1], lat))
            if lon_range:
                lon = max(lon_range[0], min(lon_range[1], lon))

            price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            max_capacity = random.randint(capacity_range[0], capacity_range[1])

            lot = ParkingZone(
                id=i + 1,
                pseudonym=f"ClusteredLot_{i+1:03d}",
                price=price,
                position=(lat, lon),
                maximum_capacity=max_capacity,
                current_capacity=0
            )

            lots.append(lot)

        return lots
    
    def generate_poi_based_parking_zones(
        self,
        pois: List[PointOfInterest],
        lots_per_poi: int = 2,
        distance_range_deg: Tuple[float, float] = (0.001, 0.005),
        price_variation: float = 0.3
    ) -> List[ParkingZone]:
        """
        Generate parking lots near points of interest with pricing based on proximity.

        Args:
            pois: List of points of interest
            lots_per_poi: Number of parking lots to generate per POI
            distance_range_deg: (min, max) distance from POI in degrees (~0.001 deg ≈ 100m)
            price_variation: Price variation factor (0.0 to 1.0)

        Returns:
            List of generated parking lots
        """
        if not pois:
            raise ValueError("Must provide at least one point of interest")

        lots = []
        lot_id = 1

        # Base prices for different POI types
        base_prices = {
            'downtown': Decimal('6.0'),
            'mall': Decimal('3.0'),
            'university': Decimal('2.5'),
            'hospital': Decimal('5.0'),
            'station': Decimal('4.0'),
            'default': Decimal('3.5')
        }

        for poi in pois:
            # Determine base price from POI name
            base_price = base_prices['default']
            for key in base_prices:
                if key.lower() in poi.pseudonym.lower():
                    base_price = base_prices[key]
                    break

            for j in range(lots_per_poi):
                # Generate position near POI (in degrees)
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.uniform(distance_range_deg[0], distance_range_deg[1])
                lat = poi.position[0] + distance * math.cos(angle)
                lon = poi.position[1] + distance * math.sin(angle)

                # Price varies based on distance (closer = more expensive)
                distance_factor = 1.0 - (distance - distance_range_deg[0]) / (distance_range_deg[1] - distance_range_deg[0])
                price_multiplier = 1.0 + (distance_factor * price_variation)
                price = base_price * Decimal(str(price_multiplier))

                # Capacity varies by POI type
                if 'downtown' in poi.pseudonym.lower():
                    capacity = random.randint(100, 250)
                elif 'mall' in poi.pseudonym.lower():
                    capacity = random.randint(200, 400)
                else:
                    capacity = random.randint(80, 180)

                lot = ParkingZone(
                    id=lot_id,
                    pseudonym=f"{poi.pseudonym}_Lot_{j+1}",
                    price=price,
                    position=(lat, lon),
                    maximum_capacity=capacity,
                    current_capacity=0
                )

                lots.append(lot)
                lot_id += 1

        return lots


class CityGenerator:
    """
    Generates complete city configurations for simulation.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize city generator.
        
        Args:
            seed: Random seed for reproducibility (None for random)
        """
        if seed is not None:
            random.seed(seed)
        self.parking_zone_generator = ParkingZoneGenerator(seed)
    
    def generate_simple_city(
        self,
        city_id: int = 1,
        pseudonym: str = "SimulatedCity",
        center_lat: float = 49.0,
        center_lon: float = 8.4,
        size_deg: float = 0.1,
        num_pois: int = 5,
        num_parking_zones: int = 10
    ) -> City:
        """
        Generate a simple city with random POIs and parking lots.

        Args:
            city_id: Unique city identifier
            pseudonym: City name
            center_lat: Center latitude
            center_lon: Center longitude
            size_deg: Size of city area in degrees (~0.1 deg ≈ 10km)
            num_pois: Number of points of interest
            num_parking_zones: Number of parking lots

        Returns:
            Generated City instance
        """
        # Calculate bounds
        min_lat = center_lat - size_deg / 2
        max_lat = center_lat + size_deg / 2
        min_lon = center_lon - size_deg / 2
        max_lon = center_lon + size_deg / 2

        city = City(
            id=city_id,
            pseudonym=pseudonym,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon
        )

        # Generate POIs
        poi_names = [
            "Downtown", "Mall", "University", "Hospital", "Station",
            "Park", "Museum", "Theater", "Stadium", "Airport"
        ]

        for i in range(num_pois):
            lat = random.uniform(min_lat + size_deg * 0.1, max_lat - size_deg * 0.1)
            lon = random.uniform(min_lon + size_deg * 0.1, max_lon - size_deg * 0.1)

            name = poi_names[i] if i < len(poi_names) else f"POI_{i+1}"

            poi = PointOfInterest(
                id=i + 1,
                pseudonym=name,
                position=(lat, lon)
            )
            city.add_point_of_interest(poi)

        # Generate parking lots
        lots = self.parking_zone_generator.generate_random_parking_zones(
            count=num_parking_zones,
            lat_range=(min_lat, max_lat),
            lon_range=(min_lon, max_lon)
        )

        for lot in lots:
            city.add_parking_zone(lot)

        return city
    
    def generate_urban_city(
        self,
        city_id: int = 1,
        pseudonym: str = "UrbanCity",
        center_lat: float = 49.0,
        center_lon: float = 8.4,
        size_deg: float = 0.2
    ) -> City:
        """
        Generate a realistic urban city with downtown, suburbs, and varied pricing.

        Args:
            city_id: Unique city identifier
            pseudonym: City name
            center_lat: Center latitude
            center_lon: Center longitude
            size_deg: Size of city area in degrees

        Returns:
            Generated City instance with urban layout
        """
        # Calculate bounds
        min_lat = center_lat - size_deg / 2
        max_lat = center_lat + size_deg / 2
        min_lon = center_lon - size_deg / 2
        max_lon = center_lon + size_deg / 2

        city = City(
            id=city_id,
            pseudonym=pseudonym,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon
        )

        # Create downtown area (center)
        downtown_center = (center_lat, center_lon)

        # Add strategic POIs
        pois_config = [
            ("Downtown_Center", downtown_center),
            ("Mall_West", (center_lat, min_lon + size_deg * 0.25)),
            ("Mall_East", (center_lat, min_lon + size_deg * 0.75)),
            ("University_North", (min_lat + size_deg * 0.2, center_lon)),
            ("Hospital_South", (min_lat + size_deg * 0.8, center_lon)),
            ("Train_Station", (min_lat + size_deg * 0.4, min_lon + size_deg * 0.4)),
            ("Airport", (min_lat + size_deg * 0.1, min_lon + size_deg * 0.9)),
            ("Business_District", (min_lat + size_deg * 0.6, min_lon + size_deg * 0.6))
        ]

        for i, (name, position) in enumerate(pois_config):
            poi = PointOfInterest(
                id=i + 1,
                pseudonym=name,
                position=position
            )
            city.add_point_of_interest(poi)

        # Generate parking lots near POIs
        lots = self.parking_zone_generator.generate_poi_based_parking_zones(
            pois=city.point_of_interests,
            lots_per_poi=3,
            distance_range_deg=(0.002, 0.008)
        )

        for lot in lots:
            city.add_parking_zone(lot)

        # Add some peripheral cheap parking
        peripheral_positions = [
            (min_lat + size_deg * 0.1, min_lon + size_deg * 0.1),
            (min_lat + size_deg * 0.9, min_lon + size_deg * 0.9),
            (min_lat + size_deg * 0.1, min_lon + size_deg * 0.9),
            (min_lat + size_deg * 0.9, min_lon + size_deg * 0.1)
        ]

        peripheral_lots = self.parking_zone_generator.generate_clustered_parking_zones(
            count=8,
            cluster_centers=peripheral_positions,
            cluster_radius_deg=0.005,
            lat_range=(min_lat, max_lat),
            lon_range=(min_lon, max_lon),
            price_range=(Decimal('1.0'), Decimal('2.5')),
            capacity_range=(300, 500)
        )

        # Renumber and add peripheral lots
        next_id = len(city.parking_zones) + 1
        for i, lot in enumerate(peripheral_lots):
            lot.id = next_id + i
            lot.pseudonym = f"Peripheral_{i+1}"
            city.add_parking_zone(lot)

        return city
    
    def generate_grid_city(
        self,
        city_id: int = 1,
        pseudonym: str = "GridCity",
        center_lat: float = 49.0,
        center_lon: float = 8.4,
        size_deg: float = 0.1,
        grid_size: Tuple[int, int] = (5, 5)
    ) -> City:
        """
        Generate a city with grid-based layout of POIs and parking lots.

        Args:
            city_id: Unique city identifier
            pseudonym: City name
            center_lat: Center latitude
            center_lon: Center longitude
            size_deg: Size of city area in degrees
            grid_size: (rows, cols) for grid layout

        Returns:
            Generated City instance with grid layout
        """
        # Calculate bounds
        min_lat = center_lat - size_deg / 2
        max_lat = center_lat + size_deg / 2
        min_lon = center_lon - size_deg / 2
        max_lon = center_lon + size_deg / 2

        city = City(
            id=city_id,
            pseudonym=pseudonym,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon
        )

        rows, cols = grid_size
        cell_lat = size_deg / (rows + 1)
        cell_lon = size_deg / (cols + 1)

        poi_id = 1

        # Create POIs at grid intersections
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                lat = min_lat + row * cell_lat
                lon = min_lon + col * cell_lon

                poi = PointOfInterest(
                    id=poi_id,
                    pseudonym=f"Grid_{row}_{col}",
                    position=(lat, lon)
                )
                city.add_point_of_interest(poi)
                poi_id += 1

        # Add parking lots between grid points
        lots = self.parking_zone_generator.generate_poi_based_parking_zones(
            pois=city.point_of_interests,
            lots_per_poi=1,
            distance_range_deg=(cell_lat * 0.2, cell_lat * 0.4)
        )

        for lot in lots:
            city.add_parking_zone(lot)

        return city
    
    def generate_streets_for_city(
        self,
        city: City,
        connection_probability: float = 0.3,
        speed_limit_range: Tuple[float, float] = (30.0, 60.0),
        max_distance_deg: float = 0.05
    ) -> None:
        """
        Generate streets connecting parking lots in a city.

        Args:
            city: City to add streets to
            connection_probability: Probability of creating a connection between nearby lots
            speed_limit_range: (min, max) speed limit in km/h
            max_distance_deg: Maximum connection distance in degrees
        """
        lots = city.parking_zones
        street_id = 1

        for i, lot1 in enumerate(lots):
            for lot2 in lots[i+1:]:
                # Calculate distance
                distance = lot1.distance_to_point(lot2.position)

                # Connect if close enough and random chance
                if distance < max_distance_deg and random.random() < connection_probability:
                    speed = random.uniform(speed_limit_range[0], speed_limit_range[1])

                    street = Street(
                        id=street_id,
                        pseudonym=f"Street_{lot1.id}_to_{lot2.id}",
                        from_position=lot1.position,
                        to_position=lot2.position,
                        from_parking_zone_id=lot1.id,
                        to_parking_zone_id=lot2.id,
                        speed_limit=speed
                    )

                    city.add_street(street)
                    street_id += 1
