"""
Karlsruhe-specific parking data loader.
Uses K-Means Clustering to group parking zones spatially.
"""

import numpy as np
from typing import List
from sklearn.cluster import KMeans  # Der ML-Algorithmus
from schemas.optimization import ParkingZoneInput
from services.data.osmnx_loader import OSMnxParkingLoader

class KarlsruheLoader(OSMnxParkingLoader):
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
        # Load raw zones using the parent class method
        raw_zones = super().load_zones(limit)
        
        if not raw_zones:
            return []

        # 2. Prepare data for K-Means (coordinate matrix)
        # Create an array [[lat, lon], [lat, lon], ...]
        coords = np.array([[z.lat, z.lon] for z in raw_zones])

        # Safety check: If all coordinates are 0 (error in OSM loader),
        # use a fallback to prevent the code from crashing.
        if np.all(coords == 0):
            print("⚠️ Warning: No geolocation found. Falling back to simple indexing.")
            coords = np.arange(len(raw_zones)).reshape(-1, 1)

        # 3. K-Means Configuration
        # We don't want huge clusters. We say: On average 15 parking spots per cluster.
        # This ensures fine-grained, realistic price zones.
        n_clusters = max(1, int(len(raw_zones) / 15))
        
        print(f"🧩 Running K-Means Algorithm...")
        print(f"   Input: {len(raw_zones)} Zones")
        print(f"   Target: {n_clusters} Spatial Clusters")

        # THE ALGORITHM
        kmeans = KMeans(
            n_clusters=n_clusters, 
            random_state=42,       # Fixed seed for reproducibility
            n_init=10              # Algorithm runs 10x, takes the best result
        )
        
        # The real clustering happens here:
        cluster_labels = kmeans.fit_predict(coords)

        # 4.results 
        clustered_zones = []
        
        for i, zone in enumerate(raw_zones):
            # We explicitly create the object anew to ensure
            # that the ID is set correctly.
            updated_zone = ParkingZoneInput(
                zone_id=zone.zone_id,
                # HERE comes the result from K-Means:
                cluster_group_id=int(cluster_labels[i]), 
                
                name=zone.name,
                lat=zone.lat,
                lon=zone.lon,
                capacity=zone.capacity,
                current_fee=zone.current_fee,
                current_occupancy=zone.current_occupancy,
                min_fee=zone.min_fee,
                max_fee=zone.max_fee,
                elasticity=zone.elasticity,
                short_term_share=zone.short_term_share
            )
            clustered_zones.append(updated_zone)

        print(f"✅ Clustering complete. Optimization complexity reduced by factor {len(raw_zones)/n_clusters:.1f}x")
        return clustered_zones

    def export_results_for_superset(self, optimized_zones: list, filename: str = "karlsruhe_analytics.csv"):
        self.export_results_to_csv(optimized_zones, filename)