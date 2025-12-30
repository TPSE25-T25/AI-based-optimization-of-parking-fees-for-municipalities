"""
Unit tests for ParkingLot model
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from backend.models.parkinglot import ParkingLot


class TestParkingLot:
    """Unit tests for ParkingLot model"""
    
    @pytest.fixture
    def sample_parking_lot(self):
        """Fixture for a sample parking lot"""
        return ParkingLot(
            id=1,
            pseudonym="CenterLot001",
            price=Decimal("2.50"),
            position=(52.5170, 13.4003),
            maximum_capacity=100,
            current_capacity=50
        )
    
    def test_create_parking_lot_success(self):
        """Test creating a valid parking lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("3.00"),
            position=(50.0, 10.0),
            maximum_capacity=150,
            current_capacity=75
        )
        
        assert lot.id == 1
        assert lot.pseudonym == "TestLot"
        assert lot.price == Decimal("3.00")
        assert lot.position == (50.0, 10.0)
        assert lot.maximum_capacity == 150
        assert lot.current_capacity == 75
    
    def test_create_parking_lot_with_string_price(self):
        """Test creating parking lot with string price (auto-conversion)"""
        lot = ParkingLot(
            id=2,
            pseudonym="TestLot2",
            price="4.75",
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=25
        )
        
        assert lot.price == Decimal("4.75")
    
    def test_parking_lot_pseudonym_validation(self):
        """Test that pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            ParkingLot(
                id=1,
                pseudonym="",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=0
            )
    
    def test_price_validation_negative(self):
        """Test that price cannot be negative"""
        with pytest.raises(ValidationError):
            ParkingLot(
                id=1,
                pseudonym="TestLot",
                price=Decimal("-1.00"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=0
            )
    
    def test_price_validation_zero(self):
        """Test that price can be zero (free parking)"""
        lot = ParkingLot(
            id=1,
            pseudonym="FreeLot",
            price=Decimal("0.00"),
            position=(0.0, 0.0),
            maximum_capacity=50,
            current_capacity=10
        )
        
        assert lot.price == Decimal("0.00")
    
    def test_maximum_capacity_validation_positive(self):
        """Test that maximum_capacity must be positive"""
        with pytest.raises(ValidationError):
            ParkingLot(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=0,
                current_capacity=0
            )
        
        with pytest.raises(ValidationError):
            ParkingLot(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=-10,
                current_capacity=0
            )
    
    def test_current_capacity_validation_negative(self):
        """Test that current_capacity cannot be negative"""
        with pytest.raises(ValidationError):
            ParkingLot(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=-5
            )
    
    def test_current_capacity_validation_exceeds_maximum(self):
        """Test that current_capacity cannot exceed maximum_capacity"""
        with pytest.raises(ValueError, match="cannot exceed maximum capacity"):
            ParkingLot(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=150
            )
    
    def test_current_capacity_equals_maximum(self):
        """Test that current_capacity can equal maximum_capacity (full lot)"""
        lot = ParkingLot(
            id=1,
            pseudonym="FullLot",
            price=Decimal("3.00"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        assert lot.current_capacity == lot.maximum_capacity
        assert lot.is_full()
    
    def test_available_spots_calculation(self):
        """Test available spots calculation"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=60
        )
        
        assert lot.available_spots() == 40
    
    def test_available_spots_empty_lot(self):
        """Test available spots for empty lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="EmptyLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=0
        )
        
        assert lot.available_spots() == 100
    
    def test_available_spots_full_lot(self):
        """Test available spots for full lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="FullLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        assert lot.available_spots() == 0
    
    def test_occupancy_rate_calculation(self):
        """Test occupancy rate calculation"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert lot.occupancy_rate() == 0.5
    
    def test_occupancy_rate_empty(self):
        """Test occupancy rate for empty lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="EmptyLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=0
        )
        
        assert lot.occupancy_rate() == 0.0
    
    def test_occupancy_rate_full(self):
        """Test occupancy rate for full lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="FullLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        assert lot.occupancy_rate() == 1.0
    
    def test_occupancy_rate_partial(self):
        """Test occupancy rate for partially filled lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="PartialLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=200,
            current_capacity=75
        )
        
        assert lot.occupancy_rate() == 0.375
    
    def test_is_full_true(self):
        """Test is_full returns True when lot is full"""
        lot = ParkingLot(
            id=1,
            pseudonym="FullLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=50,
            current_capacity=50
        )
        
        assert lot.is_full() is True
    
    def test_is_full_false(self):
        """Test is_full returns False when lot has space"""
        lot = ParkingLot(
            id=1,
            pseudonym="PartialLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=50,
            current_capacity=30
        )
        
        assert lot.is_full() is False
    
    def test_is_full_empty(self):
        """Test is_full returns False for empty lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="EmptyLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=50,
            current_capacity=0
        )
        
        assert lot.is_full() is False
    
    def test_can_accommodate_single_spot(self):
        """Test can_accommodate for single spot"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=99
        )
        
        assert lot.can_accommodate(1) is True
        assert lot.can_accommodate(2) is False
    
    def test_can_accommodate_multiple_spots(self):
        """Test can_accommodate for multiple spots"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=90
        )
        
        assert lot.can_accommodate(5) is True
        assert lot.can_accommodate(10) is True
        assert lot.can_accommodate(11) is False
    
    def test_can_accommodate_default_parameter(self):
        """Test can_accommodate with default parameter (1 spot)"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=99
        )
        
        assert lot.can_accommodate() is True
    
    def test_can_accommodate_full_lot(self):
        """Test can_accommodate for full lot"""
        lot = ParkingLot(
            id=1,
            pseudonym="FullLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        assert lot.can_accommodate(1) is False
        assert lot.can_accommodate() is False
    
    def test_distance_to_point_calculation(self):
        """Test distance calculation to a point"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        # Distance to (3, 4) should be 5 (3-4-5 triangle)
        distance = lot.distance_to_point((3.0, 4.0))
        assert abs(distance - 5.0) < 0.001
    
    def test_distance_to_same_point(self):
        """Test distance to the same position is zero"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(10.0, 20.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        distance = lot.distance_to_point((10.0, 20.0))
        assert distance == 0.0
    
    def test_distance_to_point_negative_coordinates(self):
        """Test distance with negative coordinates"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(-3.0, -4.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        # Distance to (0, 0) should be 5
        distance = lot.distance_to_point((0.0, 0.0))
        assert abs(distance - 5.0) < 0.001
    
    def test_parking_lot_with_fixture(self, sample_parking_lot):
        """Test using the sample parking lot fixture"""
        assert sample_parking_lot.id == 1
        assert sample_parking_lot.pseudonym == "CenterLot001"
        assert sample_parking_lot.price == Decimal("2.50")
        assert sample_parking_lot.maximum_capacity == 100
        assert sample_parking_lot.current_capacity == 50
    
    def test_available_spots_with_fixture(self, sample_parking_lot):
        """Test available spots using fixture"""
        assert sample_parking_lot.available_spots() == 50
    
    def test_occupancy_rate_with_fixture(self, sample_parking_lot):
        """Test occupancy rate using fixture"""
        assert sample_parking_lot.occupancy_rate() == 0.5
    
    def test_is_full_with_fixture(self, sample_parking_lot):
        """Test is_full using fixture"""
        assert sample_parking_lot.is_full() is False
    
    def test_can_accommodate_with_fixture(self, sample_parking_lot):
        """Test can_accommodate using fixture"""
        assert sample_parking_lot.can_accommodate(10) is True
        assert sample_parking_lot.can_accommodate(50) is True
        assert sample_parking_lot.can_accommodate(51) is False
    
    def test_parking_lot_position_tuple(self):
        """Test that position is properly stored as tuple"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(52.123, 13.456),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert isinstance(lot.position, tuple)
        assert len(lot.position) == 2
    
    def test_parking_lot_price_precision(self):
        """Test decimal precision for parking price"""
        lot = ParkingLot(
            id=1,
            pseudonym="PreciseLot",
            price=Decimal("3.75"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert lot.price == Decimal("3.75")
    
    def test_multiple_parking_lots_different_ids(self):
        """Test creating multiple parking lots with different IDs"""
        lot1 = ParkingLot(
            id=1,
            pseudonym="Lot1",
            price=Decimal("2.00"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        lot2 = ParkingLot(
            id=2,
            pseudonym="Lot2",
            price=Decimal("3.00"),
            position=(10.0, 10.0),
            maximum_capacity=150,
            current_capacity=75
        )
        
        assert lot1.id != lot2.id
        assert lot1.pseudonym != lot2.pseudonym
    
    def test_parking_lot_realistic_scenario_cheap(self):
        """Test a realistic budget parking lot scenario"""
        lot = ParkingLot(
            id=1,
            pseudonym="BudgetParking_Downtown",
            price=Decimal("1.50"),
            position=(52.5200, 13.4050),
            maximum_capacity=200,
            current_capacity=150
        )
        
        assert lot.pseudonym == "BudgetParking_Downtown"
        assert lot.available_spots() == 50
        assert lot.occupancy_rate() == 0.75
        assert lot.can_accommodate(25) is True
        assert not lot.is_full()
    
    def test_parking_lot_realistic_scenario_premium(self):
        """Test a realistic premium parking lot scenario"""
        lot = ParkingLot(
            id=2,
            pseudonym="PremiumParking_Center",
            price=Decimal("8.00"),
            position=(52.5100, 13.3900),
            maximum_capacity=50,
            current_capacity=48
        )
        
        assert lot.price == Decimal("8.00")
        assert lot.available_spots() == 2
        assert lot.occupancy_rate() == 0.96
        assert lot.can_accommodate(2) is True
        assert lot.can_accommodate(3) is False
    
    def test_parking_lot_comparison_different_prices(self):
        """Test comparing parking lots with different prices"""
        cheap_lot = ParkingLot(
            id=1,
            pseudonym="CheapLot",
            price=Decimal("1.00"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        expensive_lot = ParkingLot(
            id=2,
            pseudonym="ExpensiveLot",
            price=Decimal("10.00"),
            position=(1.0, 1.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert cheap_lot.price < expensive_lot.price
        assert cheap_lot.available_spots() == expensive_lot.available_spots()
    
    def test_parking_lot_edge_case_single_spot(self):
        """Test parking lot with single spot capacity"""
        lot = ParkingLot(
            id=1,
            pseudonym="SingleSpotLot",
            price=Decimal("5.00"),
            position=(0.0, 0.0),
            maximum_capacity=1,
            current_capacity=0
        )
        
        assert lot.maximum_capacity == 1
        assert lot.available_spots() == 1
        assert lot.can_accommodate(1) is True
        assert lot.can_accommodate(2) is False
    
    def test_parking_lot_large_capacity(self):
        """Test parking lot with very large capacity"""
        lot = ParkingLot(
            id=1,
            pseudonym="MegaLot",
            price=Decimal("2.00"),
            position=(0.0, 0.0),
            maximum_capacity=1000,
            current_capacity=250
        )
        
        assert lot.maximum_capacity == 1000
        assert lot.available_spots() == 750
        assert lot.occupancy_rate() == 0.25
        assert lot.can_accommodate(500) is True
    
    def test_parking_lot_json_schema_example(self):
        """Test that the example in model_config is valid"""
        example_data = {
            "id": 1,
            "pseudonym": "CenterLot001",
            "price": "2.50",
            "position": [52.5170, 13.4003],
            "maximum_capacity": 150,
            "current_capacity": 10
        }
        
        lot = ParkingLot(**example_data)
        
        assert lot.id == 1
        assert lot.pseudonym == "CenterLot001"
        assert lot.price == Decimal("2.50")
        assert lot.maximum_capacity == 150
        assert lot.current_capacity == 10
    
    def test_parking_lot_distance_realistic(self, sample_parking_lot):
        """Test distance calculation with realistic coordinates"""
        # Distance from sample lot to a destination
        destination = (52.5200, 13.4050)
        distance = sample_parking_lot.distance_to_point(destination)
        
        # Verify distance is calculated (positive value)
        assert distance > 0
    
    def test_can_accommodate_zero_spots(self):
        """Test can_accommodate with zero spots requested"""
        lot = ParkingLot(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        # Even a full lot can accommodate zero spots
        assert lot.can_accommodate(0) is True
