"""
Unit tests for city and parking lot generator modules.
"""

import pytest
from decimal import Decimal

from backend.models.city import City, PointOfInterest, ParkingLot
from backend.services.data.city_generator import ParkingLotGenerator, CityGenerator


@pytest.fixture
def parking_lot_generator():
    """Set up parking lot generator."""
    return ParkingLotGenerator(seed=42)


@pytest.fixture
def canvas():
    """Set up test canvas."""
    return (1000.0, 1000.0)


class TestParkingLotGenerator:
    """Test parking lot generation utilities."""
    
    def test_generate_random_parking_lots_count(self, parking_lot_generator, canvas):
        """Test that correct number of parking lots are generated."""
        lots = parking_lot_generator.generate_random_parking_lots(count=15, canvas=canvas)
        
        assert len(lots) == 15
    
    def test_generate_random_parking_lots_types(self, parking_lot_generator, canvas):
        """Test that all generated objects are ParkingLot instances."""
        lots = parking_lot_generator.generate_random_parking_lots(count=10, canvas=canvas)
        
        assert all(isinstance(lot, ParkingLot) for lot in lots)
    
    def test_generate_random_parking_lots_unique_ids(self, parking_lot_generator, canvas):
        """Test that all parking lots have unique IDs."""
        lots = parking_lot_generator.generate_random_parking_lots(count=20, canvas=canvas)
        
        ids = [lot.id for lot in lots]
        assert len(ids) == len(set(ids))
    
    def test_generate_random_parking_lots_within_canvas(self, parking_lot_generator, canvas):
        """Test that parking lot positions are within canvas bounds."""
        lots = parking_lot_generator.generate_random_parking_lots(count=30, canvas=canvas)
        
        for lot in lots:
            x, y = lot.position
            assert x >= 0
            assert x <= canvas[0]
            assert y >= 0
            assert y <= canvas[1]
    
    def test_generate_random_parking_lots_price_range(self, parking_lot_generator, canvas):
        """Test that prices are within specified range."""
        min_price = Decimal('2.0')
        max_price = Decimal('8.0')
        
        lots = parking_lot_generator.generate_random_parking_lots(
            count=20,
            canvas=canvas,
            price_range=(min_price, max_price)
        )
        
        for lot in lots:
            assert lot.price >= min_price
            assert lot.price <= max_price
    
    def test_generate_random_parking_lots_capacity_range(self, parking_lot_generator, canvas):
        """Test that capacities are within specified range."""
        min_cap = 100
        max_cap = 200
        
        lots = parking_lot_generator.generate_random_parking_lots(
            count=20,
            canvas=canvas,
            capacity_range=(min_cap, max_cap)
        )
        
        for lot in lots:
            assert lot.maximum_capacity >= min_cap
            assert lot.maximum_capacity <= max_cap
    
    def test_generate_random_parking_lots_initial_occupancy(self, parking_lot_generator, canvas):
        """Test initial occupancy setting."""
        lots = parking_lot_generator.generate_random_parking_lots(
            count=10,
            canvas=canvas,
            initial_occupancy=0.5
        )
        
        for lot in lots:
            expected_occupancy = int(lot.maximum_capacity * 0.5)
            assert lot.current_capacity == expected_occupancy
    
    def test_generate_random_parking_lots_reproducibility(self, canvas):
        """Test that seeded generator produces reproducible results."""
        lots1 = ParkingLotGenerator(seed=123).generate_random_parking_lots(count=5, canvas=canvas)
        lots2 = ParkingLotGenerator(seed=123).generate_random_parking_lots(count=5, canvas=canvas)
        
        for lot1, lot2 in zip(lots1, lots2):
            assert lot1.position == lot2.position
            assert lot1.price == lot2.price
            assert lot1.maximum_capacity == lot2.maximum_capacity
    
    def test_generate_clustered_parking_lots_count(self, parking_lot_generator, canvas):
        """Test clustered parking lot generation count."""
        centers = [(500.0, 500.0), (200.0, 200.0)]
        
        lots = parking_lot_generator.generate_clustered_parking_lots(
            count=20,
            canvas=canvas,
            cluster_centers=centers
        )
        
        assert len(lots) == 20
    
    def test_generate_clustered_parking_lots_near_centers(self, parking_lot_generator, canvas):
        """Test that clustered lots are near their centers."""
        center = (500.0, 500.0)
        radius = 100.0
        
        lots = parking_lot_generator.generate_clustered_parking_lots(
            count=30,
            canvas=canvas,
            cluster_centers=[center],
            cluster_radius=radius
        )
        
        for lot in lots:
            x_diff = abs(lot.position[0] - center[0])
            y_diff = abs(lot.position[1] - center[1])
            distance = (x_diff ** 2 + y_diff ** 2) ** 0.5
            
            # Should be within radius (with some tolerance for boundary clamping)
            assert distance <= radius * 1.5
    
    def test_generate_clustered_parking_lots_no_centers_raises_error(self, parking_lot_generator, canvas):
        """Test that clustered generation requires centers."""
        with pytest.raises(ValueError) as exc_info:
            parking_lot_generator.generate_clustered_parking_lots(
                count=10,
                canvas=canvas,
                cluster_centers=[]
            )
        
        assert "cluster center" in str(exc_info.value).lower()
    
    def test_generate_poi_based_parking_lots_count(self, parking_lot_generator):
        """Test POI-based parking lot generation."""
        pois = [
            PointOfInterest(id=1, pseudonym="Downtown", position=(500.0, 500.0)),
            PointOfInterest(id=2, pseudonym="Mall", position=(300.0, 300.0))
        ]
        
        lots = parking_lot_generator.generate_poi_based_parking_lots(
            pois=pois,
            lots_per_poi=3
        )
        
        assert len(lots) == 6  # 2 POIs * 3 lots each
    
    def test_generate_poi_based_parking_lots_pricing(self, parking_lot_generator):
        """Test that POI-based lots have appropriate pricing."""
        pois = [
            PointOfInterest(id=1, pseudonym="Downtown", position=(500.0, 500.0)),
            PointOfInterest(id=2, pseudonym="University", position=(300.0, 300.0))
        ]
        
        lots = parking_lot_generator.generate_poi_based_parking_lots(pois=pois, lots_per_poi=2)
        
        # Downtown lots should generally be more expensive than university
        downtown_lots = [lot for lot in lots if "Downtown" in lot.pseudonym]
        university_lots = [lot for lot in lots if "University" in lot.pseudonym]
        
        avg_downtown = sum(lot.price for lot in downtown_lots) / len(downtown_lots)
        avg_university = sum(lot.price for lot in university_lots) / len(university_lots)
        
        assert avg_downtown > avg_university
    
    def test_generate_poi_based_parking_lots_no_pois_raises_error(self, parking_lot_generator):
        """Test that POI-based generation requires POIs."""
        with pytest.raises(ValueError) as exc_info:
            parking_lot_generator.generate_poi_based_parking_lots(pois=[])
        
        assert "point of interest" in str(exc_info.value).lower()
    
    def test_generate_poi_based_parking_lots_naming(self, parking_lot_generator):
        """Test that lots are named after their POIs."""
        pois = [PointOfInterest(id=1, pseudonym="Stadium", position=(500.0, 500.0))]
        
        lots = parking_lot_generator.generate_poi_based_parking_lots(pois=pois, lots_per_poi=2)
        
        for lot in lots:
            assert "Stadium" in lot.pseudonym

