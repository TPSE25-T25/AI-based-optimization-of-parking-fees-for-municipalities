from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from backend.services.datasources.mobidata.mobidata_datasource import MobiDataDataSource


def _settings(
    limit=10,
    city_name="Karlsruhe",
    center_coords=(49.0069, 8.4037),
    tariffs=None,
    default_elasticity=-0.3,   # IMPORTANT: must be <= 0 for your pydantic schema
    poi_limit=5,
    search_radius=5000,
    default_current_fee=2.0,
    random_seed=42,
):
    return SimpleNamespace(
        limit=limit,
        city_name=city_name,
        center_coords=center_coords,
        tariffs=tariffs,
        default_elasticity=default_elasticity,
        poi_limit=poi_limit,
        search_radius=search_radius,
        default_current_fee=default_current_fee,
        random_seed=random_seed,
    )


def _poi(id=1, name="poi", position=(49.0, 8.4)):
    # minimal fields that your City model appears to require
    return {"id": id, "name": name, "position": list(position)}


def test_init_raises_typeerror_if_center_coords_none():
    # Because ParkingDataSource.__init__ unpacks center_coords
    ds = _settings(center_coords=None)
    with pytest.raises(TypeError):
        MobiDataDataSource(ds)


def test_load_zones_for_optimization_raises_if_api_returns_empty():
    ds = _settings(center_coords=(49.0, 8.4))
    src = MobiDataDataSource(ds)

    src.api.search_nearby = MagicMock(return_value=[])

    with pytest.raises(ValueError) as exc:
        src.load_zones_for_optimization()

    assert "No parking sites found" in str(exc.value)


def test_convert_site_to_zone_estimates_capacity_and_occupancy_and_fee():
    ds = _settings(default_current_fee=2.5, default_elasticity=-0.77)
    src = MobiDataDataSource(ds)

    site = {
        "id": 123,
        "name": "Hauptbahnhof P1",
        "lat": 49.0,
        "lon": 8.4,
        "capacity": 0,  # triggers estimate
        "type": "UNDERGROUND",
        "realtime_free_capacity": 10,
        "has_fee": True,
    }

    z = src._convert_site_to_parking_zone_input(site, index=0)

    assert z.id == 123
    assert z.position == [49.0, 8.4]
    assert z.maximum_capacity == 150  # UNDERGROUND -> 150
    assert z.current_capacity == 140  # 150 - 10
    assert z.current_fee == 2.5
    assert z.elasticity == -0.77
    assert z.min_fee == 0.5
    assert z.max_fee == 5.0


def test_convert_site_to_zone_defaults_occupancy_if_no_realtime():
    ds = _settings(default_current_fee=1.0, default_elasticity=-0.3)
    src = MobiDataDataSource(ds)

    site = {
        "id": 1,
        "lat": 49.0,
        "lon": 8.4,
        "capacity": 100,
    }

    z = src._convert_site_to_parking_zone_input(site, index=0)
    assert z.maximum_capacity == 100
    assert z.current_capacity == 60  # int(100 * 0.6)
    assert z.current_fee == 1.0
    assert z.elasticity == -0.3


def test_convert_site_to_zone_fee_zero_if_has_fee_false():
    ds = _settings(default_current_fee=9.0, default_elasticity=-0.3)
    src = MobiDataDataSource(ds)

    site = {
        "id": 2,
        "lat": 49.0,
        "lon": 8.4,
        "capacity": 50,
        "has_fee": False,
    }

    z = src._convert_site_to_parking_zone_input(site, index=0)
    assert z.current_fee == 0.0


def test_convert_spot_to_zone_paid_vs_free():
    ds = _settings(default_current_fee=3.0, default_elasticity=-0.12)
    src = MobiDataDataSource(ds)

    paid_spot = {"id": 10, "lat": 49.0, "lon": 8.4, "has_fee": True, "is_occupied": True}
    free_spot = {"id": 11, "lat": 49.1, "lon": 8.5, "has_fee": False, "is_occupied": False}

    z1 = src._convert_spot_to_parking_zone_input(paid_spot, index=0)
    z2 = src._convert_spot_to_parking_zone_input(free_spot, index=1)

    assert z1.maximum_capacity == 1
    assert z1.current_capacity == 1
    assert z1.current_fee == 3.0
    assert z1.min_fee == 0.5
    assert z1.max_fee == 5.0
    assert z1.elasticity == -0.12

    assert z2.maximum_capacity == 1
    assert z2.current_capacity == 0
    assert z2.current_fee == 0.0
    assert z2.min_fee == 0.0
    assert z2.max_fee == 0.0


