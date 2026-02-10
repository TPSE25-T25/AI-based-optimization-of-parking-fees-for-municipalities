

from pydantic import BaseModel, Field


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


class DataSourceSettings(BaseModel):
    """
    Settings for data source configuration.
    Supports OSMnx, MobiData, and Generated data sources.
    """
    data_source: str = Field(default="osmnx", description="Data source for zone loading: 'osmnx', 'mobidata', or 'generated'")
    limit: int = Field(default=1000, ge=1, description="Maximum number of parking zones to load")
    city_name: str = Field(default="Karlsruhe, Germany", description="City Name for data loading")
    center_coords: tuple = Field(default=(49.0069, 8.4037), description="Center coordinates (latitude, longitude)")
    random_seed: int = Field(default=42, description="Random seed for reproducibility")
    poi_limit: int = Field(default=50, ge=1, description="Maximum number of Points of Interest to load for the city")
    default_elasticity: float = Field(default=-0.4, description="Default price elasticity of demand")
    search_radius: int = Field(default=10000, ge=1000, description="Search radius in meters for MobiData API")
    default_current_fee: float = Field(default=2.0, ge=0, description="Default current fee for zones without specific data")
    tariffs: dict = Field(default_factory=lambda: KARLSRUHE_TARIFFS.copy(), description="Tariffs for OSMnx loader")