import pytest
from pydantic import ValidationError
from backend.services.payloads.weight_selection_payload import (
    WeightSelectionRequest, WeightSelectionResponse,
)
from backend.services.optimizer.schemas.optimization_schema import PricingScenario, OptimizedZoneResult


def _make_scenario(sid=1):
    zone = OptimizedZoneResult(id=1, new_fee=2.0, predicted_occupancy=0.8, predicted_revenue=100.0)
    return PricingScenario(
        scenario_id=sid, zones=[zone],
        score_revenue=100.0, score_occupancy_gap=0.1,
        score_demand_drop=0.05, score_user_balance=0.9,
    )


def test_weight_selection_request():
    r = WeightSelectionRequest(
        scenarios=[_make_scenario(1), _make_scenario(2)],
        weights={"revenue": 0.5, "occupancy": 0.3, "drop": 0.1, "fairness": 0.1},
    )
    assert len(r.scenarios) == 2
    assert r.weights["revenue"] == 0.5


def test_weight_selection_response():
    r = WeightSelectionResponse(scenario=_make_scenario())
    assert r.scenario.scenario_id == 1
    assert r.scenario.score_revenue == 100.0


# --- Edge cases ---

def test_weight_selection_request_missing_weights():
    with pytest.raises(ValidationError):
        WeightSelectionRequest(scenarios=[_make_scenario()])


def test_weight_selection_request_missing_scenarios():
    with pytest.raises(ValidationError):
        WeightSelectionRequest(weights={"revenue": 1.0})


def test_weight_selection_request_empty_scenarios():
    r = WeightSelectionRequest(scenarios=[], weights={"revenue": 1.0})
    assert r.scenarios == []


def test_weight_selection_request_empty_weights():
    r = WeightSelectionRequest(scenarios=[_make_scenario()], weights={})
    assert r.weights == {}


def test_weight_selection_response_missing_scenario():
    with pytest.raises(ValidationError):
        WeightSelectionResponse()
