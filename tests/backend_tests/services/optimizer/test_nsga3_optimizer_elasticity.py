import numpy as np
import pytest

from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.models.city import ParkingZone
from backend.services.settings.optimizations_settings import OptimizationSettings


# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def zones():
    # Use negative elasticities to model: higher price -> lower demand
    return [
        ParkingZone(
            id=1,
            name="Zone_A",
            current_fee=3.0,
            position=(49.01, 8.41),
            maximum_capacity=100,
            current_capacity=60,      # occupancy 0.6
            min_fee=1.0,
            max_fee=8.0,
            elasticity=-0.5,
            short_term_share=0.6,
        ),
        ParkingZone(
            id=2,
            name="Zone_B",
            current_fee=4.0,
            position=(49.02, 8.42),
            maximum_capacity=150,
            current_capacity=120,     # occupancy 0.8
            min_fee=2.0,
            max_fee=10.0,
            elasticity=-0.4,
            short_term_share=0.7,
        ),
        ParkingZone(
            id=3,
            name="Zone_C",
            current_fee=2.5,
            position=(49.03, 8.43),
            maximum_capacity=80,
            current_capacity=30,      # occupancy 0.375
            min_fee=1.5,
            max_fee=6.0,
            elasticity=-0.6,
            short_term_share=0.4,
        ),
    ]


@pytest.fixture
def settings():
    return OptimizationSettings(
        random_seed=42,
        population_size=10,
        generations=3,
        target_occupancy=0.85,
        min_fee=1.0,
        max_fee=10.0,
        fee_increment=0.1,
    )


@pytest.fixture
def optimizer(settings):
    return NSGA3OptimizerElasticity(settings)


@pytest.fixture
def data(optimizer, zones):
    return optimizer._convert_zones_to_numpy(zones)


# -----------------------------
# Tests: _calculate_physics
# -----------------------------

class TestElasticityPhysics:
    def test_calculate_physics_structure(self, optimizer, data):
        fees = data["current_current_fees"]
        out = optimizer._calculate_physics(fees, data)

        assert set(out.keys()) == {"objectives", "occupancy", "revenue", "demand_change"}
        assert isinstance(out["objectives"], list)
        assert len(out["objectives"]) == 4

    def test_calculate_physics_shapes(self, optimizer, data):
        fees = data["current_current_fees"]
        out = optimizer._calculate_physics(fees, data)
        n = len(fees)

        assert out["occupancy"].shape == (n,)
        assert out["revenue"].shape == (n,)
        assert out["demand_change"].shape == (n,)

    def test_occupancy_is_clipped(self, optimizer, data):
        # Very high fees should push occupancy down but not below 0.05
        high = data["max_fees"] * 100
        out_high = optimizer._calculate_physics(high, data)
        assert np.all(out_high["occupancy"] >= 0.05)
        assert np.all(out_high["occupancy"] <= 1.0)

        # Very low fees could push occupancy up but not above 1.0
        low = data["min_fees"] * 0.01
        out_low = optimizer._calculate_physics(low, data)
        assert np.all(out_low["occupancy"] >= 0.05)
        assert np.all(out_low["occupancy"] <= 1.0)

    def test_revenue_formula_correct(self, optimizer, data):
        fees = np.array([5.0, 6.0, 4.0], dtype=float)
        out = optimizer._calculate_physics(fees, data)

        expected = fees * (data["capacities"] * out["occupancy"])
        assert np.allclose(out["revenue"], expected, atol=1e-8)

    def test_fee_increase_reduces_occupancy_with_negative_elasticity(self, optimizer, data):
        base = data["current_current_fees"].astype(float)
        inc = base * 1.5

        out_base = optimizer._calculate_physics(base, data)
        out_inc = optimizer._calculate_physics(inc, data)

        assert np.all(out_inc["occupancy"] <= out_base["occupancy"] + 1e-12)

    def test_fee_decrease_increases_occupancy_with_negative_elasticity(self, optimizer, data):
        base = data["current_current_fees"].astype(float)
        dec = base * 0.5

        out_base = optimizer._calculate_physics(base, data)
        out_dec = optimizer._calculate_physics(dec, data)

        assert np.all(out_dec["occupancy"] >= out_base["occupancy"] - 1e-12)

    def test_loss_aversion_asymmetry(self, optimizer, data):
        """
        For same magnitude +/- change, the demand drop from increases should be stronger
        than demand gain from decreases because factor 1.2 vs 0.8.
        """
        base = data["current_current_fees"].astype(float)

        up = base * 1.1
        down = base * 0.9

        out_up = optimizer._calculate_physics(up, data)
        out_down = optimizer._calculate_physics(down, data)

        mean_drop = float(np.mean(out_up["demand_change"]))    # negative
        mean_gain = float(np.mean(out_down["demand_change"]))  # positive

        assert mean_drop < 0
        assert mean_gain > 0
        assert abs(mean_drop) > abs(mean_gain)

    def test_short_term_share_affects_fairness(self, optimizer, data):
        """
        f4_fairness = mean(max(0, pct_change) * short_term_share)
        So if we increase fees, fairness should be larger when short_term_share is higher.
        """
        base = data["current_current_fees"].astype(float)
        inc = base * 1.2

        out = optimizer._calculate_physics(inc, data)
        f4 = float(out["objectives"][3])

        data2 = dict(data)
        data2["short_term_share"] = np.ones_like(data["short_term_share"])
        out2 = optimizer._calculate_physics(inc, data2)
        f4_all_short = float(out2["objectives"][3])

        assert f4_all_short >= f4 - 1e-12


# -----------------------------
# Tests: _get_detailed_results + _simulate_scenario
# -----------------------------

class TestElasticityScenarioInterface:
    def test_get_detailed_results_matches_physics(self, optimizer, data):
        fees = data["current_current_fees"].astype(float)
        detailed = optimizer._get_detailed_results(fees, data)
        physics = optimizer._calculate_physics(fees, data)

        assert np.allclose(detailed["occupancy"], physics["occupancy"], atol=1e-8)
        assert np.allclose(detailed["revenue"], physics["revenue"], atol=1e-8)

    def test_simulate_scenario_returns_four_floats(self, optimizer, zones, data):
        fees = data["current_current_fees"].astype(float)
        f1, f2, f3, f4 = optimizer._simulate_scenario(fees, zones)

        assert isinstance(f1, (float, np.floating))
        assert isinstance(f2, (float, np.floating))
        assert isinstance(f3, (float, np.floating))
        assert isinstance(f4, (float, np.floating))

    def test_simulate_scenario_consistent_with_calculate_physics(self, optimizer, zones, data):
        fees = data["current_current_fees"].astype(float)

        sim = optimizer._simulate_scenario(fees, zones)
        physics = optimizer._calculate_physics(fees, data)["objectives"]

        assert np.allclose(np.array(sim, dtype=float), np.array(physics, dtype=float), atol=1e-8)
