"""
General OSMnx Parking Data Loader.

This module provides a generic data loader for fetching and enriching
parking data from OpenStreetMap for any city worldwide.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point
from typing import List, Dict, Optional, Tuple
from schemas.optimization import ParkingZoneInput
import urllib3

# Disable SSL warnings (OSM/Network specific)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OSMnxParkingLoader:
    """
    Generic Data Ingestion Service for any city using OpenStreetMap.

    Responsibilities:
    1. Fetches real-world parking geometry from OpenStreetMap (OSM).
    2. Enriches OSM data with optional pricing database (Hybrid Database).
    3. Simulates missing data points (Capacity, Current Occupancy) using heuristic models.

    Features:
    - City-agnostic: Works with any location worldwide
    - Automatic UTM zone detection for accurate area calculations
    - Flexible pricing: Use custom tariff database or distance-based model
    - Capacity estimation based on parking type and area
    - Occupancy simulation based on distance from city center
    """

    def __init__(
        self,
        place_name: str,
        center_coords: Tuple[float, float],
        tariff_database: Optional[Dict[str, float]] = None,
        default_elasticity: float = -0.4
    ):
        """
        Initialize the parking data loader.

        Args:
            place_name: City name for OSM query (e.g., "Berlin, Germany", "Paris, France")
            center_coords: (latitude, longitude) of city center for distance calculations
            tariff_database: Optional dict mapping location keywords to hourly prices
                            e.g., {"station": 2.50, "mall": 2.00}
            default_elasticity: Price elasticity coefficient (default: -0.4)
        """
        self.place_name = place_name
        self.center_lat, self.center_lon = center_coords
        self.tariff_database = tariff_database or {}
        self.default_elasticity = default_elasticity

        self.gdf = None         # Holds the GeoDataFrame for map visualization
        self.zone_lookup = {}   # Fast lookup dictionary for zone objects

        # UTM zone will be auto-detected based on coordinates
        self.utm_epsg = self._get_utm_epsg(self.center_lon, self.center_lat)

    def _get_utm_epsg(self, lon: float, lat: float) -> int:
        """
        Automatically determine the appropriate UTM EPSG code based on coordinates.

        UTM zones are 6° wide. Zone 1 starts at -180°.
        Northern hemisphere: EPSG:326xx, Southern: EPSG:327xx

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            EPSG code for the appropriate UTM zone
        """
        utm_zone = int((lon + 180) / 6) + 1

        # Northern or Southern hemisphere
        if lat >= 0:
            epsg = 32600 + utm_zone  # WGS84 UTM Northern Hemisphere
        else:
            epsg = 32700 + utm_zone  # WGS84 UTM Southern Hemisphere

        return epsg

    def load_zones(self, limit: int = 200) -> List[ParkingZoneInput]:
        """
        Orchestrator Method: Loads parking zones via OSM and assigns realistic prices.

        Args:
            limit: Maximum number of parking zones to return (best zones by priority/area)

        Returns:
            List of ParkingZoneInput objects ready for optimization
        """
        self.zone_lookup = {}

        print(f"🌍 Loading geospatial data for '{self.place_name}' via OpenStreetMap...")
        print(f"   Center: {self.center_lat:.4f}, {self.center_lon:.4f}")
        print(f"   UTM Zone: EPSG:{self.utm_epsg}")
        print("   (This might take 10-20 seconds, please wait...)")

        return self._load_from_osm(limit)

    def _get_price(self, name: str, dist_km: float) -> float:
        """
        Determines the current parking fee.

        Strategy:
        1. Look up the name in the tariff database (substring match).
        2. Fallback: Use a distance-based zonal model (Center = Expensive, Outskirts = Cheap).

        Args:
            name: Parking zone name
            dist_km: Distance from city center in kilometers

        Returns:
            Hourly parking fee in currency units
        """
        name_lower = str(name).lower()

        # 1. Database Lookup (substring matching)
        for keyword, price in self.tariff_database.items():
            if keyword.lower() in name_lower:
                return price

        # 2. Fallback: Zonal Model (Concentric Circles)
        # These ranges work well for most European cities
        # Can be customized per city if needed
        if dist_km < 0.8:   # 0-800m: City Center (Premium)
            return 3.00
        if dist_km < 1.5:   # 800m-1.5km: Inner City
            return 2.50
        if dist_km < 3.0:   # 1.5km-3.0km: Outer City
            return 2.00
        # >3km: Outskirts
        return 1.50

    def _estimate_capacity(self, row, area: float) -> int:
        """
        Estimate parking capacity based on area and type.

        Uses industry-standard heuristics:
        - Multi-storey: 15 sqm per car, 3 floors average
        - Underground: 15 sqm per car, 2 floors average
        - Surface: 25 sqm per car (includes lanes)

        Args:
            row: DataFrame row with parking data
            area: Parking area in square meters

        Returns:
            Estimated capacity (number of parking spaces)
        """
        # Try to extract capacity from OSM data first
        if "capacity" in row and pd.notnull(row["capacity"]):
            import re
            # Extract numbers from string (e.g., "approx 50", "100-150")
            nums = re.findall(r'\d+', str(row["capacity"]))
            if nums:
                cap = int(nums[0])
                if cap > 0:
                    return cap

        # Fallback: Estimate based on area and type
        parking_type = row.get("parking", "surface")

        if parking_type == "multi-storey":
            # 15 sqm per car, assume 3 floors
            return max(100, int(area / 15 * 3))
        elif parking_type == "underground":
            # 15 sqm per car, assume 2 floors
            return max(50, int(area / 15 * 2))
        else:
            # Surface parking: 25 sqm per car (includes lanes and access)
            return max(10, int(area / 25))

    def _estimate_occupancy(self, dist_km: float) -> float:
        """
        Estimate current occupancy based on distance from center.

        Creates a realistic gradient:
        - City center (0 km): ~95% occupancy
        - Outskirts (7+ km): ~10% occupancy
        - Linear decay in between

        Args:
            dist_km: Distance from city center in kilometers

        Returns:
            Occupancy rate between 0.0 and 1.0
        """
        # Formula: 95% at center, decaying by 12% per km
        # Clamped between 10% and 95%
        occupancy = 0.95 - (dist_km * 0.12)
        return max(0.1, min(0.95, occupancy))

    def _estimate_short_term_share(self, dist_km: float) -> float:
        """
        Estimate short-term parker share based on distance from center.

        Logic:
        - City center: 80% short-term (shoppers, tourists)
        - Outskirts: 20% short-term (mostly commuters)
        - Linear interpolation between 1-3 km

        Args:
            dist_km: Distance from city center in kilometers

        Returns:
            Share of short-term parkers (0.0 to 1.0)
        """
        if dist_km < 1.0:
            return 0.8
        elif dist_km > 3.0:
            return 0.2
        else:
            # Linear interpolation: 80% at 1km -> 20% at 3km
            return 0.8 - ((dist_km - 1.0) * 0.3)

    def _load_from_osm(self, limit: int) -> List[ParkingZoneInput]:
        """
        Fetches, cleans, and enriches raw data from OpenStreetMap.

        Args:
            limit: Maximum number of zones to return

        Returns:
            List of enriched ParkingZoneInput objects
        """
        try:
            # Filter for all amenity="parking" tags
            tags = {"amenity": "parking"}

            # 1. Fetch raw data from OSM API
            gdf_osm = ox.features_from_place(self.place_name, tags)

            # 2. Coordinate Transformation (Lat/Lon -> Meters)
            # Essential for accurate area and centroid calculation
            gdf_osm = gdf_osm.to_crs(epsg=self.utm_epsg)  # UTM (Meters)
            gdf_osm["centroid"] = gdf_osm.geometry.centroid.to_crs(epsg=4326)  # Back to Lat/Lon
            gdf_osm["area"] = gdf_osm.geometry.area

            # 3. Intelligent Sorting
            # Priority: 'multi-storey' & 'underground' > Surface parking
            if "parking" in gdf_osm.columns:
                gdf_osm["priority"] = gdf_osm["parking"].apply(
                    lambda x: 2 if x in ['multi-storey', 'underground'] else 1
                )
            else:
                gdf_osm["priority"] = 1

            # Sort by Priority (Desc) then by Area (Desc)
            top_zones = gdf_osm.sort_values(
                by=["priority", "area"],
                ascending=[False, False]
            ).head(limit)

            zones_input = []
            geometries = []
            ids = []
            names = []

            print(f"✅ OSM returned {len(gdf_osm)} raw results. Processing top {limit}...")

            # Iterate through the zones
            for idx, (osm_id, row) in enumerate(top_zones.iterrows(), 1):

                # Clean Name
                raw_name = row.get("name", "Parking Lot")
                if pd.isna(raw_name):
                    raw_name = f"Parking Zone {idx}"

                # Filter: Only public access
                access = row.get("access", "public")
                if access in ["private", "customers"]:
                    continue

                # Get coordinates
                lat = row["centroid"].y
                lon = row["centroid"].x

                # Calculate distance to center (using Haversine approximation)
                # 1 degree latitude ≈ 111 km
                dist_km = np.sqrt(
                    (lat - self.center_lat)**2 + (lon - self.center_lon)**2
                ) * 111.0

                # --- ENRICHMENT ---
                price = self._get_price(raw_name, dist_km)
                capacity = self._estimate_capacity(row, row["area"])
                occupancy = self._estimate_occupancy(dist_km)
                short_term_share = self._estimate_short_term_share(dist_km)

                # Create Data Object
                zone = self._create_zone_obj(
                    zone_id=idx,
                    name=str(raw_name),
                    capacity=capacity,
                    lat=lat,
                    lon=lon,
                    occupancy=occupancy,
                    price=price,
                    short_term_share=short_term_share
                )

                zones_input.append(zone)
                self.zone_lookup[zone.zone_id] = zone

                # Store for GeoDataFrame construction
                geometries.append(Point(lon, lat))
                ids.append(zone.zone_id)
                names.append(zone.name)

            # Create GeoDataFrame for visualization
            self.gdf = gpd.GeoDataFrame(
                {'zone_id': ids, 'name': names},
                geometry=geometries,
                crs="EPSG:4326"
            )

            print(f"✅ Successfully loaded {len(zones_input)} parking zones")
            return zones_input

        except Exception as e:
            print(f"❌ OSM Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _create_zone_obj(
        self,
        zone_id: int,
        name: str,
        capacity: int,
        lat: float,
        lon: float,
        occupancy: float,
        price: float,
        short_term_share: float
    ) -> ParkingZoneInput:
        """
        Helper to create a validated Pydantic object.

        Args:
            zone_id: Unique zone identifier
            name: Zone name
            capacity: Number of parking spaces
            lat: Latitude
            lon: Longitude
            occupancy: Current occupancy rate (0.0-1.0)
            price: Current hourly fee
            short_term_share: Share of short-term parkers (0.0-1.0)

        Returns:
            Validated ParkingZoneInput object
        """
        return ParkingZoneInput(
            zone_id=zone_id,
            name=name,
            capacity=int(capacity),
            current_fee=round(price, 2),
            current_occupancy=round(min(1.0, max(0.0, occupancy)), 2),
            min_fee=1.0,
            max_fee=8.0,
            elasticity=self.default_elasticity,
            short_term_share=round(short_term_share, 2)
        )

    def get_gdf_with_results(self, optimized_zones: list) -> gpd.GeoDataFrame:
        """
        Merges optimization results back into the spatial GeoDataFrame for mapping.

        Args:
            optimized_zones: List of OptimizedZoneResult objects

        Returns:
            GeoDataFrame with old and new fees for visualization
        """
        if self.gdf is None or self.gdf.empty:
            return gpd.GeoDataFrame()

        res_gdf = self.gdf.copy()
        res_gdf["new_fee"] = np.nan
        res_gdf["old_fee"] = np.nan

        opt_dict = {z.zone_id: z for z in optimized_zones}

        for idx, row in res_gdf.iterrows():
            zid = row['zone_id']
            if zid in opt_dict:
                opt = opt_dict[zid]
                old = self.zone_lookup.get(zid)
                if old:
                    # Round to 0.50 steps for cleaner UI visualization
                    res_gdf.at[idx, "new_fee"] = round(opt.new_fee * 2) / 2
                    res_gdf.at[idx, "old_fee"] = old.current_fee

        return res_gdf

    def export_results_to_csv(
        self,
        optimized_zones: list,
        filename: str = "parking_analytics.csv"
    ):
        """
        Exports detailed simulation data to CSV for BI Tools.

        Calculates deltas (Price Change, Revenue Change, Occupancy Change).

        Args:
            optimized_zones: List of OptimizedZoneResult objects
            filename: Output CSV filename
        """
        if not self.zone_lookup:
            print("❌ No zones loaded. Cannot export results.")
            return

        data = []
        opt_dict = {z.zone_id: z for z in optimized_zones}

        for zid, zone in self.zone_lookup.items():
            g = self.gdf[self.gdf.zone_id == zid]
            if g.empty:
                continue

            base = {
                "zone_id": zid,
                "name": zone.name,
                "capacity": zone.capacity,
                "lat": g.geometry.y.values[0],
                "lon": g.geometry.x.values[0],
                "type": "Short-Term" if zone.short_term_share > 0.5 else "Commuter",
                "price_old": zone.current_fee,
                "occupancy_old": zone.current_occupancy,
                "revenue_old": zone.current_fee * zone.capacity * zone.current_occupancy
            }

            if zid in opt_dict:
                opt = opt_dict[zid]
                # Round pricing to 0.50 steps
                new_p = round(opt.new_fee * 2) / 2

                base.update({
                    "price_new": new_p,
                    "occupancy_new": round(opt.predicted_occupancy, 2),
                    "revenue_new": round(opt.predicted_revenue, 2),
                    "delta_price": round(new_p - zone.current_fee, 2),
                    "delta_revenue": round(opt.predicted_revenue - base["revenue_old"], 2),
                    "delta_occupancy": round(opt.predicted_occupancy - zone.current_occupancy, 2)
                })

            data.append(base)

        pd.DataFrame(data).to_csv(filename, index=False)
        print(f"📊 CSV exported successfully: {filename}")


# Convenience function for quick setup
def create_city_loader(
    city_name: str,
    center_lat: float,
    center_lon: float,
    tariffs: Optional[Dict[str, float]] = None
) -> OSMnxParkingLoader:
    """
    Quick factory function to create a city loader.

    Args:
        city_name: Name for OSM query (e.g., "Munich, Germany")
        center_lat: Center latitude
        center_lon: Center longitude
        tariffs: Optional tariff database

    Returns:
        Configured OSMnxParkingLoader instance
    """
    return OSMnxParkingLoader(
        place_name=city_name,
        center_coords=(center_lat, center_lon),
        tariff_database=tariffs
    )