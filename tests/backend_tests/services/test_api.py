import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import the FastAPI app object from your api module
from backend.services.api import app


# -------------------------
# Test client fixture
# -------------------------

@pytest.fixture
def client():
    return TestClient(app)


# -------------------------
# Helpers
# -------------------------

def _scenario_dict(scenario_id: int = 1):
    """
    Build a minimal-but-valid PricingScenario dict (matches your Pydantic schema).
    This is REQUIRED because /optimize has response_model=OptimizationResponse
    which validates every scenario as PricingScenario.
    """
    return {
        "scenario_id": scenario_id,
        "zones": [
            {
                "id": 1,
                "new_fee": 2.5,
                "predicted_occupancy": 0.75,
                "predicted_revenue": 100.0,
            }
        ],
        "score_revenue": 1000.0,
        "score_occupancy_gap": 0.10,
        "score_demand_drop": 0.05,
        "score_user_balance": 0.80,
    }


def _load_city_payload(**overrides):
    base = {
        "data_source": "generated",
        "limit": 10,
        "city_name": "TestCity",
        "center_lat": 49.0,
        "center_lon": 8.4,
        "seed": 42,
        "poi_limit": 10,
        "default_elasticity": -0.3,
        "search_radius": 1000,
        "default_current_fee": 2.0,
        "tariffs": {},
    }
    base.update(overrides)
    return base


def _optimize_payload(optimizer_type="elasticity", **extra):
    settings = {
        "optimizer_type": optimizer_type,
        "random_seed": 1,
        "population_size": 10,
        "generations": 2,
        "target_occupancy": 0.85,
        "min_fee": 1.0,
        "max_fee": 10.0,
        "fee_increment": 0.25,
        **extra,
    }
    return {
        "city": {
            "id": 1,
            "name": "TestCity",
            "min_latitude": 49.0,
            "max_latitude": 49.1,
            "min_longitude": 8.3,
            "max_longitude": 8.5,
            "parking_zones": [],
            "point_of_interests": [],
        },
        "optimizer_settings": settings,
    }


def _save_result_payload(**overrides):
    base = {
        "parameters": {"a": 1},
        "map_config": None,
        "map_snapshot": None,
        "map_path": None,
        "csv_path": None,
        "best_scenario": None,
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# Basic endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestBasicEndpoints:

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json() == {"message": "Parking Fee Optimization API is running"}

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "healthy"}

    def test_optimization_settings(self, client):
        r = client.get("/optimization-settings")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_nonexistent_route_404(self, client):
        assert client.get("/nonexistent").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Reverse geocode
# ═══════════════════════════════════════════════════════════════════════════════

