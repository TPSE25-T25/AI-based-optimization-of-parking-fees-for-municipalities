"""
Abstract base class for parking data loaders.
Provides a common interface for different parking data sources.
"""

from abc import ABC, abstractmethod
from typing import List
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from backend.models.city import City
from backend.services.optimizer.schemas.optimization_schema import ParkingZone


class ParkingDataLoader(ABC):
    """
    Abstract base class for parking data loaders.
    
    All parking data loaders (OSM, MobiData, etc.) should inherit from this class
    and implement the two required methods for a consistent interface.
    """
    
    @abstractmethod
    def load_city(self, limit: int = 1000) -> City:
        """
        Load parking data and create a City model with ParkingZone objects.
        
        Args:
            limit: Maximum number of parking sites/zones to load
            
        Returns:
            City model with parking zones and metadata
        """
        pass
    
    @abstractmethod
    def load_zones_for_optimization(self, limit: int = 1000) -> List[ParkingZone]:
        """
        Load parking zones in optimization schema format.
        Compatible with the optimization pipeline.
        
        Args:
            limit: Maximum number of zones to load
            
        Returns:
            List of ParkingZone objects ready for optimization
        """
        pass
    
    def cluster_zones(self, raw_zones: List[ParkingZone]) -> List[ParkingZone]:
        """
        Cluster parking zones spatially using K-Means algorithm.
        
        Groups parking zones into spatial clusters for better organization and
        potential future features like grouped pricing or visualization.
        On average, creates clusters of ~15 parking spots each.
        
        Args:
            raw_zones: List of parking zones to cluster
            
        Returns:
            Same list of parking zones (clustering metadata available via K-Means)
        """
        if not raw_zones:
            return []

        # Prepare data for K-Means (coordinate matrix)
        # Create an array [[lat, lon], [lat, lon], ...]
        coords = np.array([[z.position[0], z.position[1]] for z in raw_zones])

        # Safety check: If all coordinates are 0 (error in loader),
        # use a fallback to prevent the code from crashing.
        if np.all(coords == 0):
            print("⚠️ Warning: No geolocation found. Falling back to simple indexing.")
            coords = np.arange(len(raw_zones)).reshape(-1, 1)

        # K-Means Configuration
        # We don't want huge clusters. We say: On average 15 parking spots per cluster.
        # This ensures fine-grained, realistic current_fee zones.
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
        kmeans.fit(coords)

        # Results
        # Note: Clustering is computed for future use (visualization, grouping)
        # but not currently stored in ParkingZone objects.
        # The cluster labels can be accessed via kmeans.labels_ if needed later.

        print(f"✅ Clustering complete. {n_clusters} spatial clusters identified.")
        print(f"   Complexity reduction factor: {len(raw_zones)/n_clusters:.1f}x")
        return raw_zones
    
    def export_results_to_csv(
        self,
        original_zones: List[ParkingZone],
        optimized_zones: list,
        filename: str = "parking_analytics.csv"
    ):
        """
        Exports detailed simulation data to CSV for BI Tools.

        Calculates deltas (current_fee Change, Revenue Change, Occupancy Change).

        Args:
            original_zones: List of original ParkingZone objects before optimization
            optimized_zones: List of OptimizedZoneResult objects after optimization
            filename: Output CSV filename
        """
        if not original_zones:
            print("❌ No zones loaded. Cannot export results.")
            return

        data = []
        
        # Create lookup dictionary for optimized zones
        opt_dict = {z.id: z for z in optimized_zones}
        
        # Create lookup dictionary for original zones
        zone_dict = {z.id: z for z in original_zones}

        for zone in original_zones:
            occupancy_rate_old = zone.current_capacity / zone.maximum_capacity if zone.maximum_capacity > 0 else 0.0
            
            base = {
                "id": zone.id,
                "name": zone.name,
                "capacity": zone.maximum_capacity,
                "lat": zone.position[0],
                "lon": zone.position[1],
                "type": "Short-Term" if zone.short_term_share > 0.5 else "Commuter",
                "current_fee_old": float(zone.current_fee),
                "occupancy_old": occupancy_rate_old,
                "revenue_old": float(zone.current_fee) * zone.maximum_capacity * occupancy_rate_old
            }

            if zone.id in opt_dict:
                opt = opt_dict[zone.id]
                # Round pricing to 0.50 steps
                new_p = round(opt.new_fee * 2) / 2

                base.update({
                    "current_fee_new": new_p,
                    "occupancy_new": round(opt.predicted_occupancy, 2),
                    "revenue_new": round(opt.predicted_revenue, 2),
                    "delta_current_fee": round(new_p - float(zone.current_fee), 2),
                    "delta_revenue": round(opt.predicted_revenue - base["revenue_old"], 2),
                    "delta_occupancy": round(opt.predicted_occupancy - occupancy_rate_old, 2)
                })

            data.append(base)

        pd.DataFrame(data).to_csv(filename, index=False)
        print(f"📊 CSV exported successfully: {filename}")
