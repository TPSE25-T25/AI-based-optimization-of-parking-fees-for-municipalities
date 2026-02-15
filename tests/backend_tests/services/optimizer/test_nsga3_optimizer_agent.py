import numpy as np
import pytest

from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased
from backend.services.settings.optimizations_settings import AgentBasedSettings
from backend.services.models.city import City, ParkingZone


# -------------------------
# Helpers / fakes
# -------------------------

class FakeParallelEngine:
    def get_backend_info(self):
        return {
            "backend": "cpu",
            "cuda_available": False,
            "n_jobs": 1,
        }

    def compute_driver_lot_scores(
        self,
        driver_positions,
        driver_destinations,
        driver_max_fees,
        lot_positions,
        lot_fees,
        lot_occupancy,
        fee_weight,
        distance_to_lot_weight,
        walking_distance_weight,
        availability_weight,
    ):
        # Deterministic scores: everyone prefers the cheapest lot.
        # Must return shape (n_drivers, n_lots)
        n_drivers = driver_positions.shape[0]
        n_lots = lot_fees.shape[0]
        scores = np.tile(lot_fees.reshape(1, n_lots), (n_drivers, 1)).astype(np.float32)
        return scores


class FakeDecisionMaker:
    def __init__(self):
        self.parallel_engine = FakeParallelEngine()

        # weights used by _run_fast_simulation()
        self.current_fee_weight = 1.0
        self.distance_to_lot_weight = 0.0
        self.walking_distance_weight = 0.0
        self.availability_weight = 0.0


class FakeSimulation:
    def __init__(self):
        self.decision_maker = FakeDecisionMaker()
        self.rejection_penalty = 10.0

    def run_simulation(self, city, drivers, reset_capacity=True):
        # Minimal fake metrics object with attributes used by _get_detailed_results
        class Metrics:
            lot_occupancy_rates = {
                z.id: (z.current_capacity / z.maximum_capacity if z.maximum_capacity else 0.0)
                for z in city.parking_zones
            }
            lot_revenues = {z.id: 123.0 for z in city.parking_zones}

        return Metrics()

    def _build_metrics(
        self,
        city,
        drivers,
        total_revenue,
        total_driver_cost,
        total_walking_distance,
        parked_count,
        rejected_count,
        lot_revenues,
    ):
        # Any object is fine; we patch OptimizationAdapter.extract_objectives_from_metrics
        return {
            "total_revenue": total_revenue,
            "parked_count": parked_count,
            "rejected_count": rejected_count,
            "lot_revenues": lot_revenues,
            "city": city,
        }


class FakeBatchSimulator:
    def __init__(self, simulation, n_jobs=-1):
        self.simulation = simulation
        self.n_jobs = n_jobs


class FakeDriver:
    def __init__(self, starting_position, destination, max_fee, desired_minutes=60):
        self.starting_position = starting_position
        self.destination = destination
        self.max_parking_current_fee = max_fee
        self.desired_parking_time = desired_minutes


class FakeAdapter:
    def __init__(self, drivers_per_zone_capacity, random_seed):
        self.drivers_per_zone_capacity = drivers_per_zone_capacity
        self.random_seed = random_seed

    def create_drivers_from_request(self, city):
        # Deterministic two-driver population
        return [
            FakeDriver((0.0, 0.0), (0.0, 0.0), max_fee=100.0, desired_minutes=60),
            FakeDriver((1.0, 1.0), (1.0, 1.0), max_fee=100.0, desired_minutes=60),
        ]


# -------------------------
# Fixtures
# -------------------------

@pytest.fixture
def sample_city():
    zones = [
        ParkingZone(
            id=1,
            name="Zone A",
            position=(49.0, 8.4),
            current_fee=2.0,
            min_fee=1.0,
            max_fee=5.0,
            maximum_capacity=10,
            current_capacity=3,
            elasticity=-0.3,
            short_term_share=0.5,
        ),
        ParkingZone(
            id=2,
            name="Zone B",
            position=(49.01, 8.41),
            current_fee=3.0,
            min_fee=1.0,
            max_fee=6.0,
            maximum_capacity=10,
            current_capacity=4,
            elasticity=-0.3,
            short_term_share=0.5,
        ),
    ]
    return City(
        id=1,
        name="TestCity",
        min_latitude=48.9,
        max_latitude=49.2,
        min_longitude=8.3,
        max_longitude=8.6,
        parking_zones=zones,
        point_of_interests=[],
    )


