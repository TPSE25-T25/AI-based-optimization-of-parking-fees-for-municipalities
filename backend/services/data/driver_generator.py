"""
Driver generation utilities for simulation testing.
"""

import random
from typing import List, Tuple
from decimal import Decimal

from ...models.driver import Driver
from ...models.city import City, PointOfInterest


class DriverGenerator:
    """
    Generates driver populations for simulation purposes.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize driver generator.
        
        Args:
            seed: Random seed for reproducibility (None for random)
        """
        if seed is not None:
            random.seed(seed)
    
    def generate_random_drivers(
        self,
        count: int,
        city: City,
        price_range: Tuple[Decimal, Decimal] = (Decimal('2.0'), Decimal('10.0')),
        parking_duration_range: Tuple[int, int] = (30, 240)
    ) -> List[Driver]:
        """
        Generate random drivers with destinations at points of interest.
        
        Args:
            count: Number of drivers to generate
            city: City model containing POIs and canvas dimensions
            price_range: (min, max) price drivers are willing to pay per hour
            parking_duration_range: (min, max) parking duration in minutes
        
        Returns:
            List of generated drivers
        """
        drivers = []
        
        if not city.point_of_interests:
            raise ValueError("City must have at least one point of interest for driver destinations")
        
        for i in range(count):
            # Random starting position within canvas
            start_x = random.uniform(0, city.canvas[0])
            start_y = random.uniform(0, city.canvas[1])
            
            # Random destination from POIs
            destination_poi = random.choice(city.point_of_interests)
            
            # Random price tolerance
            max_price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            
            # Random parking duration
            duration = random.randint(parking_duration_range[0], parking_duration_range[1])
            
            driver = Driver(
                id=i + 1,
                pseudonym=f"Driver_{i+1:04d}",
                max_parking_price=max_price,
                starting_position=(start_x, start_y),
                destination=destination_poi.position,
                desired_parking_time=duration
            )
            
            drivers.append(driver)
        
        return drivers
    
    def generate_clustered_drivers(
        self,
        count: int,
        city: City,
        cluster_centers: List[PointOfInterest],
        cluster_radius: float = 50.0,
        price_range: Tuple[Decimal, Decimal] = (Decimal('2.0'), Decimal('10.0')),
        parking_duration_range: Tuple[int, int] = (30, 240)
    ) -> List[Driver]:
        """
        Generate drivers starting near specific cluster centers (e.g., residential areas).
        
        Args:
            count: Number of drivers to generate
            city: City model
            cluster_centers: Points around which to cluster driver starting positions
            cluster_radius: Maximum distance from cluster center
            price_range: (min, max) price drivers are willing to pay per hour
            parking_duration_range: (min, max) parking duration in minutes
        
        Returns:
            List of generated drivers
        """
        drivers = []
        
        if not city.point_of_interests:
            raise ValueError("City must have at least one point of interest for driver destinations")
        
        if not cluster_centers:
            raise ValueError("Must provide at least one cluster center")
        
        for i in range(count):
            # Pick random cluster center
            cluster = random.choice(cluster_centers)
            
            # Generate position near cluster center
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, cluster_radius)
            start_x = cluster.position[0] + distance * random.uniform(-1, 1)
            start_y = cluster.position[1] + distance * random.uniform(-1, 1)
            
            # Clamp to canvas bounds
            start_x = max(0, min(city.canvas[0], start_x))
            start_y = max(0, min(city.canvas[1], start_y))
            
            # Random destination from POIs (excluding starting cluster)
            destination_poi = random.choice(city.point_of_interests)
            
            # Random price tolerance
            max_price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            
            # Random parking duration
            duration = random.randint(parking_duration_range[0], parking_duration_range[1])
            
            driver = Driver(
                id=i + 1,
                pseudonym=f"ClusteredDriver_{i+1:04d}",
                max_parking_price=max_price,
                starting_position=(start_x, start_y),
                destination=destination_poi.position,
                desired_parking_time=duration
            )
            
            drivers.append(driver)
        
        return drivers
    
    def generate_rush_hour_drivers(
        self,
        count: int,
        city: City,
        peak_destination: PointOfInterest,
        price_range: Tuple[Decimal, Decimal] = (Decimal('3.0'), Decimal('15.0')),
        parking_duration_range: Tuple[int, int] = (180, 480)
    ) -> List[Driver]:
        """
        Generate drivers simulating rush hour - many heading to same destination.
        
        Args:
            count: Number of drivers to generate
            city: City model
            peak_destination: Primary destination (e.g., downtown, office district)
            price_range: (min, max) price drivers are willing to pay per hour
            parking_duration_range: (min, max) parking duration in minutes
        
        Returns:
            List of generated drivers
        """
        drivers = []
        
        for i in range(count):
            # Random starting position
            start_x = random.uniform(0, city.canvas[0])
            start_y = random.uniform(0, city.canvas[1])
            
            # 80% go to peak destination, 20% go elsewhere
            if random.random() < 0.8:
                destination = peak_destination.position
            else:
                if city.point_of_interests:
                    destination = random.choice(city.point_of_interests).position
                else:
                    destination = peak_destination.position
            
            # Rush hour drivers might pay more
            max_price = Decimal(str(random.uniform(float(price_range[0]), float(price_range[1]))))
            
            # Longer parking during work hours
            duration = random.randint(parking_duration_range[0], parking_duration_range[1])
            
            driver = Driver(
                id=i + 1,
                pseudonym=f"RushHourDriver_{i+1:04d}",
                max_parking_price=max_price,
                starting_position=(start_x, start_y),
                destination=destination,
                desired_parking_time=duration
            )
            
            drivers.append(driver)
        
        return drivers
    
    def generate_price_sensitive_drivers(
        self,
        count: int,
        city: City,
        low_price_threshold: Decimal = Decimal('3.0'),
        parking_duration_range: Tuple[int, int] = (30, 120)
    ) -> List[Driver]:
        """
        Generate price-sensitive drivers with low price tolerance.
        
        Args:
            count: Number of drivers to generate
            city: City model
            low_price_threshold: Maximum price these drivers will pay
            parking_duration_range: (min, max) parking duration in minutes
        
        Returns:
            List of generated drivers
        """
        drivers = []
        
        if not city.point_of_interests:
            raise ValueError("City must have at least one point of interest")
        
        for i in range(count):
            start_x = random.uniform(0, city.canvas[0])
            start_y = random.uniform(0, city.canvas[1])
            
            destination_poi = random.choice(city.point_of_interests)
            
            # Low price tolerance
            max_price = Decimal(str(random.uniform(float(Decimal('1.0')), float(low_price_threshold))))
            
            duration = random.randint(parking_duration_range[0], parking_duration_range[1])
            
            driver = Driver(
                id=i + 1,
                pseudonym=f"BudgetDriver_{i+1:04d}",
                max_parking_price=max_price,
                starting_position=(start_x, start_y),
                destination=destination_poi.position,
                desired_parking_time=duration
            )
            
            drivers.append(driver)
        
        return drivers
