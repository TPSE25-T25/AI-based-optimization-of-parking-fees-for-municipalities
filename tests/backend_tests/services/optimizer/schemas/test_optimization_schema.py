import pytest
from pydantic import ValidationError

from backend.services.optimizer.schemas.optimization_schema import (
    OptimizedZoneResult,
    PricingScenario,
)


class TestOptimizedZoneResult:
    def test_create_valid(self):
        z = OptimizedZoneResult(
            id=1,
            new_fee=2.5,
            predicted_occupancy=0.8,
            predicted_revenue=123.45,
        )
        assert z.id == 1
        assert z.new_fee == 2.5

    def test_coerces_numeric_strings(self):
        z = OptimizedZoneResult(
            id="1",
            new_fee="2.5",
            predicted_occupancy="0.8",
            predicted_revenue="123.45",
        )
        assert z.id == 1
        assert z.new_fee == 2.5
        assert z.predicted_occupancy == 0.8
        assert z.predicted_revenue == 123.45

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            OptimizedZoneResult(id=1, new_fee=2.5, predicted_occupancy=0.8)

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            OptimizedZoneResult(
                id="not-an-int",
                new_fee=2.5,
                predicted_occupancy=0.8,
                predicted_revenue=10.0,
            )


class TestPricingScenario:
    def test_create_valid(self):
        zones = [
            OptimizedZoneResult(id=1, new_fee=2.5, predicted_occupancy=0.8, predicted_revenue=100.0),
            OptimizedZoneResult(id=2, new_fee=3.0, predicted_occupancy=0.7, predicted_revenue=120.0),
        ]
        s = PricingScenario(
            scenario_id=1,
            zones=zones,
            score_revenue=220.0,
            score_occupancy_gap=0.05,
            score_demand_drop=0.10,
            score_user_balance=0.8,
        )

        assert s.scenario_id == 1
        assert len(s.zones) == 2
        assert s.score_revenue == 220.0

    def test_zones_must_be_list(self):
        with pytest.raises(ValidationError):
            PricingScenario(
                scenario_id=1,
                zones="not-a-list",
                score_revenue=1.0,
                score_occupancy_gap=0.1,
                score_demand_drop=0.1,
                score_user_balance=0.1,
            )

    def test_nested_validation(self):
        with pytest.raises(ValidationError):
            PricingScenario(
                scenario_id=1,
                zones=[{"id": 1, "new_fee": 2.0}],  # missing predicted_occupancy & predicted_revenue
                score_revenue=1.0,
                score_occupancy_gap=0.1,
                score_demand_drop=0.1,
                score_user_balance=0.1,
            )
