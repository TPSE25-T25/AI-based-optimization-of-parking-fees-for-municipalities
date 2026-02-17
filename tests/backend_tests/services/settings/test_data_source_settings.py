import pytest
from pydantic import ValidationError
from backend.services.settings.data_source_settings import DataSourceSettings, KARLSRUHE_TARIFFS


def test_default_values():
    s = DataSourceSettings()
    assert s.data_source == "osmnx"
    assert s.limit == 1000
    assert s.city_name == "Karlsruhe, Germany"
    assert s.center_coords == (49.0069, 8.4037)
    assert s.random_seed == 42
    assert s.poi_limit == 50
    assert s.default_elasticity == -0.4
    assert s.search_radius == 10000
    assert s.default_current_fee == 2.0
    assert s.tariffs == KARLSRUHE_TARIFFS


def test_custom_values():
    s = DataSourceSettings(
        data_source="mobidata",
        limit=500,
        city_name="Berlin, Germany",
        center_coords=(52.52, 13.405),
        random_seed=99,
        poi_limit=20,
        default_elasticity=-0.6,
        search_radius=5000,
        default_current_fee=3.5,
        tariffs={"zone_a": 1.0},
    )
    assert s.data_source == "mobidata"
    assert s.limit == 500
    assert s.city_name == "Berlin, Germany"
    assert s.center_coords == (52.52, 13.405)
    assert s.random_seed == 99
    assert s.poi_limit == 20
    assert s.default_elasticity == -0.6
    assert s.search_radius == 5000
    assert s.default_current_fee == 3.5
    assert s.tariffs == {"zone_a": 1.0}


def test_tariffs_default_is_copy():
    s = DataSourceSettings()
    s.tariffs["new_zone"] = 9.99
    assert "new_zone" not in KARLSRUHE_TARIFFS


# --- Edge cases ---

def test_limit_minimum_boundary():
    s = DataSourceSettings(limit=1)
    assert s.limit == 1


def test_limit_below_minimum():
    with pytest.raises(ValidationError):
        DataSourceSettings(limit=0)


def test_poi_limit_minimum_boundary():
    s = DataSourceSettings(poi_limit=1)
    assert s.poi_limit == 1


def test_poi_limit_below_minimum():
    with pytest.raises(ValidationError):
        DataSourceSettings(poi_limit=0)


def test_search_radius_minimum_boundary():
    s = DataSourceSettings(search_radius=1000)
    assert s.search_radius == 1000


def test_search_radius_below_minimum():
    with pytest.raises(ValidationError):
        DataSourceSettings(search_radius=999)


def test_default_current_fee_zero():
    s = DataSourceSettings(default_current_fee=0)
    assert s.default_current_fee == 0


def test_default_current_fee_negative():
    with pytest.raises(ValidationError):
        DataSourceSettings(default_current_fee=-1)


def test_empty_tariffs():
    s = DataSourceSettings(tariffs={})
    assert s.tariffs == {}
