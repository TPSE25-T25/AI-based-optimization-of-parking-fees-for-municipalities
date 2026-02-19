# tests/backend_tests/services/datasources/osm/test_osmnx_datasource.py

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, mock_open
import math
import os
import pytest
import pandas as pd
import numpy as np

# geopandas/shapely are already project dependencies (your loader imports them)
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString, MultiPolygon

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


# ═══════════════════════════════════════════════════════════════════════════════
# UTM EPSG helper
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetUtmEpsg:

    def test_northern_hemisphere(self):
        src = OSMnxDataSource(_settings(center_coords=(10.0, 10.0)))
        epsg = src._get_utm_epsg(lon=10.0, lat=10.0)
        assert 32600 < epsg < 32700

    def test_southern_hemisphere(self):
        src = OSMnxDataSource(_settings(center_coords=(10.0, 10.0)))
        epsg = src._get_utm_epsg(lon=10.0, lat=-10.0)
        assert 32700 < epsg < 32800

    def test_equator_is_northern(self):
        src = OSMnxDataSource(_settings(center_coords=(0.0, 0.0)))
        epsg = src._get_utm_epsg(lon=0.0, lat=0.0)
        assert 32600 < epsg < 32700

    def test_dateline_west(self):
        src = OSMnxDataSource(_settings(center_coords=(0.0, -179.0)))
        epsg = src._get_utm_epsg(lon=-179.0, lat=10.0)
        assert epsg == 32601  # zone 1

    def test_dateline_east(self):
        src = OSMnxDataSource(_settings(center_coords=(0.0, 179.0)))
        epsg = src._get_utm_epsg(lon=179.0, lat=10.0)
        assert epsg == 32660  # zone 60


# ═══════════════════════════════════════════════════════════════════════════════
# Fee estimation
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCurrentFee:

    def _src(self, tariffs=None):
        return OSMnxDataSource(_settings(tariffs=tariffs or {}))

    def test_tariff_lookup_has_priority(self):
        src = self._src(tariffs={"station": 4.2})
        assert src._get_current_fee("Main Station Parking", dist_km=5.0) == 4.2

    def test_tariff_case_insensitive(self):
        src = self._src(tariffs={"MALL": 5.0})
        assert src._get_current_fee("mall parking", dist_km=0.1) == 5.0

    def test_zone_center(self):
        assert self._src()._get_current_fee("Other", dist_km=0.5) == 3.00

    def test_zone_inner(self):
        assert self._src()._get_current_fee("Other", dist_km=1.0) == 2.50

    def test_zone_outer(self):
        assert self._src()._get_current_fee("Other", dist_km=2.0) == 2.00

    def test_zone_outskirts(self):
        assert self._src()._get_current_fee("Other", dist_km=5.0) == 1.50

    def test_boundary_080(self):
        assert self._src()._get_current_fee("X", dist_km=0.8) == 2.50

    def test_boundary_150(self):
        assert self._src()._get_current_fee("X", dist_km=1.5) == 2.00

    def test_boundary_300(self):
        assert self._src()._get_current_fee("X", dist_km=3.0) == 1.50


# ═══════════════════════════════════════════════════════════════════════════════
# Occupancy estimation
# ═══════════════════════════════════════════════════════════════════════════════

class TestEstimateOccupancy:

    def _src(self):
        return OSMnxDataSource(_settings())

    def test_center(self):
        assert self._src()._estimate_occupancy(0.0) == 0.95

    def test_far_clamps_min(self):
        assert self._src()._estimate_occupancy(100.0) == 0.1

    def test_negative_dist_clamps_max(self):
        assert self._src()._estimate_occupancy(-10.0) == 0.95

    def test_mid_range(self):
        occ = self._src()._estimate_occupancy(3.0)
        assert 0.1 < occ < 0.95


# ═══════════════════════════════════════════════════════════════════════════════
# Short-term share estimation
# ═══════════════════════════════════════════════════════════════════════════════

class TestEstimateShortTermShare:

    def _src(self):
        return OSMnxDataSource(_settings())

    def test_close(self):
        assert self._src()._estimate_short_term_share(0.5) == 0.8

    def test_far(self):
        assert self._src()._estimate_short_term_share(4.0) == 0.2

    def test_mid(self):
        mid = self._src()._estimate_short_term_share(2.0)
        assert 0.2 < mid < 0.8

    def test_at_1km_boundary(self):
        assert self._src()._estimate_short_term_share(1.0) == 0.8

    def test_at_3km_boundary(self):
        assert self._src()._estimate_short_term_share(3.0) == pytest.approx(0.2)


