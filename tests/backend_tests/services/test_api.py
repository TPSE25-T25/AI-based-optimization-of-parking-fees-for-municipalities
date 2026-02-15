import pytest
from fastapi.testclient import TestClient

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


# -------------------------
# Basic endpoints
# -------------------------

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Parking Fee Optimization API is running"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_get_optimization_settings(client):
    r = client.get("/optimization-settings")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


# -------------------------
# reverse-geocode
# -------------------------

def test_reverse_geocode_success(client, monkeypatch):
    from backend.services.datasources.osm import osmnx_loader

    def fake_reverse_geocode(lat, lon):
        return {"city": "Karlsruhe", "country": "Germany", "lat": lat, "lon": lon}

    monkeypatch.setattr(
        osmnx_loader.OSMnxDataSource, "reverse_geocode", staticmethod(fake_reverse_geocode)
    )

    payload = {"center_lat": 49.0, "center_lon": 8.4}
    r = client.post("/reverse-geocode", json=payload)

    assert r.status_code == 200
    body = r.json()
    assert "geo_info" in body
    assert body["geo_info"]["city"] == "Karlsruhe"


def test_reverse_geocode_failure_returns_500(client, monkeypatch):
    from backend.services.datasources.osm import osmnx_loader

    def boom(lat, lon):
        raise RuntimeError("OSM is down")

    monkeypatch.setattr(osmnx_loader.OSMnxDataSource, "reverse_geocode", staticmethod(boom))

    payload = {"center_lat": 49.0, "center_lon": 8.4}
    r = client.post("/reverse-geocode", json=payload)

    assert r.status_code == 500
    assert "Reverse geocoding failed" in r.json()["detail"]


# -------------------------
# load_city
# -------------------------

