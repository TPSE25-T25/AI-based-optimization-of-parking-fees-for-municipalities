"""
Karlsruhe-specific parking data loader.
Supports loading from either OSMnx (OpenStreetMap) or MobiData BW API.
"""

from typing import List

from backend.services.models.city import City
from backend.services.settings.data_source_settings import DataSourceSettings
from backend.services.optimizer.schemas.optimization_schema import ParkingZone
from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource
from backend.services.datasources.mobidata.mobidata_datasource import MobiDataDataSource
from backend.services.datasources.generator.generator_datasource import GeneratorDataSource


class CityDataLoader():
    """
    Data Ingestion Service for any City.
    
    Features:
    - Can load from OSMnx (OpenStreetMap) or MobiData BW API
    - Real-world Tariff Injection (for OSMnx)
    - Automatic Spatial Clustering via K-Means
    """

    def __init__(self, datasource: DataSourceSettings):
        """
        Initialize Karlsruhe loader with specified data source.
        
        Args:
            source: Data source to use - "osmnx" for OpenStreetMap or "mobidata" for MobiData BW API
        """
        self.datasource = datasource
        if datasource.data_source == "osmnx":
            self.loader = OSMnxDataSource(data_source=datasource)
        elif datasource.data_source == "mobidata":
            self.loader = MobiDataDataSource(data_source=datasource)
        elif datasource.data_source == "generated":
            self.loader = GeneratorDataSource(data_source=datasource)
        else:
            raise ValueError(f"Invalid source: {datasource}. Must be 'osmnx', 'mobidata', or 'generated'")

    def load_zones_for_optimization(self, limit: int = 1000) -> List[ParkingZone]:
        """
        Loads zones for optimization from the configured source.
        
        Args:
            limit: Maximum number of zones to load
            
        Returns:
            List of ParkingZone objects ready for optimization
        """
        return self.loader.load_zones_for_optimization(limit)
    
    def load_city(self) -> City:
        """
        Loads the city with parking zones and POIs from the configured source.
        
        Args:
            limit: Maximum number of parking sites/zones to load
            
        Returns:
            City model with parking zones and metadata
        """
        return self.loader.load_city()

    def export_results_for_superset(self, optimized_zones: list, filename: str = "karlsruhe_analytics.csv"):
        """
        Export optimization results to CSV for analysis.
        
        Args:
            optimized_zones: List of optimized zone results
            filename: Output CSV filename
        """
        self.loader.export_results_to_csv(optimized_zones, filename)