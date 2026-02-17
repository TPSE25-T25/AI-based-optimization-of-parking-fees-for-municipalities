"""
Unit tests for city and parking lot generator modules.
"""

import pytest

from backend.services.models.city import City, PointOfInterest, ParkingZone
from backend.services.datasources.generator.city_generator import ParkingZoneGenerator, CityGenerator


@pytest.fixture
def parking_zone_generator():
    """Set up parking lot generator."""
    return ParkingZoneGenerator(seed=42)


@pytest.fixture
def geo_bounds():
    """Set up test geographic bounds (lat_range, lon_range)."""
    return ((49.0, 49.1), (8.4, 8.5))  # (lat_range, lon_range)


class TestParkingZoneGenerator:
    """Test parking lot generation utilities."""
    
    def test_generate_random_parking_zones_count(self, parking_zone_generator, geo_bounds):
        """Test that correct number of parking lots are generated."""
        lat_range, lon_range = geo_bounds
        lots = parking_zone_generator.generate_random_parking_zones(count=15, lat_range=lat_range, lon_range=lon_range)

        assert len(lots) == 15
    
    def test_generate_random_parking_zones_types(self, parking_zone_generator, geo_bounds):
        """Test that all generated objects are ParkingZone instances."""
        lat_range, lon_range = geo_bounds
        lots = parking_zone_generator.generate_random_parking_zones(count=10, lat_range=lat_range, lon_range=lon_range)

        assert all(isinstance(lot, ParkingZone) for lot in lots)
    
    def test_generate_random_parking_zones_unique_ids(self, parking_zone_generator, geo_bounds):
        """Test that all parking lots have unique IDs."""
        lat_range, lon_range = geo_bounds
        lots = parking_zone_generator.generate_random_parking_zones(count=20, lat_range=lat_range, lon_range=lon_range)

        ids = [lot.id for lot in lots]
        assert len(ids) == len(set(ids))
    
    def test_generate_random_parking_zones_within_bounds(self, parking_zone_generator, geo_bounds):
        """Test that parking lot positions are within geographic bounds."""
        lat_range, lon_range = geo_bounds
        lots = parking_zone_generator.generate_random_parking_zones(count=30, lat_range=lat_range, lon_range=lon_range)

        for lot in lots:
            lat, lon = lot.position
            assert lat >= lat_range[0]
            assert lat <= lat_range[1]
            assert lon >= lon_range[0]
            assert lon <= lon_range[1]
    
    def test_generate_random_parking_zones_current_fee_range(self, parking_zone_generator, geo_bounds):
        """Test that current_fees are within specified range."""
        lat_range, lon_range = geo_bounds
        min_current_fee = 2.0
        max_current_fee = 8.0

        lots = parking_zone_generator.generate_random_parking_zones(
            count=20,
            lat_range=lat_range,
            lon_range=lon_range,
            current_fee_range=(min_current_fee, max_current_fee)
        )

        for lot in lots:
            assert lot.current_fee >= min_current_fee
            assert lot.current_fee <= max_current_fee
    
    def test_generate_random_parking_zones_capacity_range(self, parking_zone_generator, geo_bounds):
        """Test that capacities are within specified range."""
        lat_range, lon_range = geo_bounds
        min_cap = 100
        max_cap = 200

        lots = parking_zone_generator.generate_random_parking_zones(
            count=20,
            lat_range=lat_range,
            lon_range=lon_range,
            capacity_range=(min_cap, max_cap)
        )

        for lot in lots:
            assert lot.maximum_capacity >= min_cap
            assert lot.maximum_capacity <= max_cap
    
    def test_generate_random_parking_zones_initial_occupancy(self, parking_zone_generator, geo_bounds):
        """Test that parking zones have initial occupancy within their maximum capacity."""
        lat_range, lon_range = geo_bounds
        lots = parking_zone_generator.generate_random_parking_zones(
            count=10,
            lat_range=lat_range,
            lon_range=lon_range
        )

        for lot in lots:
            # Verify current capacity is within maximum capacity (generated randomly)
            assert 0 <= lot.current_capacity <= lot.maximum_capacity
    
    def test_generate_random_parking_zones_reproducibility(self, geo_bounds):
        """Test that seeded generator produces reproducible results."""
        lat_range, lon_range = geo_bounds
        lots1 = ParkingZoneGenerator(seed=123).generate_random_parking_zones(count=5, lat_range=lat_range, lon_range=lon_range)
        lots2 = ParkingZoneGenerator(seed=123).generate_random_parking_zones(count=5, lat_range=lat_range, lon_range=lon_range)
        
        for lot1, lot2 in zip(lots1, lots2):
            assert lot1.position == lot2.position
            assert lot1.current_fee == lot2.current_fee
            assert lot1.maximum_capacity == lot2.maximum_capacity
    
    def test_generate_clustered_parking_zones_count(self, parking_zone_generator, geo_bounds):
        """Test clustered parking lot generation count."""
        lat_range, lon_range = geo_bounds
        centers = [(49.05, 8.45), (49.02, 8.42)]  # Use geographic coordinates

        lots = parking_zone_generator.generate_clustered_parking_zones(
            count=20,
            cluster_centers=centers,
            lat_range=lat_range,
            lon_range=lon_range
        )

        assert len(lots) == 20
    
    def test_generate_clustered_parking_zones_near_centers(self, parking_zone_generator, geo_bounds):
        """Test that clustered lots are near their centers."""
        lat_range, lon_range = geo_bounds
        center = (49.05, 8.45)  # Use geographic coordinates
        radius_deg = 0.01  # ~1km radius in degrees

        lots = parking_zone_generator.generate_clustered_parking_zones(
            count=30,
            cluster_centers=[center],
            cluster_radius_deg=radius_deg,
            lat_range=lat_range,
            lon_range=lon_range
        )

        for lot in lots:
            lat_diff = abs(lot.position[0] - center[0])
            lon_diff = abs(lot.position[1] - center[1])
            distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

            # Should be within radius (with some tolerance for boundary clamping)
            assert distance <= radius_deg * 1.5
    
    def test_generate_clustered_parking_zones_no_centers_raises_error(self, parking_zone_generator, geo_bounds):
        """Test that clustered generation requires centers."""
        lat_range, lon_range = geo_bounds
        with pytest.raises(ValueError) as exc_info:
            parking_zone_generator.generate_clustered_parking_zones(
                count=10,
                cluster_centers=[],
                lat_range=lat_range,
                lon_range=lon_range
            )
        
        assert "cluster center" in str(exc_info.value).lower()
    
    def test_generate_poi_based_parking_zones_count(self, parking_zone_generator):
        """Test POI-based parking lot generation."""
        pois = [
            PointOfInterest(id=1, name="Downtown", position=(49.05, 8.45)),
            PointOfInterest(id=2, name="Mall", position=(49.03, 8.43))
        ]

        lots = parking_zone_generator.generate_poi_based_parking_zones(
            pois=pois,
            lots_per_poi=3
        )

        assert len(lots) == 6  # 2 POIs * 3 lots each
    
    def test_generate_poi_based_parking_zones_pricing(self, parking_zone_generator):
        """Test that POI-based lots have appropriate pricing."""
        pois = [
            PointOfInterest(id=1, name="Downtown", position=(49.05, 8.45)),
            PointOfInterest(id=2, name="University", position=(49.03, 8.43))
        ]

        lots = parking_zone_generator.generate_poi_based_parking_zones(pois=pois, lots_per_poi=2)

        # Downtown lots should generally be more expensive than university
        downtown_lots = [lot for lot in lots if "Downtown" in lot.name]
        university_lots = [lot for lot in lots if "University" in lot.name]

        avg_downtown = sum(lot.current_fee for lot in downtown_lots) / len(downtown_lots)
        avg_university = sum(lot.current_fee for lot in university_lots) / len(university_lots)

        assert avg_downtown > avg_university
    
    def test_generate_poi_based_parking_zones_no_pois_raises_error(self, parking_zone_generator):
        """Test that POI-based generation requires POIs."""
        with pytest.raises(ValueError) as exc_info:
            parking_zone_generator.generate_poi_based_parking_zones(pois=[])
        
        assert "point of interest" in str(exc_info.value).lower()
    
    def test_generate_poi_based_parking_zones_naming(self, parking_zone_generator):
        """Test that lots are named after their POIs."""
        pois = [PointOfInterest(id=1, name="Stadium", position=(49.05, 8.45))]

        lots = parking_zone_generator.generate_poi_based_parking_zones(pois=pois, lots_per_poi=2)

        for lot in lots:
            assert "Stadium" in lot.name

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
            num_parking_zones=10
        )
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) == 5
        assert len(city.parking_zones) == 10
    
    def test_generate_simple_city_attributes(self, city_generator):
        """Test that generated city has correct attributes."""
        city = city_generator.generate_simple_city(
            city_id=42,
            name="TestCity",
            center_lat=49.0,
            center_lon=8.4,
            size_deg=0.2
        )

        assert city.id == 42
        assert city.name == "TestCity"
        # Check geographic bounds
        assert city.min_latitude == 48.9
        assert city.max_latitude == 49.1
        assert city.min_longitude == 8.3
        assert city.max_longitude == 8.5
    
    def test_generate_simple_city_poi_positions(self, city_generator):
        """Test that POIs are within geographic bounds."""
        city = city_generator.generate_simple_city(
            center_lat=49.0,
            center_lon=8.4,
            size_deg=0.1,
            num_pois=10
        )

        for poi in city.point_of_interests:
            lat, lon = poi.position
            assert lat >= city.min_latitude
            assert lat <= city.max_latitude
            assert lon >= city.min_longitude
            assert lon <= city.max_longitude
    
    def test_generate_simple_city_lot_positions(self, city_generator):
        """Test that parking lots are within geographic bounds."""
        city = city_generator.generate_simple_city(
            center_lat=49.0,
            center_lon=8.4,
            size_deg=0.1,
            num_parking_zones=15
        )

        for lot in city.parking_zones:
            lat, lon = lot.position
            assert lat >= city.min_latitude
            assert lat <= city.max_latitude
            assert lon >= city.min_longitude
            assert lon <= city.max_longitude
    
    def test_generate_simple_city_reproducibility(self):
        """Test that seeded city generator is reproducible."""
        city1 = CityGenerator(seed=999).generate_simple_city(num_pois=5, num_parking_zones=10)
        city2 = CityGenerator(seed=999).generate_simple_city(num_pois=5, num_parking_zones=10)
        
        # Check POI positions match
        for poi1, poi2 in zip(city1.point_of_interests, city2.point_of_interests):
            assert poi1.position == poi2.position
        
        # Check parking lot positions match
        for lot1, lot2 in zip(city1.parking_zones, city2.parking_zones):
            assert lot1.position == lot2.position
    
    def test_generate_urban_city_structure(self, city_generator):
        """Test urban city generation."""
        city = city_generator.generate_urban_city()
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) > 5
        assert len(city.parking_zones) > 10
    
    def test_generate_urban_city_has_strategic_pois(self, city_generator):
        """Test that urban city has strategic POIs."""
        city = city_generator.generate_urban_city()
        
        poi_names = [poi.name for poi in city.point_of_interests]
        
        # Check for key urban features
        assert any("Downtown" in name for name in poi_names)
        assert any("Mall" in name for name in poi_names)
        assert any("University" in name or "Hospital" in name for name in poi_names)
    
    def test_generate_urban_city_has_varied_pricing(self, city_generator):
        """Test that urban city has varied parking current_fees."""
        city = city_generator.generate_urban_city()
        
        current_fees = [lot.current_fee for lot in city.parking_zones]
        
        # Should have current_fee variation
        min_current_fee = min(current_fees)
        max_current_fee = max(current_fees)
        
        assert max_current_fee > min_current_fee * 1.5  # At least 50% variation
    
    def test_generate_urban_city_has_peripheral_parking(self, city_generator):
        """Test that urban city includes peripheral parking."""
        city = city_generator.generate_urban_city()
        
        # Check for peripheral lots (named "Peripheral_*")
        peripheral_lots = [lot for lot in city.parking_zones if "Peripheral" in lot.name]
        
        assert len(peripheral_lots) > 0
        
        # Peripheral lots should have low current_fees
        for lot in peripheral_lots:
            assert lot.current_fee < 3.0
    
    def test_generate_grid_city_structure(self, city_generator):
        """Test grid city generation."""
        city = city_generator.generate_grid_city(grid_size=(3, 4))
        
        assert isinstance(city, City)
        assert len(city.point_of_interests) == 12  # 3 * 4
        assert len(city.parking_zones) > 0
    
    def test_generate_grid_city_poi_naming(self, city_generator):
        """Test that grid city POIs follow naming convention."""
        city = city_generator.generate_grid_city(grid_size=(3, 3))
        
        for poi in city.point_of_interests:
            assert "Grid_" in poi.name
    
    def test_generate_grid_city_regular_spacing(self, city_generator):
        """Test that grid city has regularly spaced POIs."""
        size_deg = 0.09
        grid_size = (3, 3)
        city = city_generator.generate_grid_city(
            center_lat=49.0,
            center_lon=8.4,
            size_deg=size_deg,
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
            assert len(city.parking_zones) > 0
            
            # Check capacity calculations work
            total_capacity = city.total_parking_capacity()
            assert total_capacity > 0
            
            # Check occupancy rate is valid
            occupancy = city.city_occupancy_rate()
            assert occupancy >= 0.0
            assert occupancy <= 1.0
