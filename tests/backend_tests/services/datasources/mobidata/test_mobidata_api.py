# tests/backend_tests/services/datasources/mobidata/test_mobidata_api.py

from unittest.mock import MagicMock
import pytest
import requests

# ✅ Adjust if your module path differs
from backend.services.datasources.mobidata.mobidata_api import MobiDataAPI


def _make_response(json_data=None, status_ok=True):
    """Create a fake requests response object."""
    resp = MagicMock()
    resp.json.return_value = json_data if json_data is not None else {"ok": True}
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = requests.HTTPError("boom")
    return resp


def test_init_sets_headers_and_timeout():
    api = MobiDataAPI(timeout=11)

    assert api.timeout == 11
    # headers set on session
    assert api.session.headers["Accept"] == "application/json"
    assert "User-Agent" in api.session.headers


def test__get_builds_url_passes_params_and_timeout(monkeypatch):
    api = MobiDataAPI(timeout=9)
    fake_resp = _make_response({"hello": "world"}, status_ok=True)

    api.session.get = MagicMock(return_value=fake_resp)

    out = api._get("/v3/sources", params={"a": 1})

    api.session.get.assert_called_once()
    called_url = api.session.get.call_args.args[0]
    called_kwargs = api.session.get.call_args.kwargs

    assert called_url == f"{api.BASE_URL}/v3/sources"
    assert called_kwargs["params"] == {"a": 1}
    assert called_kwargs["timeout"] == 9
    assert out == {"hello": "world"}
    fake_resp.raise_for_status.assert_called_once()
    fake_resp.json.assert_called_once()


def test__get_raises_on_http_error(monkeypatch):
    api = MobiDataAPI(timeout=5)
    fake_resp = _make_response({"err": True}, status_ok=False)
    api.session.get = MagicMock(return_value=fake_resp)

    with pytest.raises(requests.HTTPError):
        api._get("/v3/sources")


def test_get_parking_sites_builds_params_correctly(monkeypatch):
    api = MobiDataAPI()
    api._get = MagicMock(return_value={"items": [], "total_count": 0})

    api.get_parking_sites(
        source_uid="S1",
        name="Bahnhof",
        lat=49.0,
        lon=8.4,
        radius=500,
        lat_min=48.9,
        lat_max=49.1,
        lon_min=8.3,
        lon_max=8.5,
        limit=123,
        start=10,
        purpose="CAR",
        site_type="UNDERGROUND",
    )

    api._get.assert_called_once()
    endpoint, params = api._get.call_args.args

    assert endpoint == "/v3/parking-sites"
    assert params == {
        "source_uid": "S1",
        "name": "Bahnhof",
        "lat": 49.0,
        "lon": 8.4,
        "radius": 500,
        "lat_min": 48.9,
        "lat_max": 49.1,
        "lon_min": 8.3,
        "lon_max": 8.5,
        "limit": 123,
        "start": 10,
        "purpose": "CAR",
        "type": "UNDERGROUND",  # site_type -> type
    }


def test_get_parking_spots_builds_params_correctly(monkeypatch):
    api = MobiDataAPI()
    api._get = MagicMock(return_value={"items": [], "total_count": 0})

    api.get_parking_spots(
        source_uid="S2",
        lat=49.0,
        lon=8.4,
        radius=1000,
        lat_min=48.0,
        lat_max=50.0,
        lon_min=8.0,
        lon_max=9.0,
        limit=50,
        start=5,
    )

    endpoint, params = api._get.call_args.args
    assert endpoint == "/v3/parking-spots"
    assert params == {
        "source_uid": "S2",
        "lat": 49.0,
        "lon": 8.4,
        "radius": 1000,
        "lat_min": 48.0,
        "lat_max": 50.0,
        "lon_min": 8.0,
        "lon_max": 9.0,
        "limit": 50,
        "start": 5,
    }


def test_search_nearby_paginates_sites_then_spots_and_sets_type(monkeypatch):
    api = MobiDataAPI()

    # Simulate:
    # - sites: 2 pages (2 items + 1 item), total_count=3
    # - spots: 1 page (2 items), total_count=2
    sites_page1 = {"items": [{"id": "s1"}, {"id": "s2"}], "total_count": 3}
    sites_page2 = {"items": [{"id": "s3"}], "total_count": 3}
    sites_page3 = {"items": [], "total_count": 3}

    spots_page1 = {"items": [{"id": "p1"}, {"id": "p2"}], "total_count": 2}
    spots_page2 = {"items": [], "total_count": 2}

    api.get_parking_sites = MagicMock(side_effect=[sites_page1, sites_page2, sites_page3])
    api.get_parking_spots = MagicMock(side_effect=[spots_page1, spots_page2])

    items = api.search_nearby(lat=49.0, lon=8.4, radius_meters=5000, limit=10)

    # 3 sites + 2 spots = 5
    assert len(items) == 5

    # types tagged
    assert all(i["_type"] == "site" for i in items[:3])
    assert all(i["_type"] == "spot" for i in items[3:])

    # check pagination parameters for sites
    # first call start=0, second call start=2
    assert api.get_parking_sites.call_args_list[0].kwargs["start"] == 0
    assert api.get_parking_sites.call_args_list[1].kwargs["start"] == 2

    # spots called after sites
    assert api.get_parking_spots.call_count >= 1


def test_search_nearby_respects_limit_and_trims(monkeypatch):
    api = MobiDataAPI()

    # Many site results, but limit=3 -> should trim to 3 and never fetch spots
    sites_page1 = {"items": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}, {"id": "s4"}], "total_count": 100}

    api.get_parking_sites = MagicMock(return_value=sites_page1)
    api.get_parking_spots = MagicMock(side_effect=AssertionError("should not fetch spots when limit reached by sites"))

    items = api.search_nearby(lat=49.0, lon=8.4, limit=3)

    assert len(items) == 3
    assert all(i["_type"] == "site" for i in items)


def test_search_nearby_stops_if_sites_empty_then_tries_spots(monkeypatch):
    api = MobiDataAPI()

    api.get_parking_sites = MagicMock(return_value={"items": [], "total_count": 0})
    api.get_parking_spots = MagicMock(return_value={"items": [{"id": "p1"}], "total_count": 1})

    items = api.search_nearby(lat=49.0, lon=8.4, limit=10)

    assert len(items) == 1
    assert items[0]["_type"] == "spot"


def test_context_manager_closes_session(monkeypatch):
    api = MobiDataAPI()
    api.session.close = MagicMock()

    with api as client:
        assert client is api

    api.session.close.assert_called_once()
