"""
Unit tests for City, Street, and PointOfInterest models
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from backend.models.city import City, Street, PointOfInterest
from backend.models.parkinglot import ParkingLot


class TestPointOfInterest:
    """Unit tests for PointOfInterest model"""
    
    def test_create_poi_success(self):
        """Test creating a valid point of interest"""
        poi = PointOfInterest(
            id=1,
            pseudonym="CityHall",
            position=(52.5200, 13.4050)
        )
        
        assert poi.id == 1
        assert poi.pseudonym == "CityHall"
        assert poi.position == (52.5200, 13.4050)
    
    def test_poi_pseudonym_validation(self):
        """Test that pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            PointOfInterest(
                id=1,
                pseudonym="",
                position=(52.5200, 13.4050)
            )
    
    def test_poi_distance_to_point(self):
        """Test distance calculation from POI to a point"""
        poi = PointOfInterest(
            id=1,
            pseudonym="CityHall",
            position=(0.0, 0.0)
        )
        
        # Distance to (3, 4) should be 5 (3-4-5 triangle)
        distance = poi.distance_to_point((3.0, 4.0))
        assert distance == 5.0
    
    def test_poi_distance_to_same_point(self):
        """Test distance to the same point is zero"""
        poi = PointOfInterest(
            id=1,
            pseudonym="Station",
            position=(10.0, 20.0)
        )
        
        distance = poi.distance_to_point((10.0, 20.0))
        assert distance == 0.0