# ═══════════════════════════════════════════════════════════════════════════════
# Capacity estimation
# ═══════════════════════════════════════════════════════════════════════════════

class TestEstimateCapacity:

    def _src(self):
        return OSMnxDataSource(_settings())

    def test_parses_capacity_string(self):
        assert self._src()._estimate_capacity({"capacity": "approx 120"}, area=1000.0) == 120

    def test_capacity_zero_falls_through(self):
        """capacity='0' has cap=0, so falls through to area estimate."""
        row = {"capacity": "0", "parking": "surface"}
        result = self._src()._estimate_capacity(row, area=500.0)
        assert result == max(10, int(500.0 / 25))

    def test_capacity_none_underground(self):
        row = {"capacity": None, "parking": "underground"}
        assert self._src()._estimate_capacity(row, area=1000.0) == max(50, int(1000.0 / 15 * 2))

    def test_capacity_surface_fallback(self):
        row = {"parking": "surface"}
        assert self._src()._estimate_capacity(row, area=1000.0) == max(10, int(1000.0 / 25))

    def test_capacity_multi_storey(self):
        row = {"capacity": None, "parking": "multi-storey"}
        expected = max(100, int(1000.0 / 15 * 3))
        assert self._src()._estimate_capacity(row, area=1000.0) == expected

    def test_small_area_surface_uses_min_10(self):
        row = {"parking": "surface"}
        assert self._src()._estimate_capacity(row, area=10.0) == 10

    def test_small_area_underground_uses_min_50(self):
        row = {"capacity": None, "parking": "underground"}
        assert self._src()._estimate_capacity(row, area=10.0) == 50

    def test_small_area_multi_storey_uses_min_100(self):
        row = {"capacity": None, "parking": "multi-storey"}
        assert self._src()._estimate_capacity(row, area=10.0) == 100

    def test_no_parking_type_defaults_to_surface(self):
        row = {}
        assert self._src()._estimate_capacity(row, area=500.0) == max(10, int(500.0 / 25))

    def test_multiple_numbers_takes_first(self):
        row = {"capacity": "100-150"}
        assert self._src()._estimate_capacity(row, area=500.0) == 100


# ═══════════════════════════════════════════════════════════════════════════════
# reverse_geocode
# ═══════════════════════════════════════════════════════════════════════════════

