import os

current_dir = os.path.dirname(os.path.abspath(__file__)) 

from backend.services.data.karlsruhe_loader import KarlsruheLoader
from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased
from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest, OptimizationSettings
from backend.services.visualization.result_handler import OptimizationResultHandler

# --- 2. USER PREFERENCE CONFIGURATION (FRONTEND SIMULATION) ---
# This dictionary simulates the slider values a user would set in the web frontend.
# The algorithm selects the best solution from the Pareto Front based on these weights.
USER_WEIGHTS = {
    "revenue": 10,      # Priority: Maximize Revenue
    "occupancy": 20,    # Priority: Optimize Occupancy (Target 90%)
    "drop": 10,         # Priority: Minimize Demand Drop (Don't scare away cars)
    "fairness": 60,     # Priority: Maximize Fairness (Avoid price shocks)
}

# --- 3. SIMULATION CONFIGURATION ---
# Configure the driver-based simulation parameters
SIMULATION_CONFIG = {
    "drivers_per_zone_capacity": 1.5,          # Generate 150% drivers relative to total capacity
    "simulation_runs": 1,                       # Number of simulation runs to average (higher = more stable but slower)
    "random_seed": 42,                          # Random seed for reproducibility
    "price_weight": 1.0,                        # Driver sensitivity to price
    "distance_to_lot_weight": 0.5,             # Driver sensitivity to driving distance
    "walking_distance_weight": 1.5,            # Driver sensitivity to walking distance
    "availability_weight": 0.3                  # Driver sensitivity to lot availability
}

# --- 4. MAIN EXECUTION PIPELINE ---
def main():
    print("\n" + "="*70)
    print("🏙️  PARKING OPTIMIZATION KARLSRUHE (DRIVER-BASED SIMULATION)")
    print("="*70)

    # ---------------------------------------------------------
    # A. DATA INGESTION
    # ---------------------------------------------------------
    print("1️⃣  Initializing Data Loader (OSM + Pricing DB)...")
    loader = KarlsruheLoader()

    # Load a large dataset to stress-test the system (OSM Fetching)
    zones = loader.load_zones(limit=3500)

    if not zones:
        print("❌ Abort: No zones found.")
        return

    print(f"✅ {len(zones)} parking zones prepared for optimization.")

    # ---------------------------------------------------------
    # B. OPTIMIZATION SETUP
    # ---------------------------------------------------------
    print("\n2️⃣  Configuring AI Algorithm (NSGA-III with Driver Simulation)...")

    # Define default settings for the genetic algorithm
    settings = OptimizationSettings()

    # Wrap everything in a request object (Validation via Pydantic)
    req = OptimizationRequest(zones=zones, settings=settings)

    # ---------------------------------------------------------
    # C. EXECUTE OPTIMIZATION ENGINE WITH SIMULATION
    # ---------------------------------------------------------
    print("🚀 Starting Calculation with Driver-Based Simulation...")
    print(f"   Configuration:")
    print(f"   - Drivers per Capacity: {SIMULATION_CONFIG['drivers_per_zone_capacity']}x")
    print(f"   - Simulation Runs: {SIMULATION_CONFIG['simulation_runs']}")
    print(f"   - Price Weight: {SIMULATION_CONFIG['price_weight']}")
    print(f"   - Walking Distance Weight: {SIMULATION_CONFIG['walking_distance_weight']}")

    optimizer = NSGA3OptimizerAgentBased(
        drivers_per_zone_capacity=SIMULATION_CONFIG["drivers_per_zone_capacity"],
        simulation_runs=SIMULATION_CONFIG["simulation_runs"],
        random_seed=SIMULATION_CONFIG["random_seed"],
        price_weight=SIMULATION_CONFIG["price_weight"],
        distance_to_lot_weight=SIMULATION_CONFIG["distance_to_lot_weight"],
        walking_distance_weight=SIMULATION_CONFIG["walking_distance_weight"],
        availability_weight=SIMULATION_CONFIG["availability_weight"]
    )

    # Run the genetic algorithm with driver simulation.
    # Result: A set of Pareto-optimal scenarios (e.g., 9-15 solutions).
    response = optimizer.optimize(req, loader)

    # ---------------------------------------------------------
    # D. DECISION MAKING (A Posteriori)
    # ---------------------------------------------------------
    # Select the single best scenario that matches the USER_WEIGHTS defined above.
    best_scenario = optimizer.select_best_solution_by_weights(response, USER_WEIGHTS)

    if not best_scenario:
        print("❌ Error: No suitable solution found.")
        return

    # ---------------------------------------------------------
    # E. RESULT HANDLING (Presentation, Visualization, Export)
    # ---------------------------------------------------------
    # Use the shared result handler to avoid code duplication
    result_handler = OptimizationResultHandler(
        center_location=[49.0069, 8.4037],
        zoom_start=14,
        output_dir=current_dir
    )

    result_handler.handle_full_workflow(
        best_scenario=best_scenario,
        user_weights=USER_WEIGHTS,
        loader=loader,
        map_filename="karlsruhe_simulation_result.html",
        csv_filename="karlsruhe_simulation_superset.csv",
        method_label="Driver Simulation"
    )

if __name__ == "__main__":
    main()
