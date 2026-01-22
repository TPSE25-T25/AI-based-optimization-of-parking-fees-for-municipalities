"""
Karlsruhe-specific parking data loader.

This module provides a specialized loader for Karlsruhe with known
parking garage prices and locations.
"""

from typing import List
from schemas.optimization import ParkingZoneInput
from services.data.osmnx_loader import OSMnxParkingLoader


class KarlsruheLoader(OSMnxParkingLoader):
    """
    Data Ingestion Service for Karlsruhe.

    Extends the general OSMnx loader with Karlsruhe-specific tariff database.

    Responsibilities:
    1. Fetches real-world parking geometry from OpenStreetMap (OSM).
    2. Enriches OSM data with Karlsruhe-specific pricing knowledge.
    3. Simulates missing data points (Capacity, Current Occupancy) using heuristic models.
    """

    # --- REAL WORLD TARIFF DATABASE (Approx. Status 2024/2025) ---
    # We map substring matches in names to actual hourly tariffs.
    # This acts as a 'Ground Truth' layer over generic OSM data.
    KARLSRUHE_TARIFFS = {
        "schloss": 2.50,      # Palace Garage
        "postgalerie": 2.50,  # Shopping Mall
        "passagehof": 3.00,   # Very central, premium
        "karstadt": 2.50,
        "marktplatz": 2.50,
        "ece": 2.00,          # Ettlinger Tor Mall
        "ettlinger": 2.00,
        "kongress": 2.00,     # Congress Center
        "messe": 1.50,
        "bahnhof": 2.50,      # Main Station (Hbf)
        "hbf": 2.50,
        "süd": 2.00,          # Station South
        "zkm": 1.50,          # Museum (often cheaper)
        "filmpalast": 1.50,   # Cinema
        "ludwigsplatz": 2.50,
        "friedrichsplatz": 2.50,
        "mendelssohn": 2.00,
        "kronenplatz": 2.00,
        "fasanengarten": 1.00,  # University/Edge area
        "waldhorn": 1.50,
        "sophien": 2.00,
        "kreuzstraße": 2.00,
        "akademiestraße": 2.50,
        "stephanplatz": 2.50,
        "amalien": 2.00,
        "landratsamt": 1.50,
        "tivoli": 1.50,
        "zoo": 1.50
    }

    def __init__(self):
        """
        Initialize the Karlsruhe parking loader.

        Uses Karlsruhe Palace (Schloss) as city center.
        """
        super().__init__(
            place_name="Karlsruhe, Germany",
            center_coords=(49.0134, 8.4044),  # Karlsruhe Palace
            tariff_database=self.KARLSRUHE_TARIFFS,
            default_elasticity=-0.4
        )

    def load_zones(self, limit: int = 200) -> List[ParkingZoneInput]:
        """
        Loads parking zones for Karlsruhe via OSM.

        Args:
            limit: Maximum number of parking zones to return

        Returns:
            List of ParkingZoneInput objects ready for optimization
        """
        return super().load_zones(limit)

    def export_results_for_superset(
        self,
        optimized_zones: list,
        filename: str = "karlsruhe_analytics.csv"
    ):
        """
        Exports detailed simulation data to CSV for BI Tools.

        Backward-compatible alias for export_results_to_csv().

        Args:
            optimized_zones: List of OptimizedZoneResult objects
            filename: Output CSV filename
        """
        self.export_results_to_csv(optimized_zones, filename)