class TestReverseGeocode:

    def test_success(self, monkeypatch):
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

    def test_http_error(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl
        import requests

        fake_resp = MagicMock()
        fake_resp.raise_for_status.side_effect = requests.RequestException("fail")
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        with pytest.raises(Exception, match="Reverse geocoding failed"):
            OSMnxDataSource.reverse_geocode(49.0, 8.4)

    def test_non_request_exception(self, monkeypatch):
        """Covers the second except branch (non-requests exception)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.side_effect = ValueError("bad json")
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        with pytest.raises(Exception, match="Error processing reverse geocoding response"):
            OSMnxDataSource.reverse_geocode(49.0, 8.4)

    def test_unknown_location_fallback(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {}  # no "address" key
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        out = OSMnxDataSource.reverse_geocode(0.0, 0.0)
        assert out["city_name"] == "Unknown Location"

    def test_town_fallback(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {
            "address": {"town": "SmallTown", "country": "Germany"}
        }
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        out = OSMnxDataSource.reverse_geocode(49.0, 8.4)
        assert out["city_name"] == "SmallTown, Germany"

    def test_village_fallback(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {
            "address": {"village": "Tiny"}
        }
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        out = OSMnxDataSource.reverse_geocode(49.0, 8.4)
        assert out["city_name"] == "Tiny"  # no country

    def test_municipality_fallback(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {
            "address": {"municipality": "Muni", "country": "France"}
        }
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        out = OSMnxDataSource.reverse_geocode(49.0, 8.4)
        assert out["city_name"] == "Muni, France"

    def test_county_fallback(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {
            "address": {"county": "SomeCounty", "country": "US"}
        }
        monkeypatch.setattr(mdl.requests, "get", MagicMock(return_value=fake_resp))

        out = OSMnxDataSource.reverse_geocode(49.0, 8.4)
        assert out["city_name"] == "SomeCounty, US"


# ═══════════════════════════════════════════════════════════════════════════════
# load_points_of_interest
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadPointsOfInterest:

    def test_fallback_when_empty(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=empty))

        pois = OSMnxDataSource.load_points_of_interest(
            "Karlsruhe, Germany", (49.0, 8.4), limit=3, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "City Center"

    def test_sorted_and_limited(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        gdf = gpd.GeoDataFrame(
            {"name": ["Far", "Near"], "amenity": ["cinema", "cinema"],
             "geometry": [Point(8.5, 49.1), Point(8.401, 49.001)]},
            crs="EPSG:4326",
        )
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        pois = OSMnxDataSource.load_points_of_interest(
            "Karlsruhe, Germany", (49.0, 8.4), limit=1, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "Near"

    def test_polygon_centroid_extraction(self, monkeypatch):
        """Covers the Polygon/MultiPolygon centroid branch (lines 201-202)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        poly = Polygon([(8.40, 49.00), (8.41, 49.00), (8.41, 49.01), (8.40, 49.01)])
        gdf = gpd.GeoDataFrame(
            {"name": ["PolyPOI"], "amenity": ["cinema"], "geometry": [poly]},
            crs="EPSG:4326",
        )
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.005, 8.405), limit=5, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "PolyPOI"

    def test_linestring_centroid_extraction(self, monkeypatch):
        """LineString is also in the centroid branch."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        line = LineString([(8.40, 49.00), (8.41, 49.01)])
        gdf = gpd.GeoDataFrame(
            {"name": ["LinePOI"], "amenity": ["cinema"], "geometry": [line]},
            crs="EPSG:4326",
        )
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.005, 8.405), limit=5, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "LinePOI"

    def test_nan_name_fallback(self, monkeypatch):
        """Covers NaN name → type-based name fallback (lines 209-210)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        gdf = gpd.GeoDataFrame(
            {"name": [np.nan], "amenity": ["cinema"], "geometry": [Point(8.4, 49.0)]},
            crs="EPSG:4326",
        )
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.0, 8.4), limit=5, categories=["cinema"],
        )
        assert len(pois) == 1
        assert "Cinema" in pois[0].name or "cinema" in pois[0].name.lower()

    def test_inner_exception_continues(self, monkeypatch):
        """Covers inner except handler per category (lines 220-222)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        monkeypatch.setattr(
            mdl.ox, "features_from_place",
            MagicMock(side_effect=RuntimeError("network")),
        )

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.0, 8.4), limit=5, categories=["cinema"],
        )
        # All categories fail → empty all_pois → fallback
        assert len(pois) == 1
        assert pois[0].name == "City Center"

    def test_outer_exception_fallback(self, monkeypatch):
        """Covers outer except handler (lines 260-263)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        # Raise during distance calculation by corrupting the returned data
        gdf = gpd.GeoDataFrame(
            {"name": ["A"], "amenity": ["cinema"], "geometry": [Point(8.4, 49.0)]},
            crs="EPSG:4326",
        )
        call_count = 0

        def _fake_features(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return gdf

        monkeypatch.setattr(mdl.ox, "features_from_place", _fake_features)
        # Poison np.sqrt to blow up during distance calc in the outer try
        original_sqrt = np.sqrt

        def bad_sqrt(x):
            raise TypeError("boom")

        monkeypatch.setattr(mdl.np, "sqrt", bad_sqrt)

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.0, 8.4), limit=5, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "City Center"

    def test_default_categories_when_none(self, monkeypatch):
        """categories=None uses the full default amenity list."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=empty))

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.0, 8.4), limit=5, categories=None,
        )
        # Falls through to empty → fallback
        assert pois[0].name == "City Center"

    def test_multipolygon_centroid(self, monkeypatch):
        """MultiPolygon is handled in the same branch as Polygon."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        p1 = Polygon([(8.40, 49.00), (8.41, 49.00), (8.41, 49.01), (8.40, 49.01)])
        p2 = Polygon([(8.42, 49.02), (8.43, 49.02), (8.43, 49.03), (8.42, 49.03)])
        mp = MultiPolygon([p1, p2])
        gdf = gpd.GeoDataFrame(
            {"name": ["MultiPOI"], "amenity": ["cinema"], "geometry": [mp]},
            crs="EPSG:4326",
        )
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        pois = OSMnxDataSource.load_points_of_interest(
            "Test", (49.01, 8.41), limit=5, categories=["cinema"],
        )
        assert len(pois) == 1
        assert pois[0].name == "MultiPOI"


