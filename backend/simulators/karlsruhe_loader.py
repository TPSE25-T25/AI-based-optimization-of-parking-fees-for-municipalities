import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point
from typing import List
from schemas.optimization import ParkingZoneInput
import urllib3
import difflib # Used for fuzzy string matching

# Disable SSL warnings (OSM/Network specific)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class KarlsruheLoader:
    """
    Data Ingestion Service for Karlsruhe.
    
    Responsibilities:
    1. Fetches real-world parking geometry from OpenStreetMap (OSM).
    2. Enriches OSM data with 'Real World' pricing knowledge (Hybrid Database).
    3. Simulates missing data points (Capacity, Current Occupancy) using heuristic models.
    """

    def __init__(self):
        self.place_name = "Karlsruhe, Germany"
        
        # Center coordinates: Karlsruhe Palace (Schloss)
        # Used for distance-based pricing and occupancy simulation
        self.center_lat = 49.0134
        self.center_lon = 8.4044
        
        self.gdf = None         # Holds the GeoDataFrame for map visualization
        self.zone_lookup = {}   # Fast lookup dictionary for zone objects

        # --- REAL WORLD TARIFF DATABASE (Approx. Status 2024/2025) ---
        # We map substring matches in names to actual hourly tariffs.
        # This acts as a 'Ground Truth' layer over generic OSM data.
        self.REAL_TARIFFS = {
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
            "fasanengarten": 1.00, # University/Edge area
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

    def load_zones(self, limit: int = 200) -> List[ParkingZoneInput]:
        """
        Orchestrator Method: Loads parking zones via OSM and assigns realistic prices.
        """
        self.zone_lookup = {}
        
        print(f"🌍 Loading geospatial data for '{self.place_name}' via OpenStreetMap...")
        print("   (This might take 10-20 seconds, please wait...)")
        
        return self._load_from_osm(limit)

    def _get_real_price(self, name: str, dist_km: float) -> float:
        """
        Determines the current parking fee.
        Strategy:
        1. Look up the name in the internal database (Exact/Substring match).
        2. Fallback: Use a distance-based zonal model (Center = Expensive, Outskirts = Cheap).
        """
        name_lower = str(name).lower()
        
        # 1. Database Lookup
        for key, price in self.REAL_TARIFFS.items():
            if key in name_lower:
                return price
        
        # 2. Fallback: Zonal Model (Concentric Circles)
        # 0-800m: City Center (Premium)
        if dist_km < 0.8: return 3.00
        # 800m-1.5km: Inner City
        if dist_km < 1.5: return 2.50
        # 1.5km-3.0km: Outer City
        if dist_km < 3.0: return 2.00
        # >3km: Outskirts
        return 1.50

    def _load_from_osm(self, limit: int) -> List[ParkingZoneInput]:
        """
        Fetches, cleans, and enriches raw data from OpenStreetMap.
        """
        try:
            # Filter for all amenity="parking" tags
            tags = {"amenity": "parking"}
            
            # 1. Fetch raw data from OSM API
            gdf_osm = ox.features_from_place(self.place_name, tags)
            
            # 2. Coordinate Transformation (Lat/Lon -> Meters)
            # Essential for accurate area and centroid calculation
            gdf_osm = gdf_osm.to_crs(epsg=32632) # UTM Zone 32N (Meters)
            gdf_osm["centroid"] = gdf_osm.geometry.centroid.to_crs(epsg=4326) # Back to Lat/Lon for API
            gdf_osm["area"] = gdf_osm.geometry.area
            
            # 3. Intelligent Sorting
            # We want major parking garages first, not small private backyards.
            # Priority: 'multi-storey' & 'underground' > Surface parking
            if "parking" in gdf_osm.columns:
                gdf_osm["priority"] = gdf_osm["parking"].apply(
                    lambda x: 2 if x in ['multi-storey', 'underground'] else 1
                )
            else:
                gdf_osm["priority"] = 1
                
            # Sort by Priority (Desc) then by Area (Desc) and slice the top N results
            top_zones = gdf_osm.sort_values(by=["priority", "area"], ascending=[False, False]).head(limit)
            
            zones_input = []
            geometries = []
            ids = []
            names = []
            
            print(f"✅ OSM returned {len(gdf_osm)} raw results. Processing top {limit}...")

            # Iterate through the zones (start index at 1)
            for idx, (osm_id, row) in enumerate(top_zones.iterrows(), 1):
                
                # Clean Name
                raw_name = row.get("name", "Parking Lot")
                if pd.isna(raw_name): 
                    # Generate generic name if missing
                    raw_name = f"Parkzone {idx}"
                
                # Filter: Only public access
                access = row.get("access", "public")
                if access == "private" or access == "customers": continue

                lat = row["centroid"].y
                lon = row["centroid"].x
                
                # Calculate distance to center (approximate using 1 degree Lat = 111km)
                dist_km = np.sqrt((lat - self.center_lat)**2 + (lon - self.center_lon)**2) * 111.0

                # --- PRICE DISCOVERY ---
                real_price = self._get_real_price(raw_name, dist_km)

                # --- CAPACITY ESTIMATION ---
                # OSM often lacks capacity data. We estimate it based on area.
                cap = 0
                if "capacity" in row and pd.notnull(row["capacity"]):
                    import re
                    # Extract numbers from string (e.g. "approx 50")
                    nums = re.findall(r'\d+', str(row["capacity"]))
                    if nums: cap = int(nums[0])
                
                if cap <= 0:
                    # Heuristic: 
                    # Multi-storey = 15sqm per car (efficient) * 3 floors (assumption)
                    # Surface = 25sqm per car (lanes included)
                    area_factor = 25 
                    if row.get("parking") == "multi-storey":
                        area_factor = 15 
                        cap = max(100, int(row["area"] / area_factor * 3)) 
                    else:
                        cap = max(10, int(row["area"] / area_factor))

                # --- OCCUPANCY SIMULATION ---
                # Synthetic data: The closer to the center, the fuller it is.
                # Formula creates a gradient from ~95% (Center) to ~10% (Outskirts).
                occ = max(0.1, 0.95 - (dist_km * 0.12)) 

                # Create Data Object
                z = self._create_zone_obj(idx, str(raw_name), cap, lat, lon, occ, real_price, dist_km)
                zones_input.append(z)
                self.zone_lookup[z.zone_id] = z
                
                # Store for GeoDataFrame construction
                geometries.append(Point(lon, lat))
                ids.append(z.zone_id)
                names.append(z.name)

            # Create GeoDataFrame for visualization (Folium map)
            self.gdf = gpd.GeoDataFrame({'zone_id': ids, 'name': names}, geometry=geometries, crs="EPSG:4326")
            return zones_input
            
        except Exception as e:
            print(f"❌ OSM Error: {e}")
            return []

    def _create_zone_obj(self, zid, name, cap, lat, lon, occ, price, dist_km):
        """
        Helper to create a validated Pydantic object.
        Also determines user demographics (Shopper vs. Commuter) based on location.
        """
        # Demographic Split:
        # < 1km: 80% Short-Term (Shoppers/Tourists)
        # > 3km: 20% Short-Term (mostly Commuters)
        # Linear interpolation in between.
        if dist_km < 1.0: share = 0.8
        elif dist_km > 3.0: share = 0.2
        else: share = 0.8 - ((dist_km - 1.0) * 0.3)
        
        return ParkingZoneInput(
            zone_id=zid,
            name=f"{name}",
            capacity=int(cap),
            current_fee=price,         # This is the Ground Truth price
            current_occupancy=round(min(1.0, max(0.0, occ)), 2),
            min_fee=1.0,
            max_fee=8.0,
            elasticity=-0.4,           # Standard economic assumption
            short_term_share=round(share, 2)
        )

    def get_gdf_with_results(self, optimized_zones: list) -> gpd.GeoDataFrame:
        """
        Merges optimization results back into the spatial GeoDataFrame for mapping.
        """
        if self.gdf is None or self.gdf.empty: return gpd.GeoDataFrame()
        
        res_gdf = self.gdf.copy()
        res_gdf["new_fee"] = np.nan; res_gdf["old_fee"] = np.nan
        
        opt_dict = {z.zone_id: z for z in optimized_zones}
        
        for idx, row in res_gdf.iterrows():
            zid = row['zone_id']
            if zid in opt_dict:
                opt = opt_dict[zid]
                old = self.zone_lookup.get(zid)
                if old:
                    # Rounding to 0.50 steps for cleaner UI visualization
                    res_gdf.at[idx, "new_fee"] = round(opt.new_fee * 2) / 2
                    res_gdf.at[idx, "old_fee"] = old.current_fee
                    
        return res_gdf

    def export_results_for_superset(self, optimized_zones: list, filename: str = "karlsruhe_analytics.csv"):
        """
        Exports detailed simulation data to CSV for BI Tools (Excel, Superset, Tableau).
        Calculates deltas (Price Change, Revenue Change).
        """
        import pandas as pd
        if not self.zone_lookup: return
        
        data = []
        opt_dict = {z.zone_id: z for z in optimized_zones}
        
        for zid, zone in self.zone_lookup.items():
            g = self.gdf[self.gdf.zone_id == zid]
            if g.empty: continue
            
            base = {
                "zone_id": zid, "name": zone.name, "capacity": zone.capacity,
                "lat": g.geometry.y.values[0], "lon": g.geometry.x.values[0],
                "type": "Short-Term" if zone.short_term_share > 0.5 else "Commuter",
                "price_old": zone.current_fee, 
                "occupancy_old": zone.current_occupancy,
                "revenue_old": zone.current_fee * zone.capacity * zone.current_occupancy
            }
            
            if zid in opt_dict:
                opt = opt_dict[zid]
                # Round pricing
                new_p = round(opt.new_fee * 2) / 2
                
                base.update({
                    "price_new": new_p, 
                    "occupancy_new": round(opt.predicted_occupancy, 2),
                    "revenue_new": round(opt.predicted_revenue, 2),
                    "delta_price": round(new_p - zone.current_fee, 2),
                    "delta_revenue": round(opt.predicted_revenue - base["revenue_old"], 2)
                })
            data.append(base)
            
        pd.DataFrame(data).to_csv(filename, index=False)
        print(f"📊 CSV exported successfully: {filename}")