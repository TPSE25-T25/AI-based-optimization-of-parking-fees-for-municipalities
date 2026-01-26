"""
NSGA-3 Optimizer with Integrated Driver-Based Simulation.

This module extends the basic NSGA-3 optimizer to use the agent-based
ParkingSimulation instead of simple elasticity models. This provides
more realistic evaluations by simulating actual driver behavior.
"""

from typing import List, Tuple, Optional
import numpy as np
from copy import deepcopy

from requests import request

from backend.services.data.osmnx_loader import OSMnxLoader
from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest
from backend.services.optimizer.nsga3_optimizer import NSGA3Optimizer
from backend.services.simulation.simulation import ParkingSimulation, DriverDecision
from backend.services.optimizer.schemas.adapters import SimulationAdapter, OptimizationAdapter
from backend.models.city import City
from backend.models.driver import Driver


class NSGA3OptimizerAgentBased(NSGA3Optimizer):
    """
    NSGA-3 Optimizer that uses agent-based simulation for evaluation.

    Key differences from basic optimizer:
    - Uses ParkingSimulation for realistic driver behavior
    - Generates synthetic driver population
    - Evaluates based on actual parking choices, not elasticity
    - More accurate but slower evaluation
    """

    def __init__(
        self,
        drivers_per_zone_capacity: float = 1.5,
        simulation_runs: int = 1,
        random_seed: int = 42,
        price_weight: float = 1.0,
        distance_to_lot_weight: float = 0.5,
        walking_distance_weight: float = 1.5,
        availability_weight: float = 0.3
    ):
        """
        Initialize the optimizer.

        Args:
            drivers_per_zone_capacity: Multiplier for driver generation (e.g., 1.5 = 150% of capacity)
            simulation_runs: Number of simulation runs per evaluation (for averaging stochastic results)
            random_seed: Seed for reproducibility
            price_weight: Driver's price sensitivity
            distance_to_lot_weight: Driver's driving distance sensitivity
            walking_distance_weight: Driver's walking distance sensitivity
            availability_weight: Driver's availability sensitivity
        """
        super().__init__(random_seed=random_seed)

        self.simulation_runs = simulation_runs

        # Create adapter for converting between schemas
        self.adapter = SimulationAdapter(
            drivers_per_zone_capacity=drivers_per_zone_capacity,
            random_seed=random_seed
        )

        # Create simulation engine
        decision_maker = DriverDecision(
            price_weight=price_weight,
            distance_to_lot_weight=distance_to_lot_weight,
            walking_distance_weight=walking_distance_weight,
            availability_weight=availability_weight
        )
        self.simulation = ParkingSimulation(decision_maker=decision_maker)

        # Cache for base city and drivers (created once per optimization)
        self.base_city: Optional[City] = None
        self.base_drivers: Optional[List[Driver]] = None
        self.zone_ids: Optional[List[int]] = None

    def _initialize_simulation_environment(self, request: OptimizationRequest, loader: OSMnxLoader = None):
        """
        Initialize the base city and driver population for simulation.
        Called once at the start of optimization.

        Args:
            request: The optimization request
        """
        # Create base city from request
        self.base_city = self.adapter.create_city_from_request(request, loader)

        # Generate random driver population
        self.base_drivers = self.adapter.create_drivers_from_request(self.base_city)

        # Store zone IDs for price application
        self.zone_ids = [zone.id for zone in request.zones]

        print(f"\nSimulation Environment Initialized:")
        print(f"  City: {self.base_city.pseudonym}")
        print(f"  Parking Lots: {len(self.base_city.parking_zones)}")
        print(f"  Total Capacity: {self.base_city.total_parking_capacity()}")
        print(f"  Drivers: {len(self.base_drivers)}")

    def _get_detailed_results(self, prices: np.ndarray, _data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a price vector using simulation.

        Args:
            prices: Price vector for all zones
            _data: Dictionary with zone data (unused - agent-based uses cached state)

        Returns:
            Dictionary with occupancy and revenue arrays
        """
        # Create a copy of the city and apply prices
        city_copy = deepcopy(self.base_city)
        self.adapter.apply_prices_to_city(city_copy, prices, self.zone_ids)

        # Run simulation with driver population
        metrics = self.simulation.run_simulation(
            city=city_copy,
            drivers=self.base_drivers,
            reset_capacity=True
        )

        # Extract occupancy and revenue per zone (in correct order)
        occupancy = np.array([metrics.lot_occupancy_rates.get(zone_id, 0.0) for zone_id in self.zone_ids])
        revenue = np.array([float(metrics.lot_revenues.get(zone_id, 0.0)) for zone_id in self.zone_ids])

        return {
            "occupancy": occupancy,
            "revenue": revenue
        }

    def _simulate_scenario(
        self,
        prices: np.ndarray,
        request: OptimizationRequest
    ) -> Tuple[float, float, float, float]:
        """
        Override base class to use driver-based simulation instead of elasticity.

        This method is called by the base class's ParkingProblem._evaluate() during optimization.

        Args:
            prices: Price vector for all zones
            request: Optimization request

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        # Run simulation multiple times and average results (for stochastic stability)
        all_results = []

        for run in range(self.simulation_runs):
            # Create a copy of the city and apply prices
            city_copy = deepcopy(self.base_city)
            self.adapter.apply_prices_to_city(city_copy, prices, self.zone_ids)

            # Run simulation with driver population
            metrics = self.simulation.run_simulation(
                city=city_copy,
                drivers=self.base_drivers,
                reset_capacity=True
            )

            # Extract objectives from metrics
            objectives = OptimizationAdapter.extract_objectives_from_metrics(
                metrics=metrics,
                target_occupancy=request.settings.target_occupancy
            )

            all_results.append(objectives)

        # Average results across runs
        avg_objectives = tuple(np.mean([r[i] for r in all_results]) for i in range(4))

        return avg_objectives
    def optimize(self, request: OptimizationRequest, loader: OSMnxLoader = None):
        """
        Run NSGA-3 optimization with optional driver-based simulation.

        Args:
            request: Optimization request with zones and settings

        Returns:
            Optimization response with Pareto-optimal scenarios
        """
        # Initialize simulation environment if using simulation mode
        self._initialize_simulation_environment(request, loader)

        # Call base class optimize method
        return super().optimize(request)


# Convenience function for creating optimizer
def create_simulation_optimizer(
    drivers_per_zone_capacity: float = 1.5,
    simulation_runs: int = 1,
    random_seed: int = 42
) -> NSGA3OptimizerAgentBased:
    """
    Create a configured NSGA-3 optimizer with simulation support.

    Args:
        drivers_per_zone_capacity: Driver generation multiplier
        simulation_runs: Number of runs per evaluation (for averaging)
        random_seed: Random seed for reproducibility

    Returns:
        Configured optimizer
    """
    return NSGA3OptimizerAgentBased(
        drivers_per_zone_capacity=drivers_per_zone_capacity,
        simulation_runs=simulation_runs,
        random_seed=random_seed
    )
