"""Unit tests for Driver model — thorough + edge cases"""

import pytest
from pydantic import ValidationError
from backend.services.models.driver import Driver


def _driver(**kw):
    defaults = dict(id=1, name="D", max_parking_current_fee=5.0,
                    starting_position=(0.0, 0.0), destination=(3.0, 4.0),
                    desired_parking_time=60)
    defaults.update(kw)
    return Driver(**defaults)


class TestDriver:

    # ── Construction ──

    def test_valid_creation(self):
        d = _driver()
        assert d.id == 1 and d.name == "D"
        assert d.max_parking_current_fee == 5.0
        assert d.desired_parking_time == 60

    def test_string_fee_auto_cast(self):
        assert _driver(max_parking_current_fee="4.75").max_parking_current_fee == 4.75

    def test_position_stored_as_tuple(self):
        d = _driver()
        assert isinstance(d.starting_position, tuple)
        assert isinstance(d.destination, tuple)

    # ── Validation ──

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            _driver(name="")

    def test_negative_fee_rejected(self):
        with pytest.raises(ValidationError):
            _driver(max_parking_current_fee=-1.0)

    def test_zero_fee_allowed(self):
        assert _driver(max_parking_current_fee=0.0).max_parking_current_fee == 0.0

    def test_zero_parking_time_rejected(self):
        with pytest.raises(ValidationError):
            _driver(desired_parking_time=0)

    def test_negative_parking_time_rejected(self):
        with pytest.raises(ValidationError):
            _driver(desired_parking_time=-30)

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Driver(id=1, name="X")

    # ── distance_to_travel ──

    def test_distance_3_4_5(self):
        assert abs(_driver().distance_to_travel() - 5.0) < 1e-9

    def test_distance_to_self(self):
        d = _driver(starting_position=(10.0, 20.0), destination=(10.0, 20.0))
        assert d.distance_to_travel() == 0.0

    def test_distance_negative_coords(self):
        d = _driver(starting_position=(-3.0, -4.0), destination=(0.0, 0.0))
        assert abs(d.distance_to_travel() - 5.0) < 1e-9

    # ── hourly_budget ──

    def test_budget_two_hours(self):
        assert _driver(max_parking_current_fee=6.0, desired_parking_time=120).hourly_budget() == 12.0

    def test_budget_half_hour(self):
        assert _driver(max_parking_current_fee=4.0, desired_parking_time=30).hourly_budget() == 2.0

    def test_budget_odd_minutes(self):
        d = _driver(max_parking_current_fee=6.0, desired_parking_time=45)
        assert d.hourly_budget() == 6.0 * 45 / 60

    def test_budget_single_minute(self):
        assert _driver(max_parking_current_fee=60.0, desired_parking_time=1).hourly_budget() == 1.0

    def test_budget_zero_fee(self):
        assert _driver(max_parking_current_fee=0.0, desired_parking_time=120).hourly_budget() == 0.0

    def test_budget_long_duration(self):
        assert _driver(max_parking_current_fee=2.5, desired_parking_time=480).hourly_budget() == 20.0

    # ── Edge cases ──

    def test_minimum_parking_time(self):
        d = _driver(desired_parking_time=1)
        assert d.desired_parking_time == 1
        assert d.hourly_budget() == pytest.approx(5.0 / 60)

    def test_very_high_fee(self):
        d = _driver(max_parking_current_fee=999.99)
        assert d.max_parking_current_fee == 999.99

    def test_very_large_parking_time(self):
        d = _driver(desired_parking_time=10_000)
        assert d.hourly_budget() == pytest.approx(5.0 * 10_000 / 60)

    def test_json_schema_example_valid(self):
        data = Driver.model_config["json_schema_extra"]["example"]
        d = Driver(**data)
        assert d.name == "SimUser001" and d.desired_parking_time == 120

    def test_fee_precision(self):
        d = _driver(max_parking_current_fee=3.75, desired_parking_time=45)
        assert d.hourly_budget() == 3.75 * 0.75
