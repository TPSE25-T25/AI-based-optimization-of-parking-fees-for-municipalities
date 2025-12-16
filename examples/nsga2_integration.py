"""
Quick reference for integrating the parking simulation with NSGA-II.

This module shows the exact interface between the simulation and NSGA-II optimizer.
"""

from decimal import Decimal
from typing import List, Tuple
import numpy as np

from backend.models.city import City
from backend.models.driver import Driver
from backend.services.simulation.simulation import ParkingSimulation


# ============================================================================
# STEP 1: Define the optimization problem
# ============================================================================

class ParkingPriceOptimizationProblem:
    """
    Wrapper for parking simulation that NSGA-II can use.
    This class defines the optimization problem in terms NSGA-II understands.
    """
    
    def __init__(
        self,
        city: City,
        drivers: List[Driver],
        simulation: ParkingSimulation,
        min_price: float = 1.0,
        max_price: float = 10.0
    ):
        """
        Initialize optimization problem.
        
        Args:
            city: City model with parking lots
            drivers: Driver population for simulation
            simulation: Configured ParkingSimulation instance
            min_price: Minimum allowed price per hour
            max_price: Maximum allowed price per hour
        """
        self.city = city
        self.drivers = drivers
        self.simulation = simulation
        self.min_price = min_price
        self.max_price = max_price
        
        # Problem dimensions
        self.n_variables = len(city.parking_lots)  # One price per lot
        self.n_objectives = 3  # Revenue, variance, driver cost
        
        # Variable bounds
        self.lower_bounds = [min_price] * self.n_variables
        self.upper_bounds = [max_price] * self.n_variables
    
    def evaluate(self, price_vector: List[float]) -> Tuple[float, float, float]:
        """
        Evaluate a single price configuration.
        This is the fitness function NSGA-II calls.
        
        Args:
            price_vector: List of prices (one per parking lot)
        
        Returns:
            Tuple of three objectives (all minimization):
                - negative_revenue (maximize revenue → negate)
                - occupancy_variance (minimize for balance)
                - avg_driver_cost (minimize for satisfaction)
        """
        # Convert to Decimal for precision
        price_decimal = [Decimal(str(p)) for p in price_vector]
        
        # Run simulation
        objectives = self.simulation.evaluate_price_configuration(
            self.city,
            self.drivers,
            price_decimal,
            objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
        )
        
        return (
            objectives['negative_revenue'],
            objectives['occupancy_variance'],
            objectives['avg_driver_cost']
        )
    
    def evaluate_population(self, population: np.ndarray) -> np.ndarray:
        """
        Evaluate an entire population of solutions.
        
        Args:
            population: 2D array (n_individuals x n_variables)
        
        Returns:
            2D array (n_individuals x n_objectives)
        """
        results = []
        
        for individual in population:
            objectives = self.evaluate(individual.tolist())
            results.append(objectives)
        
        return np.array(results)


# ============================================================================
# STEP 2: Using with pymoo's NSGA-II
# ============================================================================

