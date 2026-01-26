"""
Unit tests for City, Street, and PointOfInterest models
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from backend.models.city import City, Street, PointOfInterest, ParkingZone


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
            from_position=(49.01, 8.42),
            to_position=(49.03, 8.445),
            speed_limit=2.0
        )

        assert street.id == 1
        assert street.pseudonym == "MainStreet_A_B"
        assert street.from_position == (49.01, 8.42)
        assert street.to_position == (49.03, 8.445)
        assert street.speed_limit == 2.0
    
    def test_create_street_with_parking_zones(self):
        """Test creating a street with parking lot connections"""
        street = Street(
            id=1,
            pseudonym="ConnectorStreet",
            from_position=(0.0, 0.0),
            to_position=(49.01, 8.41),
            from_parking_zone_id=1,
            to_parking_zone_id=2,
            speed_limit=5.0
        )
        
        assert street.from_parking_zone_id == 1
        assert street.to_parking_zone_id == 2
    
    def test_street_speed_limit_validation(self):
        """Test that speed limit must be positive"""
        with pytest.raises(ValidationError):
            Street(
                id=1,
                pseudonym="InvalidStreet",
                from_position=(0.0, 0.0),
                to_position=(49.01, 8.41),
                speed_limit=0.0  # Invalid: must be > 0
            )
        
        with pytest.raises(ValidationError):
            Street(
                id=1,
                pseudonym="InvalidStreet",
                from_position=(0.0, 0.0),
                to_position=(49.01, 8.41),
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
                to_position=(49.01, 8.41),
                speed_limit=1.0
            )


class TestCity:
    """Unit tests for City model"""
    
    @pytest.fixture
    def sample_parking_zone(self):
        """Fixture for a sample parking lot"""
        return ParkingZone(
            id=1,
            pseudonym="CenterLot001",
            price=Decimal("2.50"),
            position=(49.05, 8.45),
            maximum_capacity=100,
            current_capacity=50
        )

    @pytest.fixture
    def sample_poi(self):
        """Fixture for a sample point of interest"""
        return PointOfInterest(
            id=1,
            pseudonym="CityHall",
            position=(49.025, 8.425)
        )

    @pytest.fixture
    def sample_street(self):
        """Fixture for a sample street"""
        return Street(
            id=1,
            pseudonym="MainStreet",
            from_position=(49.01, 8.41),
            to_position=(49.02, 8.42),
            speed_limit=2.0
        )
    
    def test_create_city_success(self):
        """Test creating a valid city"""
        city = City(
            id=1,
            pseudonym="SimCity_Downtown",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        assert city.id == 1
        assert city.pseudonym == "SimCity_Downtown"
        assert city.min_latitude == 49.0
        assert city.max_latitude == 49.1
        assert city.min_longitude == 8.4
        assert city.max_longitude == 8.5
        assert city.parking_zones == []
        assert city.point_of_interests == []
        assert city.streets == []
    
    def test_city_bounds_validation_inverted(self):
        """Test that min bounds must be less than max bounds"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.1,
                max_latitude=49.0,  # Invalid: max < min
                min_longitude=8.4,
                max_longitude=8.5
            )

        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.0,
                max_latitude=49.1,
                min_longitude=8.5,
                max_longitude=8.4  # Invalid: max < min
            )

    def test_city_bounds_validation_equal(self):
        """Test that min and max bounds cannot be equal"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.0,
                max_latitude=49.0,  # Invalid: equal
                min_longitude=8.4,
                max_longitude=8.5
            )

        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.0,
                max_latitude=49.1,
                min_longitude=8.4,
                max_longitude=8.4  # Invalid: equal
            )
    
    def test_city_with_components(self, sample_parking_zone, sample_poi, sample_street):
        """Test creating a city with all components"""
        city = City(
            id=1,
            pseudonym="CompleteCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[sample_parking_zone],
            point_of_interests=[sample_poi],
            streets=[sample_street]
        )
        
        assert len(city.parking_zones) == 1
        assert len(city.point_of_interests) == 1
        assert len(city.streets) == 1
    
    def test_add_parking_zone_success(self, sample_parking_zone):
        """Test adding a parking lot to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_parking_zone(sample_parking_zone)
        
        assert len(city.parking_zones) == 1
        assert city.parking_zones[0].id == 1
    
    def test_add_parking_zone_outside_bounds(self):
        """Test that parking lot outside geographic bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.4,
            max_longitude=8.41
        )

        invalid_lot = ParkingZone(
            id=1,
            pseudonym="OutOfBounds",
            price=Decimal("2.50"),
            position=(50.0, 10.0),  # Outside geographic bounds
            maximum_capacity=50,
            current_capacity=0
        )
        
        with pytest.raises(ValueError, match="outside city bounds"):
            city.add_parking_zone(invalid_lot)
    
    def test_add_parking_zone_duplicate_id(self, sample_parking_zone):
        """Test that duplicate parking lot ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_parking_zone(sample_parking_zone)
        
        duplicate_lot = ParkingZone(
            id=1,  # Same ID
            pseudonym="DuplicateLot",
            price=Decimal("3.00"),
            position=(49.06, 8.46),
            maximum_capacity=75,
            current_capacity=0
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_parking_zone(duplicate_lot)
    
    def test_add_point_of_interest_success(self, sample_poi):
        """Test adding a point of interest to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_point_of_interest(sample_poi)
        
        assert len(city.point_of_interests) == 1
        assert city.point_of_interests[0].id == 1
    
    def test_add_poi_outside_bounds(self):
        """Test that POI outside geographic bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.4,
            max_longitude=8.41
        )

        invalid_poi = PointOfInterest(
            id=1,
            pseudonym="OutOfBounds",
            position=(50.0, 10.0)  # Outside geographic bounds
        )
        
        with pytest.raises(ValueError, match="outside city bounds"):
            city.add_point_of_interest(invalid_poi)
    
    def test_add_poi_duplicate_id(self, sample_poi):
        """Test that duplicate POI ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_point_of_interest(sample_poi)
        
        duplicate_poi = PointOfInterest(
            id=1,  # Same ID
            pseudonym="DuplicatePOI",
            position=(49.03, 8.43)
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_point_of_interest(duplicate_poi)
    
    def test_add_street_success(self, sample_street):
        """Test adding a street to the city"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_street(sample_street)
        
        assert len(city.streets) == 1
        assert city.streets[0].id == 1
    
    def test_add_street_outside_bounds(self):
        """Test that street outside geographic bounds raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.4,
            max_longitude=8.41
        )

        invalid_street = Street(
            id=1,
            pseudonym="OutOfBounds",
            from_position=(50.0, 10.0),  # Outside geographic bounds
            to_position=(51.0, 11.0),  # Outside geographic bounds
            speed_limit=2.0
        )
        
        with pytest.raises(ValueError, match="outside city bounds"):
            city.add_street(invalid_street)
    
    def test_add_street_duplicate_id(self, sample_street):
        """Test that duplicate street ID raises error"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        city.add_street(sample_street)
        
        duplicate_street = Street(
            id=1,  # Same ID
            pseudonym="DuplicateStreet",
            from_position=(49.03, 8.43),
            to_position=(49.04, 8.44),
            speed_limit=3.0
        )
        
        with pytest.raises(ValueError, match="already exists"):
            city.add_street(duplicate_street)
    
    def test_get_parking_zone_by_id_found(self, sample_parking_zone):
        """Test retrieving parking lot by ID"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[sample_parking_zone]
        )
        
        result = city.get_parking_zone_by_id(1)
        
        assert result is not None
        assert result.id == 1
        assert result.pseudonym == "CenterLot001"
    
    def test_get_parking_zone_by_id_not_found(self):
        """Test retrieving non-existent parking lot returns None"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        result = city.get_parking_zone_by_id(999)
        
        assert result is None
    
    def test_total_parking_capacity(self):
        """Test calculating total parking capacity"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=50
                ),
                ParkingZone(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
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
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        assert city.total_parking_capacity() == 0
    
    def test_total_occupied_spots(self):
        """Test calculating total occupied spots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=60
                ),
                ParkingZone(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
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
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=60
                ),
                ParkingZone(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
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
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="Lot1",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=50
                ),
                ParkingZone(
                    id=2,
                    pseudonym="Lot2",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
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
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        assert city.city_occupancy_rate() == 0.0
    
    def test_find_nearest_parking_zone(self):
        """Test finding nearest parking lot to a position"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="FarLot",
                    price=Decimal("2.00"),
                    position=(49.09, 8.49),
                    maximum_capacity=100,
                    current_capacity=0
                ),
                ParkingZone(
                    id=2,
                    pseudonym="NearLot",
                    price=Decimal("3.00"),
                    position=(49.015, 8.415),
                    maximum_capacity=100,
                    current_capacity=0
                )
            ]
        )
        
        nearest = city.find_nearest_parking_zone((49.01, 8.41))
        
        assert nearest is not None
        assert nearest.pseudonym == "NearLot"
    
    def test_find_nearest_parking_zone_empty_city(self):
        """Test finding nearest parking lot with no lots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        result = city.find_nearest_parking_zone((49.01, 8.41))
        
        assert result is None
    
    def test_find_available_parking_zones(self):
        """Test finding parking lots with available spots"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="FullLot",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=100  # Full
                ),
                ParkingZone(
                    id=2,
                    pseudonym="AvailableLot1",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
                    maximum_capacity=100,
                    current_capacity=50  # Available
                ),
                ParkingZone(
                    id=3,
                    pseudonym="AvailableLot2",
                    price=Decimal("2.50"),
                    position=(49.03, 8.43),
                    maximum_capacity=100,
                    current_capacity=0  # Available
                )
            ]
        )
        
        available_lots = city.find_available_parking_zones()
        
        assert len(available_lots) == 2
        pseudonyms = [lot.pseudonym for lot in available_lots]
        assert "AvailableLot1" in pseudonyms
        assert "AvailableLot2" in pseudonyms
        assert "FullLot" not in pseudonyms
    
    def test_find_available_parking_zones_all_full(self):
        """Test finding available lots when all are full"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            parking_zones=[
                ParkingZone(
                    id=1,
                    pseudonym="FullLot1",
                    price=Decimal("2.00"),
                    position=(49.01, 8.41),
                    maximum_capacity=100,
                    current_capacity=100
                ),
                ParkingZone(
                    id=2,
                    pseudonym="FullLot2",
                    price=Decimal("3.00"),
                    position=(49.02, 8.42),
                    maximum_capacity=50,
                    current_capacity=50
                )
            ]
        )
        
        available_lots = city.find_available_parking_zones()
        
        assert len(available_lots) == 0
    
    def test_get_streets_from_parking_zone(self):
        """Test getting streets that originate from a parking lot"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            streets=[
                Street(
                    id=1,
                    pseudonym="Street1",
                    from_position=(49.01, 8.41),
                    to_position=(49.02, 8.42),
                    from_parking_zone_id=1,
                    to_parking_zone_id=2,
                    speed_limit=2.0
                ),
                Street(
                    id=2,
                    pseudonym="Street2",
                    from_position=(49.01, 8.41),
                    to_position=(49.03, 8.43),
                    from_parking_zone_id=1,
                    to_parking_zone_id=3,
                    speed_limit=2.5
                ),
                Street(
                    id=3,
                    pseudonym="Street3",
                    from_position=(49.02, 8.42),
                    to_position=(49.03, 8.43),
                    from_parking_zone_id=2,
                    to_parking_zone_id=3,
                    speed_limit=3.0
                )
            ]
        )
        
        streets_from_lot_1 = city.get_streets_from_parking_zone(1)
        
        assert len(streets_from_lot_1) == 2
        pseudonyms = [street.pseudonym for street in streets_from_lot_1]
        assert "Street1" in pseudonyms
        assert "Street2" in pseudonyms
    
    def test_get_streets_to_parking_zone(self):
        """Test getting streets that lead to a parking lot"""
        city = City(
            id=1,
            pseudonym="TestCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5,
            streets=[
                Street(
                    id=1,
                    pseudonym="Street1",
                    from_position=(49.01, 8.41),
                    to_position=(49.02, 8.42),
                    from_parking_zone_id=1,
                    to_parking_zone_id=3,
                    speed_limit=2.0
                ),
                Street(
                    id=2,
                    pseudonym="Street2",
                    from_position=(49.015, 8.415),
                    to_position=(49.03, 8.43),
                    from_parking_zone_id=2,
                    to_parking_zone_id=3,
                    speed_limit=2.5
                ),
                Street(
                    id=3,
                    pseudonym="Street3",
                    from_position=(49.02, 8.42),
                    to_position=(49.04, 8.44),
                    from_parking_zone_id=3,
                    to_parking_zone_id=4,
                    speed_limit=3.0
                )
            ]
        )
        
        streets_to_lot_3 = city.get_streets_to_parking_zone(3)
        
        assert len(streets_to_lot_3) == 2
        pseudonyms = [street.pseudonym for street in streets_to_lot_3]
        assert "Street1" in pseudonyms
        assert "Street2" in pseudonyms
    
    def test_parking_zone_position_validation_at_creation(self):
        """Test that parking lot positions are validated during city creation"""
        with pytest.raises(ValidationError, match="outside city bounds"):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.4,
            max_longitude=8.41,
                parking_zones=[
                    ParkingZone(
                        id=1,
                        pseudonym="OutOfBoundsLot",
                        price=Decimal("2.00"),
                        position=(50.0, 10.0),  # Outside geographic bounds
                        maximum_capacity=50,
                        current_capacity=0
                    )
                ]
            )
    
    def test_poi_position_validation_at_creation(self):
        """Test that POI positions are validated during city creation"""
        with pytest.raises(ValidationError, match="outside city bounds"):
            City(
                id=1,
                pseudonym="InvalidCity",
                min_latitude=49.0,
            max_latitude=49.01,
            min_longitude=8.4,
            max_longitude=8.41,
                point_of_interests=[
                    PointOfInterest(
                        id=1,
                        pseudonym="OutOfBoundsPOI",
                        position=(50.0, 10.0)  # Outside geographic bounds
                    )
                ]
            )
    
    def test_city_pseudonym_validation(self):
        """Test that city pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            City(
                id=1,
                pseudonym="",
                min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
            )
    
    def test_complex_city_scenario(self):
        """Test a complex city with multiple components"""
        city = City(
            id=1,
            pseudonym="ComplexCity",
            min_latitude=49.0,
            max_latitude=49.1,
            min_longitude=8.4,
            max_longitude=8.5
        )
        
        # Add multiple parking lots
        for i in range(3):
            city.add_parking_zone(
                ParkingZone(
                    id=i+1,
                    pseudonym=f"Lot{i+1}",
                    price=Decimal("2.00") + Decimal(str(i * 0.5)),
                    position=(49.01 + i*0.01, 8.41 + i*0.01),
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
                    position=(49.05 + i*0.01, 8.45 + i*0.01)
                )
            )

        # Add streets
        for i in range(2):
            city.add_street(
                Street(
                    id=i+1,
                    pseudonym=f"Street{i+1}",
                    from_position=(49.01 + i*0.01, 8.41 + i*0.01),
                    to_position=(49.02 + i*0.01, 8.42 + i*0.01),
                    from_parking_zone_id=i+1,
                    to_parking_zone_id=i+2,
                    speed_limit=2.0
                )
            )
        
        # Verify city state
        assert len(city.parking_zones) == 3
        assert len(city.point_of_interests) == 2
        assert len(city.streets) == 2
        assert city.total_parking_capacity() == 300
        assert city.total_occupied_spots() == 60  # 0 + 20 + 40
        assert city.total_available_spots() == 240
        assert len(city.find_available_parking_zones()) == 3


