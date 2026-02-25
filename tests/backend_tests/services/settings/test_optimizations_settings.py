import pytest
from pydantic import ValidationError
from backend.services.settings.optimizations_settings import OptimizationSettings, AgentBasedSettings


def test_optimization_defaults():
    s = OptimizationSettings()
    assert s.optimizer_type == "elasticity"
    assert s.random_seed == 1
    assert s.population_size == 200
    assert s.generations == 50
    assert s.target_occupancy == 0.85
    assert s.min_fee == 0.0
    assert s.max_fee == 10.0
    assert s.fee_increment == 0.25


def test_optimization_custom():
    s = OptimizationSettings(
        random_seed=5, population_size=100, generations=20,
        target_occupancy=0.7, min_fee=1.0, max_fee=5.0, fee_increment=0.5,
    )
    assert s.population_size == 100
    assert s.generations == 20
    assert s.target_occupancy == 0.7
    assert s.min_fee == 1.0
    assert s.max_fee == 5.0
    assert s.fee_increment == 0.5


def test_agent_based_defaults():
    s = AgentBasedSettings()
    assert s.optimizer_type == "agent"
    assert s.drivers_per_zone_capacity == 2.0
    assert s.simulation_runs == 3
    assert s.driver_fee_weight == 1.5
    assert s.driver_distance_to_lot_weight == 0.8
    assert s.driver_walking_distance_weight == 2.0
    assert s.driver_availability_weight == 0.5


def test_agent_based_inherits_optimization():
    s = AgentBasedSettings(population_size=50, generations=10)
    assert s.population_size == 50
    assert s.generations == 10
    assert s.optimizer_type == "agent"


# --- Edge cases ---

def test_population_size_minimum_boundary():
    s = OptimizationSettings(population_size=10)
    assert s.population_size == 10


def test_population_size_below_minimum():
    with pytest.raises(ValidationError):
        OptimizationSettings(population_size=9)


def test_generations_minimum_boundary():
    s = OptimizationSettings(generations=1)
    assert s.generations == 1


def test_generations_below_minimum():
    with pytest.raises(ValidationError):
        OptimizationSettings(generations=0)


def test_target_occupancy_boundaries():
    assert OptimizationSettings(target_occupancy=0).target_occupancy == 0
    assert OptimizationSettings(target_occupancy=1.0).target_occupancy == 1.0


def test_target_occupancy_out_of_range():
    with pytest.raises(ValidationError):
        OptimizationSettings(target_occupancy=1.1)
    with pytest.raises(ValidationError):
        OptimizationSettings(target_occupancy=-0.1)


def test_min_fee_negative():
    with pytest.raises(ValidationError):
        OptimizationSettings(min_fee=-1)


def test_fee_increment_zero():
    with pytest.raises(ValidationError):
        OptimizationSettings(fee_increment=0)


def test_fee_increment_positive():
    s = OptimizationSettings(fee_increment=0.01)
    assert s.fee_increment == 0.01


def test_invalid_optimizer_type():
    with pytest.raises(ValidationError):
        OptimizationSettings(optimizer_type="invalid")


def test_agent_simulation_runs_below_minimum():
    with pytest.raises(ValidationError):
        AgentBasedSettings(simulation_runs=0)


def test_agent_drivers_per_zone_zero():
    with pytest.raises(ValidationError):
        AgentBasedSettings(drivers_per_zone_capacity=0)


def test_agent_negative_weight():
    with pytest.raises(ValidationError):
        AgentBasedSettings(driver_fee_weight=-1)
