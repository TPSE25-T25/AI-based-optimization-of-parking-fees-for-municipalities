"""
NSGA-3 Optimizer with Integrated Driver-Based Simulation.

This module extends the basic NSGA-3 optimizer to use the agent-based
ParkingSimulation instead of simple elasticity models. This provides
more realistic evaluations by simulating actual driver behavior.
"""

from typing import List, Tuple, Optional
import numpy as np

from backend.services.optimizer.schemas.optimization_schema import PricingScenario
from backend.services.payloads.optimization_payload import OptimizationResponse
from backend.services.optimizer.nsga3_optimizer import NSGA3Optimizer
from backend.services.settings.optimizations_settings import OptimizationSettings
from backend.services.simulation.simulation import ParkingSimulation, DriverDecision, SimulationBatch
from backend.services.optimizer.schemas.optimization_adapters import SimulationAdapter, OptimizationAdapter
from backend.services.models.city import City
from backend.services.models.driver import Driver


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
        self, optimizer_settings: OptimizationSettings):
        """
        Initialize the optimizer.

        Args:
            drivers_per_zone_capacity: Multiplier for driver generation (e.g., 1.5 = 150% of capacity)
            simulation_runs: Number of simulation runs per evaluation (for averaging stochastic results)
            random_seed: Seed for reproducibility
            current_fee_weight: Driver's current_fee sensitivity
            distance_to_lot_weight: Driver's driving distance sensitivity
            walking_distance_weight: Driver's walking distance sensitivity
            availability_weight: Driver's availability sensitivity
        """
        super().__init__(optimizer_settings)

        self.simulation_runs = optimizer_settings.simulation_runs

        # Create adapter for converting between schemas
        self.adapter = SimulationAdapter(
            drivers_per_zone_capacity=optimizer_settings.drivers_per_zone_capacity,
            random_seed=optimizer_settings.random_seed
        )

        # Create simulation engine
        decision_maker = DriverDecision(
            fee_weight=optimizer_settings.driver_fee_weight,
            distance_to_lot_weight=optimizer_settings.driver_distance_to_lot_weight,
            walking_distance_weight=optimizer_settings.driver_walking_distance_weight,
            availability_weight=optimizer_settings.driver_availability_weight
        )
        self.simulation = ParkingSimulation(
            decision_maker=decision_maker,
            use_batch_processing=True,  # Enable vectorized batch processing (fast!)
            batch_size=10000  # Large batch to process all drivers at once
        )
        
        # Create batch simulator for parallel execution of multiple runs
        self.batch_simulator = SimulationBatch(
            simulation=self.simulation,
            n_jobs=-1  # Use all available cores
        )

        # Cache for base city and drivers (created once per optimization)
        self.base_city: Optional[City] = None
        self.base_drivers: Optional[List[Driver]] = None
        self.zone_ids: Optional[List[int]] = None
        self.original_fees: Optional[List[float]] = None  # Cache original fees for restoration
        
        # Pre-computed numpy arrays for vectorized operations (avoid repeated conversions)
        self.driver_positions_cache: Optional[np.ndarray] = None
        self.driver_destinations_cache: Optional[np.ndarray] = None
        self.driver_max_fees_cache: Optional[np.ndarray] = None
        self.lot_positions_cache: Optional[np.ndarray] = None

    def _initialize_simulation_environment(self, city: City):
        """
        Initialize the base city and driver population for simulation.
        Called once at the start of optimization.

        Args:
            city: City object
        """
        # Create base city from request
        self.base_city = city

        # Generate random driver population
        self.base_drivers = self.adapter.create_drivers_from_request(self.base_city)

        # Store zone IDs for current_fee application
        self.zone_ids = [zone.id for zone in self.base_city.parking_zones]
        
        # Cache original fees for quick restoration
        self.original_fees = [zone.current_fee for zone in self.base_city.parking_zones]
        
        # Pre-compute and cache numpy arrays for driver/zone data (huge speedup!)
        self.driver_positions_cache = np.array(
            [d.starting_position for d in self.base_drivers], dtype=np.float32
        )
        self.driver_destinations_cache = np.array(
            [d.destination for d in self.base_drivers], dtype=np.float32
        )
        self.driver_max_fees_cache = np.array(
            [d.max_parking_current_fee for d in self.base_drivers], dtype=np.float32
        )
        self.lot_positions_cache = np.array(
            [z.position for z in self.base_city.parking_zones], dtype=np.float32
        )
        
        # Get backend info
        backend_info = self.simulation.decision_maker.parallel_engine.get_backend_info()

        print(f"\nSimulation Environment Initialized:")
        print(f"  City: {self.base_city.name}")
        print(f"  Parking Lots: {len(self.base_city.parking_zones)}")
        print(f"  Total Capacity: {self.base_city.total_parking_capacity()}")
        print(f"  Drivers: {len(self.base_drivers)}")
        print(f"  Parallel Backend: {backend_info['backend'].upper()}")
        print(f"  CUDA Available: {backend_info['cuda_available']}")
        print(f"  Parallel Jobs: {backend_info['n_jobs']}")
        print(f"  Batch Processing: Enabled (vectorized decisions for speed)")
        print(f"  Simulation Runs: {self.simulation_runs} {'(parallel)' if self.simulation_runs > 1 else ''}")

    def _get_detailed_results(self, current_fees: np.ndarray, _data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a current_fee vector using simulation.
        Optimized to avoid deep copy by modifying fees in-place and restoring them.

        Args:
            current_fees: current_fee vector for all zones
            _data: Dictionary with zone data (unused - agent-based uses cached state)

        Returns:
            Dictionary with occupancy and revenue arrays
        """
        # Apply fees in-place (much faster than deep copy)
        for zone, fee in zip(self.base_city.parking_zones, current_fees):
            zone.current_fee = fee
        
        # Run simulation with driver population
        metrics = self.simulation.run_simulation(
            city=self.base_city,
            drivers=self.base_drivers,
            reset_capacity=True
        )
        
        # Restore original fees
        for zone, orig_fee in zip(self.base_city.parking_zones, self.original_fees):
            zone.current_fee = orig_fee

        # Extract occupancy and revenue per zone (in correct order)
        occupancy = np.array([metrics.lot_occupancy_rates.get(id, 0.0) for id in self.zone_ids])
        revenue = np.array([float(metrics.lot_revenues.get(id, 0.0)) for id in self.zone_ids])

        return {
            "occupancy": occupancy,
            "revenue": revenue
        }

    def _simulate_scenario(
        self,
        current_fees: np.ndarray,
        city: City
    ) -> Tuple[float, float, float, float]:
        """
        Override base class to use driver-based simulation instead of elasticity.
        Optimized with cached numpy arrays for maximum speed.

        This method is called by the base class's ParkingProblem._evaluate() during optimization.

        Args:
            current_fees: current_fee vector for all zones
            city: City object (ignored, uses cached self.base_city)

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        # Apply fees in-place to cached city (much faster than deep copy)
        for zone, fee in zip(self.base_city.parking_zones, current_fees):
            zone.current_fee = fee
        
        # Run optimized simulation using cached arrays
        metrics = self._run_fast_simulation()
        
        # Restore original fees for next evaluation
        for zone, orig_fee in zip(self.base_city.parking_zones, self.original_fees):
            zone.current_fee = orig_fee
        
        # Extract objectives from metrics
        objectives = OptimizationAdapter.extract_objectives_from_metrics(
            metrics=metrics,
            target_occupancy=self.target_occupancy
        )
        
        return objectives
    
    def _run_fast_simulation(self):
        """
        Ultra-fast simulation using cached numpy arrays.
        Avoids all array conversions and uses vectorized operations.
        """
        from backend.services.simulation.simulation import SimulationMetrics
        
        # Save original capacities
        original_capacities = [lot.current_capacity for lot in self.base_city.parking_zones]
        
        # Reset capacities
        for lot in self.base_city.parking_zones:
            lot.current_capacity = 0
        
        # Get current lot state
        lot_fees = np.array([z.current_fee for z in self.base_city.parking_zones], dtype=np.float32)
        lot_occupancy = np.array([z.occupancy_rate() for z in self.base_city.parking_zones], dtype=np.float32)
        
        # Compute all driver decisions in one vectorized operation (THE FAST PART!)
        scores = self.simulation.decision_maker.parallel_engine.compute_driver_lot_scores(
            driver_positions=self.driver_positions_cache,
            driver_destinations=self.driver_destinations_cache,
            driver_max_fees=self.driver_max_fees_cache,
            lot_positions=self.lot_positions_cache,
            lot_fees=lot_fees,
            lot_occupancy=lot_occupancy,
            fee_weight=self.simulation.decision_maker.current_fee_weight,
            distance_to_lot_weight=self.simulation.decision_maker.distance_to_lot_weight,
            walking_distance_weight=self.simulation.decision_maker.walking_distance_weight,
            availability_weight=self.simulation.decision_maker.availability_weight
        )
        
        # Mask full lots
        lot_is_full = np.array([z.is_full() for z in self.base_city.parking_zones])
        scores[:, lot_is_full] = np.inf
        
        # Select best lot for each driver
        best_lot_indices = np.argmin(scores, axis=1)
        
        # Initialize metrics
        total_revenue = 0.0
        total_driver_cost = 0.0
        total_walking_distance = 0.0
        parked_count = 0
        rejected_count = 0
        lot_revenues = {lot.id: 0.0 for lot in self.base_city.parking_zones}
        
        # Apply decisions sequentially (capacity constraint)
        for driver_idx, lot_idx in enumerate(best_lot_indices):
            if scores[driver_idx, lot_idx] == np.inf:
                # No suitable lot
                rejected_count += 1
                total_driver_cost += self.simulation.rejection_penalty
            else:
                selected_lot = self.base_city.parking_zones[lot_idx]
                if not selected_lot.is_full():
                    # Park successfully
                    selected_lot.current_capacity += 1
                    driver = self.base_drivers[driver_idx]
                    
                    parking_cost = selected_lot.current_fee * driver.desired_parking_time / 60
                    walking_distance = selected_lot.distance_to_point(driver.destination)
                    
                    total_revenue += parking_cost
                    lot_revenues[selected_lot.id] += parking_cost
                    total_driver_cost += parking_cost
                    total_walking_distance += walking_distance
                    parked_count += 1
                else:
                    # Lot became full
                    rejected_count += 1
                    total_driver_cost += self.simulation.rejection_penalty
        
        # Build metrics
        metrics = self.simulation._build_metrics(
            self.base_city, self.base_drivers, total_revenue, total_driver_cost,
            total_walking_distance, parked_count, rejected_count, lot_revenues
        )
        
        # Restore capacities
        for lot, orig_capacity in zip(self.base_city.parking_zones, original_capacities):
            lot.current_capacity = orig_capacity
        
        return metrics
    def optimize(self,  city: City) -> List[PricingScenario]:
        """
        Run NSGA-3 optimization with optional driver-based simulation.

        Args:
            city: City object

        Returns:
            Optimization response with Pareto-optimal scenarios
        """
        # Initialize simulation environment if using simulation mode
        self._initialize_simulation_environment(city)

        # Call base class optimize method
        return super().optimize(city)