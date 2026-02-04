"""
Quick test to verify the driver-based simulation integration works.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.optimizer.nsga3_optimizer_agent import create_simulation_optimizer
from backend.services.optimizer.schemas.optimization_schema import (
    OptimizationRequest,
    OptimizationSettings,
    ParkingZone
)


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
            position=(100.0, 100.0),
            min_fee=0.5,
            max_fee=3.0,
            elasticity=-0.4,
            short_term_share=0.4
        ),
    ]

    settings = OptimizationSettings(
        population_size=50,
        generations=10,
        target_occupancy=0.85
    )

    request = OptimizationRequest(zones=zones, settings=settings)

    # Create optimizer with simulation
    print("\n[1] Creating optimizer with driver simulation...")
    optimizer = create_simulation_optimizer(
        drivers_per_zone_capacity=1.5,
        simulation_runs=1,
        random_seed=42
    )

    # Run optimization
    print("\n[2] Running optimization...")
    try:
        response = optimizer.optimize(request)

        print(f"\n✓ SUCCESS!")
        print(f"  Found {len(response.scenarios)} Pareto-optimal solutions")

        # Show first solution
        if response.scenarios:
            scenario = response.scenarios[0]
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
