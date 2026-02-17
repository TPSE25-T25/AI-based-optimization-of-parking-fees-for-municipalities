"""Unit tests for parking simulation — thorough + edge cases, targeting >90% coverage."""

import pytest
import numpy as np

from backend.services.models.city import City, PointOfInterest, ParkingZone
from backend.services.models.driver import Driver
from backend.services.simulation.simulation import (
    ParkingSimulation,
    DriverDecision,
    SimulationMetrics,
    SimulationBatch,
)
from backend.services.simulation.parallel_engine import ParallelEngine, ComputeBackend
from backend.services.datasources.generator.driver_generator import DriverGenerator


# ── Helpers ──────────────────────────────────────────────────────────────────

def _zone(id=1, fee=3.0, pos=(49.048, 8.448), cap=100, cur=0, **kw):
    return ParkingZone(
        id=id, name=f"Lot{id}", current_fee=fee, position=pos,
        maximum_capacity=cap, current_capacity=cur, **kw,
    )


def _driver(id=1, max_fee=5.0, start=(100.0, 100.0), dest=(500.0, 500.0), time=120):
    return Driver(
        id=id, name=f"D{id}", max_parking_current_fee=max_fee,
        starting_position=start, destination=dest, desired_parking_time=time,
    )


def _city(lots=None, pois=None):
    city = City(
        id=1, name="TestCity",
        min_latitude=49.0, max_latitude=49.1,
        min_longitude=8.4, max_longitude=8.5,
    )
    for p in (pois or [PointOfInterest(id=1, name="Downtown", position=(49.05, 8.45))]):
        city.add_point_of_interest(p)
    for z in (lots or [_zone(1, 3.0, (49.048, 8.448)), _zone(2, 5.0, (49.052, 8.452), cap=50)]):
        city.add_parking_zone(z)
    return city


