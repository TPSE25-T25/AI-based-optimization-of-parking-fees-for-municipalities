# tests/datasources/test_city_data_loader.py

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

# ✅ Adjust this import to match where CityDataLoader actually lives in your project:
# Example based on your screenshots:
from backend.services.datasources.city_data_loader import CityDataLoader


def _settings(source: str):
    """
    CityDataLoader only reads `datasource.data_source` and passes the object onward.
    Using SimpleNamespace keeps tests independent from DataSourceSettings constructor requirements.
    """
    return SimpleNamespace(data_source=source)


@pytest.mark.parametrize(
    "source, class_name",
    [
        ("osmnx", "OSMnxDataSource"),
        ("mobidata", "MobiDataDataSource"),
        ("generated", "GeneratorDataSource"),
    ],
)
def test_init_selects_correct_loader(monkeypatch, source, class_name):
    """
    Ensures the correct concrete datasource is instantiated depending on datasource.data_source.
    """
    # Import the module under test so we can patch the names CityDataLoader uses
    import backend.services.datasources.city_data_loader as mdl

    loader_instance = MagicMock(name="loader_instance")

    # Patch only the expected datasource class to return our mock instance
    # and also patch the others to fail if they are accidentally called.
    def _make_ctor(expected_name):
        def _ctor(*args, **kwargs):
            return loader_instance

        _ctor.__name__ = expected_name
        return _ctor

    for name in ["OSMnxDataSource", "MobiDataDataSource", "GeneratorDataSource"]:
        if name == class_name:
            monkeypatch.setattr(mdl, name, MagicMock(side_effect=lambda **kw: loader_instance))
        else:
            monkeypatch.setattr(
                mdl,
                name,
                MagicMock(side_effect=AssertionError(f"{name} should not be instantiated for source={source}")),
            )

    ds = _settings(source)
    loader = CityDataLoader(ds)

    # correct internal loader selected
    assert loader.loader is loader_instance


def test_init_invalid_source_raises_value_error():
    ds = _settings("invalid_source")
    with pytest.raises(ValueError) as exc:
        CityDataLoader(ds)
    assert "Invalid source" in str(exc.value)


def test_load_zones_for_optimization_delegates_to_loader(monkeypatch):
    import backend.services.datasources.city_data_loader as mdl

    # fake loader with a known return value
    loader_instance = MagicMock()
    expected = [MagicMock(), MagicMock()]
    loader_instance.load_zones_for_optimization.return_value = expected

    # make CityDataLoader pick OSMnxDataSource path and return our fake loader
    monkeypatch.setattr(mdl, "OSMnxDataSource", MagicMock(return_value=loader_instance))

    ds = _settings("osmnx")
    loader = CityDataLoader(ds)

    result = loader.load_zones_for_optimization(limit=123)

    loader_instance.load_zones_for_optimization.assert_called_once_with(123)
    assert result == expected


def test_load_city_delegates_to_loader(monkeypatch):
    import backend.services.datasources.city_data_loader as mdl

    loader_instance = MagicMock()
    expected_city = MagicMock()
    loader_instance.load_city.return_value = expected_city

    monkeypatch.setattr(mdl, "MobiDataDataSource", MagicMock(return_value=loader_instance))

    ds = _settings("mobidata")
    loader = CityDataLoader(ds)

    result = loader.load_city()

    loader_instance.load_city.assert_called_once_with()
    assert result is expected_city


def test_export_results_for_superset_delegates_to_loader(monkeypatch):
    import backend.services.datasources.city_data_loader as mdl

    loader_instance = MagicMock()

    monkeypatch.setattr(mdl, "GeneratorDataSource", MagicMock(return_value=loader_instance))

    ds = _settings("generated")
    loader = CityDataLoader(ds)

    optimized_zones = [{"id": 1}, {"id": 2}]
    loader.export_results_for_superset(optimized_zones, filename="out.csv")

    loader_instance.export_results_to_csv.assert_called_once_with(optimized_zones, "out.csv")
