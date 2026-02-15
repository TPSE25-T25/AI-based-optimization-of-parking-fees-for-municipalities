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

from backend.services.optimizer.nsga3_optimizer_agent import NSGA3OptimizerAgentBased
from backend.services.settings.optimizations_settings import AgentBasedSettings
from backend.services.models.city import ParkingZone, City, PointOfInterest


def main():
    print("="*70)
    print("QUICK SIMULATION TEST")
    print("="*70)

    # Create a simple 2-zone request
    zones = [
        ParkingZone(
            id=1,
            name="Zone A",
            maximum_capacity=100,
            current_fee=2.0,
            current_capacity=int(100 * 0.80),
            position=(0.0, 0.0),
            min_fee=1.0,
            max_fee=4.0,
            elasticity=-0.5,
            short_term_share=0.6
        ),
        ParkingZone(
            id=2,
            name="Zone B",
            maximum_capacity=80,
            current_fee=1.5,
            current_capacity=int(80 * 0.60),
            position=(1.0, 1.0),
            min_fee=0.5,
            max_fee=3.0,
            elasticity=-0.4,
            short_term_share=0.4
        ),
    ]

    # Create a City object with the zones
    city = City(
        id=1,
        name="Quick Simulation Test City",
        min_latitude=0.0,
        max_latitude=1.0,
        min_longitude=0.0,
        max_longitude=1.0,
        parking_zones=zones,
        point_of_interests=[
            PointOfInterest(id=1, name="City Center", position=(0.5, 0.5)),
            PointOfInterest(id=2, name="Shopping Mall", position=(0.3, 0.7)),
        ]
    )

    # Create agent-based settings
    settings = AgentBasedSettings(
        population_size=50,
        generations=10,
        target_occupancy=0.85,
        drivers_per_zone_capacity=1.5,
        simulation_runs=1,
        random_seed=42
    )

    # Create optimizer with simulation
    print("\n[1] Creating optimizer with driver simulation...")
    optimizer = NSGA3OptimizerAgentBased(settings)

    # Run optimization
    print("\n[2] Running optimization...")
    try:
        scenarios = optimizer.optimize(city)

        print(f"\n✓ SUCCESS!")
        print(f"  Found {len(scenarios)} Pareto-optimal solutions")

        # Show first solution
        if scenarios:
            scenario = scenarios[0]
            print(f"\n[3] First Solution (Scenario #{scenario.scenario_id}):")
            print(f"  Revenue: ${scenario.score_revenue:,.2f}")
            print(f"  Occupancy Gap: {scenario.score_occupancy_gap:.4f}")
            print(f"  Demand Drop: {scenario.score_demand_drop:.4f}")
            print(f"  User Balance: {scenario.score_user_balance:.4f}")

            print(f"\n  Zone Details:")
            for zone_result in scenario.zones:
                original = next(z for z in zones if z.id == zone_result.id)
                print(f"    {original.name}: ${float(original.current_fee):.2f} → ${zone_result.new_fee:.2f}")

        print("\n" + "="*70)
        print("TEST PASSED ✓")
        print("="*70)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        print("TEST FAILED ✗")
        print("="*70)


if __name__ == "__main__":
    main()
