"""
Unit tests for parking simulation module.
"""

import pytest

from backend.services.models.city import City, PointOfInterest, ParkingZone
from backend.services.models.driver import Driver
from backend.services.simulation.simulation import (
    ParkingSimulation, 
    DriverDecision, 
    SimulationMetrics,
    SimulationBatch
)
from backend.services.datasources.generator.driver_generator import DriverGenerator


@pytest.fixture
def decision():
    """Set up driver decision maker."""
    return DriverDecision()


@pytest.fixture
def test_driver():
    """Set up test driver."""
    return Driver(
        id=1,
        name="TestDriver",
        max_parking_current_fee=5.00,
        starting_position=(100.0, 100.0),
        destination=(500.0, 500.0),
        desired_parking_time=120
    )


@pytest.fixture
def lot1():
    """Set up first parking lot."""
    return ParkingZone(
        id=1,
        name="Lot1",
        current_fee=3.00,
        position=(200.0, 200.0),
        maximum_capacity=100,
        current_capacity=50
    )


@pytest.fixture
def lot2():
    """Set up second parking lot."""
    return ParkingZone(
        id=2,
        name="Lot2",
        current_fee=4.00,
        position=(480.0, 480.0),  # Closer to destination
        maximum_capacity=100,
        current_capacity=20
    )


class TestDriverDecision:
    """Test driver decision-making logic."""
    
    def test_calculate_lot_score(self, decision, test_driver, lot1):
        """Test scoring calculation for a parking lot."""
        score = decision.calculate_lot_score(test_driver, lot1)
        assert isinstance(score, float)
        assert score > 0
    
    def test_select_parking_zone_affordable(self, decision, test_driver, lot1, lot2):
        """Test that driver selects affordable lot."""
        lots = [lot1, lot2]
        selected = decision.select_parking_zone(test_driver, lots)
        assert selected is not None
        assert selected in lots
    
    def test_select_parking_zone_unaffordable(self, decision, test_driver):
        """Test that driver rejects unaffordable lots."""
        expensive_lot = ParkingZone(
            id=3,
            name="Expensive",
            current_fee=10.00,  # Too expensive
            position=(300.0, 300.0),
            maximum_capacity=100,
            current_capacity=0
        )
        
        result = decision.select_parking_zone(test_driver, [expensive_lot])
        assert result is None
    
    def test_select_parking_zone_empty_list(self, decision, test_driver):
        """Test behavior with no available lots."""
        result = decision.select_parking_zone(test_driver, [])
        assert result is None
    
    def test_closer_lot_preferred(self, test_driver, lot1, lot2):
        """Test that closer lot to destination is preferred when current_fees similar."""
        decision = DriverDecision(
            fee_weight=0.1,
            walking_distance_weight=10.0  # Heavy weight on proximity
        )
        
        lots = [lot1, lot2]
        selected = decision.select_parking_zone(test_driver, lots)
        
        # lot2 is much closer to destination (480, 480) vs (200, 200)
        assert selected.id == 2


@pytest.fixture
def test_city():
    """Set up test city with parking lots and POI."""
    city = City(
        id=1,
        name="TestCity",
        min_latitude=49.0,
        max_latitude=49.1,
        min_longitude=8.4,
        max_longitude=8.5
    )

    # Add POI
    poi = PointOfInterest(
        id=1,
        name="Downtown",
        position=(49.05, 8.45)
    )
    city.add_point_of_interest(poi)

    # Add parking lots
    lot1 = ParkingZone(
        id=1,
        name="Lot1",
        current_fee=3.00,
        position=(49.048, 8.448),
        maximum_capacity=100,
        current_capacity=0
    )

    lot2 = ParkingZone(
        id=2,
        name="Lot2",
        current_fee=5.00,
        position=(49.052, 8.452),
        maximum_capacity=50,
        current_capacity=0
    )
    
    city.add_parking_zone(lot1)
    city.add_parking_zone(lot2)
    
    return city


@pytest.fixture
def test_drivers(test_city):
    """Set up test drivers."""
    poi = test_city.point_of_interests[0]
    return [
        Driver(
            id=i,
            name=f"Driver{i}",
            max_parking_current_fee=6.00,
            starting_position=(100.0 + i * 10, 100.0),
            destination=poi.position,
            desired_parking_time=120
        )
        for i in range(10)
    ]


@pytest.fixture
def simulation():
    """Set up parking simulation."""
    return ParkingSimulation()


