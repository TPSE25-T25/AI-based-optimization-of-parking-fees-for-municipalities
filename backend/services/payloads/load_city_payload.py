from typing import Any, Dict, Optional
from pydantic import BaseModel

from backend.services.models.city import City

class LoadCityRequest(BaseModel):
    data_source: str = "osmnx"  # "osmnx", "mobidata", or "generated"
    limit: int = 1000
    city_name: str = "Karlsruhe, Germany"
    center_lat: float = 49.0069
    center_lon: float = 8.4037
    seed: int = 42
    poi_limit: int = 50
    default_elasticity: Optional[float] = -0.4
    search_radius: Optional[int] = 10000
    default_current_fee: Optional[float] = 2.0
    tariffs: Optional[Dict[str, float]] = None

class LoadCityResponse(BaseModel):
    city: City


class ReverseGeoLocationRequest(BaseModel):
    center_lat: float
    center_lon: float

class ReverseGeoLocationResponse(BaseModel):
    geo_info: Dict[str, Any]