def example_with_pymoo():
    """
    Example integration with pymoo library's NSGA-II implementation.
    Install: pip install pymoo
    """
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.sampling.rnd import FloatRandomSampling
    from pymoo.optimize import minimize
    
    # Assume you have city, drivers, and simulation set up
    city = None  # Your city instance
    drivers = None  # Your driver list
    simulation = ParkingSimulation()
    
    # Define problem for pymoo
    class PymooWrapper(Problem):
        def __init__(self, optimization_problem):
            self.opt_problem = optimization_problem
            
            super().__init__(
                n_var=optimization_problem.n_variables,
                n_obj=optimization_problem.n_objectives,
                xl=np.array(optimization_problem.lower_bounds),
                xu=np.array(optimization_problem.upper_bounds)
            )
        
        def _evaluate(self, x, out, *args, **kwargs):
            """Pymoo calls this for population evaluation."""
            out["F"] = self.opt_problem.evaluate_population(x)
    
    # Create problem
    opt_problem = ParkingPriceOptimizationProblem(city, drivers, simulation)
    problem = PymooWrapper(opt_problem)
    
    # Configure NSGA-II
    algorithm = NSGA2(
        pop_size=100,  # Population size
        n_offsprings=100,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True
    )
    
    # Run optimization
    result = minimize(
        problem,
        algorithm,
        ('n_gen', 100),  # 100 generations
        seed=1,
        verbose=True
    )
    
    # Extract results
    print("Pareto Front Solutions:")
    print("=" * 70)
    
    for i, (solution, objectives) in enumerate(zip(result.X, result.F)):
        print(f"\nSolution {i+1}:")
        print(f"  Prices: {solution}")
        print(f"  Revenue: ${-objectives[0]:.2f}")  # Un-negate
        print(f"  Occupancy Variance: {objectives[1]:.4f}")
        print(f"  Avg Driver Cost: ${objectives[2]:.2f}")


# ============================================================================
# STEP 3: Custom NSGA-II implementation interface
# ============================================================================

def example_custom_nsga2():
    """
    If using a custom NSGA-II implementation, here's the interface.
    """
    
    # Setup (same as above)
    city = None  # Your city
    drivers = None  # Your drivers
    simulation = ParkingSimulation()
    
    problem = ParkingPriceOptimizationProblem(city, drivers, simulation)
    
    # ---- Your NSGA-II Implementation ----
    
    # 1. Initialize population
    population_size = 100
    population = initialize_random_population(
        size=population_size,
        n_vars=problem.n_variables,
        lower=problem.lower_bounds,
        upper=problem.upper_bounds
    )
    
    # 2. Evaluate initial population
    fitness_values = problem.evaluate_population(population)
    
    # 3. Main loop
    for generation in range(100):
        # 4. Non-dominated sorting
        fronts = non_dominated_sort(fitness_values)
        
        # 5. Crowding distance
        distances = calculate_crowding_distance(fitness_values, fronts)
        
        # 6. Selection
        parents = tournament_selection(population, fronts, distances)
        
        # 7. Crossover
        offspring = simulated_binary_crossover(parents)
        
        # 8. Mutation
        offspring = polynomial_mutation(offspring)
        
        # 9. Evaluate offspring
        offspring_fitness = problem.evaluate_population(offspring)
        
        # 10. Combine and select next generation
        combined_pop = np.vstack([population, offspring])
        combined_fitness = np.vstack([fitness_values, offspring_fitness])
        
        population, fitness_values = select_next_generation(
            combined_pop,
            combined_fitness,
            population_size
        )
    
    # Extract Pareto front
    fronts = non_dominated_sort(fitness_values)
    pareto_indices = fronts[0]
    pareto_solutions = population[pareto_indices]
    pareto_objectives = fitness_values[pareto_indices]
    
    return pareto_solutions, pareto_objectives


# ============================================================================
# STEP 4: Analyzing results
# ============================================================================

