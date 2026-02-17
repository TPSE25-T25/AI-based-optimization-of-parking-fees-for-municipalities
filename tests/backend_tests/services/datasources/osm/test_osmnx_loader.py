# tests/backend_tests/services/datasources/osm/test_osmnx_datasource.py

from types import SimpleNamespace
from unittest.mock import MagicMock
import math
import pytest
import pandas as pd
import numpy as np

# geopandas/shapely are already project dependencies (your loader imports them)
import geopandas as gpd
from shapely.geometry import Point, Polygon

from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource


def _settings(
    limit=5,
    city_name="Karlsruhe, Germany",
    center_coords=(49.0069, 8.4037),
    tariffs=None,
    default_elasticity=-0.3,   # must be <= 0 for your ParkingZone schema
    poi_limit=5,
    search_radius=5000,
    default_current_fee=2.0,
    random_seed=42,
):
    return SimpleNamespace(
        limit=limit,
        city_name=city_name,
        center_coords=center_coords,
        tariffs=tariffs or {},
        default_elasticity=default_elasticity,
        poi_limit=poi_limit,
        search_radius=search_radius,
        default_current_fee=default_current_fee,
        random_seed=random_seed,
    )


# --------------------
# Pure helper methods
# --------------------

def test_get_utm_epsg_northern_and_southern():
    ds = _settings(center_coords=(10.0, 10.0))  # lat=10, lon=10
    src = OSMnxDataSource(ds)

    epsg_n = src._get_utm_epsg(lon=10.0, lat=10.0)
    assert 32600 < epsg_n < 32700  # northern hemisphere

    epsg_s = src._get_utm_epsg(lon=10.0, lat=-10.0)
    assert 32700 < epsg_s < 32800  # southern hemisphere


def test_get_current_fee_uses_tariffs_then_fallback():
    ds = _settings(tariffs={"station": 4.2})
    src = OSMnxDataSource(ds)

    assert src._get_current_fee("Main Station Parking", dist_km=5.0) == 4.2

    # fallback zonal model
    assert src._get_current_fee("Other", dist_km=0.5) == 3.00
    assert src._get_current_fee("Other", dist_km=1.0) == 2.50
    assert src._get_current_fee("Other", dist_km=2.0) == 2.00
    assert src._get_current_fee("Other", dist_km=5.0) == 1.50


def test_estimate_occupancy_clamped():
    ds = _settings()
    src = OSMnxDataSource(ds)

    assert src._estimate_occupancy(0.0) == 0.95
    assert src._estimate_occupancy(100.0) == 0.1  # clamp min
    assert src._estimate_occupancy(-10.0) == 0.95  # clamp max effectively


def test_estimate_short_term_share_piecewise():
    ds = _settings()
    src = OSMnxDataSource(ds)

    assert src._estimate_short_term_share(0.5) == 0.8
    assert src._estimate_short_term_share(4.0) == 0.2
    mid = src._estimate_short_term_share(2.0)
    assert 0.2 < mid < 0.8


def test_estimate_capacity_parses_capacity_string_then_fallback():
    ds = _settings()
    src = OSMnxDataSource(ds)

    row = {"capacity": "approx 120"}
    assert src._estimate_capacity(row, area=1000.0) == 120

    row2 = {"capacity": None, "parking": "underground"}
    # underground: max(50, int(area/15*2))
    assert src._estimate_capacity(row2, area=1000.0) == max(50, int(1000.0 / 15 * 2))

    row3 = {"parking": "surface"}
    assert src._estimate_capacity(row3, area=1000.0) == max(10, int(1000.0 / 25))


# --------------------
# reverse_geocode
# --------------------

