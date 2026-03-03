from abc import ABC, abstractmethod
from dataclasses import Field
from typing import List, Tuple, Optional
import os
import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.problem import Problem          # batch interface: _evaluate receives full population matrix
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.termination import get_termination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.mutation.pm import PM

from backend.services.models.city import City, ParkingZone
from backend.services.optimizer.schemas.optimization_schema import PricingScenario, OptimizedZoneResult
from backend.services.settings.optimizations_settings import OptimizationSettings
from backend.services.optimizer.solution_selector import SolutionSelector

# ---------------------------------------------------------------------------
# Module-level parallel / CUDA availability detection (mirrors parallel_engine)
# ---------------------------------------------------------------------------
try:
    from numba import cuda as _numba_cuda
    _CUDA_AVAILABLE: bool = _numba_cuda.is_available()
except Exception:
    _CUDA_AVAILABLE = False

try:
    from joblib import Parallel as _Parallel, delayed as _delayed
    _JOBLIB_AVAILABLE = True
except ImportError:
    _JOBLIB_AVAILABLE = False


class NSGA3Optimizer(ABC):
    """ 
    Abstract base class for NSGA-III Parking current_fee Optimization.

    Provides the NSGA-III algorithm framework and utilities.
    Subclasses must implement _simulate_scenario() for evaluation.

    Subclasses:
    - NSGA3OptimizerElasticity: Elasticity-based evaluation
    - NSGA3OptimizerAgentBased: Agent-based simulation evaluation
    """

    def __init__(self, optimizer_settings: OptimizationSettings):
        """
        Initialize the base optimizer.

        Args:
            optimizer_settings: Configuration for the optimization process (population size, generations, etc.)
        """
        self.random_seed = optimizer_settings.random_seed
        self.population_size = optimizer_settings.population_size
        self.generations = optimizer_settings.generations
        self.target_occupancy = optimizer_settings.target_occupancy
        self.min_fee = optimizer_settings.min_fee
        self.max_fee = optimizer_settings.max_fee
        self.fee_increment = optimizer_settings.fee_increment
        self.operating_hours_per_day = optimizer_settings.operating_hours_per_day

    def _convert_zones_to_numpy(self, zones: List[ParkingZone]) -> dict:
        """
        Helper Method: Converts the complex Pydantic request object into flat Numpy arrays.
        """
        data = {                                                                    #Dictionary to hold all extracted data

            "current_current_fees": np.array([float(z.current_fee) for z in zones]),            # Current current_fees for all zones


            "min_fees": np.array([z.min_fee for z in zones]),                       # minimum fees for all zones
            "max_fees": np.array([z.max_fee for z in zones]),                       # maximum fees for all zones


            "capacities": np.array([z.maximum_capacity for z in zones]),            # capacities of all zones
            "elasticities": np.array([z.elasticity for z in zones]),                # elasticities of all zones
            "current_occupancy": np.array([z.current_capacity / z.maximum_capacity if z.maximum_capacity > 0 else 0.0 for z in zones]),    # current occupancy of all zones
            "short_term_share": np.array([z.short_term_share for z in zones]),       # short term share of all zones
            "target_occupancy": self.target_occupancy,                    # target occupancy from settings
            "operating_hours_per_day": self.operating_hours_per_day       # daily operating hours for revenue scaling
        }
        return data

    @abstractmethod
    def _simulate_scenario(self, current_fees: np.ndarray, zones: List[ParkingZone]) -> Tuple[float, float, float, float]:
        """
        Evaluate a current_fee vector and return objectives.

        This is the main evaluation method called by ParkingProblem._evaluate() during optimization.
        Must be implemented by subclasses.

        Args:
            current_fees: current_fee vector for all zones
            zones: List of ParkingZone objects representing the zones

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        pass

    @abstractmethod
    def _get_detailed_results(self, current_fees: np.ndarray, data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a current_fee vector.

        Called after optimization to build the final response with zone-level details.
        Must be implemented by subclasses.

        Args:
            current_fees: current_fee vector for all zones
            data: Dictionary with zone data (from _convert_request_to_numpy)

        Returns:
            Dictionary with keys:
                - "occupancy": np.ndarray of occupancy rates per zone
                - "revenue": np.ndarray of revenue per zone
        """
        pass


    def _get_parallelization(self) -> Optional[int]:
        """
        Return the number of parallel worker threads to use when evaluating the
        population during optimization, or ``None`` for serial evaluation.

        The default implementation (base class) is always serial.  Subclasses
        override this to opt-in to parallel evaluation when their
        ``_simulate_scenario`` implementation is thread-safe.

        Returns:
            Number of worker threads, or None for serial evaluation.
        """
        return None

    def optimize(self,  city: City) -> List[PricingScenario]:
        # Step 1: Extract zone data
        zones = city.parking_zones
        data = self._convert_zones_to_numpy(zones)

        # Step 2: Determine decision variable space (per-cluster or per-zone)
        has_clusters = all(z.cluster_id is not None for z in zones)

        if has_clusters:
            unique_clusters = sorted(set(z.cluster_id for z in zones))
            n_clusters = len(unique_clusters)
            cluster_to_idx = {cid: i for i, cid in enumerate(unique_clusters)}
            zone_cluster_indices = np.array([cluster_to_idx[z.cluster_id] for z in zones])

            # Per-cluster bounds: use the most restrictive valid range within each cluster
            xl = np.array([
                max(z.min_fee for z in zones if cluster_to_idx[z.cluster_id] == i)
                for i in range(n_clusters)
            ])
            xu = np.array([
                min(z.max_fee for z in zones if cluster_to_idx[z.cluster_id] == i)
                for i in range(n_clusters)
            ])
            # Apply global optimizer min/max fee as hard constraints
            xl = np.maximum(xl, self.min_fee)
            xu = np.minimum(xu, self.max_fee)
            # Ensure xu >= xl in case of conflicting zone bounds within a cluster
            xu = np.maximum(xu, xl)
            n_vars = n_clusters
        else:
            # Fallback: original per-zone behavior (backward compatible)
            n_vars = len(zones)
            # Apply global optimizer min/max fee as hard constraints on top of zone-level bounds
            xl = np.maximum(data["min_fees"], self.min_fee)
            xu = np.minimum(data["max_fees"], self.max_fee)
            # Ensure xu >= xl in case of conflicting bounds
            xu = np.maximum(xu, xl)
            zone_cluster_indices = None

        # Keep data bounds in sync with the effective bounds used by the optimizer
        data["min_fees"] = xl[zone_cluster_indices] if zone_cluster_indices is not None else xl
        data["max_fees"] = xu[zone_cluster_indices] if zone_cluster_indices is not None else xu
                
        def round_to_increment(fees, increment, min_fees, max_fees):
            """Round fees to nearest increment and ensure within bounds."""
            if increment <= 0:
                return fees
            rounded = np.round(fees / increment) * increment
            return np.clip(rounded, min_fees, max_fees)

        """ The ParkingProblem class acts as an adapter... """
        n_parallel = self._get_parallelization()

        class ParkingProblem(Problem):
            """
            pymoo Problem adapter.

            Inherits from ``Problem`` (not ``ElementwiseProblem``) so that
            ``_evaluate`` receives the **entire population matrix** in a single
            call (shape ``[pop_size, n_vars]``).  This allows us to dispatch
            evaluations via a thread-pool when ``n_parallel > 1``.

            Thread-safety contract
            ----------------------
            * Elasticity optimizer  →  ``n_parallel=None`` (serial).  Each
              ``_simulate_scenario`` call is pure NumPy but evaluations are
              fast enough that thread overhead would dominate.
            * Agent-based optimizer →  ``n_parallel=n_workers``.
              ``_run_fast_simulation`` has been made **fully stateless**
              (no shared-city mutation), so concurrent threads are safe.
            """

            def __init__(self_, optimizer_instance):
                super().__init__(n_var=n_vars, n_obj=4, n_ieq_constr=0, xl=xl, xu=xu)
                self_.optimizer = optimizer_instance

            def _eval_single(self_, x: np.ndarray) -> np.ndarray:
                """Evaluate a single solution vector → objective array [-f1, f2, f3, f4]."""
                x_rounded = round_to_increment(x, self_.optimizer.fee_increment, xl, xu)
                zone_fees = x_rounded[zone_cluster_indices] if zone_cluster_indices is not None else x_rounded
                f1, f2, f3, f4 = self_.optimizer._simulate_scenario(zone_fees, city.parking_zones)
                return np.array([-f1, f2, f3, f4])

            def _evaluate(self_, X, out, *args, **kwargs):
                """Evaluate the full population X (shape: [pop_size, n_vars])."""
                n_solutions = X.shape[0]

                if n_parallel is not None and n_parallel > 1 and _JOBLIB_AVAILABLE:
                    # Parallel evaluation via a thread-pool.
                    # NumPy/CUDA operations release the GIL, so threads run truly
                    # concurrently for the heavy-lifting part of each simulation.
                    F_rows = _Parallel(n_jobs=n_parallel, backend="threading")(
                        _delayed(self_._eval_single)(X[i]) for i in range(n_solutions)
                    )
                else:
                    F_rows = [self_._eval_single(X[i]) for i in range(n_solutions)]

                out["F"] = np.array(F_rows)

        # create an instance of the problem
        problem = ParkingProblem(self)

        """"Algorithm Cofiguration (NSGA-III)"""
        # ... (Dieser Teil bleibt EXAKT gleich wie vorher) ...
        ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=8)

        algorithm = NSGA3(
            pop_size=self.population_size,
            ref_dirs=ref_dirs,
            n_offsprings= int(self.population_size/2),
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=1.0/n_vars, eta=20),
            eliminate_duplicates=True
        )
        termination = get_termination("n_gen", self.generations) # stops after a fixed number of generations


        """ Execution of the Optimization Algorithm (NSGA-III)"""

        # -problem: Defines WHAT to optimize( variables, boundaries, simulation logic)
        # -algorithm: Defines HOW to optimize (the NSGA-III genetic algorithm with its operators)
        # -termination: Defines WHEN to stop (after a fixed number of generations here)
        # -seed: For reproducibility
        # -verbose: Print progress to console

        print(" Starting NSGA-III Execution ")
        _par_info = (
            f"parallel threads={n_parallel}" if n_parallel and n_parallel > 1 and _JOBLIB_AVAILABLE
            else "serial (no threading)"
        )
        print(f"  CUDA available : {_CUDA_AVAILABLE}")
        print(f"  Eval strategy  : {_par_info}")
        res = minimize(problem, algorithm, termination, seed=self.random_seed, verbose=True)               # Run the optimization
        print(f" Optimization finished! Found {len(res.X)} solutions. ")

        # Prepare the final response with all scenarios found
        final_scenarios = []

        X = np.atleast_2d(res.X)
        F = np.atleast_2d(res.F)

        for i, (current_fees, objectives) in enumerate(zip(X, F)):

            # Round fees to discrete increments for final results
            current_fees_rounded = round_to_increment(current_fees, self.fee_increment, xl, xu)

            # Expand cluster-level fees to zone-level fees if clustering is active
            if zone_cluster_indices is not None:
                zone_fees_rounded = current_fees_rounded[zone_cluster_indices]
            else:
                zone_fees_rounded = current_fees_rounded

            # Get detailed results for this current_fee vector
            detailed_results = self._get_detailed_results(zone_fees_rounded, data)

            new_occupancy = detailed_results["occupancy"]
            revenue_vector = detailed_results["revenue"]

            # Build zone results for this scenario
            zone_results = []
            for j, zone in enumerate(city.parking_zones):                            # Iterate through each zone
                zone_results.append(OptimizedZoneResult(                        # Build result object for each zone
                    id=zone.id,
                    new_fee=round(float(zone_fees_rounded[j]), 2),
                    predicted_occupancy=float(new_occupancy[j]),
                    predicted_revenue=round(revenue_vector[j], 2)
                ))

            # Build the complete scenario
            scenario = PricingScenario(
                scenario_id=i + 1,
                zones=zone_results,
                score_revenue=round(objectives[0] * -1, 2),
                score_occupancy_gap=round(objectives[1], 4),
                score_demand_drop=round(objectives[2], 4),
                score_user_balance=round(1.0 -objectives[3], 4)
            )
            final_scenarios.append(scenario)

        return final_scenarios
    

    def select_best_solution_by_weights(self, scenarios: List[PricingScenario], weights: dict) -> PricingScenario:
        """
        Selects the best scenario from the Pareto Front based on user preferences.
        Delegates to SolutionSelector service.
        
        Args:
            scenarios: The result from optimize() containing all Pareto scenarios.
            weights: A dictionary with user weights (0-100), e.g., {"revenue": 50, "occupancy": 50}
            
        Returns:
            The scenario with the highest weighted score
        """
        return SolutionSelector.select_best_by_weights(scenarios, weights)