@pytest.fixture
def city_generator():
    """Set up city generator."""
    return CityGenerator(seed=42)


class TestCityGenerator:
    """Test city generation utilities."""
    
    def test_generate_simple_city_structure(self, city_generator):
        """Test basic city generation."""
        city = city_generator.generate_simple_city(
            num_pois=5,
            num_parking_lots=10
        )
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) == 5
        assert len(city.parking_lots) == 10
    
    def test_generate_simple_city_attributes(self, city_generator):
        """Test that generated city has correct attributes."""
        city = city_generator.generate_simple_city(
            city_id=42,
            pseudonym="TestCity",
            canvas=(2000.0, 2000.0)
        )
        
        assert city.id == 42
        assert city.pseudonym == "TestCity"
        assert city.canvas == (2000.0, 2000.0)
    
    def test_generate_simple_city_poi_positions(self, city_generator):
        """Test that POIs are within canvas bounds."""
        city = city_generator.generate_simple_city(
            canvas=(1000.0, 1000.0),
            num_pois=10
        )
        
        for poi in city.point_of_interests:
            x, y = poi.position
            assert x >= 0
            assert x <= 1000.0
            assert y >= 0
            assert y <= 1000.0
    
    def test_generate_simple_city_lot_positions(self, city_generator):
        """Test that parking lots are within canvas bounds."""
        city = city_generator.generate_simple_city(
            canvas=(1000.0, 1000.0),
            num_parking_lots=15
        )
        
        for lot in city.parking_lots:
            x, y = lot.position
            assert x >= 0
            assert x <= 1000.0
            assert y >= 0
            assert y <= 1000.0
    
    def test_generate_simple_city_reproducibility(self):
        """Test that seeded city generator is reproducible."""
        city1 = CityGenerator(seed=999).generate_simple_city(num_pois=5, num_parking_lots=10)
        city2 = CityGenerator(seed=999).generate_simple_city(num_pois=5, num_parking_lots=10)
        
        # Check POI positions match
        for poi1, poi2 in zip(city1.point_of_interests, city2.point_of_interests):
            assert poi1.position == poi2.position
        
        # Check parking lot positions match
        for lot1, lot2 in zip(city1.parking_lots, city2.parking_lots):
            assert lot1.position == lot2.position
    
    def test_generate_urban_city_structure(self, city_generator):
        """Test urban city generation."""
        city = city_generator.generate_urban_city()
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) > 5
        assert len(city.parking_lots) > 10
    
    def test_generate_urban_city_has_strategic_pois(self, city_generator):
        """Test that urban city has strategic POIs."""
        city = city_generator.generate_urban_city()
        
        poi_names = [poi.pseudonym for poi in city.point_of_interests]
        
        # Check for key urban features
        assert any("Downtown" in name for name in poi_names)
        assert any("Mall" in name for name in poi_names)
        assert any("University" in name or "Hospital" in name for name in poi_names)
    
    def test_generate_urban_city_has_varied_pricing(self, city_generator):
        """Test that urban city has varied parking prices."""
        city = city_generator.generate_urban_city()
        
        prices = [lot.price for lot in city.parking_lots]
        
        # Should have price variation
        min_price = min(prices)
        max_price = max(prices)
        
        assert max_price > min_price * Decimal('1.5')  # At least 50% variation
    
    def test_generate_urban_city_has_peripheral_parking(self, city_generator):
        """Test that urban city includes peripheral parking."""
        city = city_generator.generate_urban_city()
        
        # Check for peripheral lots (named "Peripheral_*")
        peripheral_lots = [lot for lot in city.parking_lots if "Peripheral" in lot.pseudonym]
        
        assert len(peripheral_lots) > 0
        
        # Peripheral lots should have low prices
        for lot in peripheral_lots:
            assert lot.price < Decimal('3.0')
    
    def test_generate_grid_city_structure(self, city_generator):
        """Test grid city generation."""
        city = city_generator.generate_grid_city(grid_size=(3, 4))
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) == 12  # 3 * 4
        assert len(city.parking_lots) > 0
    
    def test_generate_grid_city_poi_naming(self, city_generator):
        """Test that grid city POIs follow naming convention."""
        city = city_generator.generate_grid_city(grid_size=(3, 3))
        
        for poi in city.point_of_interests:
            assert "Grid_" in poi.pseudonym
    
    def test_generate_grid_city_regular_spacing(self, city_generator):
        """Test that grid city has regularly spaced POIs."""
        canvas = (900.0, 900.0)
        grid_size = (3, 3)
        city = city_generator.generate_grid_city(
            canvas=canvas,
            grid_size=grid_size
        )
        
        # POIs should be evenly distributed
        x_positions = sorted(set([poi.position[0] for poi in city.point_of_interests]))
        
        # Check spacing is roughly uniform (if we have enough unique positions)
        if len(x_positions) > 1:
            spacings = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
            avg_spacing = sum(spacings) / len(spacings)
            
            for spacing in spacings:
                # Allow 20% variation
                assert spacing > avg_spacing * 0.8
                assert spacing < avg_spacing * 1.2
    
    def test_generate_streets_for_city(self, city_generator):
        """Test street generation for a city."""
        city = city_generator.generate_simple_city(num_parking_lots=10)
        
        initial_streets = len(city.streets)
        city_generator.generate_streets_for_city(
            city,
            connection_probability=0.5
        )
        
        # Should have added some streets
        assert len(city.streets) > initial_streets
    
    def test_generate_streets_connects_nearby_lots(self, city_generator):
        """Test that streets connect nearby parking lots."""
        city = city_generator.generate_simple_city(num_parking_lots=5)
        
        city_generator.generate_streets_for_city(
            city,
            connection_probability=1.0  # Always connect if close enough
        )
        
        # All streets should connect existing parking lots
        for street in city.streets:
            assert street.from_parking_lot_id is not None
            assert street.to_parking_lot_id is not None
            
            # IDs should be valid
            lot_ids = [lot.id for lot in city.parking_lots]
            assert street.from_parking_lot_id in lot_ids
            assert street.to_parking_lot_id in lot_ids
    
    def test_generate_streets_speed_limit_range(self, city_generator):
        """Test that generated streets have speeds in specified range."""
        city = city_generator.generate_simple_city(num_parking_lots=8)
        
        min_speed = 2.0
        max_speed = 5.0
        
        city_generator.generate_streets_for_city(
            city,
            connection_probability=0.8,
            speed_limit_range=(min_speed, max_speed)
        )
        
        for street in city.streets:
            assert street.speed_limit >= min_speed
            assert street.speed_limit <= max_speed
    
    def test_different_generators_produce_different_cities(self):
        """Test that unseeded generators produce different results."""
        gen1 = CityGenerator()
        gen2 = CityGenerator()
        
        city1 = gen1.generate_simple_city(num_pois=5)
        city2 = gen2.generate_simple_city(num_pois=5)
        
        # At least some POIs should have different positions
        differences = sum(
            1 for poi1, poi2 in zip(city1.point_of_interests, city2.point_of_interests)
            if poi1.position != poi2.position
        )
        
        assert differences > 0
    
    def test_all_city_types_valid(self, city_generator):
        """Test that all city generation types produce valid cities."""
        city_generators = [
            lambda: city_generator.generate_simple_city(),
            lambda: city_generator.generate_urban_city(),
            lambda: city_generator.generate_grid_city(grid_size=(3, 3))
        ]
        
        for gen_func in city_generators:
            city = gen_func()
            
            # Basic validation
            assert isinstance(city, City)
            assert len(city.point_of_interests) > 0
            assert len(city.parking_lots) > 0
            
            # Check capacity calculations work
            total_capacity = city.total_parking_capacity()
            assert total_capacity > 0
            
            # Check occupancy rate is valid
            occupancy = city.city_occupancy_rate()
            assert occupancy >= 0.0
            assert occupancy <= 1.0