class TestStreet:
    """Unit tests for Street model"""
    
    def test_create_street_success(self):
        """Test creating a valid street"""
        street = Street(
            id=1,
            pseudonym="MainStreet_A_B",
            from_position=(100.0, 200.0),
            to_position=(300.0, 450.0),
            speed_limit=2.0
        )
        
        assert street.id == 1
        assert street.pseudonym == "MainStreet_A_B"
        assert street.from_position == (100.0, 200.0)
        assert street.to_position == (300.0, 450.0)
        assert street.speed_limit == 2.0
    
    def test_create_street_with_parking_lots(self):
        """Test creating a street with parking lot connections"""
        street = Street(
            id=1,
            pseudonym="ConnectorStreet",
            from_position=(0.0, 0.0),
            to_position=(100.0, 100.0),
            from_parking_lot_id=1,
            to_parking_lot_id=2,
            speed_limit=5.0
        )
        
        assert street.from_parking_lot_id == 1
        assert street.to_parking_lot_id == 2
    
    def test_street_speed_limit_validation(self):
        """Test that speed limit must be positive"""
        with pytest.raises(ValidationError):
            Street(
                id=1,
                pseudonym="InvalidStreet",
                from_position=(0.0, 0.0),
                to_position=(100.0, 100.0),
                speed_limit=0.0  # Invalid: must be > 0
            )
        
        with pytest.raises(ValidationError):
            Street(
                id=1,
                pseudonym="InvalidStreet",
                from_position=(0.0, 0.0),
                to_position=(100.0, 100.0),
                speed_limit=-1.0  # Invalid: must be > 0
            )
    
    def test_street_length_calculation(self):
        """Test street length calculation"""
        street = Street(
            id=1,
            pseudonym="TestStreet",
            from_position=(0.0, 0.0),
            to_position=(3.0, 4.0),
            speed_limit=1.0
        )
        
        # Should be 5 (3-4-5 triangle)
        assert street.length() == 5.0
    
    def test_street_travel_cost_calculation(self):
        """Test travel cost calculation"""
        street = Street(
            id=1,
            pseudonym="TestStreet",
            from_position=(0.0, 0.0),
            to_position=(10.0, 0.0),  # Length = 10
            speed_limit=2.0
        )
        
        # Travel cost = length / speed = 10 / 2 = 5
        assert street.travel_cost() == 5.0
    
    def test_street_pseudonym_validation(self):
        """Test that pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            Street(
                id=1,
                pseudonym="",
                from_position=(0.0, 0.0),
                to_position=(100.0, 100.0),
                speed_limit=1.0
            )


class TestCity:
    """Unit tests for City model"""
    
    @pytest.fixture
    def sample_parking_lot(self):
        """Fixture for a sample parking lot"""
        return ParkingLot(
            id=1,
            pseudonym="CenterLot001",
            price=Decimal("2.50"),
            position=(500.0, 500.0),
            maximum_capacity=100,
            current_capacity=50
        )
    
    @pytest.fixture
    def sample_poi(self):
        """Fixture for a sample point of interest"""
        return PointOfInterest(
            id=1,
            pseudonym="CityHall",
            position=(250.0, 250.0)
        )
    
    @pytest.fixture
    def sample_street(self):
        """Fixture for a sample street"""
        return Street(
            id=1,
            pseudonym="MainStreet",
            from_position=(100.0, 100.0),
            to_position=(200.0, 200.0),
            speed_limit=2.0
        )
    
    def test_create_city_success(self):
        """Test creating a valid city"""
        city = City(
            id=1,
            pseudonym="SimCity_Downtown",
            canvas=(1000.0, 1000.0)
        )
        
        assert city.id == 1
        assert city.pseudonym == "SimCity_Downtown"
        assert city.canvas == (1000.0, 1000.0)
        assert city.parking_lots == []
        assert city.point_of_interests == []
        assert city.streets == []
    
    def test_city_canvas_validation_negative(self):
        """Test that canvas dimensions must be positive"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(-100.0, 500.0)
            )
        
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(500.0, -100.0)
            )
    
    def test_city_canvas_validation_zero(self):
        """Test that canvas dimensions cannot be zero"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(0.0, 500.0)
            )
        
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(500.0, 0.0)
            )
    
    def test_city_with_components(self, sample_parking_lot, sample_poi, sample_street):
        """Test creating a city with all components"""
        city = City(
            id=1,
            pseudonym="CompleteCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[sample_parking_lot],
            point_of_interests=[sample_poi],
            streets=[sample_street]
        )
        
        assert len(city.parking_lots) == 1
        assert len(city.point_of_interests) == 1
        assert len(city.streets) == 1
    
    def test_add_parking_lot_success(self, sample_parking_lot):
        """Test adding a parking lot to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_parking_lot(sample_parking_lot)
        
        assert len(city.parking_lots) == 1
        assert city.parking_lots[0].id == 1
    
    def test_add_parking_lot_outside_canvas(self):
        """Test that parking lot outside canvas bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(100.0, 100.0)
        )
        
        invalid_lot = ParkingLot(
            id=1,
            pseudonym="OutOfBounds",
            price=Decimal("2.50"),
            position=(150.0, 50.0),  # Outside canvas
            maximum_capacity=50,
            current_capacity=0
        )
        
        with pytest.raises(ValueError, match="outside canvas bounds"):
            city.add_parking_lot(invalid_lot)
    
    def test_add_parking_lot_duplicate_id(self, sample_parking_lot):
        """Test that duplicate parking lot ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_parking_lot(sample_parking_lot)
        
        duplicate_lot = ParkingLot(
            id=1,  # Same ID
            pseudonym="DuplicateLot",
            price=Decimal("3.00"),
            position=(600.0, 600.0),
            maximum_capacity=75,
            current_capacity=0
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_parking_lot(duplicate_lot)
    
    def test_add_point_of_interest_success(self, sample_poi):
        """Test adding a point of interest to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_point_of_interest(sample_poi)
        
        assert len(city.point_of_interests) == 1
        assert city.point_of_interests[0].id == 1
    
    def test_add_poi_outside_canvas(self):
        """Test that POI outside canvas bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(100.0, 100.0)
        )
        
        invalid_poi = PointOfInterest(
            id=1,
            pseudonym="OutOfBounds",
            position=(150.0, 50.0)
        )
        
        with pytest.raises(ValueError, match="outside canvas bounds"):
            city.add_point_of_interest(invalid_poi)
    
    def test_add_poi_duplicate_id(self, sample_poi):
        """Test that duplicate POI ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_point_of_interest(sample_poi)
        
        duplicate_poi = PointOfInterest(
            id=1,  # Same ID
            pseudonym="DuplicatePOI",
            position=(300.0, 300.0)
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_point_of_interest(duplicate_poi)
    
    def test_add_street_success(self, sample_street):
        """Test adding a street to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_street(sample_street)
        
        assert len(city.streets) == 1
        assert city.streets[0].id == 1
    
    def test_add_street_outside_canvas(self):
        """Test that street outside canvas bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(100.0, 100.0)
        )
        
        invalid_street = Street(
            id=1,
            pseudonym="OutOfBounds",
            from_position=(50.0, 50.0),
            to_position=(150.0, 150.0),  # Outside canvas
            speed_limit=2.0
        )
        
        with pytest.raises(ValueError, match="outside canvas bounds"):
            city.add_street(invalid_street)
    
    def test_add_street_duplicate_id(self, sample_street):
        """Test that duplicate street ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        city.add_street(sample_street)
        
        duplicate_street = Street(
            id=1,  # Same ID
            pseudonym="DuplicateStreet",
            from_position=(300.0, 300.0),
            to_position=(400.0, 400.0),
            speed_limit=3.0
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_street(duplicate_street)
    
    def test_get_parking_lot_by_id_found(self, sample_parking_lot):
        """Test retrieving parking lot by ID"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[sample_parking_lot]
        )
        
        result = city.get_parking_lot_by_id(1)
        
        assert result is not None
        assert result.id == 1
        assert result.pseudonym == "CenterLot001"
    
    def test_get_parking_lot_by_id_not_found(self):
        """Test retrieving non-existent parking lot returns None"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        result = city.get_parking_lot_by_id(999)
        
        assert result is None
    
    def test_total_parking_capacity(self):
        """Test calculating total parking capacity"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=50
                ),
                ParkingLot(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=150,
                    current_capacity=75
                )
            ]
        )
        
        assert city.total_parking_capacity() == 250
    
    def test_total_parking_capacity_empty(self):
        """Test total parking capacity with no parking lots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        assert city.total_parking_capacity() == 0
    
    def test_total_occupied_spots(self):
        """Test calculating total occupied spots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=60
                ),
                ParkingLot(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=150,
                    current_capacity=90
                )
            ]
        )
        
        assert city.total_occupied_spots() == 150
    
    def test_total_available_spots(self):
        """Test calculating total available spots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=60
                ),
                ParkingLot(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=150,
                    current_capacity=90
                )
            ]
        )
        
        # (100-60) + (150-90) = 40 + 60 = 100
        assert city.total_available_spots() == 100
    
    def test_city_occupancy_rate(self):
        """Test calculating city-wide occupancy rate"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=50
                ),
                ParkingLot(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=100,
                    current_capacity=30
                )
            ]
        )
        
        # (50+30) / (100+100) = 80/200 = 0.4
        assert city.city_occupancy_rate() == 0.4
    
    def test_city_occupancy_rate_zero_capacity(self):
        """Test occupancy rate with zero capacity"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        assert city.city_occupancy_rate() == 0.0
    
    def test_find_nearest_parking_lot(self):
        """Test finding nearest parking lot to a position"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="FarLot",
                    price=Decimal("2.00"),
                    position=(900.0, 900.0),
                    maximum_capacity=100,
                    current_capacity=0
                ),
                ParkingLot(
                    id=2,
                    pseudonym="NearLot",
                    price=Decimal("3.00"),
                    position=(105.0, 105.0),
                    maximum_capacity=100,
                    current_capacity=0
                )
            ]
        )
        
        nearest = city.find_nearest_parking_lot((100.0, 100.0))
        
        assert nearest is not None
        assert nearest.pseudonym == "NearLot"
    
    def test_find_nearest_parking_lot_empty_city(self):
        """Test finding nearest parking lot with no lots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0)
        )
        
        result = city.find_nearest_parking_lot((100.0, 100.0))
        
        assert result is None
    
    def test_find_available_parking_lots(self):
        """Test finding parking lots with available spots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="FullLot",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=100  # Full
                ),
                ParkingLot(
                    id=2,
                    pseudonym="AvailableLot1",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=100,
                    current_capacity=50  # Available
                ),
                ParkingLot(
                    id=3,
                    pseudonym="AvailableLot2",
                    price=Decimal("2.50"),
                    position=(300.0, 300.0),
                    maximum_capacity=100,
                    current_capacity=0  # Available
                )
            ]
        )
        
        available_lots = city.find_available_parking_lots()
        
        assert len(available_lots) == 2
        pseudonyms = [lot.pseudonym for lot in available_lots]
        assert "AvailableLot1" in pseudonyms
        assert "AvailableLot2" in pseudonyms
        assert "FullLot" not in pseudonyms
    
    def test_find_available_parking_lots_all_full(self):
        """Test finding available lots when all are full"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            parking_lots=[
                ParkingLot(
                    id=1,
                    pseudonym="FullLot1",
                    price=Decimal("2.00"),
                    position=(100.0, 100.0),
                    maximum_capacity=100,
                    current_capacity=100
                ),
                ParkingLot(
                    id=2,
                    pseudonym="FullLot2",
                    price=Decimal("3.00"),
                    position=(200.0, 200.0),
                    maximum_capacity=50,
                    current_capacity=50
                )
            ]
        )
        
        available_lots = city.find_available_parking_lots()
        
        assert len(available_lots) == 0
    
    def test_get_streets_from_parking_lot(self):
        """Test getting streets that originate from a parking lot"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            streets=[
                Street(
                    id=1,
                    pseudonym="Street1",
                    from_position=(100.0, 100.0),
                    to_position=(200.0, 200.0),
                    from_parking_lot_id=1,
                    to_parking_lot_id=2,
                    speed_limit=2.0
                ),
                Street(
                    id=2,
                    pseudonym="Street2",
                    from_position=(100.0, 100.0),
                    to_position=(300.0, 300.0),
                    from_parking_lot_id=1,
                    to_parking_lot_id=3,
                    speed_limit=2.5
                ),
                Street(
                    id=3,
                    pseudonym="Street3",
                    from_position=(200.0, 200.0),
                    to_position=(300.0, 300.0),
                    from_parking_lot_id=2,
                    to_parking_lot_id=3,
                    speed_limit=3.0
                )
            ]
        )
        
        streets_from_lot_1 = city.get_streets_from_parking_lot(1)
        
        assert len(streets_from_lot_1) == 2
        pseudonyms = [street.pseudonym for street in streets_from_lot_1]
        assert "Street1" in pseudonyms
        assert "Street2" in pseudonyms
    
    def test_get_streets_to_parking_lot(self):
        """Test getting streets that lead to a parking lot"""
        city = City(
            id=1,
            pseudonym="TestCity",
            canvas=(1000.0, 1000.0),
            streets=[
                Street(
                    id=1,
                    pseudonym="Street1",
                    from_position=(100.0, 100.0),
                    to_position=(200.0, 200.0),
                    from_parking_lot_id=1,
                    to_parking_lot_id=3,
                    speed_limit=2.0
                ),
                Street(
                    id=2,
                    pseudonym="Street2",
                    from_position=(150.0, 150.0),
                    to_position=(300.0, 300.0),
                    from_parking_lot_id=2,
                    to_parking_lot_id=3,
                    speed_limit=2.5
                ),
                Street(
                    id=3,
                    pseudonym="Street3",
                    from_position=(200.0, 200.0),
                    to_position=(400.0, 400.0),
                    from_parking_lot_id=3,
                    to_parking_lot_id=4,
                    speed_limit=3.0
                )
            ]
        )
        
        streets_to_lot_3 = city.get_streets_to_parking_lot(3)
        
        assert len(streets_to_lot_3) == 2
        pseudonyms = [street.pseudonym for street in streets_to_lot_3]
        assert "Street1" in pseudonyms
        assert "Street2" in pseudonyms
    
    def test_parking_lot_position_validation_at_creation(self):
        """Test that parking lot positions are validated during city creation"""
        with pytest.raises(ValidationError, match="outside canvas bounds"):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(100.0, 100.0),
                parking_lots=[
                    ParkingLot(
                        id=1,
                        pseudonym="OutOfBoundsLot",
                        price=Decimal("2.00"),
                        position=(150.0, 50.0),  # Outside canvas
                        maximum_capacity=50,
                        current_capacity=0
                    )
                ]
            )
    
    def test_poi_position_validation_at_creation(self):
        """Test that POI positions are validated during city creation"""
        with pytest.raises(ValidationError, match="outside canvas bounds"):
            City(
                id=1,
                pseudonym="InvalidCity",
                canvas=(100.0, 100.0),
                point_of_interests=[
                    PointOfInterest(
                        id=1,
                        pseudonym="OutOfBoundsPOI",
                        position=(150.0, 50.0)  # Outside canvas
                    )
                ]
            )
    
    def test_city_pseudonym_validation(self):
        """Test that city pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="",
                canvas=(1000.0, 1000.0)
            )
    
    def test_complex_city_scenario(self):
        """Test a complex city with multiple components"""
        city = City(
            id=1,
            pseudonym="ComplexCity",
            canvas=(1000.0, 1000.0)
        )
        
        # Add multiple parking lots
        for i in range(3):
            city.add_parking_lot(
                ParkingLot(
                    id=i+1,
                    pseudonym=f"Lot{i+1}",
                    price=Decimal("2.00") + Decimal(str(i * 0.5)),
                    position=(100.0 + i*100, 100.0 + i*100),
                    maximum_capacity=100,
                    current_capacity=i * 20
                )
            )
        
        # Add POIs
        for i in range(2):
            city.add_point_of_interest(
                PointOfInterest(
                    id=i+1,
                    pseudonym=f"POI{i+1}",
                    position=(500.0 + i*100, 500.0 + i*100)
                )
            )
        
        # Add streets
        for i in range(2):
            city.add_street(
                Street(
                    id=i+1,
                    pseudonym=f"Street{i+1}",
                    from_position=(100.0 + i*100, 100.0 + i*100),
                    to_position=(200.0 + i*100, 200.0 + i*100),
                    from_parking_lot_id=i+1,
                    to_parking_lot_id=i+2,
                    speed_limit=2.0
                )
            )
        
        # Verify city state
        assert len(city.parking_lots) == 3
        assert len(city.point_of_interests) == 2
        assert len(city.streets) == 2
        assert city.total_parking_capacity() == 300
        assert city.total_occupied_spots() == 60  # 0 + 20 + 40
        assert city.total_available_spots() == 240
        assert len(city.find_available_parking_lots()) == 3
