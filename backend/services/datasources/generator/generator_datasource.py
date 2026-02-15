


from typing import List
from backend.services.models.city import City, ParkingZone
from backend.services.datasources.parking_data_source import ParkingDataSource
from backend.services.settings.data_source_settings import DataSourceSettings
from backend.services.datasources.generator.city_generator import CityGenerator


class GeneratorDataSource(ParkingDataSource):
    """
    Data Ingestion Service for Generated Parking Data.
    
    Features:
    - Generates synthetic parking zones for testing and simulation.
    - Automatic Spatial Clustering via K-Means
    """

    def __init__(self, data_source: DataSourceSettings):
        """
        Initialize Generated Data loader with specified data source.
        
        Args:
            seed: Random seed for reproducibility (affects both generation and K-Means clustering)
            city_name: Name of the simulated city
            center_coords: (latitude, longitude) center coordinates for the city
            poi_limit: Maximum number of POIs to generate (default: 50)
        """
        super().__init__(data_source)
        self.city_generator = CityGenerator(data_source.random_seed)

    def load_city(self) -> City:
        """
        Load generated parking data and create a City model with ParkingZone objects.
        
        Args:
            limit: Maximum number of parking sites/zones to load
            
        Returns:
            City model with parking zones and metadata
        """
        city = self.city_generator.generate_simple_city(
            name=self.city_name,
            center_lat=self.center_coords[0],
            center_lon=self.center_coords[1],
            num_pois=self.poi_limit,
            num_parking_zones=self.limit
        )
        return city
    
    def load_zones_for_optimization(self) -> List[ParkingZone]:
        """
        Load generated parking zones in optimization schema format.
        Compatible with the optimization pipeline.
        
        Args:
            limit: Maximum number of zones to load
            
        Returns:
            List of ParkingZone objects ready for optimization
        """
        return self.load_city()