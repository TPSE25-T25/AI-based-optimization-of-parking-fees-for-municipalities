"""
Unit tests for Driver model
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from backend.models.driver import Driver


class TestDriver:
    """Unit tests for Driver model"""
    
    @pytest.fixture
    def sample_driver(self):
        """Fixture for a sample driver"""
        return Driver(
            id=1,
            pseudonym="SimUser001",
            max_parking_price=Decimal("5.00"),
            starting_position=(52.5200, 13.4050),
            destination=(52.5170, 13.4003),
            desired_parking_time=120
        )
    
    def test_create_driver_success(self):
        """Test creating a valid driver"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("3.50"),
            starting_position=(50.0, 10.0),
            destination=(50.5, 10.5),
            desired_parking_time=60
        )
        
        assert driver.id == 1
        assert driver.pseudonym == "TestDriver"
        assert driver.max_parking_price == Decimal("3.50")
        assert driver.starting_position == (50.0, 10.0)
        assert driver.destination == (50.5, 10.5)
        assert driver.desired_parking_time == 60
    
    def test_create_driver_with_string_price(self):
        """Test creating driver with string price (auto-conversion)"""
        driver = Driver(
            id=2,
            pseudonym="TestDriver2",
            max_parking_price="4.75",
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=90
        )
        
        assert driver.max_parking_price == Decimal("4.75")
    
    def test_driver_pseudonym_validation(self):
        """Test that pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            Driver(
                id=1,
                pseudonym="",
                max_parking_price=Decimal("5.00"),
                starting_position=(0.0, 0.0),
                destination=(1.0, 1.0),
                desired_parking_time=60
            )
    
    def test_max_parking_price_validation_negative(self):
        """Test that max_parking_price cannot be negative"""
        with pytest.raises(ValidationError):
            Driver(
                id=1,
                pseudonym="TestDriver",
                max_parking_price=Decimal("-1.00"),
                starting_position=(0.0, 0.0),
                destination=(1.0, 1.0),
                desired_parking_time=60
            )
    
    def test_max_parking_price_validation_zero(self):
        """Test that max_parking_price can be zero (free parking only)"""
        driver = Driver(
            id=1,
            pseudonym="FreeSeeker",
            max_parking_price=Decimal("0.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=30
        )
        
        assert driver.max_parking_price == Decimal("0.00")
    
    def test_desired_parking_time_validation_positive(self):
        """Test that desired_parking_time must be positive"""
        with pytest.raises(ValidationError):
            Driver(
                id=1,
                pseudonym="TestDriver",
                max_parking_price=Decimal("5.00"),
                starting_position=(0.0, 0.0),
                destination=(1.0, 1.0),
                desired_parking_time=0
            )
        
        with pytest.raises(ValidationError):
            Driver(
                id=1,
                pseudonym="TestDriver",
                max_parking_price=Decimal("5.00"),
                starting_position=(0.0, 0.0),
                destination=(1.0, 1.0),
                desired_parking_time=-30
            )
    
    def test_distance_to_travel_calculation(self):
        """Test distance calculation between start and destination"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("5.00"),
            starting_position=(0.0, 0.0),
            destination=(3.0, 4.0),
            desired_parking_time=60
        )
        
        # Should be 5.0 (3-4-5 triangle)
        distance = driver.distance_to_travel()
        assert abs(distance - 5.0) < 0.001
    
    def test_distance_to_travel_same_position(self):
        """Test distance when start equals destination"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("5.00"),
            starting_position=(10.0, 20.0),
            destination=(10.0, 20.0),
            desired_parking_time=60
        )
        
        distance = driver.distance_to_travel()
        assert distance == 0.0
    
    def test_distance_to_travel_negative_coordinates(self):
        """Test distance with negative coordinates"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("5.00"),
            starting_position=(-3.0, -4.0),
            destination=(0.0, 0.0),
            desired_parking_time=60
        )
        
        # Should be 5.0
        distance = driver.distance_to_travel()
        assert abs(distance - 5.0) < 0.001
    
    def test_hourly_budget_calculation(self):
        """Test hourly budget calculation"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("6.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=120  # 2 hours
        )
        
        budget = driver.hourly_budget()
        assert budget == Decimal("12.00")
    
    def test_hourly_budget_partial_hour(self):
        """Test hourly budget for partial hours"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("4.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=30  # 0.5 hours
        )
        
        budget = driver.hourly_budget()
        assert budget == Decimal("2.00")
    
    def test_hourly_budget_odd_minutes(self):
        """Test hourly budget with odd number of minutes"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("6.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=45  # 0.75 hours
        )
        
        budget = driver.hourly_budget()
        expected = Decimal("6.00") * Decimal("45") / Decimal("60")
        assert budget == expected
    
    def test_hourly_budget_single_minute(self):
        """Test hourly budget for single minute"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("60.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=1
        )
        
        budget = driver.hourly_budget()
        expected = Decimal("60.00") / Decimal("60")
        assert budget == expected
    
    def test_hourly_budget_zero_price(self):
        """Test hourly budget with zero max price"""
        driver = Driver(
            id=1,
            pseudonym="FreeSeeker",
            max_parking_price=Decimal("0.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=120
        )
        
        budget = driver.hourly_budget()
        assert budget == Decimal("0.00")
    
    def test_hourly_budget_long_duration(self):
        """Test hourly budget for long parking duration"""
        driver = Driver(
            id=1,
            pseudonym="LongTermParker",
            max_parking_price=Decimal("2.50"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=480  # 8 hours
        )
        
        budget = driver.hourly_budget()
        assert budget == Decimal("20.00")
    
    def test_driver_with_fixture(self, sample_driver):
        """Test using the sample driver fixture"""
        assert sample_driver.id == 1
        assert sample_driver.pseudonym == "SimUser001"
        assert sample_driver.max_parking_price == Decimal("5.00")
        assert sample_driver.desired_parking_time == 120
    
    def test_driver_distance_with_fixture(self, sample_driver):
        """Test distance calculation using fixture"""
        distance = sample_driver.distance_to_travel()
        # Distance from (52.5200, 13.4050) to (52.5170, 13.4003)
        # Using Euclidean: sqrt((52.5170-52.5200)^2 + (13.4003-13.4050)^2)
        lat_diff = 52.5170 - 52.5200
        lon_diff = 13.4003 - 13.4050
        expected = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
        assert abs(distance - expected) < 0.0001
    
    def test_driver_budget_with_fixture(self, sample_driver):
        """Test budget calculation using fixture"""
        budget = sample_driver.hourly_budget()
        # 120 minutes = 2 hours, at $5/hour = $10
        assert budget == Decimal("10.00")
    
    def test_multiple_drivers_different_ids(self):
        """Test creating multiple drivers with different IDs"""
        driver1 = Driver(
            id=1,
            pseudonym="Driver1",
            max_parking_price=Decimal("3.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=60
        )
        
        driver2 = Driver(
            id=2,
            pseudonym="Driver2",
            max_parking_price=Decimal("4.00"),
            starting_position=(2.0, 2.0),
            destination=(3.0, 3.0),
            desired_parking_time=90
        )
        
        assert driver1.id != driver2.id
        assert driver1.pseudonym != driver2.pseudonym
    
    def test_driver_position_tuples(self):
        """Test that positions are properly stored as tuples"""
        driver = Driver(
            id=1,
            pseudonym="TestDriver",
            max_parking_price=Decimal("5.00"),
            starting_position=(52.123, 13.456),
            destination=(52.789, 13.012),
            desired_parking_time=60
        )
        
        assert isinstance(driver.starting_position, tuple)
        assert isinstance(driver.destination, tuple)
        assert len(driver.starting_position) == 2
        assert len(driver.destination) == 2
    
    def test_driver_price_precision(self):
        """Test decimal precision for parking price"""
        driver = Driver(
            id=1,
            pseudonym="PreciseDriver",
            max_parking_price=Decimal("3.75"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=45
        )
        
        budget = driver.hourly_budget()
        # 45 minutes = 0.75 hours, at $3.75/hour = $2.8125
        expected = Decimal("3.75") * Decimal("0.75")
        assert budget == expected
    
    def test_driver_realistic_scenario(self):
        """Test a realistic driver scenario"""
        # Driver commuting to work, willing to pay up to €3/hour, needs 8 hours
        driver = Driver(
            id=42,
            pseudonym="Commuter_Alice",
            max_parking_price=Decimal("3.00"),
            starting_position=(52.5200, 13.4050),  # Home
            destination=(52.5100, 13.3900),  # Office
            desired_parking_time=480  # 8 hours (full workday)
        )
        
        assert driver.pseudonym == "Commuter_Alice"
        
        # Check distance is reasonable
        distance = driver.distance_to_travel()
        assert distance > 0
        
        # Check budget: 8 hours at €3/hour = €24
        budget = driver.hourly_budget()
        assert budget == Decimal("24.00")
    
    def test_driver_short_term_parking(self):
        """Test driver needing very short parking duration"""
        driver = Driver(
            id=1,
            pseudonym="QuickStop",
            max_parking_price=Decimal("10.00"),
            starting_position=(0.0, 0.0),
            destination=(0.1, 0.1),
            desired_parking_time=15  # 15 minutes
        )
        
        budget = driver.hourly_budget()
        # 15 minutes = 0.25 hours, at $10/hour = $2.50
        assert budget == Decimal("2.50")
    
    def test_driver_comparison_different_budgets(self):
        """Test comparing drivers with different budgets"""
        budget_driver = Driver(
            id=1,
            pseudonym="BudgetDriver",
            max_parking_price=Decimal("2.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=60
        )
        
        premium_driver = Driver(
            id=2,
            pseudonym="PremiumDriver",
            max_parking_price=Decimal("10.00"),
            starting_position=(0.0, 0.0),
            destination=(1.0, 1.0),
            desired_parking_time=60
        )
        
        assert budget_driver.hourly_budget() < premium_driver.hourly_budget()
        assert budget_driver.max_parking_price < premium_driver.max_parking_price
    
    def test_driver_json_schema_example(self):
        """Test that the example in Config is valid"""
        example_data = {
            "id": 1,
            "pseudonym": "SimUser001",
            "max_parking_price": "5.00",
            "starting_position": [52.5200, 13.4050],
            "destination": [52.5170, 13.4003],
            "desired_parking_time": 120
        }
        
        driver = Driver(**example_data)
        
        assert driver.id == 1
        assert driver.pseudonym == "SimUser001"
        assert driver.max_parking_price == Decimal("5.00")
        assert driver.desired_parking_time == 120
