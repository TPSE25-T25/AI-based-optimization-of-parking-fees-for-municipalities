"""
Unit tests for driver generator module.
"""

import pytest
from decimal import Decimal

from backend.models.city import City, PointOfInterest
from backend.models.driver import Driver
from backend.services.data.driver_generator import DriverGenerator


@pytest.fixture
def test_city():
    """Set up test city with POIs."""
    city = City(
        id=1,
        pseudonym="TestCity",
        canvas=(1000.0, 1000.0)
    )
    
    # Add points of interest
    pois = [
        PointOfInterest(id=1, pseudonym="Downtown", position=(500.0, 500.0)),
        PointOfInterest(id=2, pseudonym="Mall", position=(300.0, 700.0)),
        PointOfInterest(id=3, pseudonym="University", position=(700.0, 300.0))
    ]
    
    for poi in pois:
        city.add_point_of_interest(poi)
    
    return city


@pytest.fixture
def generator():
    """Create a seeded driver generator."""
    return DriverGenerator(seed=42)


class TestDriverGenerator:
    """Test driver generation utilities."""
    
    def test_generate_random_drivers_count(self, generator, test_city):
        """Test that correct number of drivers are generated."""
        drivers = generator.generate_random_drivers(count=50, city=test_city)
        
        assert len(drivers) == 50
    
    def test_generate_random_drivers_types(self, generator, test_city):
        """Test that all generated objects are Driver instances."""
        drivers = generator.generate_random_drivers(count=20, city=test_city)
        
        assert all(isinstance(d, Driver) for d in drivers)
    
    def test_generate_random_drivers_unique_ids(self, generator, test_city):
        """Test that all drivers have unique IDs."""
        drivers = generator.generate_random_drivers(count=30, city=test_city)
        
        ids = [d.id for d in drivers]
        assert len(ids) == len(set(ids))
    
    def test_generate_random_drivers_within_canvas(self, generator, test_city):
        """Test that driver starting positions are within canvas bounds."""
        drivers = generator.generate_random_drivers(count=50, city=test_city)
        
        for driver in drivers:
            x, y = driver.starting_position
            assert x >= 0
            assert x <= test_city.canvas[0]
            assert y >= 0
            assert y <= test_city.canvas[1]
    
    def test_generate_random_drivers_destinations_are_pois(self, generator, test_city):
        """Test that destinations are at POI locations."""
        drivers = generator.generate_random_drivers(count=50, city=test_city)
        
        poi_positions = {poi.position for poi in test_city.point_of_interests}
        
        for driver in drivers:
            assert driver.destination in poi_positions
    
    def test_generate_random_drivers_price_range(self, generator, test_city):
        """Test that driver max prices are within specified range."""
        min_price = Decimal('2.0')
        max_price = Decimal('8.0')
        
        drivers = generator.generate_random_drivers(
            count=50,
            city=test_city,
            price_range=(min_price, max_price)
        )
        
        for driver in drivers:
            assert driver.max_parking_price >= min_price
            assert driver.max_parking_price <= max_price
    
    def test_generate_random_drivers_duration_range(self, generator, test_city):
        """Test that parking durations are within specified range."""
        min_duration = 30
        max_duration = 180
        
        drivers = generator.generate_random_drivers(
            count=50,
            city=test_city,
            parking_duration_range=(min_duration, max_duration)
        )
        
        for driver in drivers:
            assert driver.desired_parking_time >= min_duration
            assert driver.desired_parking_time <= max_duration
    
    def test_generate_random_drivers_reproducibility(self, test_city):
        """Test that seeded generator produces reproducible results."""
        # Generate twice with same seed - should produce same results
        drivers1 = DriverGenerator(seed=123).generate_random_drivers(count=10, city=test_city)
        drivers2 = DriverGenerator(seed=123).generate_random_drivers(count=10, city=test_city)
        
        for d1, d2 in zip(drivers1, drivers2):
            assert d1.id == d2.id
            assert d1.starting_position == d2.starting_position
            assert d1.destination == d2.destination
            assert d1.max_parking_price == d2.max_parking_price
            assert d1.desired_parking_time == d2.desired_parking_time
    
    def test_generate_random_drivers_no_pois_raises_error(self, generator):
        """Test that generator raises error when city has no POIs."""
        empty_city = City(id=2, pseudonym="EmptyCity", canvas=(1000.0, 1000.0))
        
        with pytest.raises(ValueError) as exc_info:
            generator.generate_random_drivers(count=10, city=empty_city)
        
        assert "point of interest" in str(exc_info.value).lower()
    
    def test_generate_clustered_drivers_count(self, generator, test_city):
        """Test clustered driver generation count."""
        drivers = generator.generate_clustered_drivers(
            count=50,
            city=test_city,
            cluster_centers=[test_city.point_of_interests[0]]
        )
        
        assert len(drivers) == 50
    
    def test_generate_clustered_drivers_near_centers(self, generator, test_city):
        """Test that clustered drivers start near cluster centers."""
        cluster_center = test_city.point_of_interests[0]
        cluster_radius = 50.0
        
        drivers = generator.generate_clustered_drivers(
            count=30,
            city=test_city,
            cluster_centers=[cluster_center],
            cluster_radius=cluster_radius
        )
        
        # Most drivers should start near the cluster center
        for driver in drivers:
            x_diff = abs(driver.starting_position[0] - cluster_center.position[0])
            y_diff = abs(driver.starting_position[1] - cluster_center.position[1])
            
            # Should be within reasonable distance (allowing for random spread)
            # Using 2x radius as reasonable bound due to random component
            assert x_diff <= cluster_radius * 2
            assert y_diff <= cluster_radius * 2
    
    def test_generate_clustered_drivers_multiple_clusters(self, generator, test_city):
        """Test clustered generation with multiple cluster centers."""
        drivers = generator.generate_clustered_drivers(
            count=60,
            city=test_city,
            cluster_centers=test_city.point_of_interests[:2]  # Use first 2 POIs
        )
        
        assert len(drivers) == 60
        assert all(isinstance(d, Driver) for d in drivers)
    
    def test_generate_clustered_drivers_no_clusters_raises_error(self, generator, test_city):
        """Test that clustered generation requires cluster centers."""
        with pytest.raises(ValueError) as exc_info:
            generator.generate_clustered_drivers(
                count=10,
                city=test_city,
                cluster_centers=[]
            )
        
        assert "cluster center" in str(exc_info.value).lower()
    
    def test_generate_clustered_drivers_no_pois_raises_error(self, generator):
        """Test that clustered generation requires POIs."""
        empty_city = City(id=2, pseudonym="EmptyCity", canvas=(1000.0, 1000.0))
        
        with pytest.raises(ValueError) as exc_info:
            generator.generate_clustered_drivers(
                count=10,
                city=empty_city,
                cluster_centers=[PointOfInterest(id=99, pseudonym="Center", position=(100.0, 100.0))]
            )
        
        assert "point of interest" in str(exc_info.value).lower()
    
    def test_generate_rush_hour_drivers_count(self, generator, test_city):
        """Test rush hour driver generation count."""
        drivers = generator.generate_rush_hour_drivers(
            count=100,
            city=test_city,
            peak_destination=test_city.point_of_interests[0]
        )
        
        assert len(drivers) == 100
    
    def test_generate_rush_hour_drivers_peak_destination(self, generator, test_city):
        """Test that most rush hour drivers go to peak destination."""
        peak_poi = test_city.point_of_interests[0]
        
        drivers = generator.generate_rush_hour_drivers(
            count=100,
            city=test_city,
            peak_destination=peak_poi
        )
        
        # Count how many go to peak destination
        to_peak = sum(1 for d in drivers if d.destination == peak_poi.position)
        
        # Should be majority (around 80% based on implementation)
        assert to_peak > 50
    
    def test_generate_rush_hour_drivers_price_range(self, generator, test_city):
        """Test rush hour driver price range."""
        min_price = Decimal('5.0')
        max_price = Decimal('15.0')
        
        drivers = generator.generate_rush_hour_drivers(
            count=50,
            city=test_city,
            peak_destination=test_city.point_of_interests[0],
            price_range=(min_price, max_price)
        )
        
        for driver in drivers:
            assert driver.max_parking_price >= min_price
            assert driver.max_parking_price <= max_price
    
    def test_generate_rush_hour_drivers_longer_durations(self, generator, test_city):
        """Test rush hour drivers have longer parking durations."""
        min_duration = 180  # 3 hours
        max_duration = 480  # 8 hours
        
        drivers = generator.generate_rush_hour_drivers(
            count=50,
            city=test_city,
            peak_destination=test_city.point_of_interests[0],
            parking_duration_range=(min_duration, max_duration)
        )
        
        for driver in drivers:
            assert driver.desired_parking_time >= min_duration
            assert driver.desired_parking_time <= max_duration
    
    def test_generate_price_sensitive_drivers_count(self, generator, test_city):
        """Test price-sensitive driver generation count."""
        drivers = generator.generate_price_sensitive_drivers(
            count=40,
            city=test_city
        )
        
        assert len(drivers) == 40
    
    def test_generate_price_sensitive_drivers_low_prices(self, generator, test_city):
        """Test that price-sensitive drivers have low price tolerance."""
        threshold = Decimal('3.0')
        
        drivers = generator.generate_price_sensitive_drivers(
            count=50,
            city=test_city,
            low_price_threshold=threshold
        )
        
        for driver in drivers:
            assert driver.max_parking_price <= threshold
            assert driver.max_parking_price > Decimal('0')
    
    def test_generate_price_sensitive_drivers_custom_threshold(self, generator, test_city):
        """Test price-sensitive drivers with custom threshold."""
        custom_threshold = Decimal('2.5')
        
        drivers = generator.generate_price_sensitive_drivers(
            count=30,
            city=test_city,
            low_price_threshold=custom_threshold
        )
        
        for driver in drivers:
            assert driver.max_parking_price <= custom_threshold
    
    def test_generate_price_sensitive_drivers_shorter_durations(self, generator, test_city):
        """Test price-sensitive drivers typically have shorter durations."""
        drivers = generator.generate_price_sensitive_drivers(
            count=50,
            city=test_city,
            parking_duration_range=(30, 120)
        )
        
        for driver in drivers:
            assert driver.desired_parking_time >= 30
            assert driver.desired_parking_time <= 120
    
    def test_generate_price_sensitive_drivers_no_pois_raises_error(self, generator):
        """Test that price-sensitive generation requires POIs."""
        empty_city = City(id=2, pseudonym="EmptyCity", canvas=(1000.0, 1000.0))
        
        with pytest.raises(ValueError) as exc_info:
            generator.generate_price_sensitive_drivers(
                count=10,
                city=empty_city
            )
        
        assert "point of interest" in str(exc_info.value).lower()
    
    def test_different_generators_produce_different_results(self, test_city):
        """Test that unseeded generators produce different results."""
        gen1 = DriverGenerator()  # No seed
        gen2 = DriverGenerator()  # No seed
        
        drivers1 = gen1.generate_random_drivers(count=5, city=test_city)
        drivers2 = gen2.generate_random_drivers(count=5, city=test_city)
        
        # At least some drivers should be different
        differences = sum(
            1 for d1, d2 in zip(drivers1, drivers2)
            if d1.starting_position != d2.starting_position
        )
        
        assert differences > 0
    
    def test_all_driver_types_have_valid_attributes(self, generator, test_city):
        """Test that all generator types produce valid Driver objects."""
        generator_methods = [
            lambda: generator.generate_random_drivers(count=10, city=test_city),
            lambda: generator.generate_clustered_drivers(
                count=10, city=test_city, cluster_centers=[test_city.point_of_interests[0]]
            ),
            lambda: generator.generate_rush_hour_drivers(
                count=10, city=test_city, peak_destination=test_city.point_of_interests[0]
            ),
            lambda: generator.generate_price_sensitive_drivers(
                count=10, city=test_city
            )
        ]
        
        for method in generator_methods:
            drivers = method()
            
            for driver in drivers:
                # Check all required attributes exist and are valid
                assert isinstance(driver.id, int)
                assert driver.id > 0
                assert isinstance(driver.pseudonym, str)
                assert len(driver.pseudonym) > 0
                assert isinstance(driver.max_parking_price, Decimal)
                assert driver.max_parking_price > Decimal('0')
                assert isinstance(driver.starting_position, tuple)
                assert len(driver.starting_position) == 2
                assert isinstance(driver.destination, tuple)
                assert len(driver.destination) == 2
                assert isinstance(driver.desired_parking_time, int)
                assert driver.desired_parking_time > 0