def test_reverse_geocode_success(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl

    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.json.return_value = {
        "address": {"city": "Karlsruhe", "country": "Germany"}
    }

    monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

    out = OSMnxDataSource.reverse_geocode(49.0, 8.4)
    assert out["city_name"] == "Karlsruhe, Germany"
    assert out["latitude"] == 49.0
    assert out["longitude"] == 8.4
    assert out["address_details"]["city"] == "Karlsruhe"


def test_reverse_geocode_http_error(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl
    import requests

    fake_resp = MagicMock()
    fake_resp.raise_for_status.side_effect = requests.RequestException("fail")
    monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

    with pytest.raises(Exception) as exc:
        OSMnxDataSource.reverse_geocode(49.0, 8.4)

    assert "Reverse geocoding failed" in str(exc.value)


# --------------------
# load_points_of_interest (mock osmnx)
# --------------------

def test_load_points_of_interest_fallback_when_empty(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl

    # empty GeoDataFrame
    empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=empty))

    pois = OSMnxDataSource.load_points_of_interest(
        "Karlsruhe, Germany",
        (49.0, 8.4),
        limit=3,
        categories=["cinema"],
    )

    assert len(pois) == 1
    assert pois[0].name == "City Center"
    assert tuple(pois[0].position) == (49.0, 8.4)


def test_load_points_of_interest_creates_objects_sorted_and_limited(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl

    # Two points, one closer to center
    gdf = gpd.GeoDataFrame(
        {
            "name": ["Far", "Near"],
            "amenity": ["cinema", "cinema"],
            "geometry": [Point(8.5, 49.1), Point(8.401, 49.001)],
        },
        crs="EPSG:4326",
    )

    monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

    pois = OSMnxDataSource.load_points_of_interest(
        "Karlsruhe, Germany",
        (49.0, 8.4),
        limit=1,
        categories=["cinema"],
    )

    assert len(pois) == 1
    assert pois[0].name == "Near"  # closer point first
    assert pois[0].id == 1


# --------------------
# _load_from_osm & load_zones_for_optimization
# --------------------

def _make_osm_gdf():
    """
    Create a tiny OSM-like GeoDataFrame with amenity=parking.
    Includes:
    - public zone
    - private zone (should be filtered)
    - customers zone (should be filtered)
    """
    # Create 3 small polygons near center
    poly1 = Polygon([(8.40, 49.00), (8.401, 49.00), (8.401, 49.001), (8.40, 49.001)])
    poly2 = Polygon([(8.41, 49.01), (8.411, 49.01), (8.411, 49.011), (8.41, 49.011)])
    poly3 = Polygon([(8.42, 49.02), (8.421, 49.02), (8.421, 49.021), (8.42, 49.021)])

    gdf = gpd.GeoDataFrame(
        {
            "name": ["Public Lot", "Private Lot", np.nan],
            "access": ["public", "private", "customers"],
            "parking": ["surface", "underground", "multi-storey"],
            "capacity": [None, None, None],
            "geometry": [poly1, poly2, poly3],
        },
        crs="EPSG:4326",
    )
    return gdf


def test__load_from_osm_filters_private_and_builds_zone_lookup_and_gdf(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl

    ds = _settings(limit=10, default_elasticity=-0.4, center_coords=(49.0, 8.4))
    src = OSMnxDataSource(ds)

    monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=_make_osm_gdf()))

    zones = src._load_from_osm()

    # Only public should remain => 1
    assert len(zones) == 1
    assert zones[0].name == "Public Lot"

    # zone_lookup filled
    assert zones[0].id in src.zone_lookup

    # gdf for visualization built
    assert src.gdf is not None
    assert not src.gdf.empty


def test_load_zones_for_optimization_delegates_load_from_osm_and_clusters(monkeypatch):
    ds = _settings(default_elasticity=-0.4)
    src = OSMnxDataSource(ds)

    fake_zones = [MagicMock(id=1), MagicMock(id=2)]
    src._load_from_osm = MagicMock(return_value=fake_zones)
    src.cluster_zones = MagicMock(side_effect=lambda z: z)

    out = src.load_zones_for_optimization()

    src._load_from_osm.assert_called_once()
    src.cluster_zones.assert_called_once_with(fake_zones)
    assert out == fake_zones


# --------------------
# load_city
# --------------------

def test_load_city_raises_if_no_zones(monkeypatch):
    ds = _settings()
    src = OSMnxDataSource(ds)

    src.load_zones_for_optimization = MagicMock(return_value=[])

    with pytest.raises(ValueError):
        src.load_city()


def test_load_city_builds_city_and_calls_pois(monkeypatch):
    import backend.services.datasources.osm.osmnx_loader as mdl

    ds = _settings(city_name="Karlsruhe, Germany", center_coords=(49.0, 8.4), poi_limit=2, default_elasticity=-0.4)
    src = OSMnxDataSource(ds)

    # create real ParkingZone objects via internal helper to satisfy City validation
    z1 = src._create_zone_obj(1, "A", capacity=10, lat=49.0, lon=8.4, occupancy=0.5, current_fee=2.0, short_term_share=0.6)
    z2 = src._create_zone_obj(2, "B", capacity=20, lat=49.2, lon=8.6, occupancy=0.5, current_fee=2.0, short_term_share=0.6)

    src.load_zones_for_optimization = MagicMock(return_value=[z1, z2])

    pois = [mdl.PointOfInterest(id=1, name="poi1", position=(49.01, 8.41)),
            mdl.PointOfInterest(id=2, name="poi2", position=(49.02, 8.42))]
    monkeypatch.setattr(mdl.OSMnxDataSource, "load_points_of_interest", MagicMock(return_value=pois))

    city = src.load_city()

    mdl.OSMnxDataSource.load_points_of_interest.assert_called_once_with(
        "Karlsruhe, Germany",
        (49.0, 8.4),
        limit=2
    )

    assert city.name == "Karlsruhe_Germany" or "Karlsruhe" in city.name
    assert len(city.parking_zones) == 2
    assert len(city.point_of_interests) == 2


# --------------------
# get_gdf_with_results (note: current code has a bug)
# --------------------

@pytest.mark.xfail(reason="Bug in get_gdf_with_results: uses row['id'] but gdf was built with 'zone_id'")
def test_get_gdf_with_results_fails_due_to_column_name_bug(monkeypatch):
    ds = _settings(default_elasticity=-0.4)
    src = OSMnxDataSource(ds)

    # minimal gdf as created in _load_from_osm: zone_id, name, geometry
    src.gdf = gpd.GeoDataFrame(
        {"zone_id": [1], "name": ["A"], "geometry": [Point(8.4, 49.0)]},
        crs="EPSG:4326",
    )
    src.zone_lookup = {1: MagicMock(current_fee=2.0)}

    opt = [SimpleNamespace(id=1, new_fee=3.0, predicted_occupancy=0.7, predicted_revenue=100.0)]
    src.get_gdf_with_results(opt)  # should xfail currently
