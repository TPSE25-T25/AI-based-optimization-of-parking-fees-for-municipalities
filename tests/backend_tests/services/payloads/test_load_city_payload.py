import pytest
from pydantic import ValidationError
from backend.services.payloads.load_city_payload import (
    LoadCityRequest, LoadCityResponse,
    ReverseGeoLocationRequest, ReverseGeoLocationResponse,
)
from backend.services.models.city import City


def test_load_city_request_defaults():
    r = LoadCityRequest()
    assert r.data_source == "osmnx"
    assert r.limit == 1000
    assert r.city_name == "Karlsruhe, Germany"
    assert r.center_lat == 49.0069
    assert r.center_lon == 8.4037
    assert r.seed == 42
    assert r.poi_limit == 50
    assert r.default_elasticity == -0.4
    assert r.search_radius == 10000
    assert r.default_current_fee == 2.0
    assert r.tariffs is None


def test_load_city_request_custom():
    r = LoadCityRequest(data_source="mobidata", limit=50, city_name="Berlin", tariffs={"a": 1.0})
    assert r.data_source == "mobidata"
    assert r.limit == 50
    assert r.tariffs == {"a": 1.0}


def test_load_city_response():
    city = City(id=1, name="Test", min_latitude=0, max_latitude=1, min_longitude=0, max_longitude=1)
    r = LoadCityResponse(city=city)
    assert r.city.name == "Test"


def test_reverse_geo_request():
    r = ReverseGeoLocationRequest(center_lat=49.0, center_lon=8.4)
    assert r.center_lat == 49.0
    assert r.center_lon == 8.4


def test_reverse_geo_response():
    r = ReverseGeoLocationResponse(geo_info={"city": "Karlsruhe"})
    assert r.geo_info["city"] == "Karlsruhe"


# --- Edge cases ---

def test_load_city_request_optional_none():
    r = LoadCityRequest(default_elasticity=None, search_radius=None, default_current_fee=None)
    assert r.default_elasticity is None
    assert r.search_radius is None
    assert r.default_current_fee is None


def test_load_city_request_empty_tariffs():
    r = LoadCityRequest(tariffs={})
    assert r.tariffs == {}


def test_load_city_request_wrong_type():
    with pytest.raises(ValidationError):
        LoadCityRequest(limit="not_a_number")


def test_load_city_response_missing_city():
    with pytest.raises(ValidationError):
        LoadCityResponse()


def test_reverse_geo_request_missing_fields():
    with pytest.raises(ValidationError):
        ReverseGeoLocationRequest()


def test_reverse_geo_response_empty_dict():
    r = ReverseGeoLocationResponse(geo_info={})
    assert r.geo_info == {}
