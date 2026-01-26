"""
Karlsruhe-specific parking data loader.
Uses K-Means Clustering to group parking zones spatially.
"""

from typing import List

from backend.services.optimizer.schemas.optimization_schema import ParkingZoneInput
from backend.services.data.osmnx_loader import OSMnxLoader


class KarlsruheLoader(OSMnxLoader):
    """
    Data Ingestion Service for Karlsruhe.
    
    Features:
    - Real-world Tariff Injection
    - Spatial Clustering via K-Means (Scikit-Learn)
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

    def __init__(self):
        super().__init__(
            place_name="Karlsruhe, Germany",
            center_coords=(49.0134, 8.4044),
            tariff_database=self.KARLSRUHE_TARIFFS,
            default_elasticity=-0.4
        )

    def load_zones(self, limit: int = 200) -> List[ParkingZoneInput]:
        """
        Loads zones and applies High-Quality Spatial Clustering (K-Means).
        """
        raw_zones = super().load_zones(limit)
        return super().cluster_zones(raw_zones)

    def export_results_for_superset(self, optimized_zones: list, filename: str = "karlsruhe_analytics.csv"):
        self.export_results_to_csv(optimized_zones, filename)