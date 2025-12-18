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
        Central calculation engine. 
        Computes physical changes (occupancy, revenue) AND objective scores.
        """
        
        # 1. Physics Calculations (The logic you extracted)

        # Calculate percentage price change
        price_change_pct = (prices - data["current_prices"]) / (data["current_prices"] + 1e-6)
        
        # Calculate demand change based on elasticity
        demand_change_pct = data["elasticities"] * price_change_pct
        
        # Calculate new occupancy (clamped between 0% and 100%)
        new_occupancy = np.clip(data["current_occupancy"] * (1 + demand_change_pct), 0.0, 1.0)
        
        # Calculate revenue for each zone
        revenue_vector = prices * (data["capacities"] * new_occupancy)

        # 2. Objective Calculations (Scoring)
        
        # Obj 1: Total Revenue (Maximize -> Minimize negative sum)
        f1_revenue = np.sum(revenue_vector)
        
        # Obj 2: Occupancy Gap (Minimize distance to target)
        # Note: 'target_occupancy' must be in the data dict
        gap_vector = np.abs(new_occupancy - data["target_occupancy"])
        f2_gap = np.mean(gap_vector)

        # Obj 3: Demand Drop (Minimize churn/loss)
        # Only count negative demand changes
        loss_vector = np.minimum(0, demand_change_pct)
        f3_drop = np.mean(loss_vector * -1)

        # Obj 4: User Fairness (Maximize -> Minimize impact)
        # Only count price increases, weighted by short-term share
        impact_vector = np.maximum(0, price_change_pct) * data["short_term_share"]
        f4_fairness = np.mean(impact_vector)

        # 3. Return everything in one package
        return {
            "objectives": [f1_revenue, f2_gap, f3_drop, f4_fairness], 
            "occupancy": new_occupancy,       
            "revenue": revenue_vector,        
            "demand_change": demand_change_pct
            }
        
        
        

    def _simulate_scenario(self, prices: np.ndarray, request: OptimizationRequest) -> Tuple[float, float, float, float]:
        """
        Internal Evaluation Function (The Simulation Core).
        Calculates objectives based on price elasticity.
        """
        
        data = self._convert_request_to_numpy(request)              # Convert request data to numpy arrays
        
        # Unpack vectors for easier reading
        current_prices = data["current_prices"]                     
        current_occupancy = data["current_occupancy"]
        elasticities = data["elasticities"]
        capacities = data["capacities"]
        short_term_share = data["short_term_share"]
        
        target_occ = request.settings.target_occupancy                  # Target occupancy from settings    

        """  SIMULATION LOGIC """

        # calculates percentage price change (New - Old) / Old for each zone
        price_change_pct = (prices - current_prices) / (current_prices + 1e-6)

        # calculates the new demand change based on elasticity
        demand_change_pct = elasticities * price_change_pct

        # calculates the new occupancy based on demand change
        new_occupancy = current_occupancy * (1 + demand_change_pct)

        # CRITICAL: Clamp values! Occupancy cannot be < 0% or > 100% (1.0)
        # If math says 120%, we cut it off at 100%.
        new_occupancy = np.clip(new_occupancy, 0.0, 1.0)

        """ OBJECTIVE CALCULATIONS """

        # Objective 1: Revenue (Maximize)
        revenue_vector = prices * (capacities * new_occupancy)                  #vector of revenues for all zones
        f1_total_revenue = np.sum(revenue_vector)                               #total revenue across all zones

        # Objective 2: Occupancy Gap (Minimize)
        gap_vector = np.abs(new_occupancy - target_occ)                         #vector of occupancy gaps for all zones
        f2_occupancy_gap = np.mean(gap_vector)                                  # Average gap across all zones

        # Objective 3: Demand Drop (Minimize)
        loss_vector = np.minimum(0, demand_change_pct)                          #vector of demand drops (only negative changes)
        f3_demand_drop = np.mean(loss_vector * -1)                              # Average demand drop across all zones (as positive value)


        # Objective 4: User Group Balance (Maximize)
        impact_vector = np.maximum(0, price_change_pct) * short_term_share      #vector of negative impacts on short-term users (only price increases)
        f4_fairness = np.mean(impact_vector)                                    # Average impact across all zones

        return f1_total_revenue, f2_occupancy_gap, f3_demand_drop, f4_fairness


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