class TestParkingSimulation:
    """Test parking simulation engine."""
    
    def test_run_simulation_basic(self, simulation, test_city, test_drivers):
        """Test basic simulation execution."""
        metrics = simulation.run_simulation(test_city, test_drivers)
        
        assert isinstance(metrics, SimulationMetrics)
        assert metrics.total_parked >= 0
        assert metrics.total_parked + metrics.total_rejected == len(test_drivers)
    
    def test_simulation_resets_capacity(self, simulation, test_city, test_drivers):
        """Test that simulation resets capacity when requested."""
        # Set some initial capacity
        test_city.parking_zones[0].current_capacity = 50
        
        metrics = simulation.run_simulation(test_city, test_drivers, reset_capacity=True)
        
        # After simulation with reset, capacity should reflect only new drivers
        total_capacity = sum(lot.maximum_capacity for lot in test_city.parking_zones)
        assert metrics.total_parked <= total_capacity
    
    def test_simulation_respects_capacity(self, simulation, test_city):
        """Test that simulation doesn't exceed lot capacity."""
        # Create many drivers for small capacity
        poi = test_city.point_of_interests[0]
        many_drivers = [
            Driver(
                id=i,
                name=f"Driver{i}",
                max_parking_current_fee=10.00,
                starting_position=(100.0, 100.0),
                destination=poi.position,
                desired_parking_time=60
            )
            for i in range(200)  # More than total capacity (150)
        ]
        
        metrics = simulation.run_simulation(test_city, many_drivers)
        
        # Should have rejections
        assert metrics.total_rejected > 0
        # Total parked shouldn't exceed capacity
        assert metrics.total_parked <= 150
    
    def test_revenue_calculation(self, simulation, test_city, test_drivers):
        """Test revenue calculation."""
        metrics = simulation.run_simulation(test_city, test_drivers)
        
        assert isinstance(metrics.total_revenue, float)
        assert metrics.total_revenue >= 0
        
        if metrics.total_parked > 0:
            assert metrics.total_revenue > 0
    
    def test_occupancy_metrics(self, simulation, test_city, test_drivers):
        """Test occupancy calculations."""
        metrics = simulation.run_simulation(test_city, test_drivers)
        
        assert metrics.overall_occupancy_rate >= 0.0
        assert metrics.overall_occupancy_rate <= 1.0
        assert metrics.occupancy_variance >= 0.0
    
    def test_evaluate_current_fee_configuration(self, simulation, test_city, test_drivers):
        """Test current_fee configuration evaluation."""
        current_fee_vector = [4.00, 4.00]
        
        objectives = simulation.evaluate_current_fee_configuration(
            test_city,
            test_drivers,
            current_fee_vector,
            objectives=['revenue', 'occupancy_variance']
        )
        
        assert 'revenue' in objectives
        assert 'occupancy_variance' in objectives
        assert isinstance(objectives['revenue'], float)
        assert isinstance(objectives['occupancy_variance'], float)
    
    def test_evaluate_current_fee_configuration_wrong_length(self, simulation, test_city, test_drivers):
        """Test error handling for wrong current_fee vector length."""
        current_fee_vector = [4.00]  # Only 1 current_fee for 2 lots
        
        with pytest.raises(ValueError):
            simulation.evaluate_current_fee_configuration(
                test_city,
                test_drivers,
                current_fee_vector
            )




@pytest.fixture
def batch_city():
    """Set up city for batch simulation tests."""
    city = City(
        id=1,
        name="TestCity",
        min_latitude=49.0,
        max_latitude=49.1,
        min_longitude=8.4,
        max_longitude=8.5
    )

    poi = PointOfInterest(id=1, name="Downtown", position=(49.05, 8.45))
    city.add_point_of_interest(poi)

    lot = ParkingZone(
        id=1,
        name="Lot1",
        current_fee=3.00,
        position=(49.048, 8.448),
        maximum_capacity=100,
        current_capacity=0
    )
    city.add_parking_zone(lot)

    return city


@pytest.fixture
def driver_generator():
    """Set up driver generator."""
    return DriverGenerator(seed=42)


@pytest.fixture
def batch_simulation():
    """Set up batch simulation."""
    return SimulationBatch(ParkingSimulation())


class TestSimulationBatch:
    """Test batch simulation functionality."""
    
    def test_run_multiple_simulations(self, batch_simulation, batch_city, driver_generator):
        """Test running multiple simulations."""
        driver_sets = [
            driver_generator.generate_random_drivers(count=20, city=batch_city)
            for _ in range(3)
        ]
        
        results = batch_simulation.run_multiple_simulations(batch_city, driver_sets)
        
        assert len(results) == 3
        assert all(isinstance(m, SimulationMetrics) for m in results)
    
    def test_average_metrics(self, batch_simulation, batch_city, driver_generator):
        """Test metric averaging."""
        driver_sets = [
            driver_generator.generate_random_drivers(count=20, city=batch_city)
            for _ in range(5)
        ]
        
        results = batch_simulation.run_multiple_simulations(batch_city, driver_sets)
        avg_metrics = batch_simulation.average_metrics(results)
        
        assert 'avg_revenue' in avg_metrics
        assert 'avg_utilization' in avg_metrics
        assert isinstance(avg_metrics['avg_revenue'], float)
