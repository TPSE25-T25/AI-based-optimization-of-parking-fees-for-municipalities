from typing import Any, List, Tuple, Dict
import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3  # Der Algorithmus selbst
from pymoo.core.problem import ElementwiseProblem 
from pymoo.optimize import minimize 
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.termination import get_termination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.mutation.pm import PM

from schemas.optimization import OptimizationRequest, OptimizationResponse, PricingScenario, OptimizedZoneResult, OptimizationSettings, ParkingZoneInput

class NSGA3Optimizer:
    """
    Core Service for Parking Price Optimization.
    
    Responsibilities:
    1. Receives the optimization request from the API/Frontend (optimize).
    2. Evaluates how 'good' a specific price set is (_simulate_scenario).
    3. Executes the actual NSGA-III genetic algorithm (to be implemented).
    """

    def __init__(self):
        # Constructor. Currently empty.
        # In the future, we could load configuration files or ML models here.
        pass

    def _convert_request_to_numpy(self, request: OptimizationRequest) -> dict:
        """
        Helper Method: Converts the complex Pydantic request object into flat Numpy arrays.
        """
        zones = request.zones                                                       # List of all zones to be optimized
        
        data = {                                                                    #Dictionary to hold all extracted data  
            
            "current_prices": np.array([z.current_fee for z in zones]),             # Current prices for all zones 
            
            
            "min_fees": np.array([z.min_fee for z in zones]),                       # minimum fees for all zones
            "max_fees": np.array([z.max_fee for z in zones]),                       # maximum fees for all zones
            
            
            "capacities": np.array([z.capacity for z in zones]),                    # capacities of all zones
            "elasticities": np.array([z.elasticity for z in zones]),                # elasticities of all zones
            "current_occupancy": np.array([z.current_occupancy for z in zones]),    # current occupancy of all zones
            "short_term_share": np.array([z.short_term_share for z in zones]),       # short term share of all zones
            "target_occupancy": request.settings.target_occupancy                     # target occupancy from settings
        }
        
        return data


    def _calculate_physics(self, prices: np.ndarray, data: dict) -> dict:
        """
        Central Physics Engine.
        Simulates user behavior based on price elasticity, loss aversion, and user groups.
        Uses NumPy vectorization for high-performance batch processing.
        """
        
        # 1. Calculate Price Delta
        # Calculate percentage change relative to current price.
        # We add 1e-6 (epsilon) to current_prices to prevent "Division by Zero" errors.
        price_change_pct = (prices - data["current_prices"]) / (data["current_prices"] + 1e-6)
        
        # ---------------------------------------------------------
        # Behavioral Economics Logic (Asymmetric Elasticity)
        # ---------------------------------------------------------
        
        # A) Loss Aversion:
        # If price increases (>0), users react 20% more strongly (factor 1.2).
        # If price drops, the reaction is standard/dampened (factor 0.8).
        sensitivity_factor = np.where(price_change_pct > 0, 1.2, 0.8)
        
        # B) User Group Split:
        # Short-term users (Shoppers) react fully to price changes.
        short_term_impact = data["elasticities"] * price_change_pct * sensitivity_factor
        
        # Long-term users (Commuters) are less sensitive (50% of elasticity) due to necessity.
        long_term_impact  = (data["elasticities"] * 0.5) * price_change_pct * sensitivity_factor
        
        # C) Weighted Average Demand Change:
        # Combine both groups based on the specific 'short_term_share' of each zone.
        share_short = data["short_term_share"]
        total_demand_change = (short_term_impact * share_short) + (long_term_impact * (1.0 - share_short))
        
        # ---------------------------------------------------------
        # Physical Constraints & Results
        # ---------------------------------------------------------
        
        # Calculate new occupancy rate based on demand change.
        # np.clip enforces hard physical limits:
        # - Min: 0.05 (5% "hard core" demand that never leaves)
        # - Max: 1.00 (100% capacity limit, parkings cannot be overfull)
        new_occupancy = np.clip(data["current_occupancy"] * (1 + total_demand_change), 0.05, 1.0)
        
        # Calculate absolute Revenue per zone (New Price * Capacity * New Occupancy)
        revenue_vector = prices * (data["capacities"] * new_occupancy)

        # ---------------------------------------------------------
        # Calculate Optimization Objectives (KPIs)
        # ---------------------------------------------------------
        
        # Objective 1: Maximize Total Revenue (Sum of all zones)
        f1_revenue = np.sum(revenue_vector)
        
        # Objective 2: Minimize Occupancy Gap (Deviation from target, e.g., 85%)
        # We use np.abs() because being too empty is as bad as being too full.
        gap_vector = np.abs(new_occupancy - data["target_occupancy"])
        f2_gap = np.mean(gap_vector)

        # Objective 3: Minimize Demand Drop (Traffic reduction)
        # We only count negative changes (losses). np.minimum(0, ...) filters out gains.
        # Multiplied by -1 to make it a positive value for minimization logic.
        loss_vector = np.minimum(0, total_demand_change)
        f3_drop = np.mean(loss_vector * -1)

        # Objective 4: Maximize Fairness / Minimize Price Shock
        # We focus on price increases only (np.maximum(0, ...)).
        # Weighted by short_term_share since tourists/shoppers feel price hikes the most.
        impact_vector = np.maximum(0, price_change_pct) * data["short_term_share"]
        f4_fairness = np.mean(impact_vector)

        # Return results packaged in a dictionary
        return {
            "objectives": [f1_revenue, f2_gap, f3_drop, f4_fairness], 
            "occupancy": new_occupancy,       
            "revenue": revenue_vector,        
            "demand_change": total_demand_change
        }
        
        
        

    def _simulate_scenario(self, prices: np.ndarray, request: OptimizationRequest) -> Tuple[float, float, float, float]:
        """
        Internal Evaluation Wrapper.
        Acts as a bridge between the Genetic Algorithm (pymoo) and the Physics Engine.
        It reduces the complex simulation results down to the 4 specific scores (objectives) required by NSGA-III.
        """
        
        # 1. Data Preparation
        # Convert the hierarchical Pydantic object into flat, high-performance NumPy arrays.
        data = self._convert_request_to_numpy(request)      
        
        # 2. Physics Simulation
        # Run the central calculation logic. 
        # We pass the proposed 'prices' and the static 'data'.
        results = self._calculate_physics(prices, data)
        
        # 3. Objective Extraction
        # The physics engine returns detailed data (including occupancy per zone), 
        # but the optimizer ONLY needs the 4 objective scores to grade this solution.
        objs = results["objectives"]
        
        # 4. Return
        # Unpack and return the objectives as a strict tuple of floats.
        # Order: (Revenue, Occupancy Gap, Demand Drop, User Fairness)
        return objs[0], objs[1], objs[2], objs[3]


    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:

        # Define the search space: xl (Lower Bound) and xu (Upper Bound) for each zone.
        # The algorithm is forced to find prices strictly between min_fee and max_fee.
        xl = np.array([z.min_fee for z in request.zones])                       
        xu = np.array([z.max_fee for z in request.zones])

        # Number of decision variables (one price per zone)
        n_vars = len(request.zones) 

        """ The ParkingProblem class acts as an adapter (or bridge). It translates the language of mathematics (pymoo library) 
        into the language of our business logic (parking fees and revenue). 
        It encapsulates our constraints, boundaries, and the simulation function into a standardized format that the algorithm can understand and execute"""
        class ParkingProblem(ElementwiseProblem):
            def __init__(self, optimizer_instance, req):
                
                # Configurate the Pyymoo base class (ElementwiseProblem)
                # We pass our specific parameters (n_var, n_obj, xl, xu) to the parent constructor -> allows pymoo to understand our problem setup
                super().__init__(n_var=n_vars, n_obj=4, n_ieq_constr=0, xl=xl, xu=xu)
                
                # Store references to the optimizer instance and request for later use
                self.optimizer = optimizer_instance
                self.req = req

            def _evaluate(self, x: np.ndarray, out: Dict[str, Any], *args, **kwargs):

                # Evaluate a single solution 'x' (a set of prices for all zones)
                # Calls the optimizer's simulation function to get objective values
                f1, f2, f3, f4 = self.optimizer._simulate_scenario(x, self.req)
                
                # Store the results in the output dictionary; note that f1(Revenue) is negated because pymoo minimizes by default
                out["F"] = [-f1, f2, f3, f4]

        # create an instance of the problem
        problem = ParkingProblem(self, request)


        """"Algorithm Cofiguration (NSGA-III)"""
        
        # Create reference directions for 4 objectives
            # das-dennis method generates well-distributed reference points in the objective space
            # n_partitions controls the density of these points
            # More partitions = more reference points = potentially better diversity in solutions
        ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=8)               

        pop_size = request.settings.population_size
        n_gen = request.settings.generations

        # Configure the NSGA-III algorithm with operators and parameters
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
        res = minimize(problem, algorithm, termination, seed=1, verbose=True)               # Run the optimization
        print(f" Optimization finished! Found {len(res.X)} solutions. ")

       

        # Prepare the final response with all scenarios found
        final_scenarios = []

        X = np.atleast_2d(res.X)
        F = np.atleast_2d(res.F)

        # go through all solutions found by NSGA-III; (i, (prices, objectives))
        for i, (prices, objectives) in enumerate(zip(X, F)):
            
            
            # convert request data to numpy arrays for simulation
            data = self._convert_request_to_numpy(request)
            
            # run physics calculation to get detailed results for this price set
            simulation_results = self._calculate_physics(prices, data)

            # Extract the necessary arrays from the returned dictionary using their keys
            new_occupancy = simulation_results["occupancy"]
            revenue_vector = simulation_results["revenue"]
            


            # Build zone results for this scenario
            zone_results = []
            for j, zone in enumerate(request.zones):                            # Iterate through each zone
                zone_results.append(OptimizedZoneResult(                        # Build result object for each zone
                    zone_id=zone.zone_id,
                    new_fee=round(prices[j], 2),
                    predicted_occupancy=float(new_occupancy[j]),
                    predicted_revenue=round(revenue_vector[j], 2)
                ))

            # Build the complete scenario
            scenario = PricingScenario(                                         # Build scenario object
                scenario_id=i + 1,
                zones=zone_results,
                score_revenue=round(objectives[0] * -1, 2), # Negierung aufheben!
                score_occupancy_gap=round(objectives[1], 4),
                score_demand_drop=round(objectives[2], 4),
                score_user_balance=round(1.0 -objectives[3], 4)
            )
            final_scenarios.append(scenario)                                    # Add scenario to the final list

        return OptimizationResponse(scenarios=final_scenarios)                  # Return all scenarios as the final response
    

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
