import pytest
from pydantic import ValidationError
from backend.services.payloads.optimization_payload import (
    OptimizationRequest, OptimizationResponse, OptimizationSettingsResponse,
)
from backend.services.models.city import City
from backend.services.settings.optimizations_settings import OptimizationSettings
from backend.services.optimizer.schemas.optimization_schema import PricingScenario, OptimizedZoneResult


def _make_city():
    return City(id=1, name="Test", min_latitude=0, max_latitude=1, min_longitude=0, max_longitude=1)


def _make_scenario(sid=1):
    zone = OptimizedZoneResult(id=1, new_fee=2.0, predicted_occupancy=0.8, predicted_revenue=100.0)
    return PricingScenario(
        scenario_id=sid, zones=[zone],
        score_revenue=100.0, score_occupancy_gap=0.1,
        score_demand_drop=0.05, score_user_balance=0.9,
    )


def test_optimization_request():
    r = OptimizationRequest(city=_make_city(), optimizer_settings=OptimizationSettings())
    assert r.city.name == "Test"
    assert r.optimizer_settings.optimizer_type == "elasticity"


def test_optimization_response():
    r = OptimizationResponse(scenarios=[_make_scenario(1), _make_scenario(2)])
    assert len(r.scenarios) == 2
    assert r.scenarios[0].scenario_id == 1


def test_optimization_settings_response():
    r = OptimizationSettingsResponse()
    assert "population_size" in r.settings
    assert "generations" in r.settings


# --- Edge cases ---

def test_optimization_request_missing_city():
    with pytest.raises(ValidationError):
        OptimizationRequest(optimizer_settings=OptimizationSettings())


def test_optimization_request_missing_settings():
    with pytest.raises(ValidationError):
        OptimizationRequest(city=_make_city())


def test_optimization_response_empty_scenarios():
    r = OptimizationResponse(scenarios=[])
    assert r.scenarios == []


def test_optimization_response_missing_scenarios():
    with pytest.raises(ValidationError):
        OptimizationResponse()


def test_optimization_settings_response_custom():
    r = OptimizationSettingsResponse(settings={"custom": {"default": 1}})
    assert r.settings["custom"]["default"] == 1