def test_load_zones_for_optimization_converts_sites_and_spots_and_skips_bad_items(capsys):
    ds = _settings(limit=10, center_coords=(49.0, 8.4), default_elasticity=-0.3)
    src = MobiDataDataSource(ds)

    # Avoid real clustering
    src.cluster_zones = MagicMock(side_effect=lambda zones: zones)

    api_items = [
        {"_type": "site", "id": 1, "name": "Site 1", "lat": 49.0, "lon": 8.4, "capacity": 10, "realtime_free_capacity": 2},
        {"_type": "spot", "id": 2, "lat": 49.01, "lon": 8.41, "has_fee": True, "is_occupied": False},
        {"_type": "site", "id": 999, "name": "Bad Site", "lon": 8.5, "capacity": 10},  # missing lat -> raises
    ]
    src.api.search_nearby = MagicMock(return_value=api_items)

    zones = src.load_zones_for_optimization()
    out = capsys.readouterr().out

    assert len(zones) == 2
    assert hasattr(src, "original_zones")
    assert len(src.original_zones) == 2
    assert "Skipped" in out
    src.cluster_zones.assert_called_once()


def test_load_city_builds_city_and_calls_pois_loader(monkeypatch):
    import backend.services.datasources.mobidata.mobidata_datasource as mdl

    ds = _settings(city_name="Karlsruhe", center_coords=(49.0, 8.4), poi_limit=2, default_elasticity=-0.3)
    src = MobiDataDataSource(ds)

    # Build real ParkingZone objects via the datasource conversion (so City validation passes)
    z1 = src._convert_site_to_parking_zone_input(
        {"id": 1, "name": "A", "lat": 49.0, "lon": 8.4, "capacity": 10, "realtime_free_capacity": 5}, index=0
    )
    z2 = src._convert_site_to_parking_zone_input(
        {"id": 2, "name": "B", "lat": 49.2, "lon": 8.6, "capacity": 20, "realtime_free_capacity": 10}, index=1
    )
    src.load_zones_for_optimization = MagicMock(return_value=[z1, z2])

    # POIs must satisfy City model requirements
    pois = [_poi(1, "poi1", (49.05, 8.45)), _poi(2, "poi2", (49.06, 8.46))]
    monkeypatch.setattr(mdl.OSMnxDataSource, "load_points_of_interest", MagicMock(return_value=pois))

    city = src.load_city()

    mdl.OSMnxDataSource.load_points_of_interest.assert_called_once_with("Karlsruhe", (49.0, 8.4), limit=2)

    assert city.name == "Karlsruhe"
    assert len(city.parking_zones) == 2
    assert len(city.point_of_interests) == 2

    # Bounds include padding (0.02 for this range)
    assert city.min_latitude == pytest.approx(49.0 - 0.02, rel=1e-6)
    assert city.max_latitude == pytest.approx(49.2 + 0.02, rel=1e-6)
    assert city.min_longitude == pytest.approx(8.4 - 0.02, rel=1e-6)
    assert city.max_longitude == pytest.approx(8.6 + 0.02, rel=1e-6)


def test_export_results_to_csv_prints_if_no_original_zones(capsys):
    ds = _settings()
    src = MobiDataDataSource(ds)

    src.export_results_to_csv(optimized_zones=[], filename="x.csv")
    out = capsys.readouterr().out
    assert "No zones loaded" in out


def test_context_manager_closes_api():
    ds = _settings()
    src = MobiDataDataSource(ds)
    src.api.close = MagicMock()

    with src as ctx:
        assert ctx is src

    src.api.close.assert_called_once()
