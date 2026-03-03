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
        # (n_drivers, n_lots) walking distances — computed once, reused every evaluation
        self.walking_distances_cache: Optional[np.ndarray] = None
        # (n_drivers,) desired parking times — avoids Python object access in hot loop
        self.driver_parking_times_cache: Optional[np.ndarray] = None
        # (n_lots,) maximum capacities — avoids Python object access in hot loop
        self.zone_max_capacities_cache: Optional[np.ndarray] = None

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

        # Pre-compute walking distances: (n_drivers, n_lots) matrix.
        # Driver destinations never change during optimization, so this is computed once.
        driver_dest = self.driver_destinations_cache[:, np.newaxis, :]  # (n_drivers, 1, 2)
        lot_pos = self.lot_positions_cache[np.newaxis, :, :]             # (1, n_lots, 2)
        self.walking_distances_cache = np.sqrt(
            np.sum((driver_dest - lot_pos) ** 2, axis=2)
        ).astype(np.float32)  # (n_drivers, n_lots)

        # Pre-compute driver desired parking times (avoids Python object access in hot loop)
        self.driver_parking_times_cache = np.array(
            [d.desired_parking_time for d in self.base_drivers], dtype=np.float32
        )

        # Pre-compute zone maximum capacities (avoids Python object access in hot loop)
        self.zone_max_capacities_cache = np.array(
            [z.maximum_capacity for z in self.base_city.parking_zones], dtype=np.int32
        )
        
        # Get backend info
        backend_info = self.simulation.decision_maker.parallel_engine.get_backend_info()

        print(f"\nSimulation Environment Initialized:")
        print(f"  City: {self.base_city.name}")
        print(f"  Parking Lots: {len(self.base_city.parking_zones)}")
        print(f"  Total Capacity: {self.base_city.total_parking_capacity}")
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
        # Revenue is scaled to daily totals (one turnover cycle × operating hours per day)
        occupancy = np.array([metrics.lot_occupancy_rates.get(id, 0.0) for id in self.zone_ids])
        revenue = np.array([float(metrics.lot_revenues.get(id, 0.0)) for id in self.zone_ids]) * self.operating_hours_per_day

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
        Ultra-fast simulation using pre-cached numpy arrays.
        Key optimisations vs. the naïve loop:
        - Walking distances pre-computed once during initialisation (n_drivers × n_lots matrix).
        - Driver parking times pre-cached as a numpy array.
        - Capacity tracking uses a numpy int-array counter instead of Python object calls.
        - Revenue and walking distance totals computed with vectorised numpy ops after the
          sequential capacity-enforcement pass (the only part that cannot be fully vectorised).
        """
        from backend.services.simulation.simulation import SimulationMetrics

        n_lots = len(self.base_city.parking_zones)
        n_drivers = len(self.base_drivers)

        # Save and reset capacities
        original_capacities = [lot.current_capacity for lot in self.base_city.parking_zones]
        for lot in self.base_city.parking_zones:
            lot.current_capacity = 0

        # Build fee array for this evaluation (fees change each call — cannot be cached)
        lot_fees = np.array([z.current_fee for z in self.base_city.parking_zones], dtype=np.float32)

        # Occupancy is 0 for all lots right after reset — skip the list comprehension
        lot_occupancy = np.zeros(n_lots, dtype=np.float32)

        # Compute all driver-lot scores in one vectorised call (CUDA / CPU-parallel / CPU-vec)
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
        # No lots are full at reset — skip the full-lot masking step

        # Best lot per driver
        best_lot_indices = np.argmin(scores, axis=1)           # (n_drivers,)
        best_scores = scores[np.arange(n_drivers), best_lot_indices]  # (n_drivers,)

        # --- Sequential pass: enforce capacity constraints ---
        # Uses numpy arrays instead of Python object attribute access for speed.
        lot_capacity_counter = np.zeros(n_lots, dtype=np.int32)
        parked_driver_idx: list[int] = []
        parked_lot_idx: list[int] = []
        rejected_count = 0
        total_driver_cost = 0.0

        for driver_idx in range(n_drivers):
            lot_idx = int(best_lot_indices[driver_idx])
            if best_scores[driver_idx] == np.inf:
                # No affordable / reachable lot
                rejected_count += 1
                total_driver_cost += self.simulation.rejection_penalty
            elif lot_capacity_counter[lot_idx] < self.zone_max_capacities_cache[lot_idx]:
                lot_capacity_counter[lot_idx] += 1
                parked_driver_idx.append(driver_idx)
                parked_lot_idx.append(lot_idx)
            else:
                # Lot filled up during this pass
                rejected_count += 1
                total_driver_cost += self.simulation.rejection_penalty

        # --- Vectorised post-pass: compute revenue and walking distances at once ---
        total_revenue = 0.0
        total_walking_distance = 0.0
        lot_revenues = {zone.id: 0.0 for zone in self.base_city.parking_zones}
        parked_count = len(parked_driver_idx)

        if parked_count > 0:
            pd_arr = np.array(parked_driver_idx, dtype=np.int32)
            pl_arr = np.array(parked_lot_idx, dtype=np.int32)

            # parking_cost = fee × desired_time_hours  (one entry per parked driver)
            parking_costs = lot_fees[pl_arr] * self.driver_parking_times_cache[pd_arr] / 60.0

            # Walking distances from pre-computed (n_drivers, n_lots) matrix
            walking_dists = self.walking_distances_cache[pd_arr, pl_arr]

            total_revenue = float(np.sum(parking_costs)) * self.operating_hours_per_day
            total_walking_distance = float(np.sum(walking_dists))
            total_driver_cost += float(np.sum(parking_costs))  # unscaled, like the original

            # Per-lot revenues — np.bincount is O(n_drivers), far faster than a dict loop
            lot_rev_arr = (
                np.bincount(pl_arr, weights=parking_costs, minlength=n_lots)
                * self.operating_hours_per_day
            )
            lot_revenues = {
                zone.id: float(lot_rev_arr[i])
                for i, zone in enumerate(self.base_city.parking_zones)
            }

        # Apply final per-lot capacities so _build_metrics sees correct occupancy rates
        for i, lot in enumerate(self.base_city.parking_zones):
            lot.current_capacity = int(lot_capacity_counter[i])

        metrics = self.simulation._build_metrics(
            self.base_city, self.base_drivers, total_revenue, total_driver_cost,
            total_walking_distance, parked_count, rejected_count, lot_revenues
        )

        # Restore original capacities
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