def analyze_pareto_front(solutions: np.ndarray, objectives: np.ndarray, city: City):
    """
    Analyze the Pareto front solutions.
    
    Args:
        solutions: Price configurations (n_solutions x n_lots)
        objectives: Objective values (n_solutions x 3)
        city: City model for reference
    """
    print("\nPareto Front Analysis:")
    print("=" * 70)
    
    lot_names = [lot.pseudonym for lot in sorted(city.parking_lots, key=lambda x: x.id)]
    
    for i, (prices, objs) in enumerate(zip(solutions, objectives)):
        print(f"\nSolution {i+1}:")
        print(f"  Revenue: ${-objs[0]:.2f}")  # Un-negate
        print(f"  Occupancy Balance (variance): {objs[1]:.4f}")
        print(f"  Driver Satisfaction (avg cost): ${objs[2]:.2f}")
        print(f"  Price Configuration:")
        
        for name, price in zip(lot_names, prices):
            print(f"    {name}: ${price:.2f}/hour")
    
    # Find extreme solutions
    print("\n" + "=" * 70)
    print("Extreme Solutions:")
    print("=" * 70)
    
    # Highest revenue
    max_revenue_idx = np.argmin(objectives[:, 0])  # Remember, negated
    print(f"\nHighest Revenue Solution:")
    print(f"  Revenue: ${-objectives[max_revenue_idx, 0]:.2f}")
    print(f"  Prices: {solutions[max_revenue_idx]}")
    
    # Best balanced
    min_variance_idx = np.argmin(objectives[:, 1])
    print(f"\nBest Balanced Solution:")
    print(f"  Occupancy Variance: {objectives[min_variance_idx, 1]:.4f}")
    print(f"  Prices: {solutions[min_variance_idx]}")
    
    # Best for drivers
    min_cost_idx = np.argmin(objectives[:, 2])
    print(f"\nBest for Drivers:")
    print(f"  Avg Driver Cost: ${objectives[min_cost_idx, 2]:.2f}")
    print(f"  Prices: {solutions[min_cost_idx]}")


# ============================================================================
# STEP 5: Stochastic evaluation (multiple runs)
# ============================================================================

def stochastic_evaluation(
    city: City,
    simulation: ParkingSimulation,
    price_vector: List[float],
    n_runs: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Evaluate a price configuration multiple times with different driver populations.
    Returns mean and std of objectives.
    
    Args:
        city: City model
        simulation: Simulation instance
        price_vector: Price configuration to evaluate
        n_runs: Number of simulation runs
    
    Returns:
        (mean_objectives, std_objectives)
    """
    from backend.services.data.driver_generator import DriverGenerator
    
    generator = DriverGenerator()  # No seed = different each time
    results = []
    
    for _ in range(n_runs):
        # Generate new driver population
        drivers = generator.generate_random_drivers(count=500, city=city)
        
        # Evaluate
        price_decimal = [Decimal(str(p)) for p in price_vector]
        objectives = simulation.evaluate_price_configuration(
            city, drivers, price_decimal,
            objectives=['negative_revenue', 'occupancy_variance', 'avg_driver_cost']
        )
        
        results.append([
            objectives['negative_revenue'],
            objectives['occupancy_variance'],
            objectives['avg_driver_cost']
        ])
    
    results = np.array(results)
    return results.mean(axis=0), results.std(axis=0)


# ============================================================================
# Placeholder functions (implement in your NSGA-II)
# ============================================================================

def initialize_random_population(size, n_vars, lower, upper):
    """Generate random initial population."""
    return np.random.uniform(lower, upper, size=(size, n_vars))

def non_dominated_sort(fitness):
    """Implement non-dominated sorting."""
    pass

def calculate_crowding_distance(fitness, fronts):
    """Calculate crowding distance for diversity."""
    pass

def tournament_selection(population, fronts, distances):
    """Select parents via tournament selection."""
    pass

def simulated_binary_crossover(parents):
    """SBX crossover operator."""
    pass

def polynomial_mutation(offspring):
    """Polynomial mutation operator."""
    pass

def select_next_generation(population, fitness, size):
    """Select next generation using elitism."""
    pass


# ============================================================================
# Complete example
# ============================================================================

if __name__ == "__main__":
    """
    Complete workflow example.
    """
    
    # This would be a complete example if you have pymoo installed
    print("NSGA-II Integration Reference")
    print("=" * 70)
    print("\nKey Points:")
    print("1. Use ParkingPriceOptimizationProblem.evaluate() as fitness function")
    print("2. Each solution is a vector of prices (one per parking lot)")
    print("3. Three objectives: -revenue, variance, avg_cost (all minimize)")
    print("4. Bounds: typically 1.0 to 10.0 per hour")
    print("5. Pareto front gives trade-off solutions")
    print("\nSee functions above for integration details.")
