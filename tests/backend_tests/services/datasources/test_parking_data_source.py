# tests/backend_tests/services/datasources/test_parking_data_source_base.py

from types import SimpleNamespace
import pandas as pd
import numpy as np
import pytest

# ✅ Adjust this import to your actual file path
# Example if the class is in: backend/services/datasources/parking_data_source.py
from backend.services.datasources.parking_data_source import ParkingDataSource


class DummyParkingDataSource(ParkingDataSource):
    """Concrete subclass to allow instantiation of abstract base class in tests."""
    def load_city(self):
        raise NotImplementedError

    def load_zones_for_optimization(self, limit: int = 1000):
        raise NotImplementedError


def _ds_settings(
    limit=1000,
    city_name="Karlsruhe",
    center_coords=(49.0069, 8.4037),
    tariffs=None,
    default_elasticity=0.3,
    poi_limit=100,
    search_radius=2500,
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


def _zone(
    id="z1",
    name="Zone 1",
    maximum_capacity=10,
    current_capacity=5,
    position=(49.0, 8.4),
    short_term_share=0.6,
    current_fee=2.0,
):
    # Using SimpleNamespace keeps tests independent from your schema implementation
    return SimpleNamespace(
        id=id,
        name=name,
        maximum_capacity=maximum_capacity,
        current_capacity=current_capacity,
        position=position,
        short_term_share=short_term_share,
        current_fee=current_fee,
    )


def _opt_zone(
    id="z1",
    new_fee=3.1,
    predicted_occupancy=0.8,
    predicted_revenue=100.0,
):
    return SimpleNamespace(
        id=id,
        new_fee=new_fee,
        predicted_occupancy=predicted_occupancy,
        predicted_revenue=predicted_revenue,
    )


def test_init_sets_attributes_from_settings():
    ds = _ds_settings(
        limit=123,
        city_name="X",
        center_coords=(1.1, 2.2),
        tariffs={"A": 1.0},
        default_elasticity=0.9,
        poi_limit=77,
        search_radius=999,
        default_current_fee=4.5,
        random_seed=7,
    )
    s = DummyParkingDataSource(ds)

    assert s.limit == 123
    assert s.city_name == "X"
    assert s.center_coords == (1.1, 2.2)
    assert s.center_lat == 1.1
    assert s.center_lon == 2.2
    assert s.tariffs == {"A": 1.0}
    assert s.default_elasticity == 0.9
    assert s.poi_limit == 77
    assert s.search_radius == 999
    assert s.default_current_fee == 4.5
    assert s.random_seed == 7


def test_cluster_zones_empty_returns_empty(monkeypatch):
    # If empty, it should return [] and never call KMeans
    import backend.services.datasources.parking_data_source as mdl

    monkeypatch.setattr(mdl, "KMeans", lambda *a, **k: (_ for _ in ()).throw(AssertionError("KMeans should not be called")))
    s = DummyParkingDataSource(_ds_settings())

    assert s.cluster_zones([]) == []


def test_cluster_zones_calls_kmeans_with_expected_clusters(monkeypatch, capsys):
    """
    For 30 zones => n_clusters = max(1, int(30/15)) = 2
    Ensures KMeans is created with correct params and fit called with Nx2 coords.
    """
    import backend.services.datasources.parking_data_source as mdl

    created = {}

    class FakeKMeans:
        def __init__(self, n_clusters, random_state, n_init):
            created["n_clusters"] = n_clusters
            created["random_state"] = random_state
            created["n_init"] = n_init
            self.fitted_on = None

        def fit(self, X):
            self.fitted_on = np.array(X)
            created["fit_shape"] = self.fitted_on.shape

    monkeypatch.setattr(mdl, "KMeans", FakeKMeans)

    s = DummyParkingDataSource(_ds_settings(random_seed=123))
    zones = [_zone(id=f"z{i}", position=(49.0 + i * 0.001, 8.4 + i * 0.001)) for i in range(30)]

    out = s.cluster_zones(zones)
    captured = capsys.readouterr().out

    assert out is zones
    assert created["n_clusters"] == 2
    assert created["random_state"] == 123
    assert created["n_init"] == 10
    assert created["fit_shape"] == (30, 2)
    assert "Running K-Means" in captured
    assert "Clustering complete" in captured


def test_cluster_zones_all_zero_coords_uses_fallback_indexing(monkeypatch, capsys):
    """
    If all coords are (0,0), code falls back to 1D indexing coords: shape (n,1)
    """
    import backend.services.datasources.parking_data_source as mdl

    created = {}

    class FakeKMeans:
        def __init__(self, n_clusters, random_state, n_init):
            self.fitted_on = None

        def fit(self, X):
            arr = np.array(X)
            created["fit_shape"] = arr.shape
            created["fit_values_first_row"] = arr[0].tolist()

    monkeypatch.setattr(mdl, "KMeans", FakeKMeans)

    s = DummyParkingDataSource(_ds_settings(random_seed=1))
    zones = [_zone(id=f"z{i}", position=(0.0, 0.0)) for i in range(10)]

    out = s.cluster_zones(zones)
    captured = capsys.readouterr().out

    assert out is zones
    assert "Warning: No geolocation found" in captured
    assert created["fit_shape"] == (10, 1)
    assert created["fit_values_first_row"] == [0]  # starts at 0


def test_export_results_to_csv_no_original_zones_prints_and_returns(tmp_path, capsys):
    s = DummyParkingDataSource(_ds_settings())
    out_file = tmp_path / "out.csv"

    s.export_results_to_csv([], optimized_zones=[_opt_zone()], filename=str(out_file))
    captured = capsys.readouterr().out

    assert "No zones loaded. Cannot export results." in captured
    assert not out_file.exists()


def test_export_results_to_csv_writes_csv_and_computes_deltas(tmp_path, capsys):
    s = DummyParkingDataSource(_ds_settings())

    # original zones
    z1 = _zone(
        id="A",
        name="Alpha",
        maximum_capacity=10,
        current_capacity=5,  # occupancy_old = 0.5
        position=(49.0, 8.4),
        short_term_share=0.6,
        current_fee=2.0,
    )
    z2 = _zone(
        id="B",
        name="Beta",
        maximum_capacity=20,
        current_capacity=10,  # occupancy_old = 0.5
        position=(49.1, 8.5),
        short_term_share=0.2,
        current_fee=1.5,
    )

    # optimize only A; B should have only old fields
    optA = _opt_zone(
        id="A",
        new_fee=3.1,                # should round to 3.0 (0.5 steps)
        predicted_occupancy=0.8,
        predicted_revenue=123.456,
    )

    out_file = tmp_path / "analytics.csv"
    s.export_results_to_csv([z1, z2], optimized_zones=[optA], filename=str(out_file))

    captured = capsys.readouterr().out
    assert "CSV exported successfully" in captured
    assert out_file.exists()

    df = pd.read_csv(out_file)

    # Should include 2 rows
    assert set(df["id"].tolist()) == {"A", "B"}

    rowA = df[df["id"] == "A"].iloc[0]
    rowB = df[df["id"] == "B"].iloc[0]

    # Old values A
    assert rowA["name"] == "Alpha"
    assert rowA["capacity"] == 10
    assert rowA["type"] == "Short-Term"
    assert rowA["current_fee_old"] == 2.0
    assert rowA["occupancy_old"] == 0.5
    assert rowA["revenue_old"] == 2.0 * 10 * 0.5  # 10.0

    # New values A (rounded to 0.5 steps)
    assert rowA["current_fee_new"] == 3.0
    assert rowA["occupancy_new"] == 0.8
    assert rowA["revenue_new"] == round(123.456, 2)  # 123.46
    assert rowA["delta_current_fee"] == 1.0          # 3.0 - 2.0
    assert rowA["delta_revenue"] == round(123.456 - 10.0, 2)  # 113.46
    assert rowA["delta_occupancy"] == round(0.8 - 0.5, 2)     # 0.3

    # For B (not optimized): should not have new columns filled (will be NaN)
    assert rowB["name"] == "Beta"
    assert rowB["type"] == "Commuter"
    assert rowB["current_fee_old"] == 1.5
    assert rowB["occupancy_old"] == 0.5
    assert rowB["revenue_old"] == 1.5 * 20 * 0.5  # 15.0

    # These columns exist but should be NaN for B
    assert pd.isna(rowB.get("current_fee_new"))
    assert pd.isna(rowB.get("delta_current_fee"))