class TestReverseGeocode:

    def test_success(self, client, monkeypatch):
        from backend.services.datasources.osm import osmnx_loader

        monkeypatch.setattr(
            osmnx_loader.OSMnxDataSource, "reverse_geocode",
            staticmethod(lambda lat, lon: {"city": "Karlsruhe", "lat": lat, "lon": lon}),
        )

        r = client.post("/reverse-geocode", json={"center_lat": 49.0, "center_lon": 8.4})
        assert r.status_code == 200
        assert r.json()["geo_info"]["city"] == "Karlsruhe"

    def test_failure_returns_500(self, client, monkeypatch):
        from backend.services.datasources.osm import osmnx_loader

        monkeypatch.setattr(
            osmnx_loader.OSMnxDataSource, "reverse_geocode",
            staticmethod(lambda lat, lon: (_ for _ in ()).throw(RuntimeError("OSM down"))),
        )

        r = client.post("/reverse-geocode", json={"center_lat": 49.0, "center_lon": 8.4})
        assert r.status_code == 500
        assert "Reverse geocoding failed" in r.json()["detail"]

    def test_missing_fields_422(self, client):
        assert client.post("/reverse-geocode", json={}).status_code == 422

    def test_missing_one_field_422(self, client):
        assert client.post("/reverse-geocode", json={"center_lat": 49.0}).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Load city
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadCity:

    @staticmethod
    def _dummy_city(parking_zones=None):
        """Return a City-compatible dict accepted by LoadCityResponse."""
        from backend.services.models.city import City
        zones = parking_zones if parking_zones is not None else [
            {
                "id": 1, "name": "Lot1", "current_fee": 2.0,
                "position": [49.01, 8.41],
                "maximum_capacity": 50, "current_capacity": 25,
            }
        ]
        return City(
            id=1, name="MockCity",
            min_latitude=49.0, max_latitude=49.1,
            min_longitude=8.3, max_longitude=8.5,
            parking_zones=zones, point_of_interests=[],
        )

    def _mock_loader(self, monkeypatch, parking_zones=None, raise_exc=None):
        import backend.services.api as api_module
        city_obj = self._dummy_city(parking_zones)

        class FakeLoader:
            def __init__(self, datasource):
                pass

            def load_city(self):
                if raise_exc:
                    raise raise_exc
                return city_obj

        monkeypatch.setattr(api_module, "CityDataLoader", FakeLoader)

    def test_success(self, client, monkeypatch):
        self._mock_loader(monkeypatch)
        r = client.post("/load_city", json=_load_city_payload())
        assert r.status_code == 200
        assert "city" in r.json()

    def test_no_parking_zones_returns_502(self, client, monkeypatch):
        self._mock_loader(monkeypatch, parking_zones=[])
        r = client.post("/load_city", json=_load_city_payload())
        assert r.status_code == 502
        assert "No parking data" in r.json()["detail"]

    def test_loader_exception_returns_502(self, client, monkeypatch):
        self._mock_loader(monkeypatch, raise_exc=RuntimeError("Connection failed"))
        r = client.post("/load_city", json=_load_city_payload())
        assert r.status_code == 502
        assert "Failed to load data" in r.json()["detail"]

    def test_empty_body_defaults_fail_502(self, client):
        # All LoadCityRequest fields have defaults; {} is valid but tariffs=None
        # fails DataSourceSettings validation → caught → 502
        r = client.post("/load_city", json={})
        assert r.status_code == 502

    def test_invalid_field_type_422(self, client):
        payload = _load_city_payload(center_lat="not-a-number")
        assert client.post("/load_city", json=payload).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Optimize
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimize:

    def test_elasticity_path(self, client, monkeypatch):
        import backend.services.api as api_module

        class FakeOpt:
            def __init__(self, s): pass
            def optimize(self, city): return [_scenario_dict(1)]

        monkeypatch.setattr(api_module, "NSGA3OptimizerElasticity", FakeOpt)
        r = client.post("/optimize", json=_optimize_payload("elasticity"))
        assert r.status_code == 200
        assert r.json()["scenarios"][0]["scenario_id"] == 1

    def test_agent_path(self, client, monkeypatch):
        import backend.services.api as api_module

        class FakeOpt:
            def __init__(self, s): pass
            def optimize(self, city): return [_scenario_dict(2)]

        monkeypatch.setattr(api_module, "NSGA3OptimizerAgentBased", FakeOpt)
        r = client.post("/optimize", json=_optimize_payload(
            "agent",
            drivers_per_zone_capacity=1.0,
            simulation_runs=1,
            driver_fee_weight=1.0,
            driver_distance_to_lot_weight=0.0,
            driver_walking_distance_weight=0.0,
            driver_availability_weight=0.0,
        ))
        assert r.status_code == 200
        assert r.json()["scenarios"][0]["scenario_id"] == 2

    def test_invalid_optimizer_type_422(self, client):
        assert client.post("/optimize", json=_optimize_payload("wat")).status_code == 422

    def test_missing_body_422(self, client):
        assert client.post("/optimize", json={}).status_code == 422

    def test_missing_city_422(self, client):
        payload = _optimize_payload()
        del payload["city"]
        assert client.post("/optimize", json=payload).status_code == 422

    def test_missing_optimizer_settings_422(self, client):
        payload = _optimize_payload()
        del payload["optimizer_settings"]
        assert client.post("/optimize", json=payload).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Select best solution
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelectBestSolution:

    def test_success(self, client, monkeypatch):
        import backend.services.api as api_module

        monkeypatch.setattr(
            api_module.SolutionSelector, "select_best_by_weights",
            staticmethod(lambda scenarios, weights: _scenario_dict(99)),
        )
        payload = {
            "scenarios": [_scenario_dict(1), _scenario_dict(2)],
            "weights": {"revenue": 100},
        }
        r = client.post("/select_best_solution_by_weight", json=payload)
        assert r.status_code == 200
        assert r.json()["scenario"]["scenario_id"] == 99

    def test_empty_scenarios_field(self, client, monkeypatch):
        import backend.services.api as api_module

        monkeypatch.setattr(
            api_module.SolutionSelector, "select_best_by_weights",
            staticmethod(lambda scenarios, weights: _scenario_dict(1)),
        )
        payload = {"scenarios": [], "weights": {"revenue": 1}}
        r = client.post("/select_best_solution_by_weight", json=payload)
        assert r.status_code == 200

    def test_missing_body_422(self, client):
        assert client.post("/select_best_solution_by_weight", json={}).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Results CRUD endpoints (mocked DB)
