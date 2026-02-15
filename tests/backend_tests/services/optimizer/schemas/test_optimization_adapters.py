import numpy as np
import pytest

from backend.services.optimizer.schemas.optimization_adapters import (
    SimulationAdapter,
    OptimizationAdapter,
    create_default_adapter,
)
from backend.services.models.city import City, ParkingZone


# -------------------------
# Helpers
# -------------------------

@pytest.fixture
def sample_zones():
    return [
        ParkingZone(
            id=1,
            name="Zone A",
            position=(49.00, 8.40),
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
            position=(49.02, 8.42),
            current_fee=3.0,
            min_fee=1.0,
            max_fee=6.0,
            maximum_capacity=20,
            current_capacity=6,
            elasticity=-0.4,
            short_term_share=0.6,
        ),
    ]


@pytest.fixture
def sample_city(sample_zones):
    return City(
        id=123,
        name="TestCity",
        min_latitude=48.9,
        max_latitude=49.3,
        min_longitude=8.3,
        max_longitude=8.6,
        parking_zones=sample_zones,
        point_of_interests=[],
    )


# -------------------------
# Tests: SimulationAdapter
# -------------------------

class TestSimulationAdapterCreateCityFromRequest:
    def test_raises_if_no_zones(self):
        adapter = SimulationAdapter()
        with pytest.raises(ValueError):
            adapter.create_city_from_request([])

    def test_bounds_are_computed_with_padding(self, sample_zones, monkeypatch):
        adapter = SimulationAdapter(bounds_padding=0.01)

        # Prevent real OSM call
        from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource
        monkeypatch.setattr(
            OSMnxDataSource,
            "load_points_of_interest",
            staticmethod(lambda city_name, center_coords, limit: []),
        )

        city = adapter.create_city_from_request(sample_zones)

        lats = [z.position[0] for z in sample_zones]
        lons = [z.position[1] for z in sample_zones]

        assert city.min_latitude == min(lats) - 0.01
        assert city.max_latitude == max(lats) + 0.01
        assert city.min_longitude == min(lons) - 0.01
        assert city.max_longitude == max(lons) + 0.01

        # Also sanity check center coords were computed (indirectly by no crash)
        assert city.name == "OptimizationCity"
        assert city.parking_zones == sample_zones
        assert city.point_of_interests == []


class TestSimulationAdapterCreateDriversFromRequest:
    def test_uses_total_capacity_and_multiplier(self, sample_city, monkeypatch):
        adapter = SimulationAdapter(drivers_per_zone_capacity=2.0, random_seed=99)

        # total capacity = 10 + 20 = 30, multiplier 2.0 => 60 drivers
        expected_num = int(sample_city.total_parking_capacity() * 2.0)

        # Patch DriverGenerator.generate_random_drivers to avoid randomness & heavy objects
        from backend.services.datasources.generator.driver_generator import DriverGenerator

        calls = {"seed": None, "num": None, "city": None}

        def fake_init(self, seed):
            calls["seed"] = seed

        def fake_generate(self, num_drivers, city):
            calls["num"] = num_drivers
            calls["city"] = city
            return ["driver"] * num_drivers

        monkeypatch.setattr(DriverGenerator, "__init__", fake_init, raising=False)
        monkeypatch.setattr(DriverGenerator, "generate_random_drivers", fake_generate, raising=False)

        drivers = adapter.create_drivers_from_request(sample_city)

        assert calls["seed"] == 99
        assert calls["num"] == expected_num
        assert calls["city"] is sample_city
        assert len(drivers) == expected_num


class TestSimulationAdapterApplyFees:
    def test_applies_fees_only_for_existing_ids(self, sample_city):
        adapter = SimulationAdapter()

        zone_ids = [1, 999, 2]  # 999 doesn't exist
        fees = np.array([4.5, 7.7, 1.25], dtype=np.float32)

        before = {z.id: z.current_fee for z in sample_city.parking_zones}

        out_city = adapter.apply_current_fees_to_city(sample_city, fees, zone_ids)

        assert out_city is sample_city

        after = {z.id: z.current_fee for z in sample_city.parking_zones}
        assert after[1] == float(fees[0])
        assert after[2] == float(fees[2])
        # unchanged zone ids not targeted remain same (only 1 & 2 existed)
        assert set(after.keys()) == set(before.keys())

    def test_handles_mismatched_lengths_by_zip(self, sample_city):
        adapter = SimulationAdapter()

        zone_ids = [1, 2, 3]  # 3 doesn't exist, also longer than fees
        fees = np.array([9.0, 8.0], dtype=np.float32)

        adapter.apply_current_fees_to_city(sample_city, fees, zone_ids)

        assert sample_city.get_parking_zone_by_id(1).current_fee == 9.0
        assert sample_city.get_parking_zone_by_id(2).current_fee == 8.0


# -------------------------
# Tests: OptimizationAdapter
# -------------------------

class TestOptimizationAdapterExtractObjectives:
    def test_extract_objectives_happy_path(self):
        # Build a minimal "metrics-like" object with required attributes
        class Metrics:
            total_revenue = 1000.0
            lot_occupancy_rates = {1: 0.80, 2: 0.90}
            rejection_rate = 0.10
            average_driver_cost = 5.0
            occupancy_variance = 0.04

        target = 0.85
        f1, f2, f3, f4 = OptimizationAdapter.extract_objectives_from_metrics(Metrics(), target)

        assert f1 == 1000.0
        # avg gap: |0.80-0.85|=0.05, |0.90-0.85|=0.05 => 0.05
        assert abs(f2 - 0.05) < 1e-9
        assert f3 == 0.10

        # user_balance = avg( 1/(avg_cost+1), 1/(var+1) )
        expected_cost = 1.0 / (5.0 + 1.0)
        expected_var = 1.0 / (0.04 + 1.0)
        expected_balance = (expected_cost + expected_var) / 2.0
        assert abs(f4 - expected_balance) < 1e-9

    def test_extract_objectives_no_lots(self):
        class Metrics:
            total_revenue = 0.0
            lot_occupancy_rates = {}
            rejection_rate = 0.0
            average_driver_cost = 0.0
            occupancy_variance = 0.0

        f1, f2, f3, f4 = OptimizationAdapter.extract_objectives_from_metrics(Metrics(), target_occupancy=0.85)
        assert f1 == 0.0
        assert f2 == 0.0  # handled empty list
        assert f3 == 0.0
        assert f4 == 1.0  # (1/(0+1) + 1/(0+1))/2 = 1


# -------------------------
# Tests: factory
# -------------------------

class TestCreateDefaultAdapter:
    def test_factory_sets_values(self):
        a = create_default_adapter(drivers_per_zone_capacity=1.2, random_seed=7, bounds_padding=0.02)
        assert isinstance(a, SimulationAdapter)
        assert a.drivers_per_zone_capacity == 1.2
        assert a.random_seed == 7
        assert a.bounds_padding == 0.02
