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

        # Store zone IDs for result extraction
        self.zone_ids = [zone.id for zone in self.base_city.parking_zones]

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
        n_par = self._get_parallelization()
        print(f"  NSGA-III eval  : {'parallel threads=' + str(n_par) if n_par else 'serial'}")

    def _get_parallelization(self):
        """
        Enable parallel population evaluation for the Agent-based optimizer.

        ``_run_fast_simulation`` is **fully stateless** (takes fees as a parameter
        and never mutates shared city state), so concurrent thread invocations are
        safe.  We use threading rather than multiprocessing to share the pre-cached
        numpy arrays and benefit from CUDA / NumPy releasing the GIL.

        Returns:
            Number of worker threads (≥2) when joblib is available, else None.
        """
        try:
            from joblib import Parallel  # noqa: F401  (just probing availability)
            import os
            # Use physical core count (not hyper-threads) capped at 8 to avoid
            # excessive thread contention on the sequential capacity loop.
            n_workers = min(os.cpu_count() or 4, 8)
            return n_workers if n_workers > 1 else None
        except ImportError:
            return None

    def _get_detailed_results(self, current_fees: np.ndarray, _data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a current_fee vector.

        Args:
            current_fees: current_fee vector for all zones
            _data: Dictionary with zone data (unused – agent-based uses cached state)

        Returns:
            Dictionary with occupancy and revenue arrays
        """
        # _run_fast_simulation is now stateless: pass fees directly, no city mutation
        metrics = self._run_fast_simulation(current_fees.astype(np.float32))

        occupancy = np.array([metrics.lot_occupancy_rates.get(id, 0.0) for id in self.zone_ids])
        # Revenue was already scaled inside _run_fast_simulation
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

        Fully stateless: ``_run_fast_simulation`` now accepts fees as a parameter
        and never touches shared city state, making this safe to call from multiple
        threads simultaneously (required for NSGA-III parallel population evaluation).

        Args:
            current_fees: current_fee vector for all zones
            city: City object (unused – cached self.base_city is used internally)

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        metrics = self._run_fast_simulation(current_fees.astype(np.float32))

        objectives = OptimizationAdapter.extract_objectives_from_metrics(
            metrics=metrics,
            target_occupancy=self.target_occupancy
        )

        return objectives
    
    def _run_fast_simulation(self, lot_fees: np.ndarray):
        """
        **Stateless** ultra-fast simulation using pre-cached numpy arrays.

        Thread-safety
        -------------
        This method accepts ``lot_fees`` as an explicit parameter and **never
        mutates any shared state** (no writes to ``self.base_city`` fees or
        capacities).  Occupancy is tracked in a local ``lot_capacity_counter``
        array and converted to rates inline, so multiple threads can run this
        method concurrently without any locking.

        Key optimisations
        -----------------
        - Walking distances pre-computed once during initialisation
          (n_drivers × n_lots matrix, immutable).
        - Driver parking times pre-cached as a numpy array.
        - Capacity tracking uses a local numpy int-array counter.
        - Revenue + walking distance totals computed with vectorised numpy ops
          after the sequential capacity-enforcement pass.
        - SimulationMetrics built directly from local arrays (no city writes).

        Args:
            lot_fees: (n_lots,) float32 array of fees for this evaluation.

        Returns:
            SimulationMetrics populated with all relevant metrics.
        """
        from backend.services.simulation.simulation import SimulationMetrics

        n_lots = len(self.base_city.parking_zones)
        n_drivers = len(self.base_drivers)

        # Occupancy is 0 at the start of each fresh evaluation
        lot_occupancy = np.zeros(n_lots, dtype=np.float32)

        # ── Compute all driver-lot scores in one vectorised call ──────────────
        # Uses CUDA / CPU-parallel / CPU-vectorised depending on available backend.
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
        # No lots are full at the start — skip the full-lot masking step

        # Best lot per driver
        best_lot_indices = np.argmin(scores, axis=1)                            # (n_drivers,)
        best_scores = scores[np.arange(n_drivers), best_lot_indices]            # (n_drivers,)

        # ── Sequential pass: enforce capacity constraints ─────────────────────
        # This is the only part that cannot be fully vectorised (order-dependent).
        lot_capacity_counter = np.zeros(n_lots, dtype=np.int32)                 # LOCAL – no city writes
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

        # ── Vectorised post-pass: revenue and walking distances ───────────────
        total_revenue = 0.0
        total_walking_distance = 0.0
        lot_revenues_map = {zone.id: 0.0 for zone in self.base_city.parking_zones}
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
            total_driver_cost += float(np.sum(parking_costs))

            # Per-lot revenues — np.bincount is O(n_drivers), far faster than a dict loop
            lot_rev_arr = (
                np.bincount(pl_arr, weights=parking_costs, minlength=n_lots)
                * self.operating_hours_per_day
            )
            lot_revenues_map = {
                zone.id: float(lot_rev_arr[i])
                for i, zone in enumerate(self.base_city.parking_zones)
            }

        # ── Compute occupancy from local counter — NO city writes ─────────────
        occupancy_rates = lot_capacity_counter.astype(np.float64) / np.maximum(
            self.zone_max_capacities_cache, 1
        )
        lot_occupancy_rates_map = {
            zone.id: float(occupancy_rates[i])
            for i, zone in enumerate(self.base_city.parking_zones)
        }
        overall_occ = float(np.mean(occupancy_rates))
        total_drivers = n_drivers

        # ── Build and return SimulationMetrics directly ───────────────────────
        metrics = SimulationMetrics(
            total_revenue=total_revenue,
            average_revenue_per_lot=total_revenue / n_lots if n_lots > 0 else 0.0,
            total_parked=parked_count,
            total_rejected=rejected_count,
            overall_occupancy_rate=overall_occ,
            occupancy_variance=float(np.var(occupancy_rates)) if n_lots > 1 else 0.0,
            occupancy_std_dev=float(np.std(occupancy_rates)) if n_lots > 1 else 0.0,
            average_driver_cost=total_driver_cost / total_drivers if total_drivers > 0 else 0.0,
            average_walking_distance=total_walking_distance / parked_count if parked_count > 0 else 0.0,
            average_current_fee_paid=total_revenue / parked_count if parked_count > 0 else 0.0,
            utilization_rate=overall_occ,
            rejection_rate=rejected_count / total_drivers if total_drivers > 0 else 0.0,
            lot_occupancy_rates=lot_occupancy_rates_map,
            lot_revenues=lot_revenues_map,
        )

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