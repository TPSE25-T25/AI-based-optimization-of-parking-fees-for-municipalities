"""
Unit tests for NSGA3Optimizer.
Tests the multi-objective optimization engine for parking pricing.
"""

import pytest
import numpy as np
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.models.city import ParkingZone, City
from backend.services.settings.optimizations_settings import OptimizationSettings
from backend.services.optimizer.schemas.optimization_schema import PricingScenario
from backend.services.payloads.optimization_payload import OptimizationRequest


@pytest.fixture
def sample_zones():
    """Create sample parking zones for testing."""
    return [
        ParkingZone(
            id=1,
            name="Zone_A",
            current_fee=3.0,
            position=(49.01, 8.41),
            maximum_capacity=100,
            current_capacity=60,
            min_fee=1.0,
            max_fee=8.0,
            elasticity=-0.5,
            short_term_share=0.6
        ),
        ParkingZone(
            id=2,
            name="Zone_B",
            current_fee=4.0,
            position=(49.02, 8.42),
            maximum_capacity=150,
            current_capacity=120,
            min_fee=2.0,
            max_fee=10.0,
            elasticity=-0.4,
            short_term_share=0.7
        ),
        ParkingZone(
            id=3,
            name="Zone_C",
            current_fee=2.5,
            position=(49.03, 8.43),
            maximum_capacity=80,
            current_capacity=30,
            min_fee=1.5,
            max_fee=6.0,
            elasticity=-0.6,
            short_term_share=0.4
        )
    ]


@pytest.fixture
def optimization_settings():
    """Create optimization settings for testing."""
    return OptimizationSettings(
        population_size=20,  # Small for faster tests
        generations=5,       # Small for faster tests
        target_occupancy=0.85
    )


@pytest.fixture
def optimization_request(sample_zones, optimization_settings):
    """Create a complete optimization request for testing."""
    city = City(
        id=1,
        name="TestCity",
        min_latitude=49.0,
        max_latitude=49.04,
        min_longitude=8.40,
        max_longitude=8.44,
        parking_zones=sample_zones,
        point_of_interests=[]
    )
    return OptimizationRequest(
        city=city,
        optimizer_settings=optimization_settings
    )


@pytest.fixture
def optimizer():
    """Create an optimizer instance with fixed seed for reproducibility."""
    settings = OptimizationSettings(
        random_seed=42,
        population_size=20,
        generations=5,
        target_occupancy=0.85
    )
    return NSGA3OptimizerElasticity(settings)