# ═══════════════════════════════════════════════════════════════════════════════
# _load_from_osm & load_zones_for_optimization
# ═══════════════════════════════════════════════════════════════════════════════

def _make_osm_gdf():
    """OSM-like GeoDataFrame with public, private and customers zones."""
    poly1 = Polygon([(8.40, 49.00), (8.401, 49.00), (8.401, 49.001), (8.40, 49.001)])
    poly2 = Polygon([(8.41, 49.01), (8.411, 49.01), (8.411, 49.011), (8.41, 49.011)])
    poly3 = Polygon([(8.42, 49.02), (8.421, 49.02), (8.421, 49.021), (8.42, 49.021)])

    return gpd.GeoDataFrame(
        {
            "name": ["Public Lot", "Private Lot", np.nan],
            "access": ["public", "private", "customers"],
            "parking": ["surface", "underground", "multi-storey"],
            "capacity": [None, None, None],
            "geometry": [poly1, poly2, poly3],
        },
        crs="EPSG:4326",
    )


class TestLoadFromOsm:

    def test_filters_private_and_builds_zone_lookup_and_gdf(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        ds = _settings(limit=10, default_elasticity=-0.4, center_coords=(49.0, 8.4))
        src = OSMnxDataSource(ds)
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=_make_osm_gdf()))

        zones = src._load_from_osm()
        assert len(zones) == 1
        assert zones[0].name == "Public Lot"
        assert zones[0].id in src.zone_lookup
        assert src.gdf is not None and not src.gdf.empty

    def test_nan_name_gets_replaced(self, monkeypatch):
        """Zone with NaN name gets 'Parking Zone N'."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        poly = Polygon([(8.40, 49.00), (8.401, 49.00), (8.401, 49.001), (8.40, 49.001)])
        gdf = gpd.GeoDataFrame(
            {
                "name": [np.nan],
                "access": ["public"],
                "parking": ["surface"],
                "capacity": [None],
                "geometry": [poly],
            },
            crs="EPSG:4326",
        )
        src = OSMnxDataSource(_settings(limit=10, default_elasticity=-0.4))
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        zones = src._load_from_osm()
        assert len(zones) == 1
        assert zones[0].name.startswith("Parking Zone")

    def test_no_parking_column_defaults_priority(self, monkeypatch):
        """Covers the else branch where 'parking' column is missing (line 515)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        poly = Polygon([(8.40, 49.00), (8.401, 49.00), (8.401, 49.001), (8.40, 49.001)])
        gdf = gpd.GeoDataFrame(
            {
                "name": ["NoParkCol"],
                "access": ["public"],
                "capacity": [None],
                "geometry": [poly],
            },
            crs="EPSG:4326",
        )
        src = OSMnxDataSource(_settings(limit=10, default_elasticity=-0.4))
        monkeypatch.setattr(mdl.ox, "features_from_place", MagicMock(return_value=gdf))

        zones = src._load_from_osm()
        assert len(zones) == 1

    def test_osm_exception_returns_empty(self, monkeypatch):
        """Covers except branch in _load_from_osm (lines 589-593)."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        monkeypatch.setattr(
            mdl.ox, "features_from_place",
            MagicMock(side_effect=RuntimeError("OSM down")),
        )
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        zones = src._load_from_osm()
        assert zones == []


class TestLoadZonesForOptimization:

    def test_delegates_and_clusters(self):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))

        fake_zones = [MagicMock(id=1), MagicMock(id=2)]
        src._load_from_osm = MagicMock(return_value=fake_zones)
        src.cluster_zones = MagicMock(side_effect=lambda z: z)

        out = src.load_zones_for_optimization()

        src._load_from_osm.assert_called_once()
        src.cluster_zones.assert_called_once_with(fake_zones)
        assert out == fake_zones

    def test_resets_zone_lookup(self):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        src.zone_lookup = {"old": True}
        src._load_from_osm = MagicMock(return_value=[])
        src.cluster_zones = MagicMock(side_effect=lambda z: z)

        src.load_zones_for_optimization()
        assert src.zone_lookup == {}


# ═══════════════════════════════════════════════════════════════════════════════
# load_city
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadCity:

    def test_raises_on_no_zones(self):
        src = OSMnxDataSource(_settings())
        src.load_zones_for_optimization = MagicMock(return_value=[])
        with pytest.raises(ValueError, match="No parking zones found"):
            src.load_city()

    def test_builds_city_and_pois(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        ds = _settings(
            city_name="Karlsruhe, Germany",
            center_coords=(49.0, 8.4),
            poi_limit=2,
            default_elasticity=-0.4,
        )
        src = OSMnxDataSource(ds)

        z1 = src._create_zone_obj(1, "A", 10, 49.0, 8.4, 0.5, 2.0, 0.6)
        z2 = src._create_zone_obj(2, "B", 20, 49.2, 8.6, 0.5, 2.0, 0.6)
        src.load_zones_for_optimization = MagicMock(return_value=[z1, z2])

        pois = [
            mdl.PointOfInterest(id=1, name="poi1", position=(49.01, 8.41)),
            mdl.PointOfInterest(id=2, name="poi2", position=(49.02, 8.42)),
        ]
        monkeypatch.setattr(
            mdl.OSMnxDataSource, "load_points_of_interest",
            MagicMock(return_value=pois),
        )

        city = src.load_city()
        assert len(city.parking_zones) == 2
        assert len(city.point_of_interests) == 2
        assert "Karlsruhe" in city.name

    def test_bounds_have_padding(self, monkeypatch):
        import backend.services.datasources.osm.osmnx_loader as mdl

        src = OSMnxDataSource(_settings(default_elasticity=-0.4, poi_limit=1))
        z1 = src._create_zone_obj(1, "X", 10, 49.0, 8.4, 0.5, 2.0, 0.6)
        z2 = src._create_zone_obj(2, "Y", 20, 49.1, 8.5, 0.5, 2.0, 0.6)
        src.load_zones_for_optimization = MagicMock(return_value=[z1, z2])

        poi = mdl.PointOfInterest(id=1, name="p", position=(49.05, 8.45))
        monkeypatch.setattr(
            mdl.OSMnxDataSource, "load_points_of_interest",
            MagicMock(return_value=[poi]),
        )

        city = src.load_city()
        assert city.min_latitude < 49.0
        assert city.max_latitude > 49.1
        assert city.min_longitude < 8.4
        assert city.max_longitude > 8.5

    def test_single_zone_padding_uses_fallback(self, monkeypatch):
        """When max == min, padding uses 0.01 fallback."""
        import backend.services.datasources.osm.osmnx_loader as mdl

        src = OSMnxDataSource(_settings(default_elasticity=-0.4, poi_limit=1))
        z1 = src._create_zone_obj(1, "Only", 10, 49.0, 8.4, 0.5, 2.0, 0.6)
        src.load_zones_for_optimization = MagicMock(return_value=[z1])

        poi = mdl.PointOfInterest(id=1, name="p", position=(49.0, 8.4))
        monkeypatch.setattr(
            mdl.OSMnxDataSource, "load_points_of_interest",
            MagicMock(return_value=[poi]),
        )

        city = src.load_city()
        # With a single zone lat range is 0, so padding = 0.01
        assert city.min_latitude == pytest.approx(49.0 - 0.01, abs=1e-6)
        assert city.max_latitude == pytest.approx(49.0 + 0.01, abs=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
# _create_zone_obj
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateZoneObj:

    def _src(self):
        return OSMnxDataSource(_settings(default_elasticity=-0.4))

    def test_basic_creation(self):
        z = self._src()._create_zone_obj(1, "Z", 100, 49.0, 8.4, 0.5, 2.0, 0.6)
        assert z.id == 1
        assert z.name == "Z"
        assert z.maximum_capacity == 100
        assert z.current_capacity == 50
        assert z.current_fee == 2.0
        assert z.position == (49.0, 8.4)
        assert z.elasticity == -0.4
        assert z.short_term_share == 0.6

    def test_occupancy_clamped_above_1(self):
        z = self._src()._create_zone_obj(1, "Z", 100, 49.0, 8.4, 1.5, 2.0, 0.6)
        assert z.current_capacity == 100  # clamped to 1.0

    def test_occupancy_clamped_below_0(self):
        z = self._src()._create_zone_obj(1, "Z", 100, 49.0, 8.4, -0.5, 2.0, 0.6)
        assert z.current_capacity == 0  # clamped to 0.0

    def test_fee_rounding(self):
        z = self._src()._create_zone_obj(1, "Z", 100, 49.0, 8.4, 0.5, 2.333, 0.6)
        assert z.current_fee == 2.33


# ═══════════════════════════════════════════════════════════════════════════════
# get_gdf_with_results
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetGdfWithResults:

    def _src_with_gdf(self):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        src.gdf = gpd.GeoDataFrame(
            {"zone_id": [1, 2], "name": ["A", "B"],
             "geometry": [Point(8.4, 49.0), Point(8.5, 49.1)]},
            crs="EPSG:4326",
        )
        z1 = src._create_zone_obj(1, "A", 100, 49.0, 8.4, 0.5, 2.0, 0.6)
        z2 = src._create_zone_obj(2, "B", 200, 49.1, 8.5, 0.7, 3.0, 0.4)
        src.zone_lookup = {1: z1, 2: z2}
        return src

    def test_none_gdf_returns_empty(self):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        src.gdf = None
        result = src.get_gdf_with_results([])
        assert result.empty

    def test_empty_gdf_returns_empty(self):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        src.gdf = gpd.GeoDataFrame()
        result = src.get_gdf_with_results([])
        assert result.empty

    def test_merges_optimized_zones(self):
        src = self._src_with_gdf()
        opt = [
            SimpleNamespace(id=1, new_fee=3.0, predicted_occupancy=0.7, predicted_revenue=100.0),
            SimpleNamespace(id=2, new_fee=4.5, predicted_occupancy=0.8, predicted_revenue=200.0),
        ]
        result = src.get_gdf_with_results(opt)

        assert not result.empty
        assert result.loc[result["zone_id"] == 1, "new_fee"].values[0] == 3.0
        assert result.loc[result["zone_id"] == 1, "old_fee"].values[0] == 2.0
        assert result.loc[result["zone_id"] == 2, "predicted_revenue"].values[0] == 200.0

    def test_unmatched_zone_stays_nan(self):
        src = self._src_with_gdf()
        # Only optimize zone 1, zone 2 stays NaN
        opt = [SimpleNamespace(id=1, new_fee=3.0, predicted_occupancy=0.7, predicted_revenue=100.0)]
        result = src.get_gdf_with_results(opt)

        assert np.isnan(result.loc[result["zone_id"] == 2, "new_fee"].values[0])

    def test_no_optimized_zones_all_nan(self):
        src = self._src_with_gdf()
        result = src.get_gdf_with_results([])
        assert np.isnan(result["new_fee"].values[0])

    def test_fee_rounded_to_050(self):
        """new_fee is rounded to nearest 0.50 step."""
        src = self._src_with_gdf()
        opt = [SimpleNamespace(id=1, new_fee=2.3, predicted_occupancy=0.7, predicted_revenue=100.0)]
        result = src.get_gdf_with_results(opt)
        # round(2.3 * 2) / 2 = round(4.6) / 2 = 5 / 2 = 2.5
        assert result.loc[result["zone_id"] == 1, "new_fee"].values[0] == 2.5


# ═══════════════════════════════════════════════════════════════════════════════
# export_results_to_csv
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportResultsToCsv:

    def test_delegates_to_parent(self, monkeypatch, tmp_path):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))

        z1 = src._create_zone_obj(1, "A", 100, 49.0, 8.4, 0.5, 2.0, 0.6)
        src.zone_lookup = {1: z1}

        opt = SimpleNamespace(id=1, new_fee=3.0, predicted_occupancy=0.7, predicted_revenue=150.0)

        out_file = str(tmp_path / "out.csv")
        src.export_results_to_csv([opt], filename=out_file)

        assert os.path.exists(out_file)
        df = pd.read_csv(out_file)
        assert len(df) == 1
        assert "current_fee_new" in df.columns

    def test_empty_zone_lookup_no_file(self, tmp_path, capsys):
        src = OSMnxDataSource(_settings(default_elasticity=-0.4))
        src.zone_lookup = {}

        out_file = str(tmp_path / "out.csv")
        src.export_results_to_csv([], filename=out_file)

        assert not os.path.exists(out_file)
        captured = capsys.readouterr()
        assert "No zones" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
# Construction edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstruction:

    def test_defaults(self):
        src = OSMnxDataSource(_settings())
        assert src.city_name == "Karlsruhe, Germany"
        assert src.gdf is None
        assert src.zone_lookup == {}
        assert src.utm_epsg > 0

    def test_none_tariffs_default_to_empty(self):
        src = OSMnxDataSource(_settings(tariffs=None))
        assert src.tariffs == {}

