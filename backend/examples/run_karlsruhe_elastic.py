import os

current_dir = os.path.dirname(os.path.abspath(__file__)) 

from backend.services.data.karlsruhe_loader import KarlsruheLoader
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest, OptimizationSettings
from backend.services.visualization.result_handler import OptimizationResultHandler

# --- 2. USER PREFERENCE CONFIGURATION (FRONTEND SIMULATION) ---
# This dictionary simulates the slider values a user would set in the web frontend.
# The algorithm selects the best solution from the Pareto Front based on these weights.
USER_WEIGHTS = {
    "revenue": 60,      # Priority: Maximize Revenue
    "occupancy": 20,    # Priority: Optimize Occupancy (Target 90%)
    "drop": 10,         # Priority: Minimize Demand Drop (Don't scare away cars)
    "fairness": 10,     # Priority: Maximize Fairness (Avoid current_fee shocks)
}

# --- 3. MAIN EXECUTION PIPELINE ---
def main():
    print("\n" + "="*60)
    print("🏙️  PARKING OPTIMIZATION KARLSRUHE (FULL END-TO-END TEST)")
    print("="*60)

    # ---------------------------------------------------------
    # A. DATA INGESTION
    # ---------------------------------------------------------
    print("1️⃣  Initializing Data Loader (OSM + Pricing DB)...")
    loader = KarlsruheLoader()
    
    # Load a large dataset to stress-test the system (OSM Fetching)
    zones = loader.load_city(limit=3500) 
    
    if not zones:
        print("❌ Abort: No zones found.")
        return

    print(f"✅ {len(zones)} parking zones prepared for optimization.")

    # ---------------------------------------------------------
    # B. OPTIMIZATION SETUP
    # ---------------------------------------------------------
    print("\n2️⃣  Configuring AI Algorithm (NSGA-III)...")
    
    # Define settings for the genetic algorithm
    settings = OptimizationSettings(
        population_size=200,    # Number of candidate solutions per generation (higher = better diversity)
        generations=100,        # Number of evolutionary iterations (higher = better convergence)
        target_occupancy=0.90   # Strategic Goal: Aim for 90% utilization
    )
    
    # Wrap everything in a request object (Validation via Pydantic)
    req = OptimizationRequest(zones=zones, settings=settings)

    # ---------------------------------------------------------
    # C. EXECUTE OPTIMIZATION ENGINE
    # ---------------------------------------------------------
    print("🚀 Starting Calculation... (This may take a while for >1000 zones)")
    optimizer = NSGA3OptimizerElasticity()
    
    # Run the genetic algorithm. 
    # Result: A set of Pareto-optimal scenarios (e.g., 9-15 solutions).
    response = optimizer.optimize(req)
    
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
        map_filename="karlsruhe_elastic_result.html",
        csv_filename="karlsruhe_elastic_superset.csv",
        method_label="Elasticity Model"
    )

    print("\n" + "="*60)
    print("🎉 PROCESS FINISHED SUCCESSFULLY")

if __name__ == "__main__":
    main()
    