class TestNSGA3OptimizerDataConversion:
    """Test data conversion methods."""

    def test_convert_request_to_numpy_structure(self, optimizer, optimization_request):
        """Test that conversion produces correct dictionary structure."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)

        # Check all expected keys are present
        expected_keys = {
            "current_current_fees", "min_fees", "max_fees", "capacities",
            "elasticities", "current_occupancy", "short_term_share", "target_occupancy"
        }
        assert set(data.keys()) == expected_keys

    def test_convert_request_to_numpy_types(self, optimizer, optimization_request):
        """Test that arrays have correct numpy types."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)

        # Check that all arrays are numpy arrays
        for key in ["current_current_fees", "min_fees", "max_fees", "capacities",
                    "elasticities", "current_occupancy", "short_term_share"]:
            assert isinstance(data[key], np.ndarray)

    def test_convert_request_to_numpy_shapes(self, optimizer, optimization_request):
        """Test that arrays have correct shapes."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        n_zones = len(optimization_request.city.parking_zones)

        # Check array dimensions
        for key in ["current_current_fees", "min_fees", "max_fees", "capacities",
                    "elasticities", "current_occupancy", "short_term_share"]:
            assert data[key].shape == (n_zones,)

    def test_convert_request_to_numpy_values(self, optimizer, optimization_request):
        """Test that converted values match input data."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        zones = optimization_request.city.parking_zones

        # Check specific values
        assert data["current_current_fees"][0] == float(zones[0].current_fee)
        assert data["min_fees"][1] == zones[1].min_fee
        assert data["max_fees"][2] == zones[2].max_fee
        assert data["capacities"][0] == zones[0].maximum_capacity
        assert data["elasticities"][1] == zones[1].elasticity

    def test_convert_request_occupancy_calculation(self, optimizer, optimization_request):
        """Test that occupancy is calculated correctly."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        zones = optimization_request.city.parking_zones

        # Zone 0: 60/100 = 0.6
        expected_occ_0 = zones[0].current_capacity / zones[0].maximum_capacity
        assert abs(data["current_occupancy"][0] - expected_occ_0) < 1e-6

        # Zone 1: 120/150 = 0.8
        expected_occ_1 = zones[1].current_capacity / zones[1].maximum_capacity
        assert abs(data["current_occupancy"][1] - expected_occ_1) < 1e-6

    def test_convert_request_very_small_capacity_handling(self, optimizer):
        """Test handling of zones with very small capacity."""
        zone_small_capacity = ParkingZone(
            id=99,
            name="SmallZone",
            current_fee=3.0,
            position=(49.0, 8.4),
            maximum_capacity=1,  # Minimum valid capacity
            current_capacity=0,
            min_fee=1.0,
            max_fee=5.0
        )

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.39,
            max_longitude=8.41,
            parking_zones=[zone_small_capacity],
            point_of_interests=[]
        )

        data = optimizer._convert_zones_to_numpy(city.parking_zones)

        # Should calculate occupancy correctly for small capacities
        assert data["current_occupancy"][0] == 0.0


class TestNSGA3OptimizerPhysicsCalculation:
    """Test physics simulation engine."""

    def test_calculate_physics_returns_correct_structure(self, optimizer, optimization_request):
        """Test that physics calculation returns expected structure."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = data["current_current_fees"]

        results = optimizer._calculate_physics(current_fees, data)

        # Check structure
        assert "objectives" in results
        assert "occupancy" in results
        assert "revenue" in results
        assert "demand_change" in results

        # Check objectives count
        assert len(results["objectives"]) == 4

    def test_calculate_physics_array_shapes(self, optimizer, optimization_request):
        """Test that output arrays have correct shapes."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = data["current_current_fees"]
        n_zones = len(optimization_request.city.parking_zones)

        results = optimizer._calculate_physics(current_fees, data)

        # Check array shapes
        assert results["occupancy"].shape == (n_zones,)
        assert results["revenue"].shape == (n_zones,)
        assert results["demand_change"].shape == (n_zones,)

    def test_calculate_physics_current_fee_increase_reduces_demand(self, optimizer, optimization_request):
        """Test that current_fee increases reduce occupancy (negative elasticity)."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)

        # Calculate with current current_fees
        results_current = optimizer._calculate_physics(data["current_current_fees"], data)

        # Calculate with doubled current_fees
        increased_current_fees = data["current_current_fees"] * 2.0
        results_increased = optimizer._calculate_physics(increased_current_fees, data)

        # With negative elasticity, higher current_fees should reduce occupancy
        assert np.all(results_increased["occupancy"] <= results_current["occupancy"])

    def test_calculate_physics_current_fee_decrease_increases_demand(self, optimizer, optimization_request):
        """Test that current_fee decreases increase occupancy."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)

        # Calculate with current current_fees
        results_current = optimizer._calculate_physics(data["current_current_fees"], data)

        # Calculate with halved current_fees
        decreased_current_fees = data["current_current_fees"] * 0.5
        results_decreased = optimizer._calculate_physics(decreased_current_fees, data)

        # Lower current_fees should increase occupancy
        assert np.all(results_decreased["occupancy"] >= results_current["occupancy"])

    def test_calculate_physics_occupancy_constraints(self, optimizer, optimization_request):
        """Test that occupancy is constrained to valid range."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)

        # Test with very low current_fees (should cap at 1.0)
        low_current_fees = data["min_fees"] * 0.1
        results_low = optimizer._calculate_physics(low_current_fees, data)
        assert np.all(results_low["occupancy"] >= 0.05)
        assert np.all(results_low["occupancy"] <= 1.0)

        # Test with very high current_fees (should stay above 0.05)
        high_current_fees = data["max_fees"] * 10.0
        results_high = optimizer._calculate_physics(high_current_fees, data)
        assert np.all(results_high["occupancy"] >= 0.05)
        assert np.all(results_high["occupancy"] <= 1.0)

    def test_calculate_physics_revenue_calculation(self, optimizer, optimization_request):
        """Test that revenue is calculated correctly."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = np.array([5.0, 6.0, 4.0])

        results = optimizer._calculate_physics(current_fees, data)

        # Revenue should be: current_fee * capacity * occupancy
        for i in range(len(current_fees)):
            expected_revenue = current_fees[i] * data["capacities"][i] * results["occupancy"][i]
            assert abs(results["revenue"][i] - expected_revenue) < 1e-6

    def test_calculate_physics_objectives_types(self, optimizer, optimization_request):
        """Test that objective values are floats."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = data["current_current_fees"]

        results = optimizer._calculate_physics(current_fees, data)

        # All objectives should be numeric
        for obj in results["objectives"]:
            assert isinstance(obj, (float, np.floating))

    def test_calculate_physics_loss_aversion(self, optimizer, optimization_request):
        """Test that loss aversion affects current_fee increases more than decreases."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        base_current_fees = data["current_current_fees"]

        # 10% current_fee increase
        increased_current_fees = base_current_fees * 1.1
        results_increase = optimizer._calculate_physics(increased_current_fees, data)

        # 10% current_fee decrease
        decreased_current_fees = base_current_fees * 0.9
        results_decrease = optimizer._calculate_physics(decreased_current_fees, data)

        # The demand drop from a 10% increase should be larger than
        # the demand gain from a 10% decrease (loss aversion)
        avg_demand_drop = np.mean(results_increase["demand_change"])
        avg_demand_gain = np.mean(results_decrease["demand_change"])

        assert avg_demand_drop < 0  # Negative change from increase
        assert avg_demand_gain > 0  # Positive change from decrease
        assert abs(avg_demand_drop) > abs(avg_demand_gain)  # Stronger reaction to increases


class TestNSGA3OptimizerSimulation:
    """Test scenario simulation wrapper."""

    def test_simulate_scenario_returns_four_objectives(self, optimizer, optimization_request):
        """Test that simulation returns exactly 4 objectives."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = data["current_current_fees"]

        f1, f2, f3, f4 = optimizer._simulate_scenario(current_fees, optimization_request.city.parking_zones)

        # Should return 4 float values
        assert isinstance(f1, (float, np.floating))
        assert isinstance(f2, (float, np.floating))
        assert isinstance(f3, (float, np.floating))
        assert isinstance(f4, (float, np.floating))

    def test_simulate_scenario_consistent_with_physics(self, optimizer, optimization_request):
        """Test that simulation wrapper matches physics calculation."""
        data = optimizer._convert_zones_to_numpy(optimization_request.city.parking_zones)
        current_fees = data["current_current_fees"]

        # Get objectives from simulation
        sim_objectives = optimizer._simulate_scenario(current_fees, optimization_request.city.parking_zones)

        # Get objectives from physics directly
        physics_results = optimizer._calculate_physics(current_fees, data)
        physics_objectives = physics_results["objectives"]

        # Should match
        for i in range(4):
            assert abs(sim_objectives[i] - physics_objectives[i]) < 1e-6


