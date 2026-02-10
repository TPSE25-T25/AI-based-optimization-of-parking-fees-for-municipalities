import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# --- 1. PATH CONFIGURATION ---
# Add the 'backend' directory to the system path so Python can find our custom modules.
current_file_path = os.path.abspath(__file__)           # .../backend/Tests/run_Karlsruhe.py
current_dir = os.path.dirname(current_file_path)        # .../backend/Tests
backend_dir = os.path.dirname(current_dir)              # .../backend

import folium
from folium.plugins import MarkerCluster
from backend.services.datasources.city_data_loader import CityDataLoader
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity
from backend.services.settings.optimizations_settings import OptimizationSettings
from backend.services.settings.data_source_settings import DataSourceSettings
from backend.services.visualization.result_handler import OptimizationResultHandler

from backend.services.database.init_db import init_db
from backend.services.database.database import SessionLocal
from backend.services.database.models import SimulationResult

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
    datasource_settings = DataSourceSettings(
        data_source="osmnx",
        city_name="Karlsruhe, Germany",
        center_coords=(49.0069, 8.4037),
        limit=50,  # Limit zones for faster testing
        poi_limit=20
    )
    loader = CityDataLoader(datasource=datasource_settings)
    
    # Load a large dataset to stress-test the system (OSM Fetching)
    city = loader.load_city() 
    
    if not city or not city.parking_zones:
        print("❌ Abort: No zones found.")
        return

    print(f"✅ {len(city.parking_zones)} parking zones prepared for optimization.")

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

    # ---------------------------------------------------------
    # C. EXECUTE OPTIMIZATION ENGINE
    # ---------------------------------------------------------
    print("🚀 Starting Calculation... (This may take a while for >1000 zones)")
    optimizer = NSGA3OptimizerElasticity(settings)
    
    # Run the genetic algorithm. 
    # Result: A set of Pareto-optimal scenarios (e.g., 9-15 solutions).
    scenarios = optimizer.optimize(city)
    
    # ---------------------------------------------------------
    # D. DECISION MAKING (A Posteriori)
    # ---------------------------------------------------------
    # Select the single best scenario that matches the USER_WEIGHTS defined above.
    best_scenario = optimizer.select_best_solution_by_weights(scenarios, USER_WEIGHTS)

    if not best_scenario:
        print("❌ Error: No suitable solution found.")
        return

    # ---------------------------------------------------------
    # E. VISUALIZATION (Map Generation)
    # ---------------------------------------------------------
    print("\n3️⃣  Generating interactive map...")
    
    # Create a mapping from zone ID to optimized results
    optimized_zones_map = {zone.id: zone for zone in best_scenario.zones}
    
    # Initialize Folium Map centered on Karlsruhe
    m = folium.Map(location=[49.0069, 8.4037], zoom_start=14, tiles="cartodbpositron")
    cluster = MarkerCluster().add_to(m)

    # Iterate through city zones and add markers
    for zone in city.parking_zones:
        if zone.id in optimized_zones_map:
            optimized = optimized_zones_map[zone.id]
            new_fee = optimized.new_fee
            old_fee = zone.current_fee
            
            # Determine Color Logic based on price change
            diff = new_fee - old_fee
            if diff > 0.1:
                color = 'red'       # Price Hike (Expensive)
                trend = "📈 Higher"
            elif diff < -0.1:
                color = 'green'     # Price Drop (Cheaper)
                trend = "📉 Lower"
            else:
                color = 'blue'      # Stable
                trend = "➡️ Stable"

            # Create HTML Popup content
            popup_html = f"""
            <div style="font-family: Arial; min-width: 150px;">
                <b>{zone.name}</b><hr>
                Status: <b>{trend}</b><br>
                Old: {old_fee:.2f} €<br>
                New: <b>{new_fee:.2f} €</b><br>
                Predicted Occupancy: {optimized.predicted_occupancy*100:.1f}%
            </div>
            """

            # Add marker to map cluster (position is (lat, lon))
            folium.CircleMarker(
                location=[zone.position[0], zone.position[1]],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(cluster)

    # Save Map to disk
    output_filename = "karlsruhe_result.html"
    output_path = os.path.join(current_dir, output_filename)
    m.save(output_path)
    print(f"✅ Map saved: {output_path}")

    # ---------------------------------------------------------
    # F. DATA EXPORT
    # ---------------------------------------------------------
    print("\n4️⃣  Exporting Data...")
    csv_path = os.path.join(current_dir, "karlsruhe_superset.csv")
    
    # Export detailed CSV for external analysis (Superset, Tableau, Excel)
    loader.export_results_for_superset(best_scenario.zones, csv_path)
    print(f"✅ CSV exported: {csv_path}")

    # ---------------------------------------------------------
    # G. PERSIST RESULTS (Database)
    # ---------------------------------------------------------
    print("\n5️⃣  Persisting Results to DB...")
    init_db()
    session = SessionLocal()
    try:
        result = SimulationResult(
            parameters={
                "settings": settings.model_dump(),
                "user_weights": USER_WEIGHTS,
                "zone_count": len(city.parking_zones)
            },
            map_path=os.path.relpath(output_path, backend_dir),
            csv_path=os.path.relpath(csv_path, backend_dir),
            best_scenario={
                "scenario_id": best_scenario.scenario_id,
                "score_revenue": best_scenario.score_revenue,
                "score_occupancy_gap": best_scenario.score_occupancy_gap,
                "score_demand_drop": best_scenario.score_demand_drop,
                "score_user_balance": best_scenario.score_user_balance
            }
        )
        session.add(result)
        session.commit()
        session.refresh(result)
        print(f"✅ DB row created: id={result.id}")
    finally:
        session.close()

    print("\n" + "="*60)
    print("🎉 PROCESS FINISHED SUCCESSFULLY")


if __name__ == "__main__":
    main()
    