"""
General OSMnx Parking Data Loader.

This module provides a generic data loader for fetching and enriching
parking data from OpenStreetMap for any city worldwide.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox

from sklearn.cluster import KMeans
from shapely.geometry import Point
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from backend.services.optimizer.schemas.optimization_schema import ParkingZoneInput
from backend.models.city import PointOfInterest, City, ParkingZone
from backend.services.data.parking_data_loader import ParkingDataLoader
import urllib3

# Disable SSL warnings (OSM/Network specific)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OSMnxLoader(ParkingDataLoader):
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

    def load_zones_for_optimization(self, limit: int = 1000) -> List[ParkingZoneInput]:
        """
        Load parking zones in optimization schema format.
        Compatible with the optimization pipeline.

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

        raw_zones = self._load_from_osm(limit)
        return self.cluster_zones(raw_zones)

    def load_city(self, limit: int = 1000) -> City:
        """
        Load parking data and create a City model with ParkingZone objects.
        
        Args:
            limit: Maximum number of parking sites/zones to load
            
        Returns:
            City model with parking zones and metadata
        """
        # Load parking zones for optimization
        parking_zones = self.load_zones_for_optimization(limit)
        
        if not parking_zones:
            raise ValueError(f"No parking zones found for '{self.place_name}'")
        
        # Calculate geographic bounds from parking zones
        lats = [zone.position[0] for zone in parking_zones]
        lons = [zone.position[1] for zone in parking_zones]
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        # Add small padding to bounds
        lat_padding = (max_lat - min_lat) * 0.1 or 0.01
        lon_padding = (max_lon - min_lon) * 0.1 or 0.01
        
        min_lat -= lat_padding
        max_lat += lat_padding
        min_lon -= lon_padding
        max_lon += lon_padding
        
        # Load POIs
        pois = self.load_pois(limit=50)
        
        # Create City model
        city_pseudonym = self.place_name.replace(", ", "_").replace(" ", "_")
        city = City(
            id=1,
            pseudonym=city_pseudonym,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon,
            parking_zones=parking_zones,
            point_of_interests=pois
        )
        
        print(f"✅ City model created: {city.pseudonym}")
        print(f"   Bounds: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})")
        print(f"   Parking zones: {len(city.parking_zones)}")
        print(f"   Points of Interest: {len(city.point_of_interests)}")
        print(f"   Total capacity: {city.total_parking_capacity()} spots")
        print(f"   Occupancy: {city.city_occupancy_rate()*100:.1f}%")
        
        return city

    def load_pois(self, limit: int = 50) -> List[PointOfInterest]:
        """
        Load Points of Interest (POIs) from OpenStreetMap for driver destinations.

        Fetches various POI categories that are common driver destinations:
        - Shopping (malls, supermarkets, shops)
        - Tourism (museums, attractions, monuments)
        - Transportation hubs (train stations, bus terminals)
        - Public buildings (town hall, library, post office)
        - Entertainment (cinema, theater, restaurants)
        - Education (universities, schools)
        - Healthcare (hospitals, clinics)

        Args:
            limit: Maximum number of POIs to return

        Returns:
            List of PointOfInterest objects
        """
        print(f"📍 Loading Points of Interest for '{self.place_name}'...")

        # Define POI categories to fetch from OSM
        # These are the most common driver destinations
        poi_tags = {
            'amenity': [
                'restaurant', 'cafe', 'fast_food',  # Dining
                'cinema', 'theatre', 'library',      # Entertainment & Culture
                'hospital', 'clinic', 'pharmacy',    # Healthcare
                'bank', 'post_office', 'townhall',   # Services
                'university', 'school', 'college'    # Education
            ]
        }

        all_pois = []

        try:
            # Fetch POIs by category
            for category, values in poi_tags.items():
                try:
                    tags = {category: values}
                    gdf_poi = ox.features_from_place(self.place_name, tags)

                    if not gdf_poi.empty:
                        # Convert to lat/lon for centroids
                        gdf_poi = gdf_poi.to_crs(epsg=4326)

                        # Extract relevant POIs
                        for _, row in gdf_poi.iterrows():
                            # Get centroid for polygon/line features
                            if row.geometry.geom_type in ['Polygon', 'MultiPolygon', 'LineString']:
                                centroid = row.geometry.centroid
                                lat, lon = centroid.y, centroid.x
                            else:
                                lat, lon = row.geometry.y, row.geometry.x

                            # Get name (fallback to type if no name)
                            name = row.get('name', f"{category.title()} {len(all_pois) + 1}")
                            if pd.isna(name):
                                poi_type = row.get(category, 'Unknown')
                                name = f"{poi_type.replace('_', ' ').title()} {len(all_pois) + 1}"

                            all_pois.append({
                                'name': str(name),
                                'lat': lat,
                                'lon': lon,
                                'category': category,
                                'type': row.get(category, 'unknown')
                            })

                except Exception as e:
                    print(f"   ⚠ Warning: Could not fetch {category} POIs: {e}")
                    continue

            # Prioritize central POIs (closer to city center)
            if all_pois:
                # Calculate distance from center
                for poi in all_pois:
                    dist = np.sqrt(
                        (poi['lat'] - self.center_lat)**2 +
                        (poi['lon'] - self.center_lon)**2
                    ) * 111.0  # Approximate km
                    poi['dist_from_center'] = dist

                # Sort by distance (prioritize central locations)
                all_pois.sort(key=lambda x: x['dist_from_center'])

                # Take top N POIs
                selected_pois = all_pois[:limit]

                # Create PointOfInterest objects
                poi_objects = []
                for i, poi_data in enumerate(selected_pois, 1):
                    poi_obj = PointOfInterest(
                        id=i,
                        pseudonym=poi_data['name'],
                        position=(poi_data['lat'], poi_data['lon'])
                    )
                    poi_objects.append(poi_obj)

                print(f"✅ Loaded {len(poi_objects)} Points of Interest")
                print(f"   Categories: Shopping, Dining, Tourism, Healthcare, Education, Entertainment")

                return poi_objects
            else:
                print("⚠ No POIs found. Using fallback city center POI.")
                # Fallback: Create a single POI at city center
                return [PointOfInterest(
                    id=1,
                    pseudonym="City Center",
                    position=(self.center_lat, self.center_lon)
                )]

        except Exception as e:
            print(f"❌ Error loading POIs: {e}")
            print("   Using fallback city center POI.")
            # Fallback: Create a single POI at city center
            return [PointOfInterest(
                id=1,
                pseudonym="City Center",
                position=(self.center_lat, self.center_lon)
            )]

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
                self.zone_lookup[zone.id] = zone

                # Store for GeoDataFrame construction
                geometries.append(Point(lon, lat))
                ids.append(zone.id)
                names.append(zone.pseudonym)

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
        clamped_occupancy = min(1.0, max(0.0, occupancy))
        current_capacity = int(capacity * clamped_occupancy)

        return ParkingZoneInput(
            id=zone_id,
            pseudonym=name,
            maximum_capacity=int(capacity),
            current_capacity=current_capacity,
            price=Decimal(str(round(price, 2))),
            position=(lat, lon),
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
        res_gdf["predicted_occupancy"] = np.nan
        res_gdf["predicted_revenue"] = np.nan

        opt_dict = {z.zone_id: z for z in optimized_zones}

        for idx, row in res_gdf.iterrows():
            zid = row['zone_id']
            if zid in opt_dict:
                opt = opt_dict[zid]
                old = self.zone_lookup.get(zid)
                if old:
                    # Round to 0.50 steps for cleaner UI visualization
                    res_gdf.at[idx, "new_fee"] = round(opt.new_fee * 2) / 2
                    res_gdf.at[idx, "old_fee"] = float(old.price)
                    res_gdf.at[idx, "predicted_occupancy"] = opt.predicted_occupancy
                    res_gdf.at[idx, "predicted_revenue"] = opt.predicted_revenue

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
        # Get original zones from zone_lookup
        original_zones = list(self.zone_lookup.values())
        super().export_results_to_csv(original_zones, optimized_zones, filename)