# ═══════════════════════════════════════════════════════════════════════════════

class _FakeResult:
    def __init__(self, id=1, **kw):
        self.id = id
        self.created_at = "2026-01-01T00:00:00"
        self.parameters = kw.get("parameters", {"x": 1})
        self.map_config = kw.get("map_config")
        self.map_snapshot = kw.get("map_snapshot")
        self.map_path = kw.get("map_path")
        self.csv_path = kw.get("csv_path")
        self.best_scenario = kw.get("best_scenario")


class _FakeSession:
    def __init__(self, stored=None):
        self._stored = stored if stored is not None else [_FakeResult(1), _FakeResult(2)]

    def add(self, obj): pass
    def commit(self): pass
    def close(self): pass

    def refresh(self, obj):
        obj.id = 123
        obj.created_at = "2026-01-01T00:00:00"

    def execute(self, stmt):
        parent = self

        class _Exec:
            def scalars(self): return self
            def all(self): return parent._stored

        return _Exec()

    def get(self, model, rid):
        return next((r for r in self._stored if r.id == rid), None)


@pytest.fixture
def db_client(monkeypatch):
    import backend.services.api as api_module
    monkeypatch.setattr(api_module, "SessionLocal", lambda: _FakeSession())
    return TestClient(app)


class TestResultsEndpoints:

    def test_save_result(self, db_client):
        r = db_client.post("/results", json=_save_result_payload())
        assert r.status_code == 200
        assert "id" in r.json()
        assert "created_at" in r.json()

    def test_save_result_full_fields(self, db_client):
        r = db_client.post("/results", json=_save_result_payload(
            map_config={"center": [49, 8]},
            map_snapshot=[{"zones": []}],
            map_path="/maps/test.html",
            csv_path="/exports/test.csv",
            best_scenario={"revenue": 500},
        ))
        assert r.status_code == 200

    def test_save_result_missing_parameters_422(self, client):
        r = client.post("/results", json={})
        assert r.status_code == 422

    def test_list_results(self, db_client):
        r = db_client.get("/results")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert all("id" in item and "parameters" in item for item in data)

    def test_list_results_empty(self, monkeypatch, client):
        import backend.services.api as api_module
        monkeypatch.setattr(api_module, "SessionLocal", lambda: _FakeSession(stored=[]))
        r = client.get("/results")
        assert r.status_code == 200
        assert r.json() == []

    def test_get_result_exists(self, db_client):
        r = db_client.get("/results/1")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == 1
        for key in ("parameters", "map_config", "map_snapshot", "map_path", "csv_path", "best_scenario"):
            assert key in body

    def test_get_result_not_found_404(self, db_client):
        r = db_client.get("/results/999")
        assert r.status_code == 404
        assert "Result not found" in r.json()["detail"]

    def test_get_result_with_all_fields(self, monkeypatch, client):
        import backend.services.api as api_module
        full = _FakeResult(
            id=5, parameters={"p": 1}, map_config={"z": 13},
            map_snapshot={"s": 1}, map_path="/m.html",
            csv_path="/c.csv", best_scenario={"r": 100},
        )
        monkeypatch.setattr(api_module, "SessionLocal", lambda: _FakeSession(stored=[full]))
        r = client.get("/results/5")
        assert r.status_code == 200
        body = r.json()
        assert body["map_path"] == "/m.html"
        assert body["best_scenario"] == {"r": 100}
