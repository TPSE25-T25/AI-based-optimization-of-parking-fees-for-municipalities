"""
MobiData BW parking data loader.
Loads real-world parking data from MobiData BW API and converts to City model.
"""

from typing import List, Tuple, Optional

from backend.services.datasources.mobidata.mobidata_api import MobiDataAPI
from backend.services.models.city import City, ParkingZone
from backend.services.optimizer.schemas.optimization_schema import ParkingZone
from backend.services.datasources.parking_data_source import ParkingDataSource
from backend.services.settings.data_source_settings import DataSourceSettings
from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource


class MobiDataDataSource(ParkingDataSource):
    """
    Data Ingestion Service for MobiData BW parking data.
    
    Features:
    - Real-world parking data from MobiData BW API
    - Supports search by city name or coordinates
    - Converts API data to City model with ParkingZone objects
    """

    def __init__(self, data_source: DataSourceSettings):
        """
        Initialize the MobiData loader.
        
        Args:
            city_name: Name of the city to search for (e.g., "Karlsruhe")
            center_coords: (latitude, longitude) for radius search
            search_radius: Search radius in meters (default: 5000m = 5km)
            default_current_fee: Default hourly parking current_fee when not available
            default_elasticity: Default current_fee elasticity coefficient
            seed: Random seed for K-Means clustering (default: 42)
            poi_limit: Maximum number of POIs to load (default: 50)
        """
        super().__init__(data_source)
        self.api = MobiDataAPI()
    
    def load_city(self) -> City:
        """
        Load parking data and create a City model.
        
        Args:
            limit: Maximum number of parking sites to load
            
        Returns:
            City model with parking zones and metadata
        """
        # Load zones using the optimization format (without clustering)
        parking_zones = self.load_zones_for_optimization()
        
        # Calculate geographic bounds from parking zones
        lats = [pz.position[0] for pz in parking_zones]
        lons = [pz.position[1] for pz in parking_zones]
        
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
                
        # Load POIs only if we have a valid city name for OSM
        pois = OSMnxDataSource.load_points_of_interest(self.city_name, self.center_coords, limit=self.poi_limit)
        
        # Create City model
        city = City(
            id=1,
            name=self.city_name,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon,
            parking_zones=parking_zones,
            point_of_interests=pois
        )
        
        print(f"✅ City model created: {city.name}")
        print(f"   Bounds: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})")
        print(f"   Total capacity: {city.total_parking_capacity()} spots")
        print(f"   Occupancy: {city.city_occupancy_rate()*100:.1f}%")
        
        return city
    
    def _convert_site_to_parking_zone_input(self, site: dict, index: int) -> ParkingZone:
        """
        Convert a MobiData parking site to a ParkingZone model.
        
        Args:
            site: Parking site data from MobiData API
            index: Sequential index for ID assignment
            
        Returns:
            ParkingZone object
        """
        # Extract required fields
        site_id = site.get('id', index + 1)
        name = site.get('name', f"ParkingSite_{site_id}")
        
        # Location
        lat = float(site['lat'])
        lon = float(site['lon'])
        
        # Capacity information
        max_capacity = site.get('capacity', 0)
        if max_capacity <= 0:
            # If no capacity info, estimate based on type
            site_type = site.get('type', '')
            max_capacity = self._estimate_capacity(site_type)
        
        # Current occupancy from realtime data
        free_capacity = site.get('realtime_free_capacity')
        if free_capacity is not None and free_capacity >= 0:
            current_capacity = max(0, max_capacity - free_capacity)
        else:
            # No realtime data, estimate 60% occupancy
            current_capacity = int(max_capacity * 0.6)
        
        # Ensure current doesn't exceed maximum
        current_capacity = min(current_capacity, max_capacity)
        
        # current_fee information
        current_fee = self._extract_current_fee(site)
        
        # Create ParkingZone
        zone = ParkingZone(
            id=site_id,
            name=name.replace(" ", "_").replace(",", "")[:50],
            current_fee=current_fee,
            position=[lat, lon],
            maximum_capacity=max_capacity,
            current_capacity=current_capacity,
            min_fee=0.5,
            max_fee=5.0,
            elasticity=self.default_elasticity,
            short_term_share=0.5
        )
        
        return zone
    
    def _convert_spot_to_parking_zone_input(self, spot: dict, index: int) -> ParkingZone:
        """
        Convert a MobiData parking spot to a ParkingZone model.
        
        Args:
            spot: Parking spot data from MobiData API
            index: Sequential index for ID assignment
            
        Returns:
            ParkingZone object
        """
        # Extract required fields
        spot_id = spot.get('id', index + 1)
        
        # Location
        lat = float(spot['lat'])
        lon = float(spot['lon'])
        
        # Individual spots have capacity of 1
        max_capacity = 1
        
        # Check if spot is currently occupied
        # For spots, we might have different status indicators
        is_occupied = spot.get('is_occupied', False)
        current_capacity = 1 if is_occupied else 0
        
        # current_fee information - spots might be free/on-street parking
        has_fee = spot.get('has_fee', False)
        current_fee = self.default_current_fee if has_fee else 0.0
        
        # Generate a name for the spot
        name = f"ParkingSpot_{spot_id}"
        
        # Create ParkingZone
        zone = ParkingZone(
            id=spot_id,
            name=name[:50],
            current_fee=current_fee,
            position=[lat, lon],
            maximum_capacity=max_capacity,
            current_capacity=current_capacity,
            min_fee=0.0 if not has_fee else 0.5,
            max_fee=5.0 if has_fee else 0.0,
            elasticity=self.default_elasticity,
            short_term_share=0.5
        )
        
        return zone
    
    def _extract_current_fee(self, site: dict) -> float:
        """
        Extract or estimate parking current_fee from site data.
        
        Args:
            site: Parking site data from API
            
        Returns:
            Hourly parking current_fee
        """
        # Check if site has fee information
        has_fee = site.get('has_fee', True)
        if not has_fee:
            return 0.0
        
        # MobiData doesn't provide detailed pricing, use default
        # Could be enhanced with external pricing database
        return self.default_current_fee
    
    def _estimate_capacity(self, site_type: str) -> int:
        """
        Estimate parking capacity based on site type.
        
        Args:
            site_type: Type of parking site
            
        Returns:
            Estimated capacity
        """
        # Capacity estimates by parking type
        capacity_map = {
            'CAR_PARK': 200,
            'UNDERGROUND': 150,
            'OFF_STREET_PARKING_GROUND': 100,
            'ON_STREET': 20,
            'OTHER': 50
        }
        
        return capacity_map.get(site_type, 50)
    
    def load_zones_for_optimization(self) -> List[ParkingZone]:
        """
        Load parking zones in optimization schema format.
        Compatible with the optimization pipeline.
        
        Args:
            limit: Maximum number of zones to load
            cluster: Whether to cluster zones (default: True)
            
        Returns:
            List of ParkingZone objects ready for optimization
        """        
        print(f"🌍 Loading parking data from MobiData BW API...")
        
        # Fetch parking sites from API
        if self.center_coords:
            lat, lon = self.center_coords
            print(f"   Searching near: {lat:.4f}, {lon:.4f} (radius: {self.search_radius}m)")
            sites = self.api.search_nearby(lat, lon, self.search_radius, limit=self.limit)
        else:
            raise ValueError("Either city_name or center_coords must be provided")
        
        if not sites:
            raise ValueError(f"No parking sites found for the specified search criteria")
        
        # Count sites vs spots
        num_sites = sum(1 for item in sites if item.get('_type') == 'site')
        num_spots = sum(1 for item in sites if item.get('_type') == 'spot')
        print(f"   Found {len(sites)} parking locations ({num_sites} sites, {num_spots} spots)")
        
        # Convert API sites/spots to ParkingZone objects
        zones = []
        for idx, item in enumerate(sites):
            try:
                if item.get('_type') == 'spot':
                    zone = self._convert_spot_to_parking_zone_input(item, idx)
                else:
                    zone = self._convert_site_to_parking_zone_input(item, idx)
                zones.append(zone)
            except Exception as e:
                print(f"   ⚠️ Warning: Skipped {item.get('_type', 'item')} {item.get('id', '?')}: {e}")
                continue
        
        print(f"   Successfully loaded {len(zones)} parking zones")
        
        # Store zones for CSV export
        self.original_zones = zones.copy()
        return self.cluster_zones(zones)
    
    def export_results_to_csv(
        self,
        optimized_zones: list,
        filename: str = "parking_analytics.csv"
    ):
        """
        Export optimization results to CSV.
        
        Args:
            optimized_zones: List of OptimizedZoneResult objects
            filename: Output CSV filename
        """
        if not hasattr(self, 'original_zones') or not self.original_zones:
            print("❌ No zones loaded. Cannot export results.")
            return
        
        # Use parent class method
        super().export_results_to_csv(self.original_zones, optimized_zones, filename)
    
    def close(self):
        """Close API connection."""
        self.api.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