class TestNSGA3OptimizerOptimization:
    """Test the main optimization method."""

    def test_optimize_returns_valid_response(self, optimizer, optimization_request):
        """Test that optimize returns a valid OptimizationResponse."""
        response = optimizer.optimize(optimization_request.city)

        # Check type
        assert isinstance(response, list)

        # Check that it contains PricingScenarios
        assert all(isinstance(s, PricingScenario) for s in response)

    def test_optimize_returns_multiple_scenarios(self, optimizer, optimization_request):
        """Test that optimize returns multiple Pareto-optimal scenarios."""
        response = optimizer.optimize(optimization_request.city)

        # Should return at least one scenario
        assert len(response) >= 1

        # Should return multiple scenarios (Pareto front)
        assert len(response) > 1

    def test_optimize_scenarios_have_valid_structure(self, optimizer, optimization_request):
        """Test that each scenario has the correct structure."""
        response = optimizer.optimize(optimization_request.city)

        for scenario in response:
            # Check scenario structure
            assert isinstance(scenario, PricingScenario)
            assert hasattr(scenario, 'scenario_id')
            assert hasattr(scenario, 'zones')
            assert hasattr(scenario, 'score_revenue')
            assert hasattr(scenario, 'score_occupancy_gap')
            assert hasattr(scenario, 'score_demand_drop')
            assert hasattr(scenario, 'score_user_balance')

            # Check zone results
            assert len(scenario.zones) == len(optimization_request.city.parking_zones)

    def test_optimize_respects_current_fee_bounds(self, optimizer, optimization_request):
        """Test that optimized current_fees respect min/max fee constraints."""
        response = optimizer.optimize(optimization_request.city)
        zones = optimization_request.city.parking_zones

        for scenario in response:
            for i, zone_result in enumerate(scenario.zones):
                # Check that new fee is within bounds
                assert zone_result.new_fee >= zones[i].min_fee
                assert zone_result.new_fee <= zones[i].max_fee

    def test_optimize_reproducibility_with_seed(self):
        """Test that optimization is reproducible with same seed."""
        zones = [
            ParkingZone(
                id=1,
                name="TestZone",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=50,
                min_fee=1.0,
                max_fee=8.0
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        request = OptimizationRequest(
            city=city,
            optimizer_settings=OptimizationSettings(
                population_size=20,
                generations=5,
                target_occupancy=0.85
            )
        )

        # Run optimization twice with same seed
        optimizer1 = NSGA3OptimizerElasticity(OptimizationSettings(random_seed=123))
        response1 = optimizer1.optimize(request.city)

        optimizer2 = NSGA3OptimizerElasticity(OptimizationSettings(random_seed=123))
        response2 = optimizer2.optimize(request.city)

        # Results should be identical
        assert len(response1) == len(response2)

        # Check first scenario matches
        assert response1[0].score_revenue == response2[0].score_revenue
        assert response1[0].zones[0].new_fee == response2[0].zones[0].new_fee

    def test_optimize_with_single_zone(self, optimizer):
        """Test optimization with a single parking zone."""
        zones = [
            ParkingZone(
                id=1,
                name="SingleZone",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=60,
                min_fee=1.0,
                max_fee=8.0
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        request = OptimizationRequest(
            city=city,
            optimizer_settings=OptimizationSettings(
                population_size=10,
                generations=3
            )
        )

        response = optimizer.optimize(request.city)

        # Should still work with single zone
        assert len(response) >= 1
        assert len(response[0].zones) == 1

    def test_optimize_zone_ids_preserved(self, optimizer, optimization_request):
        """Test that zone IDs are preserved in results."""
        response = optimizer.optimize(optimization_request.city)
        original_ids = {z.id for z in optimization_request.city.parking_zones}

        for scenario in response:
            result_ids = {z.id for z in scenario.zones}
            assert result_ids == original_ids


class TestNSGA3OptimizerBestSolutionSelection:
    """Test best solution selection method."""

    @pytest.fixture
    def sample_response(self, optimizer, optimization_request):
        """Create a sample optimization response for testing."""
        return optimizer.optimize(optimization_request.city)

    def test_select_best_solution_returns_scenario(self, optimizer, sample_response):
        """Test that selection returns a valid scenario."""
        weights = {"revenue": 50, "occupancy": 50}

        best = optimizer.select_best_solution_by_weights(sample_response, weights)

        assert isinstance(best, PricingScenario)
        assert best in sample_response

    def test_select_best_solution_revenue_weight(self, optimizer, sample_response):
        """Test selection with 100% revenue weight."""
        weights = {"revenue": 100, "occupancy": 0, "drop": 0, "fairness": 0}

        best = optimizer.select_best_solution_by_weights(sample_response, weights)

        # Should select scenario with highest revenue
        max_revenue = max(s.score_revenue for s in sample_response)
        assert best.score_revenue == max_revenue

    def test_select_best_solution_balanced_weights(self, optimizer, sample_response):
        """Test selection with balanced weights."""
        weights = {"revenue": 25, "occupancy": 25, "drop": 25, "fairness": 25}

        best = optimizer.select_best_solution_by_weights(sample_response, weights)

        # Should return a scenario (exact scenario depends on normalization)
        assert best is not None
        assert best in sample_response

    def test_select_best_solution_missing_weights(self, optimizer, sample_response):
        """Test selection with missing weights (should default to 0)."""
        weights = {"revenue": 100}  # Only one weight provided

        best = optimizer.select_best_solution_by_weights(sample_response, weights)

        # Should still work and return highest revenue scenario
        assert best is not None

    def test_select_best_solution_empty_weights(self, optimizer, sample_response):
        """Test selection with empty weights."""
        weights = {}

        best = optimizer.select_best_solution_by_weights(sample_response, weights)

        # Should still return a scenario (first one or arbitrary)
        assert best is not None

    def test_select_best_solution_single_scenario(self, optimizer):
        """Test selection when only one scenario exists."""
        # Create a response with a single scenario
        zones = [
            ParkingZone(
                id=1,
                name="Zone",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=50,
                min_fee=2.9,
                max_fee=3.1  # Very narrow range to force single solution
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        response = optimizer.optimize(city)
        weights = {"revenue": 50, "occupancy": 50}

        best = optimizer.select_best_solution_by_weights(response, weights)

        # Should return the only scenario
        assert best is not None


class TestNSGA3OptimizerEdgeCases:
    """Test edge cases and error handling."""

    def test_optimizer_with_different_random_seeds(self):
        """Test that different seeds produce different results."""
        zones = [
            ParkingZone(
                id=1,
                name="Zone",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=50,
                min_fee=1.0,
                max_fee=8.0
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        # Run with different seeds
        optimizer1 = NSGA3OptimizerElasticity(OptimizationSettings(random_seed=1))
        response1 = optimizer1.optimize(city)

        optimizer2 = NSGA3OptimizerElasticity(OptimizationSettings(random_seed=2))
        response2 = optimizer2.optimize(city)

        # Results should differ (at least in some scenarios)
        # Note: With genetic algorithms, there's a small chance they could be identical
        # but with different seeds, it's highly unlikely
        current_fees1 = [s.zones[0].new_fee for s in response1]
        current_fees2 = [s.zones[0].new_fee for s in response2]

        # At least one current_fee should differ
        assert current_fees1 != current_fees2

    def test_optimizer_with_tight_current_fee_bounds(self, optimizer):
        """Test optimization with very tight current_fee bounds."""
        zones = [
            ParkingZone(
                id=1,
                name="TightBounds",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=50,
                min_fee=2.9,
                max_fee=3.1  # Only 0.2 range
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        response = optimizer.optimize(city)

        # Should complete without errors
        assert len(response) >= 1

        # All current_fees should be within tight bounds
        for scenario in response:
            assert 2.9 <= scenario.zones[0].new_fee <= 3.1

    def test_optimizer_with_fully_occupied_zone(self, optimizer):
        """Test optimization with a fully occupied parking zone."""
        zones = [
            ParkingZone(
                id=1,
                name="FullZone",
                current_fee=3.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=100,  # Fully occupied
                min_fee=1.0,
                max_fee=10.0
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        response = optimizer.optimize(city)

        # Should complete and suggest higher current_fees for full zone
        assert len(response) >= 1

    def test_optimizer_with_empty_zone(self, optimizer):
        """Test optimization with an empty parking zone."""
        zones = [
            ParkingZone(
                id=1,
                name="EmptyZone",
                current_fee=8.0,
                position=(49.01, 8.41),
                maximum_capacity=100,
                current_capacity=0,  # Empty
                min_fee=1.0,
                max_fee=10.0
            )
        ]

        city = City(
            id=1,
            name="TestCity",
            min_latitude=49.0,
            max_latitude=49.02,
            min_longitude=8.40,
            max_longitude=8.42,
            parking_zones=zones,
            point_of_interests=[]
        )

        response = optimizer.optimize(city)

        # Should complete and suggest lower current_fees for empty zone
        assert len(response) >= 1