@pytest.fixture
def settings():
    # MUST be AgentBasedSettings (has simulation_runs and driver weights)
    return AgentBasedSettings(
        random_seed=42,
        population_size=10,
        generations=2,
        target_occupancy=0.85,
        min_fee=1.0,
        max_fee=10.0,
        fee_increment=0.5,
        simulation_runs=1,
        drivers_per_zone_capacity=1.0,
        driver_fee_weight=1.0,
        driver_distance_to_lot_weight=0.0,
        driver_walking_distance_weight=0.0,
        driver_availability_weight=0.0,
    )


@pytest.fixture
def optimizer(settings):
    opt = NSGA3OptimizerAgentBased(settings)

    # Replace heavy real components with fakes
    opt.adapter = FakeAdapter(
        drivers_per_zone_capacity=settings.drivers_per_zone_capacity,
        random_seed=settings.random_seed,
    )
    opt.simulation = FakeSimulation()
    opt.batch_simulator = FakeBatchSimulator(simulation=opt.simulation, n_jobs=1)

    return opt


# -------------------------
# Tests
# -------------------------

class TestNSGA3OptimizerAgentBased:
    def test_initialize_simulation_environment_sets_caches(self, optimizer, sample_city):
        optimizer._initialize_simulation_environment(sample_city)

        assert optimizer.base_city is sample_city
        assert optimizer.base_drivers is not None
        assert len(optimizer.base_drivers) == 2

        assert optimizer.zone_ids == [1, 2]
        assert optimizer.original_fees == [2.0, 3.0]

        # Cached arrays should exist with correct shapes
        assert optimizer.driver_positions_cache.shape == (2, 2)
        assert optimizer.driver_destinations_cache.shape == (2, 2)
        assert optimizer.driver_max_fees_cache.shape == (2,)
        assert optimizer.lot_positions_cache.shape == (2, 2)

    def test_get_detailed_results_restores_original_fees(self, optimizer, sample_city):
        optimizer._initialize_simulation_environment(sample_city)

        new_fees = np.array([5.0, 6.0], dtype=np.float32)
        before = [z.current_fee for z in sample_city.parking_zones]

        out = optimizer._get_detailed_results(new_fees, _data={})

        after = [z.current_fee for z in sample_city.parking_zones]
        assert after == before, "Fees must be restored after _get_detailed_results"

        assert "occupancy" in out and "revenue" in out
        assert out["occupancy"].shape == (2,)
        assert out["revenue"].shape == (2,)

    def test_run_fast_simulation_resets_and_restores_capacities(self, optimizer, sample_city):
        optimizer._initialize_simulation_environment(sample_city)

        # Start with known capacities
        sample_city.parking_zones[0].current_capacity = 3
        sample_city.parking_zones[1].current_capacity = 4
        before_caps = [z.current_capacity for z in sample_city.parking_zones]

        metrics = optimizer._run_fast_simulation()

        after_caps = [z.current_capacity for z in sample_city.parking_zones]
        assert after_caps == before_caps, "Capacities must be restored after _run_fast_simulation"
        assert metrics is not None

    def test_simulate_scenario_restores_original_fees(self, optimizer, sample_city, monkeypatch):
        # IMPORTANT: import the module directly (reliable)
        import backend.services.optimizer.schemas.optimization_adapters as adapters_module

        def fake_extract_objectives_from_metrics(metrics, target_occupancy):
            return (100.0, 0.1, 0.2, 0.3)

        monkeypatch.setattr(
            adapters_module.OptimizationAdapter,
            "extract_objectives_from_metrics",
            staticmethod(fake_extract_objectives_from_metrics),
        )

        optimizer._initialize_simulation_environment(sample_city)

        before = [z.current_fee for z in sample_city.parking_zones]
        objectives = optimizer._simulate_scenario(
            current_fees=np.array([4.0, 5.0], dtype=np.float32),
            city=sample_city,
        )
        after = [z.current_fee for z in sample_city.parking_zones]

        assert after == before, "Fees must be restored after _simulate_scenario"
        assert objectives == (100.0, 0.1, 0.2, 0.3)

    def test_optimize_calls_initialize_environment(self, optimizer, sample_city, monkeypatch):
        called = {"init": False, "super": False}

        def fake_init(city):
            called["init"] = True

        monkeypatch.setattr(optimizer, "_initialize_simulation_environment", fake_init)

        # Patch base class optimize so we don't run pymoo
        from backend.services.optimizer import nsga3_optimizer as base_module

        def fake_base_optimize(self, city):
            called["super"] = True
            return []

        monkeypatch.setattr(base_module.NSGA3Optimizer, "optimize", fake_base_optimize)

        result = optimizer.optimize(sample_city)

        assert called["init"] is True
        assert called["super"] is True
        assert result == []