def test_load_city_success(client, monkeypatch):
    # We mock CityDataLoader.load_city so we avoid real datasources
    from backend.services.datasources import city_data_loader

    class DummyCity:
        def __init__(self):
            self.parking_zones = [{"id": 1}]
            self.point_of_interests = []
            self.name = "OptimizationCity"

    class FakeLoader:
        def __init__(self, datasource):
            self.datasource = datasource

        def load_city(self):
            return DummyCity()

    monkeypatch.setattr(city_data_loader, "CityDataLoader", FakeLoader)

    # IMPORTANT: tariffs must be a dict for DataSourceSettings validation
    payload = {
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
        "tariffs": {},  # <-- fix (was None)
    }

    r = client.post("/load_city", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "city" in body
    assert "parking_zones" in body["city"]



# -------------------------
# optimize (mock both optimizers)
# -------------------------

def test_optimize_elasticity_path(client, monkeypatch):
    import backend.services.api as api_module

    class FakeElasticityOptimizer:
        def __init__(self, settings):
            self.settings = settings

        def optimize(self, city):
            # MUST return a valid PricingScenario shape because response_model validates it
            return [_scenario_dict(1)]

    monkeypatch.setattr(api_module, "NSGA3OptimizerElasticity", FakeElasticityOptimizer)

    payload = {
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
        "optimizer_settings": {
            "optimizer_type": "elasticity",
            "random_seed": 1,
            "population_size": 10,
            "generations": 2,
            "target_occupancy": 0.85,
            "min_fee": 1.0,
            "max_fee": 10.0,
            "fee_increment": 0.25,
        },
    }

    r = client.post("/optimize", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "scenarios" in body
    assert body["scenarios"][0]["scenario_id"] == 1


def test_optimize_agent_path(client, monkeypatch):
    import backend.services.api as api_module

    class FakeAgentOptimizer:
        def __init__(self, settings):
            self.settings = settings

        def optimize(self, city):
            return [_scenario_dict(2)]

    monkeypatch.setattr(api_module, "NSGA3OptimizerAgentBased", FakeAgentOptimizer)

    payload = {
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
        "optimizer_settings": {
            "optimizer_type": "agent",
            "random_seed": 1,
            "population_size": 10,
            "generations": 2,
            "target_occupancy": 0.85,
            "min_fee": 1.0,
            "max_fee": 10.0,
            "fee_increment": 0.25,
            # Agent-based extras required by AgentBasedSettings
            "drivers_per_zone_capacity": 1.0,
            "simulation_runs": 1,
            "driver_fee_weight": 1.0,
            "driver_distance_to_lot_weight": 0.0,
            "driver_walking_distance_weight": 0.0,
            "driver_availability_weight": 0.0,
        },
    }

    r = client.post("/optimize", json=payload)
    assert r.status_code == 200
    assert r.json()["scenarios"][0]["scenario_id"] == 2


def test_optimize_invalid_type_returns_422(client):
    """
    Because optimizer_type is a Literal in your Pydantic settings,
    FastAPI rejects the request body before reaching your endpoint logic.
    That produces 422, not 400.
    """
    payload = {
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
        "optimizer_settings": {
            "optimizer_type": "wat",
            "random_seed": 1,
            "population_size": 10,
            "generations": 2,
            "target_occupancy": 0.85,
            "min_fee": 1.0,
            "max_fee": 10.0,
            "fee_increment": 0.25,
        },
    }

    r = client.post("/optimize", json=payload)
    assert r.status_code == 422


# -------------------------
# select_best_solution_by_weight (mock selector)
# -------------------------

def test_select_best_solution_by_weight(client, monkeypatch):
    import backend.services.api as api_module

    def fake_select_best(scenarios, weights):
        # Return a valid PricingScenario shape, because response_model validates it.
        return _scenario_dict(99)

    monkeypatch.setattr(
        api_module.SolutionSelector, "select_best_by_weights", staticmethod(fake_select_best)
    )

    # IMPORTANT: WeightSelectionRequest expects List[PricingScenario]
    payload = {
        "scenarios": [_scenario_dict(1), _scenario_dict(2)],
        "weights": {"revenue": 100},
    }
    r = client.post("/select_best_solution_by_weight", json=payload)

    assert r.status_code == 200
    body = r.json()
    assert "scenario" in body
    assert body["scenario"]["scenario_id"] == 99


# -------------------------
# DB endpoints (/results) - fully mocked SessionLocal + SimulationResult
# -------------------------

def test_results_endpoints_smoke(client, monkeypatch):
    """
    Smoke-test the DB endpoints without a real DB by replacing SessionLocal.
    """
    import backend.services.api as api_module

    class FakeResult:
        def __init__(self, id=1):
            self.id = id
            self.created_at = "2026-01-01T00:00:00"
            self.parameters = {"x": 1}
            self.map_config = None
            self.map_snapshot = None
            self.map_path = None
            self.csv_path = None
            self.best_scenario = None

    class FakeSession:
        def __init__(self):
            self._stored = [FakeResult(1), FakeResult(2)]

        def add(self, obj):
            ...

        def commit(self):
            ...

        def refresh(self, obj):
            obj.id = 123
            obj.created_at = "2026-01-01T00:00:00"

        def close(self):
            ...

        def execute(self, stmt):
            class FakeExec:
                def __init__(self, rows):
                    self._rows = rows

                def scalars(self):
                    return self

                def all(self):
                    return self._rows

            return FakeExec(self._stored)

        def get(self, model, rid):
            for r in self._stored:
                if r.id == rid:
                    return r
            return None

    monkeypatch.setattr(api_module, "SessionLocal", lambda: FakeSession())

    # save_result
    save_payload = {
        "parameters": {"a": 1},
        "map_config": None,
        "map_snapshot": None,
        "map_path": None,
        "csv_path": None,
        "best_scenario": None,
    }
    r = client.post("/results", json=save_payload)
    assert r.status_code == 200
    assert "id" in r.json()

    # list_results
    r = client.get("/results")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert "id" in data[0]

    # get_result existing
    r = client.get("/results/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1

    # get_result missing
    r = client.get("/results/999")
    assert r.status_code == 404
