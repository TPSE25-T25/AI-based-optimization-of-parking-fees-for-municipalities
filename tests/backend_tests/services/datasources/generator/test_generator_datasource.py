"""Tests for GeneratorDataSource with edge cases."""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.datasources.generator.generator_datasource import GeneratorDataSource
from backend.services.models.city import City


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _settings(**overrides):
    base = dict(
        data_source="generated",
        limit=5,
        city_name="TestCity",
        center_coords=(49.0, 8.4),
        tariffs={},
        default_elasticity=-0.3,
        poi_limit=3,
        search_radius=5000,
        default_current_fee=2.0,
        random_seed=42,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestInit:

    def test_default_construction(self):
        src = GeneratorDataSource(_settings())
        assert src.city_name == "TestCity"
        assert src.limit == 5
        assert src.center_coords == (49.0, 8.4)
        assert src.random_seed == 42
        assert src.city_generator is not None

    def test_custom_seed_propagates(self):
        src = GeneratorDataSource(_settings(random_seed=99))
        assert src.random_seed == 99

    def test_inherits_parking_data_source_attrs(self):
        src = GeneratorDataSource(_settings(
            tariffs={"station": 3.0},
            default_elasticity=-0.5,
            poi_limit=10,
            search_radius=8000,
            default_current_fee=3.5,
        ))
        assert src.tariffs == {"station": 3.0}
        assert src.default_elasticity == -0.5
        assert src.poi_limit == 10
        assert src.search_radius == 8000
        assert src.default_current_fee == 3.5

    def test_none_seed(self):
        """None seed should still construct without error."""
        src = GeneratorDataSource(_settings(random_seed=None))
        assert src.city_generator is not None


# ---------------------------------------------------------------------------
# load_city
# ---------------------------------------------------------------------------

class TestLoadCity:

    def test_returns_city_instance(self):
        src = GeneratorDataSource(_settings(limit=3, poi_limit=2))
        city = src.load_city()
        assert isinstance(city, City)

    def test_city_has_expected_name(self):
        src = GeneratorDataSource(_settings(city_name="Hamburg"))
        city = src.load_city()
        assert city.name == "Hamburg"

    def test_parking_zones_count_matches_limit(self):
        src = GeneratorDataSource(_settings(limit=7))
        city = src.load_city()
        assert len(city.parking_zones) == 7

    def test_pois_count_matches_poi_limit(self):
        src = GeneratorDataSource(_settings(poi_limit=4, limit=3))
        city = src.load_city()
        assert len(city.point_of_interests) == 4

    def test_center_coords_affect_bounds(self):
        src = GeneratorDataSource(_settings(center_coords=(52.5, 13.4)))
        city = src.load_city()
        assert city.min_latitude < 52.5 < city.max_latitude
        assert city.min_longitude < 13.4 < city.max_longitude

    def test_seed_reproducibility(self):
        """Same seed → identical results."""
        c1 = GeneratorDataSource(_settings(random_seed=7)).load_city()
        c2 = GeneratorDataSource(_settings(random_seed=7)).load_city()
        fees1 = [z.current_fee for z in c1.parking_zones]
        fees2 = [z.current_fee for z in c2.parking_zones]
        assert fees1 == fees2

    def test_different_seeds_differ(self):
        c1 = GeneratorDataSource(_settings(random_seed=1)).load_city()
        c2 = GeneratorDataSource(_settings(random_seed=999)).load_city()
        fees1 = [z.current_fee for z in c1.parking_zones]
        fees2 = [z.current_fee for z in c2.parking_zones]
        assert fees1 != fees2

    def test_zero_poi_limit(self):
        """0 POIs requested → city has no POIs."""
        src = GeneratorDataSource(_settings(poi_limit=0, limit=2))
        city = src.load_city()
        assert len(city.point_of_interests) == 0

    def test_single_parking_zone(self):
        src = GeneratorDataSource(_settings(limit=1, poi_limit=1))
        city = src.load_city()
        assert len(city.parking_zones) == 1

    def test_large_zone_count(self):
        src = GeneratorDataSource(_settings(limit=50, poi_limit=1))
        city = src.load_city()
        assert len(city.parking_zones) == 50

    def test_zones_have_valid_positions(self):
        src = GeneratorDataSource(_settings(limit=5, center_coords=(49.0, 8.4)))
        city = src.load_city()
        for z in city.parking_zones:
            lat, lon = z.position
            assert city.min_latitude <= lat <= city.max_latitude
            assert city.min_longitude <= lon <= city.max_longitude

    def test_zones_have_positive_capacity(self):
        src = GeneratorDataSource(_settings(limit=10))
        city = src.load_city()
        for z in city.parking_zones:
            assert z.maximum_capacity >= 1
            assert 0 <= z.current_capacity <= z.maximum_capacity

    def test_zones_have_nonnegative_fee(self):
        src = GeneratorDataSource(_settings(limit=10))
        city = src.load_city()
        for z in city.parking_zones:
            assert z.current_fee >= 0

    def test_zones_sequential_ids(self):
        src = GeneratorDataSource(_settings(limit=5))
        city = src.load_city()
        ids = [z.id for z in city.parking_zones]
        assert ids == list(range(1, 6))

    def test_delegates_to_city_generator(self):
        src = GeneratorDataSource(_settings(limit=3, poi_limit=2))
        fake_city = City(
            id=1, name="Fake", min_latitude=48.9, max_latitude=49.1,
            min_longitude=8.3, max_longitude=8.5,
        )
        src.city_generator.generate_simple_city = MagicMock(return_value=fake_city)

        result = src.load_city()

        src.city_generator.generate_simple_city.assert_called_once_with(
            name="TestCity",
            center_lat=49.0,
            center_lon=8.4,
            num_pois=2,
            num_parking_zones=3,
        )
        assert result is fake_city


# ---------------------------------------------------------------------------
# load_zones_for_optimization
# ---------------------------------------------------------------------------

class TestLoadZonesForOptimization:

    def test_returns_city_object(self):
        """load_zones_for_optimization delegates to load_city."""
        src = GeneratorDataSource(_settings(limit=3))
        result = src.load_zones_for_optimization()
        # The method just calls self.load_city(), returning a City
        assert isinstance(result, City)

    def test_delegates_to_load_city(self):
        src = GeneratorDataSource(_settings())
        sentinel = object()
        src.load_city = MagicMock(return_value=sentinel)

        result = src.load_zones_for_optimization()

        src.load_city.assert_called_once()
        assert result is sentinel