class TestParkingZone:
    """Unit tests for ParkingZone model"""
    
    @pytest.fixture
    def sample_parking_zone(self):
        """Fixture for a sample parking lot"""
        return ParkingZone(
            id=1,
            pseudonym="CenterLot001",
            price=Decimal("2.50"),
            position=(52.5170, 13.4003),
            maximum_capacity=100,
            current_capacity=50
        )
    
    def test_create_parking_zone_success(self):
        """Test creating a valid parking lot"""
        lot = ParkingZone(
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
    
    def test_create_parking_zone_with_string_price(self):
        """Test creating parking lot with string price (auto-conversion)"""
        lot = ParkingZone(
            id=2,
            pseudonym="TestLot2",
            price="4.75",
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=25
        )
        
        assert lot.price == Decimal("4.75")
    
    def test_parking_zone_pseudonym_validation(self):
        """Test that pseudonym cannot be empty"""
        with pytest.raises(ValidationError):
            ParkingZone(
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
            ParkingZone(
                id=1,
                pseudonym="TestLot",
                price=Decimal("-1.00"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=0
            )
    
    def test_price_validation_zero(self):
        """Test that price can be zero (free parking)"""
        lot = ParkingZone(
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
            ParkingZone(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=0,
                current_capacity=0
            )
        
        with pytest.raises(ValidationError):
            ParkingZone(
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
            ParkingZone(
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
            ParkingZone(
                id=1,
                pseudonym="TestLot",
                price=Decimal("2.50"),
                position=(0.0, 0.0),
                maximum_capacity=100,
                current_capacity=150
            )
    
    def test_current_capacity_equals_maximum(self):
        """Test that current_capacity can equal maximum_capacity (full lot)"""
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
        lot = ParkingZone(
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
    
    def test_parking_zone_with_fixture(self, sample_parking_zone):
        """Test using the sample parking lot fixture"""
        assert sample_parking_zone.id == 1
        assert sample_parking_zone.pseudonym == "CenterLot001"
        assert sample_parking_zone.price == Decimal("2.50")
        assert sample_parking_zone.maximum_capacity == 100
        assert sample_parking_zone.current_capacity == 50
    
    def test_available_spots_with_fixture(self, sample_parking_zone):
        """Test available spots using fixture"""
        assert sample_parking_zone.available_spots() == 50
    
    def test_occupancy_rate_with_fixture(self, sample_parking_zone):
        """Test occupancy rate using fixture"""
        assert sample_parking_zone.occupancy_rate() == 0.5
    
    def test_is_full_with_fixture(self, sample_parking_zone):
        """Test is_full using fixture"""
        assert sample_parking_zone.is_full() is False
    
    def test_can_accommodate_with_fixture(self, sample_parking_zone):
        """Test can_accommodate using fixture"""
        assert sample_parking_zone.can_accommodate(10) is True
        assert sample_parking_zone.can_accommodate(50) is True
        assert sample_parking_zone.can_accommodate(51) is False
    
    def test_parking_zone_position_tuple(self):
        """Test that position is properly stored as tuple"""
        lot = ParkingZone(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(52.123, 13.456),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert isinstance(lot.position, tuple)
        assert len(lot.position) == 2
    
    def test_parking_zone_price_precision(self):
        """Test decimal precision for parking price"""
        lot = ParkingZone(
            id=1,
            pseudonym="PreciseLot",
            price=Decimal("3.75"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert lot.price == Decimal("3.75")
    
    def test_multiple_parking_zones_different_ids(self):
        """Test creating multiple parking lots with different IDs"""
        lot1 = ParkingZone(
            id=1,
            pseudonym="Lot1",
            price=Decimal("2.00"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        lot2 = ParkingZone(
            id=2,
            pseudonym="Lot2",
            price=Decimal("3.00"),
            position=(10.0, 10.0),
            maximum_capacity=150,
            current_capacity=75
        )
        
        assert lot1.id != lot2.id
        assert lot1.pseudonym != lot2.pseudonym
    
    def test_parking_zone_realistic_scenario_cheap(self):
        """Test a realistic budget parking lot scenario"""
        lot = ParkingZone(
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
    
    def test_parking_zone_realistic_scenario_premium(self):
        """Test a realistic premium parking lot scenario"""
        lot = ParkingZone(
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
    
    def test_parking_zone_comparison_different_prices(self):
        """Test comparing parking lots with different prices"""
        cheap_lot = ParkingZone(
            id=1,
            pseudonym="CheapLot",
            price=Decimal("1.00"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        expensive_lot = ParkingZone(
            id=2,
            pseudonym="ExpensiveLot",
            price=Decimal("10.00"),
            position=(1.0, 1.0),
            maximum_capacity=100,
            current_capacity=50
        )
        
        assert cheap_lot.price < expensive_lot.price
        assert cheap_lot.available_spots() == expensive_lot.available_spots()
    
    def test_parking_zone_edge_case_single_spot(self):
        """Test parking lot with single spot capacity"""
        lot = ParkingZone(
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
    
    def test_parking_zone_large_capacity(self):
        """Test parking lot with very large capacity"""
        lot = ParkingZone(
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
    
    def test_parking_zone_json_schema_example(self):
        """Test that the example in model_config is valid"""
        example_data = {
            "id": 1,
            "pseudonym": "CenterLot001",
            "price": "2.50",
            "position": [52.5170, 13.4003],
            "maximum_capacity": 150,
            "current_capacity": 10
        }
        
        lot = ParkingZone(**example_data)
        
        assert lot.id == 1
        assert lot.pseudonym == "CenterLot001"
        assert lot.price == Decimal("2.50")
        assert lot.maximum_capacity == 150
        assert lot.current_capacity == 10
    
    def test_parking_zone_distance_realistic(self, sample_parking_zone):
        """Test distance calculation with realistic coordinates"""
        # Distance from sample lot to a destination
        destination = (52.5200, 13.4050)
        distance = sample_parking_zone.distance_to_point(destination)
        
        # Verify distance is calculated (positive value)
        assert distance > 0
    
    def test_can_accommodate_zero_spots(self):
        """Test can_accommodate with zero spots requested"""
        lot = ParkingZone(
            id=1,
            pseudonym="TestLot",
            price=Decimal("2.50"),
            position=(0.0, 0.0),
            maximum_capacity=100,
            current_capacity=100
        )
        
        # Even a full lot can accommodate zero spots
        assert lot.can_accommodate(0) is True
