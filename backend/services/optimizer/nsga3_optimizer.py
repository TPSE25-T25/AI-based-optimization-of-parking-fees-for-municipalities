from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Dict
import numpy as np
import time
from pymoo.algorithms.moo.nsga3 import NSGA3  # Der Algorithmus selbst
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.termination import get_termination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.mutation.pm import PM

from backend.schemas.optimization_schema import OptimizationRequest, OptimizationResponse, PricingScenario, OptimizedZoneResult, OptimizationSettings, ParkingZoneInput

class NSGA3Optimizer(ABC):
    """
    Abstract base class for NSGA-III Parking Price Optimization.

    Provides the NSGA-III algorithm framework and utilities.
    Subclasses must implement _simulate_scenario() for evaluation.

    Subclasses:
    - NSGA3OptimizerElasticity: Elasticity-based evaluation
    - NSGA3OptimizerAgentBased: Agent-based simulation evaluation
    """

    def __init__(self, random_seed: int = 1):
        """
        Initialize the base optimizer.

        Args:
            random_seed: Seed for reproducibility
        """
        self.random_seed = random_seed

    def _convert_request_to_numpy(self, request: OptimizationRequest) -> dict:
        """
        Helper Method: Converts the complex Pydantic request object into flat Numpy arrays.
        """
        zones = request.zones

        data = {                                                                    #Dictionary to hold all extracted data

            "current_prices": np.array([float(z.price) for z in zones]),            # Current prices for all zones


            "min_fees": np.array([z.min_fee for z in zones]),                       # minimum fees for all zones
            "max_fees": np.array([z.max_fee for z in zones]),                       # maximum fees for all zones


            "capacities": np.array([z.maximum_capacity for z in zones]),            # capacities of all zones
            "elasticities": np.array([z.elasticity for z in zones]),                # elasticities of all zones
            "current_occupancy": np.array([z.current_capacity / z.maximum_capacity if z.maximum_capacity > 0 else 0.0 for z in zones]),    # current occupancy of all zones
            "short_term_share": np.array([z.short_term_share for z in zones]),       # short term share of all zones
            "target_occupancy": request.settings.target_occupancy                     # target occupancy from settings
        }
        return data

    @abstractmethod
    def _simulate_scenario(self, prices: np.ndarray, request: OptimizationRequest) -> Tuple[float, float, float, float]:
        """
        Evaluate a price vector and return objectives.

        This is the main evaluation method called by ParkingProblem._evaluate() during optimization.
        Must be implemented by subclasses.

        Args:
            prices: Price vector for all zones
            request: Optimization request with zones and settings

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        pass

    @abstractmethod
    def _get_detailed_results(self, prices: np.ndarray, data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a price vector.

        Called after optimization to build the final response with zone-level details.
        Must be implemented by subclasses.

        Args:
            prices: Price vector for all zones
            data: Dictionary with zone data (from _convert_request_to_numpy)

        Returns:
            Dictionary with keys:
                - "occupancy": np.ndarray of occupancy rates per zone
                - "revenue": np.ndarray of revenue per zone
        """
        pass


    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        # Record start time
        start_time = time.time()

        # Step 1: Extract zone data
        data = self._convert_request_to_numpy(request)

        # Number of decision variables = number of zones
        n_vars = len(request.zones)

        # Step 2: Set price bounds per zone
        xl = data["min_fees"]
        xu = data["max_fees"]

        """ The ParkingProblem class acts as an adapter... """
        class ParkingProblem(ElementwiseProblem):
            def __init__(self, optimizer_instance, req):
                # n_var = number of zones
                super().__init__(n_var=n_vars, n_obj=4, n_ieq_constr=0, xl=xl, xu=xu)
                self.optimizer = optimizer_instance
                self.req = req

            def _evaluate(self, x, out, *args, **kwargs):
                # x contains prices directly for each zone
                f1, f2, f3, f4 = self.optimizer._simulate_scenario(x, self.req)

                out["F"] = [-f1, f2, f3, f4]

        # create an instance of the problem
        problem = ParkingProblem(self, request)

        """"Algorithm Cofiguration (NSGA-III)"""
        # ... (Dieser Teil bleibt EXAKT gleich wie vorher) ...
        ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=8)
        pop_size = request.settings.population_size
        n_gen = request.settings.generations
        
        algorithm = NSGA3(
            pop_size=pop_size,
            ref_dirs=ref_dirs,
            n_offsprings= int(pop_size/2),
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=1.0/n_vars, eta=20),
            eliminate_duplicates=True
        )
        termination = get_termination("n_gen", n_gen) # stops after a fixed number of generations


        """ Execution of the Optimization Algorithm (NSGA-III)"""

        # -problem: Defines WHAT to optimize( variables, boundaries, simulation logic)
        # -algorithm: Defines HOW to optimize (the NSGA-III genetic algorithm with its operators)
        # -termination: Defines WHEN to stop (after a fixed number of generations here)
        # -seed: For reproducibility
        # -verbose: Print progress to console

        print(" Starting NSGA-III Execution ")
        res = minimize(problem, algorithm, termination, seed=self.random_seed, verbose=True)               # Run the optimization
        print(f" Optimization finished! Found {len(res.X)} solutions. ")

        # Prepare the final response with all scenarios found
        final_scenarios = []

        X = np.atleast_2d(res.X)
        F = np.atleast_2d(res.F)

        for i, (prices, objectives) in enumerate(zip(X, F)):

            # Get detailed results for this price vector
            detailed_results = self._get_detailed_results(prices, data)

            new_occupancy = detailed_results["occupancy"]
            revenue_vector = detailed_results["revenue"]

            # Build zone results for this scenario
            zone_results = []
            for j, zone in enumerate(request.zones):                            # Iterate through each zone
                zone_results.append(OptimizedZoneResult(                        # Build result object for each zone
                    zone_id=zone.id,
                    new_fee=round(prices[j], 2),
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

        # Calculate computation time
        computation_time = time.time() - start_time

        return OptimizationResponse(
            scenarios=final_scenarios,
            computation_time_seconds=round(computation_time, 2)
        )
    

    def select_best_solution_by_weights(self, response: OptimizationResponse, weights: dict) -> PricingScenario:
        """
        Selects the single best scenario from the Pareto Front based on user preferences.
        It normalizes all objective values to a 0-1 scale to ensure fair comparison
        between different units (Euros vs. Percentages).
        
        Args:
            response: The result from optimize() containing all Pareto scenarios.
            weights: A dictionary with user weights (0-100), e.g., {"revenue": 50, "occupancy": 50}
        """
        scenarios = response.scenarios
        if not scenarios: return None

        print(f"\n⚖️  Calculating best compromise for weights: {weights}")

        # ---------------------------------------------------------
        # 1. Prepare Data for Normalization (Min-Max Scaling)
        # ---------------------------------------------------------
        
        # Extract lists of all values to find the range (Min/Max) for each objective.
        revenues = [s.score_revenue for s in scenarios]
        gaps = [s.score_occupancy_gap for s in scenarios]
        drops = [s.score_demand_drop for s in scenarios]
        balances = [s.score_user_balance for s in scenarios]

        # Determine boundaries. 
        # This is needed to scale a value like "5000€" down to "0.8" relative to the others.
        min_rev, max_rev = min(revenues), max(revenues)
        min_gap, max_gap = min(gaps), max(gaps)
        min_drop, max_drop = min(drops), max(drops)
        min_bal, max_bal = min(balances), max(balances)

        best_score = -float('inf')
        best_scenario = None

        # ---------------------------------------------------------
        # 2. Score Each Scenario
        # ---------------------------------------------------------
        for s in scenarios:
            
            # --- A. Normalize Values (Scale 0.0 to 1.0) ---
            
            # Objective: MAXIMIZE Revenue
            # Formula: (Value - Min) / (Max - Min)
            # Result: 1.0 means this is the scenario with the highest revenue.
            norm_rev = (s.score_revenue - min_rev) / (max_rev - min_rev) if max_rev > min_rev else 1.0
            
            # Objective: MINIMIZE Gap
            # Formula: 1.0 - (Standard Normalization)
            # Result: We invert the scale because "Small Gap" is good. 1.0 means perfect target hit.
            norm_gap = 1.0 - ((s.score_occupancy_gap - min_gap) / (max_gap - min_gap)) if max_gap > min_gap else 1.0

            # Objective: MINIMIZE Demand Drop
            # Result: Invert scale. 1.0 means "No Drop" (Best case), 0.0 means "High Drop".
            norm_drop = 1.0 - ((s.score_demand_drop - min_drop) / (max_drop - min_drop)) if max_drop > min_drop else 1.0

            # Objective: MAXIMIZE Fairness (User Balance)
            # Result: 1.0 means "Very Fair", 0.0 means "Unfair".
            norm_bal = (s.score_user_balance - min_bal) / (max_bal - min_bal) if max_bal > min_bal else 1.0

            # --- B. Apply User Weights ---
            # Multiply normalized scores with user preferences (e.g., 0.5 for 50%).
            # .get("key", 0) ensures that if a weight is missing, it counts as 0%.
            score = (weights.get("revenue", 0) * norm_rev) + \
                    (weights.get("occupancy", 0) * norm_gap) + \
                    (weights.get("drop", 0) * norm_drop) + \
                    (weights.get("fairness", 0) * norm_bal)
            
            # Track the winner
            if score > best_score:
                best_score = score
                best_scenario = s

        print(f"🏆 Winner: Scenario #{best_scenario.scenario_id} (Weighted Score: {best_score:.2f})")
        print(f"   Details: Revenue={best_scenario.score_revenue}€ | Gap={best_scenario.score_occupancy_gap*100:.1f}%")
        
        return best_scenario
