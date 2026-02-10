"""
TODO: Should refactor this... :/
As it is kinda of a overcomplex bukakke
"""

from typing import List, Tuple
import numpy as np

from backend.services.datasources.generator.driver_generator import DriverGenerator
from backend.services.datasources.osm.osmnx_loader import OSMnxDataSource
from backend.services.models.city import City, ParkingZone
from backend.services.models.driver import Driver


class SimulationAdapter:
    """
    Adapter for converting optimization requests to simulation models.
    """

    def __init__(
        self,
        drivers_per_zone_capacity: float = 1,
        random_seed: int = 42,
        bounds_padding: float = 0.01
    ):
        """
        Initialize the adapter.

        Args:
            drivers_per_zone_capacity: Multiplier for driver generation (e.g., 1.5 = 150% of capacity)
            random_seed: Seed for reproducible random generation
            bounds_padding: Padding to add to geographic bounds (in degrees)
        """
        self.drivers_per_zone_capacity = drivers_per_zone_capacity
        self.random_seed = random_seed
        self.bounds_padding = bounds_padding

    def create_city_from_request(
        self,
        zones: List[ParkingZone]
    ) -> City:
        """
        Create a City model from an OptimizationRequest.

        Args:
            request: The optimization request
            datasource: OSMnx datasource instance for fetching POIs
            city_id: Unique city identifier
            city_name: City name/name

        Returns:
            City model with parking lots
        """
        # Calculate geographic bounds from parking zones
        if not zones:
            raise ValueError("Cannot create city without parking zones")

        latitudes = [zone.position[0] for zone in zones]
        longitudes = [zone.position[1] for zone in zones]

        min_lat = min(latitudes) - self.bounds_padding
        max_lat = max(latitudes) + self.bounds_padding
        min_lon = min(longitudes) - self.bounds_padding
        max_lon = max(longitudes) + self.bounds_padding

        # Create city with real geographic bounds
        city = City(
            id=1,
            name="OptimizationCity",
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon,
            parking_zones=zones,
            point_of_interests=OSMnxDataSource.load_points_of_interest(
                city_name="OptimizationCity",
                center_coords=((min_lat + max_lat) / 2, (min_lon + max_lon) / 2),
                limit=1000
            ),
        )

        return city

    def create_drivers_from_request(
        self,
        city: City
    ) -> List[Driver]:
        """
        Generate realistic driver population based on zones and their characteristics.

        Args:
            request: The optimization request
            city: The city model (to get parking lot positions)

        Returns:
            List of Driver instances
        """
        num_drivers = int(city.total_parking_capacity() * self.drivers_per_zone_capacity)
        return DriverGenerator(self.random_seed).generate_random_drivers(num_drivers, city)


    def apply_current_fees_to_city(
        self,
        city: City,
        current_fee_vector: np.ndarray,
        zone_ids: List[int]
    ) -> City:
        """
        Apply a current_fee vector to city parking lots.

        Args:
            city: The city model
            current_fee_vector: Array of current_fees (same order as zone_ids)
            zone_ids: List of zone IDs corresponding to current_fee_vector

        Returns:
            City with updated current_fees (modifies in place and returns for convenience)
        """
        for current_fee, id in zip(current_fee_vector, zone_ids):
            lot = city.get_parking_zone_by_id(id)
            if lot:
                lot.current_fee = float(current_fee)

        return city

class OptimizationAdapter:
    """
    Adapter for converting simulation results back to optimization metrics.
    """

    @staticmethod
    def extract_objectives_from_metrics(
        metrics,
        target_occupancy: float,
        original_revenue: float = None
    ) -> Tuple[float, float, float, float]:
        """
        Extract the 4 optimization objectives from simulation metrics.

        Args:
            metrics: SimulationMetrics from ParkingSimulation
            target_occupancy: Target occupancy rate
            original_revenue: Original revenue before optimization (for comparison)

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        # Objective 1: Total Revenue (maximize)
        f1_revenue = float(metrics.total_revenue)

        # Objective 2: Occupancy Gap (minimize)
        # Calculate average gap from target across all lots
        occupancy_gaps = [
            abs(occ_rate - target_occupancy)
            for occ_rate in metrics.lot_occupancy_rates.values()
        ]
        f2_occupancy_gap = sum(occupancy_gaps) / len(occupancy_gaps) if occupancy_gaps else 0.0

        # Objective 3: Demand Drop (minimize)
        # Use rejection rate as proxy for demand drop
        f3_demand_drop = metrics.rejection_rate

        # Objective 4: User Balance (maximize)
        # Use inverse of average driver cost and occupancy variance
        # Lower cost and lower variance = better balance
        cost_component = 1.0 / (float(metrics.average_driver_cost) + 1.0)
        variance_component = 1.0 / (metrics.occupancy_variance + 1.0)
        f4_user_balance = (cost_component + variance_component) / 2.0

        return f1_revenue, f2_occupancy_gap, f3_demand_drop, f4_user_balance


def create_default_adapter(
    drivers_per_zone_capacity: float = 1.5,
    random_seed: int = 42,
    bounds_padding: float = 0.01
) -> SimulationAdapter:
    """
    Create a SimulationAdapter with default settings.

    Args:
        drivers_per_zone_capacity: Multiplier for driver generation
        random_seed: Seed for reproducibility
        bounds_padding: Padding to add to geographic bounds (in degrees)

    Returns:
        Configured SimulationAdapter
    """
    return SimulationAdapter(
        drivers_per_zone_capacity=drivers_per_zone_capacity,
        random_seed=random_seed,
        bounds_padding=bounds_padding
    )
