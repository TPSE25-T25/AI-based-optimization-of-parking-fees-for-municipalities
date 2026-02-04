"""
Karlsruhe-specific parking data loader.
Supports loading from either OSMnx (OpenStreetMap) or MobiData BW API.
"""

from typing import List, Literal

from backend.models.city import City
from backend.services.optimizer.schemas.optimization_schema import ParkingZone
from backend.services.data.parking_data_loader import ParkingDataLoader
from backend.services.data.osmnx_loader import OSMnxLoader
from backend.services.data.mobidata_loader import MobiDataLoader


class KarlsruheLoader(ParkingDataLoader):
    """
    Data Ingestion Service for Karlsruhe.
    
    Features:
    - Can load from OSMnx (OpenStreetMap) or MobiData BW API
    - Real-world Tariff Injection (for OSMnx)
    - Automatic Spatial Clustering via K-Means
    """

    # --- REAL WORLD TARIFF DATABASE (Status 2025) ---
    KARLSRUHE_TARIFFS = {
        "schloss": 2.50, "postgalerie": 2.50, "passagehof": 3.00,
        "karstadt": 2.50, "marktplatz": 2.50, "ece": 2.00,
        "ettlinger": 2.00, "kongress": 2.00, "messe": 1.50,
        "bahnhof": 2.50, "hbf": 2.50, "süd": 2.00, "zkm": 1.50,
        "filmpalast": 1.50, "ludwigsplatz": 2.50, "friedrichsplatz": 2.50,
        "mendelssohn": 2.00, "kronenplatz": 2.00, "fasanengarten": 1.00,
        "waldhorn": 1.50, "sophien": 2.00, "kreuzstraße": 2.00,
        "akademiestraße": 2.50, "stephanplatz": 2.50, "amalien": 2.00,
        "landratsamt": 1.50, "tivoli": 1.50, "zoo": 1.50
    }

    # Karlsruhe coordinates
    CENTER_LAT = 49.0134
    CENTER_LON = 8.4044

    def __init__(self, source: Literal["osmnx", "mobidata"] = "osmnx"):
        """
        Initialize Karlsruhe loader with specified data source.
        
        Args:
            source: Data source to use - "osmnx" for OpenStreetMap or "mobidata" for MobiData BW API
        """
        self.source = source
        
        if source == "osmnx":
            self.loader = OSMnxLoader(
                place_name="Karlsruhe, Germany",
                center_coords=(self.CENTER_LAT, self.CENTER_LON),
                tariff_database=self.KARLSRUHE_TARIFFS,
                default_elasticity=-0.4
            )
        elif source == "mobidata":
            self.loader = MobiDataLoader(
                city_name="Karlsruhe",
                center_coords=(self.CENTER_LAT, self.CENTER_LON),
                search_radius=10000,  # 12km radius
                default_current_fee=2.0,
                default_elasticity=-0.4
            )
        else:
            raise ValueError(f"Invalid source: {source}. Must be 'osmnx' or 'mobidata'")

    def load_zones_for_optimization(self, limit: int = 1000) -> List[ParkingZone]:
        """
        Loads zones for optimization from the configured source.
        
        Args:
            limit: Maximum number of zones to load
            
        Returns:
            List of ParkingZone objects ready for optimization
        """
        return self.loader.load_zones_for_optimization(limit)
    
    def load_city(self, limit: int = 1000) -> City:
        """
        Loads the city with parking zones and POIs from the configured source.
        
        Args:
            limit: Maximum number of parking sites/zones to load
            
        Returns:
            City model with parking zones and metadata
        """
        return self.loader.load_city(limit)

    def export_results_for_superset(self, optimized_zones: list, filename: str = "karlsruhe_analytics.csv"):
        """
        Export optimization results to CSV for analysis.
        
        Args:
            optimized_zones: List of optimized zone results
            filename: Output CSV filename
        """
        self.loader.export_results_to_csv(optimized_zones, filename)