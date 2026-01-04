"""
City and parking lot generation utilities for simulation testing.
"""

import random
import math
from typing import List, Tuple, Optional
from decimal import Decimal

from ...models.city import City, PointOfInterest, Street, ParkingLot


class ParkingLotGenerator:
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
    
    def generate_random_parking_lots(
        self,
        count: int,
        canvas: Tuple[float, float],
        price_range: Tuple[Decimal, Decimal] = (Decimal('1.0'), Decimal('10.0')),
        capacity_range: Tuple[int, int] = (50, 300),
        initial_occupancy: float = 0.0
    ) -> List[ParkingLot]:
        """
        Generate random parking lots within canvas bounds.
        
        Args:
            count: Number of parking lots to generate
            canvas: Canvas dimensions (width, height)
            price_range: (min, max) hourly parking price
            capacity_range: (min, max) parking capacity
            initial_occupancy: Initial occupancy rate (0.0 to 1.0)
        
        Returns:
            List of generated parking lots
        """
        lots = []
        
        for i in range(count):
            x = random.uniform(0, canvas[0])
            y = random.uniform(0, canvas[1])
            
            price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            max_capacity = random.randint(capacity_range[0], capacity_range[1])
            current_capacity = int(max_capacity * initial_occupancy)
            
            lot = ParkingLot(
                id=i + 1,
                pseudonym=f"ParkingLot_{i+1:03d}",
                price=price,
                position=(x, y),
                maximum_capacity=max_capacity,
                current_capacity=current_capacity
            )
            
            lots.append(lot)
        
        return lots
    
    def generate_clustered_parking_lots(
        self,
        count: int,
        canvas: Tuple[float, float],
        cluster_centers: List[Tuple[float, float]],
        cluster_radius: float = 100.0,
        price_range: Tuple[Decimal, Decimal] = (Decimal('2.0'), Decimal('8.0')),
        capacity_range: Tuple[int, int] = (50, 200)
    ) -> List[ParkingLot]:
        """
        Generate parking lots clustered around specific points.
        
        Args:
            count: Number of parking lots to generate
            canvas: Canvas dimensions (width, height)
            cluster_centers: List of (x, y) positions to cluster around
            cluster_radius: Maximum distance from cluster center
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
            center_x, center_y = random.choice(cluster_centers)
            
            # Generate position near cluster center
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, cluster_radius)
            x = center_x + distance * math.cos(angle)
            y = center_y + distance * math.sin(angle)
            
            # Clamp to canvas bounds
            x = max(0, min(canvas[0], x))
            y = max(0, min(canvas[1], y))
            
            price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            max_capacity = random.randint(capacity_range[0], capacity_range[1])
            
            lot = ParkingLot(
                id=i + 1,
                pseudonym=f"ClusteredLot_{i+1:03d}",
                price=price,
                position=(x, y),
                maximum_capacity=max_capacity,
                current_capacity=0
            )
            
            lots.append(lot)
        
        return lots
    
    def generate_poi_based_parking_lots(
        self,
        pois: List[PointOfInterest],
        lots_per_poi: int = 2,
        distance_range: Tuple[float, float] = (10.0, 50.0),
        price_variation: float = 0.3
    ) -> List[ParkingLot]:
        """
        Generate parking lots near points of interest with pricing based on proximity.
        
        Args:
            pois: List of points of interest
            lots_per_poi: Number of parking lots to generate per POI
            distance_range: (min, max) distance from POI
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
                # Generate position near POI
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.uniform(distance_range[0], distance_range[1])
                x = poi.position[0] + distance * math.cos(angle)
                y = poi.position[1] + distance * math.sin(angle)
                
                # Price varies based on distance (closer = more expensive)
                distance_factor = 1.0 - (distance - distance_range[0]) / (distance_range[1] - distance_range[0])
                price_multiplier = 1.0 + (distance_factor * price_variation)
                price = base_price * Decimal(str(price_multiplier))
                
                # Capacity varies by POI type
                if 'downtown' in poi.pseudonym.lower():
                    capacity = random.randint(100, 250)
                elif 'mall' in poi.pseudonym.lower():
                    capacity = random.randint(200, 400)
                else:
                    capacity = random.randint(80, 180)
                
                lot = ParkingLot(
                    id=lot_id,
                    pseudonym=f"{poi.pseudonym}_Lot_{j+1}",
                    price=price,
                    position=(x, y),
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
        self.parking_lot_generator = ParkingLotGenerator(seed)
    
    def generate_simple_city(
        self,
        city_id: int = 1,
        pseudonym: str = "SimulatedCity",
        canvas: Tuple[float, float] = (1000.0, 1000.0),
        num_pois: int = 5,
        num_parking_lots: int = 10
    ) -> City:
        """
        Generate a simple city with random POIs and parking lots.
        
        Args:
            city_id: Unique city identifier
            pseudonym: City name
            canvas: Canvas dimensions (width, height)
            num_pois: Number of points of interest
            num_parking_lots: Number of parking lots
        
        Returns:
            Generated City instance
        """
        city = City(id=city_id, pseudonym=pseudonym, canvas=canvas)
        
        # Generate POIs
        poi_names = [
            "Downtown", "Mall", "University", "Hospital", "Station",
            "Park", "Museum", "Theater", "Stadium", "Airport"
        ]
        
        for i in range(num_pois):
            x = random.uniform(canvas[0] * 0.1, canvas[0] * 0.9)
            y = random.uniform(canvas[1] * 0.1, canvas[1] * 0.9)
            
            name = poi_names[i] if i < len(poi_names) else f"POI_{i+1}"
            
            poi = PointOfInterest(
                id=i + 1,
                pseudonym=name,
                position=(x, y)
            )
            city.add_point_of_interest(poi)
        
        # Generate parking lots
        lots = self.parking_lot_generator.generate_random_parking_lots(
            count=num_parking_lots,
            canvas=canvas
        )
        
        for lot in lots:
            city.add_parking_lot(lot)
        
        return city
    
    def generate_urban_city(
        self,
        city_id: int = 1,
        pseudonym: str = "UrbanCity",
        canvas: Tuple[float, float] = (2000.0, 2000.0)
    ) -> City:
        """
        Generate a realistic urban city with downtown, suburbs, and varied pricing.
        
        Args:
            city_id: Unique city identifier
            pseudonym: City name
            canvas: Canvas dimensions (width, height)
        
        Returns:
            Generated City instance with urban layout
        """
        city = City(id=city_id, pseudonym=pseudonym, canvas=canvas)
        
        # Create downtown area (center)
        downtown_center = (canvas[0] / 2, canvas[1] / 2)
        
        # Add strategic POIs
        pois_config = [
            ("Downtown_Center", downtown_center),
            ("Mall_West", (canvas[0] * 0.25, canvas[1] * 0.5)),
            ("Mall_East", (canvas[0] * 0.75, canvas[1] * 0.5)),
            ("University_North", (canvas[0] * 0.5, canvas[1] * 0.2)),
            ("Hospital_South", (canvas[0] * 0.5, canvas[1] * 0.8)),
            ("Train_Station", (canvas[0] * 0.4, canvas[1] * 0.4)),
            ("Airport", (canvas[0] * 0.9, canvas[1] * 0.1)),
            ("Business_District", (canvas[0] * 0.6, canvas[1] * 0.6))
        ]
        
        for i, (name, position) in enumerate(pois_config):
            poi = PointOfInterest(
                id=i + 1,
                pseudonym=name,
                position=position
            )
            city.add_point_of_interest(poi)
        
        # Generate parking lots near POIs
        lots = self.parking_lot_generator.generate_poi_based_parking_lots(
            pois=city.point_of_interests,
            lots_per_poi=3,
            distance_range=(20.0, 80.0)
        )
        
        for lot in lots:
            city.add_parking_lot(lot)
        
        # Add some peripheral cheap parking
        peripheral_positions = [
            (canvas[0] * 0.1, canvas[1] * 0.1),
            (canvas[0] * 0.9, canvas[1] * 0.9),
            (canvas[0] * 0.1, canvas[1] * 0.9),
            (canvas[0] * 0.9, canvas[1] * 0.1)
        ]
        
        peripheral_lots = self.parking_lot_generator.generate_clustered_parking_lots(
            count=8,
            canvas=canvas,
            cluster_centers=peripheral_positions,
            cluster_radius=50.0,
            price_range=(Decimal('1.0'), Decimal('2.5')),
            capacity_range=(300, 500)
        )
        
        # Renumber and add peripheral lots
        next_id = len(city.parking_lots) + 1
        for i, lot in enumerate(peripheral_lots):
            lot.id = next_id + i
            lot.pseudonym = f"Peripheral_{i+1}"
            city.add_parking_lot(lot)
        
        return city
    
    def generate_grid_city(
        self,
        city_id: int = 1,
        pseudonym: str = "GridCity",
        canvas: Tuple[float, float] = (1000.0, 1000.0),
        grid_size: Tuple[int, int] = (5, 5)
    ) -> City:
        """
        Generate a city with grid-based layout of POIs and parking lots.
        
        Args:
            city_id: Unique city identifier
            pseudonym: City name
            canvas: Canvas dimensions (width, height)
            grid_size: (rows, cols) for grid layout
        
        Returns:
            Generated City instance with grid layout
        """
        city = City(id=city_id, pseudonym=pseudonym, canvas=canvas)
        
        rows, cols = grid_size
        cell_width = canvas[0] / (cols + 1)
        cell_height = canvas[1] / (rows + 1)
        
        poi_id = 1
        
        # Create POIs at grid intersections
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                x = col * cell_width
                y = row * cell_height
                
                poi = PointOfInterest(
                    id=poi_id,
                    pseudonym=f"Grid_{row}_{col}",
                    position=(x, y)
                )
                city.add_point_of_interest(poi)
                poi_id += 1
        
        # Add parking lots between grid points
        lots = self.parking_lot_generator.generate_poi_based_parking_lots(
            pois=city.point_of_interests,
            lots_per_poi=1,
            distance_range=(cell_width * 0.2, cell_width * 0.4)
        )
        
        for lot in lots:
            city.add_parking_lot(lot)
        
        return city
    
    def generate_streets_for_city(
        self,
        city: City,
        connection_probability: float = 0.3,
        speed_limit_range: Tuple[float, float] = (1.0, 3.0)
    ) -> None:
        """
        Generate streets connecting parking lots in a city.
        
        Args:
            city: City to add streets to
            connection_probability: Probability of creating a connection between nearby lots
            speed_limit_range: (min, max) speed limit values
        """
        lots = city.parking_lots
        street_id = 1
        
        for i, lot1 in enumerate(lots):
            for lot2 in lots[i+1:]:
                # Calculate distance
                distance = lot1.distance_to_point(lot2.position)
                
                # Connect if close enough and random chance
                max_connection_distance = min(city.canvas) * 0.3
                if distance < max_connection_distance and random.random() < connection_probability:
                    speed = random.uniform(speed_limit_range[0], speed_limit_range[1])
                    
                    street = Street(
                        id=street_id,
                        pseudonym=f"Street_{lot1.id}_to_{lot2.id}",
                        from_position=lot1.position,
                        to_position=lot2.position,
                        from_parking_lot_id=lot1.id,
                        to_parking_lot_id=lot2.id,
                        speed_limit=speed
                    )
                    
                    city.add_street(street)
                    street_id += 1