def _drivers(n=10, city=None, max_fee=6.0, dest=None):
    dest = dest or (city.point_of_interests[0].position if city else (49.05, 8.45))
    return [
        _driver(i, max_fee=max_fee, start=(100.0 + i * 10, 100.0), dest=dest, time=120)
        for i in range(n)
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# SimulationMetrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationMetrics:

    def test_defaults(self):
        m = SimulationMetrics()
        assert m.total_revenue == 0.0
        assert m.total_parked == 0
        assert m.total_rejected == 0
        assert m.lot_occupancy_rates == {}

    def test_custom_values(self):
        m = SimulationMetrics(total_revenue=100.0, total_parked=5, rejection_rate=0.2)
        assert m.total_revenue == 100.0
        assert m.total_parked == 5
        assert m.rejection_rate == 0.2


# ═══════════════════════════════════════════════════════════════════════════════
# DriverDecision
# ═══════════════════════════════════════════════════════════════════════════════

class TestDriverDecision:

    def test_default_weights(self):
        dd = DriverDecision()
        assert dd.current_fee_weight == 1.0
        assert dd.distance_to_lot_weight == 0.5
        assert dd.walking_distance_weight == 1.5
        assert dd.availability_weight == 0.3

    def test_custom_weights(self):
        dd = DriverDecision(fee_weight=2.0, walking_distance_weight=3.0)
        assert dd.current_fee_weight == 2.0
        assert dd.walking_distance_weight == 3.0

    def test_custom_parallel_engine(self):
        engine = ParallelEngine(backend=ComputeBackend.CPU_SERIAL)
        dd = DriverDecision(parallel_engine=engine)
        assert dd.parallel_engine is engine

    # ── calculate_lot_score ──

    def test_calculate_lot_score_positive(self):
        score = DriverDecision().calculate_lot_score(_driver(), _zone())
        assert isinstance(score, float) and score > 0

    def test_score_custom_normalize(self):
        dd = DriverDecision()
        d, z = _driver(), _zone()
        s1 = dd.calculate_lot_score(d, z, normalize_current_fee=1.0, normalize_distance=1.0)
        s2 = dd.calculate_lot_score(d, z, normalize_current_fee=100.0, normalize_distance=100.0)
        assert s1 > s2  # smaller normalizers → larger scores

    def test_score_zero_fee_lot(self):
        score = DriverDecision().calculate_lot_score(_driver(), _zone(fee=0.0))
        assert score >= 0

    def test_score_full_lot_penalized(self):
        dd = DriverDecision()
        d = _driver()
        empty = _zone(cur=0, cap=100)
        full = _zone(cur=99, cap=100)
        assert dd.calculate_lot_score(d, empty) < dd.calculate_lot_score(d, full)

    # ── _calculate_distance ──

    def test_calculate_distance(self):
        assert DriverDecision._calculate_distance((0, 0), (3, 4)) == pytest.approx(5.0)

    def test_calculate_distance_same_point(self):
        assert DriverDecision._calculate_distance((5, 5), (5, 5)) == 0.0

    # ── select_parking_zone ──

    def test_select_affordable(self):
        dd = DriverDecision()
        lots = [_zone(1, 3.0), _zone(2, 4.0)]
        selected = dd.select_parking_zone(_driver(max_fee=5.0), lots)
        assert selected is not None and selected in lots

    def test_select_unaffordable_returns_none(self):
        result = DriverDecision().select_parking_zone(_driver(max_fee=1.0), [_zone(fee=10.0)])
        assert result is None

    def test_select_empty_list_returns_none(self):
        assert DriverDecision().select_parking_zone(_driver(), []) is None

    def test_closer_lot_preferred(self):
        dd = DriverDecision(fee_weight=0.0, walking_distance_weight=10.0)
        far = _zone(1, 1.0, (0.0, 0.0))
        close = _zone(2, 1.0, (490.0, 490.0))
        selected = dd.select_parking_zone(_driver(dest=(500.0, 500.0)), [far, close])
        assert selected.id == 2

    def test_select_single_affordable_lot(self):
        lot = _zone(fee=3.0)
        assert DriverDecision().select_parking_zone(_driver(max_fee=5.0), [lot]) is lot

    def test_exact_fee_boundary_affordable(self):
        lot = _zone(fee=5.0)
        assert DriverDecision().select_parking_zone(_driver(max_fee=5.0), [lot]) is lot

    # ── select_parking_zones_batch ──

    def test_batch_empty_drivers(self):
        result = DriverDecision().select_parking_zones_batch([], [_zone()])
        assert result == []

    def test_batch_empty_lots(self):
        result = DriverDecision().select_parking_zones_batch([_driver()], [])
        assert result == [None]

    def test_batch_all_affordable(self):
        dd = DriverDecision()
        lots = [_zone(1, 2.0, (200.0, 200.0)), _zone(2, 3.0, (300.0, 300.0))]
        drivers = [_driver(1, max_fee=10.0), _driver(2, max_fee=10.0)]
        results = dd.select_parking_zones_batch(drivers, lots)
        assert len(results) == 2
        assert all(idx is not None for idx in results)

    def test_batch_all_unaffordable(self):
        dd = DriverDecision()
        lots = [_zone(fee=100.0)]
        results = dd.select_parking_zones_batch([_driver(max_fee=1.0)], lots)
        assert results == [None]

    def test_batch_full_lots_masked(self):
        dd = DriverDecision()
        full_lot = _zone(1, 1.0, cap=10, cur=10)  # full
        cheap_lot = _zone(2, 1.0, cap=100, cur=0)
        results = dd.select_parking_zones_batch([_driver(max_fee=10.0)], [full_lot, cheap_lot])
        assert results == [1]  # index 1 = cheap_lot

    def test_batch_precomputed_arrays(self):
        dd = DriverDecision()
        lots = [_zone(1, 2.0, (200.0, 200.0))]
        drivers = [_driver(1, max_fee=10.0, start=(100.0, 100.0), dest=(300.0, 300.0))]
        dp = np.array([[100.0, 100.0]], dtype=np.float32)
        dd_dest = np.array([[300.0, 300.0]], dtype=np.float32)
        df = np.array([10.0], dtype=np.float32)
        lp = np.array([[200.0, 200.0]], dtype=np.float32)
        results = dd.select_parking_zones_batch(
            drivers, lots,
            driver_positions=dp, driver_destinations=dd_dest,
            driver_max_fees=df, lot_positions=lp,
        )
        assert results == [0]


# ═══════════════════════════════════════════════════════════════════════════════
# ParkingSimulation
# ═══════════════════════════════════════════════════════════════════════════════

class TestParkingSimulationInit:

    def test_default_init(self):
        sim = ParkingSimulation()
        assert sim.use_batch_processing is True
        assert sim.rejection_penalty == 100.0
        assert sim.batch_size == 500

    def test_custom_init(self):
        dd = DriverDecision(fee_weight=2.0)
        sim = ParkingSimulation(decision_maker=dd, rejection_penalty=50.0,
                                use_batch_processing=False, batch_size=100)
        assert sim.decision_maker is dd
        assert sim.rejection_penalty == 50.0
        assert sim.use_batch_processing is False
        assert sim.batch_size == 100


class TestParkingSimulationBatch:
    """Tests using batch processing (default)."""

    def test_basic_run(self):
        city = _city()
        drivers = _drivers(10, city)
        m = ParkingSimulation().run_simulation(city, drivers)
        assert isinstance(m, SimulationMetrics)
        assert m.total_parked + m.total_rejected == 10

    def test_reset_capacity(self):
        city = _city()
        city.parking_zones[0].current_capacity = 50
        m = ParkingSimulation().run_simulation(city, _drivers(5, city), reset_capacity=True)
        assert m.total_parked <= sum(z.maximum_capacity for z in city.parking_zones)

    def test_no_reset_capacity(self):
        city = _city()
        city.parking_zones[0].current_capacity = 0
        m = ParkingSimulation().run_simulation(city, _drivers(5, city), reset_capacity=False)
        assert isinstance(m, SimulationMetrics)

    def test_capacity_respected(self):
        city = _city(lots=[_zone(1, 1.0, (49.048, 8.448), cap=5), _zone(2, 1.0, (49.052, 8.452), cap=5)])
        drivers = _drivers(20, city, max_fee=10.0)
        m = ParkingSimulation().run_simulation(city, drivers)
        assert m.total_parked <= 10
        assert m.total_rejected > 0

    def test_revenue_positive(self):
        city = _city()
        m = ParkingSimulation().run_simulation(city, _drivers(5, city))
        if m.total_parked > 0:
            assert m.total_revenue > 0
            assert m.average_current_fee_paid > 0

    def test_occupancy_metrics(self):
        city = _city()
        m = ParkingSimulation().run_simulation(city, _drivers(5, city))
        assert 0.0 <= m.overall_occupancy_rate <= 1.0
        assert m.occupancy_variance >= 0.0
        assert m.occupancy_std_dev >= 0.0

    def test_lot_level_metrics(self):
        city = _city()
        m = ParkingSimulation().run_simulation(city, _drivers(5, city))
        assert set(m.lot_occupancy_rates.keys()) == {z.id for z in city.parking_zones}
        assert set(m.lot_revenues.keys()) == {z.id for z in city.parking_zones}

    def test_lot_becomes_full_mid_batch(self):
        """Driver assigned a lot that fills up before it's their turn → rejected."""
        city = _city(lots=[_zone(1, 1.0, cap=2, cur=0)])
        drivers = _drivers(10, city, max_fee=10.0)
        m = ParkingSimulation(batch_size=10).run_simulation(city, drivers)
        assert m.total_parked <= 2
        assert m.total_rejected >= 8

    def test_no_affordable_lots(self):
        city = _city(lots=[_zone(1, fee=100.0)])
        m = ParkingSimulation().run_simulation(city, _drivers(5, city, max_fee=1.0))
        assert m.total_parked == 0
        assert m.total_rejected == 5

    def test_zero_drivers(self):
        city = _city()
        m = ParkingSimulation().run_simulation(city, [])
        assert m.total_parked == 0 and m.total_rejected == 0 and m.total_revenue == 0.0

    def test_capacity_restored_after_simulation(self):
        city = _city()
        city.parking_zones[0].current_capacity = 42
        ParkingSimulation().run_simulation(city, _drivers(5, city))
        assert city.parking_zones[0].current_capacity == 42

    def test_small_batch_size(self):
        city = _city()
        m = ParkingSimulation(batch_size=2).run_simulation(city, _drivers(7, city))
        assert m.total_parked + m.total_rejected == 7


class TestParkingSimulationSequential:
    """Tests using sequential processing path."""

    def _sim(self, **kw):
        return ParkingSimulation(use_batch_processing=False, **kw)

    def test_basic_sequential(self):
        city = _city()
        m = self._sim().run_simulation(city, _drivers(10, city))
        assert isinstance(m, SimulationMetrics)
        assert m.total_parked + m.total_rejected == 10

    def test_sequential_reset_capacity(self):
        city = _city()
        city.parking_zones[0].current_capacity = 50
        m = self._sim().run_simulation(city, _drivers(5, city), reset_capacity=True)
        assert m.total_parked <= sum(z.maximum_capacity for z in city.parking_zones)

    def test_sequential_no_reset(self):
        city = _city()
        m = self._sim().run_simulation(city, _drivers(5, city), reset_capacity=False)
        assert isinstance(m, SimulationMetrics)

    def test_sequential_capacity_respected(self):
        city = _city(lots=[_zone(1, 1.0, (49.048, 8.448), cap=3), _zone(2, 1.0, (49.052, 8.452), cap=3)])
        m = self._sim().run_simulation(city, _drivers(20, city, max_fee=10.0))
        assert m.total_parked <= 6
        assert m.total_rejected > 0

    def test_sequential_rejection_penalty(self):
        city = _city(lots=[_zone(fee=100.0)])
        m = self._sim(rejection_penalty=50.0).run_simulation(
            city, _drivers(2, city, max_fee=1.0),
        )
        assert m.average_driver_cost == pytest.approx(50.0)

    def test_sequential_restores_capacity(self):
        city = _city()
        city.parking_zones[0].current_capacity = 7
        self._sim().run_simulation(city, _drivers(3, city))
        assert city.parking_zones[0].current_capacity == 7

    def test_sequential_revenue(self):
        city = _city()
        m = self._sim().run_simulation(city, _drivers(5, city))
        if m.total_parked > 0:
            assert m.total_revenue > 0

    def test_sequential_zero_drivers(self):
        m = self._sim().run_simulation(_city(), [])
        assert m.total_parked == 0 and m.total_revenue == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# _build_metrics edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildMetrics:

    def test_single_lot_zero_variance(self):
        city = _city(lots=[_zone(1, 2.0, cap=100)])
        m = ParkingSimulation().run_simulation(city, _drivers(3, city))
        assert m.occupancy_variance == 0.0
        assert m.occupancy_std_dev == 0.0

    def test_zero_parked_averages(self):
        city = _city(lots=[_zone(fee=100.0)])
        m = ParkingSimulation().run_simulation(city, _drivers(3, city, max_fee=1.0))
        assert m.average_walking_distance == 0.0
        assert m.average_current_fee_paid == 0.0

    def test_average_revenue_per_lot(self):
        city = _city()
        m = ParkingSimulation().run_simulation(city, _drivers(10, city))
        if m.total_revenue > 0:
            expected = m.total_revenue / len(city.parking_zones)
            assert m.average_revenue_per_lot == pytest.approx(expected)


# ═══════════════════════════════════════════════════════════════════════════════
# evaluate_current_fee_configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluateFeeConfig:

    def test_basic_evaluation(self):
        city = _city()
        objectives = ParkingSimulation().evaluate_current_fee_configuration(
            city, _drivers(10, city), [4.0, 4.0],
            objectives=["revenue", "occupancy_variance"],
        )
        assert "revenue" in objectives and "occupancy_variance" in objectives
        assert isinstance(objectives["revenue"], float)

    def test_wrong_fee_vector_length(self):
        with pytest.raises(ValueError, match="doesn't match"):
            ParkingSimulation().evaluate_current_fee_configuration(
                _city(), _drivers(5), [4.0],
            )

    def test_all_objectives_returned(self):
        city = _city()
        objectives = ParkingSimulation().evaluate_current_fee_configuration(
            city, _drivers(5, city), [3.0, 5.0],
        )
        expected_keys = {
            "revenue", "negative_revenue", "occupancy_variance",
            "avg_driver_cost", "rejection_rate", "occupancy_std_dev",
            "utilization_rate", "negative_utilization",
        }
        assert set(objectives.keys()) == expected_keys

    def test_negative_revenue_sign(self):
        city = _city()
        obj = ParkingSimulation().evaluate_current_fee_configuration(
            city, _drivers(5, city), [3.0, 5.0],
        )
        assert obj["negative_revenue"] == pytest.approx(-obj["revenue"])

    def test_unknown_objective_ignored(self):
        city = _city()
        obj = ParkingSimulation().evaluate_current_fee_configuration(
            city, _drivers(5, city), [3.0, 5.0],
            objectives=["revenue", "nonexistent"],
        )
        assert "revenue" in obj
        assert "nonexistent" not in obj

    def test_fee_vector_applied(self):
        city = _city()
        drivers = _drivers(10, city, max_fee=10.0)
        low = ParkingSimulation().evaluate_current_fee_configuration(
            city, drivers, [1.0, 1.0],
        )
        high = ParkingSimulation().evaluate_current_fee_configuration(
            city, drivers, [9.0, 9.0],
        )
        # Higher fees → more rejections or higher revenue per driver
        assert low["revenue"] != high["revenue"] or low["rejection_rate"] != high["rejection_rate"]


# ═══════════════════════════════════════════════════════════════════════════════
# SimulationBatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationBatch:

    def _batch(self, **kw):
        return SimulationBatch(ParkingSimulation(), **kw)

    def _gen_sets(self, city, n_sets=3, n_drivers=20):
        gen = DriverGenerator(seed=42)
        return [gen.generate_random_drivers(count=n_drivers, city=city) for _ in range(n_sets)]

    def test_run_multiple(self):
        city = _city()
        results = self._batch().run_multiple_simulations(city, self._gen_sets(city, 3))
        assert len(results) == 3
        assert all(isinstance(m, SimulationMetrics) for m in results)

    def test_run_single_set_falls_to_sequential(self):
        city = _city()
        results = self._batch().run_multiple_simulations(city, self._gen_sets(city, 1))
        assert len(results) == 1

    def test_run_parallel_false(self):
        city = _city()
        results = self._batch().run_multiple_simulations(
            city, self._gen_sets(city, 3), parallel=False,
        )
        assert len(results) == 3

    def test_run_with_fee_vector(self):
        city = _city()
        results = self._batch().run_multiple_simulations(
            city, self._gen_sets(city, 2), current_fee_vector=[4.0, 4.0],
        )
        assert len(results) == 2

    def test_run_sequential_with_fee_vector(self):
        city = _city()
        results = self._batch().run_multiple_simulations(
            city, self._gen_sets(city, 2), current_fee_vector=[4.0, 4.0], parallel=False,
        )
        assert len(results) == 2

    def test_average_metrics(self):
        city = _city()
        results = self._batch().run_multiple_simulations(city, self._gen_sets(city, 5))
        avg = self._batch().average_metrics(results)
        assert "avg_revenue" in avg and "avg_utilization" in avg
        assert isinstance(avg["avg_revenue"], float)

    def test_average_metrics_empty(self):
        assert self._batch().average_metrics([]) == {}

    def test_average_metrics_single(self):
        city = _city()
        results = self._batch().run_multiple_simulations(city, self._gen_sets(city, 1))
        avg = self._batch().average_metrics(results)
        assert avg["std_revenue"] == 0.0
        assert avg["std_occupancy_variance"] == 0.0

    def test_parallel_with_fee_vector(self):
        city = _city()
        results = self._batch().run_multiple_simulations(
            city, self._gen_sets(city, 3), current_fee_vector=[3.0, 5.0], parallel=True,
        )
        assert len(results) == 3

    def test_parallel_without_fee_vector(self):
        city = _city()
        results = self._batch().run_multiple_simulations(
            city, self._gen_sets(city, 3), current_fee_vector=None, parallel=True,
        )
        assert len(results) == 3
