"""
MobiData BW ParkAPI Client

Simple wrapper for the MobiData BW parking API providing access to parking sites,
parking spots, and sources across Baden-Württemberg.

API Documentation: https://api.mobidata-bw.de/park-api/api/public
"""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime


class MobiDataAPI:
    """Client for the MobiData BW ParkAPI service."""
    
    BASE_URL = "https://api.mobidata-bw.de/park-api/api/public"
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the MobiData API client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'ParkingOptimization/1.0'
        })
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a GET request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: On API errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    # ===== V3 API Methods =====
    
    def get_parking_sites(
        self,
        source_uid: Optional[str] = None,
        name: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        limit: Optional[int] = None,
        start: Optional[int] = None,
        purpose: Optional[str] = None,
        site_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get parking sites with optional filters.
        
        Args:
            source_uid: Filter by source UID
            name: Search by name (e.g., "Bahnhof")
            lat: Latitude for radius search
            lon: Longitude for radius search
            radius: Radius in meters (requires lat/lon)
            lat_min, lat_max, lon_min, lon_max: Bounding box coordinates
            limit: Maximum number of results
            start: Start offset for pagination
            purpose: Filter by purpose (CAR, BIKE, MOTORCYCLE, ITEM)
            site_type: Filter by type (CAR_PARK, UNDERGROUND, etc.)
            
        Returns:
            Dict with 'items', 'total_count', and pagination info
        """
        params = {}
        if source_uid: params['source_uid'] = source_uid
        if name: params['name'] = name
        if lat is not None: params['lat'] = lat
        if lon is not None: params['lon'] = lon
        if radius: params['radius'] = radius
        if lat_min is not None: params['lat_min'] = lat_min
        if lat_max is not None: params['lat_max'] = lat_max
        if lon_min is not None: params['lon_min'] = lon_min
        if lon_max is not None: params['lon_max'] = lon_max
        if limit: params['limit'] = limit
        if start: params['start'] = start
        if purpose: params['purpose'] = purpose
        if site_type: params['type'] = site_type
        
        return self._get("/v3/parking-sites", params)
    
    def get_parking_site(self, parking_site_id: int) -> Dict[str, Any]:
        """
        Get a specific parking site by ID.
        
        Args:
            parking_site_id: Parking site ID
            
        Returns:
            Parking site details
        """
        return self._get(f"/v3/parking-sites/{parking_site_id}")
    
    def get_parking_site_history(self, parking_site_id: int) -> Dict[str, Any]:
        """
        Get historical data for a parking site.
        
        Args:
            parking_site_id: Parking site ID
            
        Returns:
            Dict with historical 'items' and 'total_count'
        """
        return self._get(f"/v3/parking-sites/{parking_site_id}/history")
    
    def get_parking_spots(
        self,
        source_uid: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: Optional[int] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        limit: Optional[int] = None,
        start: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get individual parking spots with optional filters.
        
        Args:
            source_uid: Filter by source UID
            lat: Latitude for radius search
            lon: Longitude for radius search
            radius: Radius in meters (requires lat/lon)
            lat_min, lat_max, lon_min, lon_max: Bounding box coordinates
            limit: Maximum number of results
            start: Start offset for pagination
            
        Returns:
            Dict with 'items', 'total_count', and pagination info
        """
        params = {}
        if source_uid: params['source_uid'] = source_uid
        if lat is not None: params['lat'] = lat
        if lon is not None: params['lon'] = lon
        if radius: params['radius'] = radius
        if lat_min is not None: params['lat_min'] = lat_min
        if lat_max is not None: params['lat_max'] = lat_max
        if lon_min is not None: params['lon_min'] = lon_min
        if lon_max is not None: params['lon_max'] = lon_max
        if limit: params['limit'] = limit
        if start: params['start'] = start
        
        return self._get("/v3/parking-spots", params)
    
    def get_parking_spot(self, parking_spot_id: int) -> Dict[str, Any]:
        """
        Get a specific parking spot by ID.
        
        Args:
            parking_spot_id: Parking spot ID
            
        Returns:
            Parking spot details
        """
        return self._get(f"/v3/parking-spots/{parking_spot_id}")
    
    def get_sources(self) -> Dict[str, Any]:
        """
        Get all available data sources.
        
        Returns:
            Dict with source 'items' and 'total_count'
        """
        return self._get("/v3/sources")
    
    def get_source(self, source_id: int) -> Dict[str, Any]:
        """
        Get a specific source by ID.
        
        Args:
            source_id: Source ID
            
        Returns:
            Source details
        """
        return self._get(f"/v3/sources/{source_id}")
    
    # ===== V2 API Methods =====
    
    def get_lots_v2(
        self,
        location: Optional[List[float]] = None,
        radius: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get parking lots using ParkAPI V2 format.
        
        Args:
            location: [lon, lat] coordinates
            radius: Search radius
            
        Returns:
            Dict with 'count', 'results', and pagination
        """
        params = {}
        if location: params['location'] = f"{location[0]},{location[1]}"
        if radius: params['radius'] = radius
        
        return self._get("/v2/lots/", params)
    
    def get_pool_v2(self, pool_id: str) -> Dict[str, Any]:
        """
        Get a specific pool/source using ParkAPI V2 format.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Pool details
        """
        return self._get(f"/v2/pools/{pool_id}/")
    
    # ===== V1 API Methods =====
    
    def get_cities_v1(self) -> Dict[str, Any]:
        """
        Get available cities using ParkAPI V1 format.
        
        Returns:
            Dict with 'cities', 'api_version', 'server_version'
        """
        return self._get("/v1")
    
    def get_city_lots_v1(self, pool_id: str) -> Dict[str, Any]:
        """
        Get parking lots for a city using ParkAPI V1 format.
        
        Args:
            pool_id: City/pool identifier
            
        Returns:
            Dict with 'lots', 'last_updated', 'last_downloaded'
        """
        return self._get(f"/v1/{pool_id}")
    
    # ===== Datex2 Format =====
    
    def get_datex2_json(self, source_uid: Optional[str] = None) -> Dict[str, Any]:
        """
        Get parking sites in Datex2 format.
        
        Args:
            source_uid: Optional source UID filter
            
        Returns:
            Datex2 format parking data
        """
        params = {}
        if source_uid: params['source_uid'] = source_uid
        
        return self._get("/datex2/json", params)
    
    def search_nearby(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Search for parking sites and individual parking spots near a location.
        Automatically handles pagination to retrieve all results from both endpoints.
        
        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters
            limit: Maximum total results to retrieve
            
        Returns:
            List of parking sites and spots (aggregated from all pages)
        """
        all_items = []
        
        # Fetch parking sites
        start = 0
        page_limit = min(1000, limit)  # API max is 1000 per request
        
        while len(all_items) < limit:
            result = self.get_parking_sites(
                lat=lat,
                lon=lon,
                radius=radius_meters,
                limit=page_limit,
                start=start
            )
            items = result.get('items', [])
            
            if not items:
                break  # No more results
            
            # Mark items as parking sites
            for item in items:
                item['_type'] = 'site'
            
            all_items.extend(items)
            total_count = result.get('total_count', len(all_items))
            
            # Stop if we've retrieved all available items or reached our limit
            if len(all_items) >= total_count or len(all_items) >= limit:
                break
            
            start += len(items)
            
            # Adjust page_limit for final page if needed
            remaining = min(limit - len(all_items), 1000)
            page_limit = remaining
        
        # Fetch individual parking spots (not part of sites)
        if len(all_items) < limit:
            start = 0
            remaining_limit = limit - len(all_items)
            page_limit = min(1000, remaining_limit)
            
            while len(all_items) < limit:
                result = self.get_parking_spots(
                    lat=lat,
                    lon=lon,
                    radius=radius_meters,
                    limit=page_limit,
                    start=start
                )
                items = result.get('items', [])
                
                if not items:
                    break  # No more results
                
                # Mark items as parking spots
                for item in items:
                    item['_type'] = 'spot'
                
                all_items.extend(items)
                total_count = result.get('total_count', len(all_items))
                
                # Stop if we've retrieved all available items or reached our limit
                if len(all_items) >= total_count or len(all_items) >= limit:
                    break
                
                start += len(items)
                
                # Adjust page_limit for final page if needed
                remaining = min(limit - len(all_items), 1000)
                page_limit = remaining
        
        return all_items[:limit]  # Trim to exact limit if needed
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
