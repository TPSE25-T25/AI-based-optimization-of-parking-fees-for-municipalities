import os
from decimal import Decimal

current_dir = os.path.dirname(os.path.abspath(__file__))

from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest, OptimizationSettings, ParkingZoneInput
from backend.services.optimizer.nsga3_optimizer_elasticity import NSGA3OptimizerElasticity

def run_ultimate_table_test():
    print("\n" + "="*160)
    print("   OPTIMIERUNGS-ERGEBNISSE: ALLE 4 ZIELE & DETAILS")
    print("="*160)

    # 1. TEST-DATEN (Deine simple Gemeinde)
    # besser: viele Szenarien pro Zone, damit der Pareto-Front sichtbar wird
    zones = [
        ParkingZoneInput(
            id=1,
            pseudonym="Zentrum",
            maximum_capacity=100,
            current_capacity=95,  # 95% occupancy = 95 spots
            price=Decimal("2.00"),
            position=(0.0, 0.0),  # Placeholder position
            short_term_share=0.7,
            elasticity=-0.4,
            min_fee=1.0,
            max_fee=8.0
        ),
        ParkingZoneInput(
            id=2,
            pseudonym="Dorf",
            maximum_capacity=50,
            current_capacity=10,  # 20% occupancy = 10 spots
            price=Decimal("3.00"),
            position=(1.0, 1.0),  # Placeholder position
            short_term_share=0.2,
            elasticity=-0.6,
            min_fee=0.5,
            max_fee=5.0
        )
    ]

    req = OptimizationRequest(
        zones=zones,
        settings=OptimizationSettings(population_size=500, generations=80, target_occupancy=0.85)
    )

    # 2. BERECHNUNG
    print("... Algorithmus rechnet ...")
    optimizer = NSGA3OptimizerElasticity()
    result = optimizer.optimize(req)
    
    # Wir sortieren nach Gewinn, damit es übersichtlich bleibt
    sorted_scenarios = sorted(result.scenarios, key=lambda x: x.score_revenue, reverse=True)

    print(f"\nGEFUNDENE LÖSUNGEN: {len(sorted_scenarios)}\n")

    # 3. TABELLEN-KOPF BAUEN
    # Wir nutzen Abkürzungen, damit es in eine Zeile passt:
    # NUTZER = Nutzergruppenverteilung (Score)
    # DROP   = Nachfragerückgang
    # GAP    = Abweichung von 85% Auslastung
    
    header = f"{'ID':<4} | {'GEWINN':<9} | {'GAP':<6} | {'DROP':<6} | {'NUTZER':<6} ||"

    for z in zones:
        header += f" Z{z.id} PREIS | Z{z.id} AUSL |"
    
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for sc in sorted_scenarios:
        # Teil 1: Deine 4 Optimierungsziele
        # Nutzer-Score: 1.0 ist perfekt, 0.0 ist schlecht
        # Drop: 0.05 bedeutet 5% Rückgang
        
        row_str = f"#{sc.scenario_id:<3} | {sc.score_revenue:>6.2f} € | {sc.score_occupancy_gap:>6.4f} | {sc.score_demand_drop:>6.4f} | {sc.score_user_balance:>6.2f} ||"
        
        # Teil 2: Die Details pro Zone (Preis & Auslastung)
        for z_res in sc.zones:
            row_str += f" {z_res.new_fee:>7.2f}€ | {z_res.predicted_occupancy*100:>6.1f}%   |"
        
        print(row_str)

    print("-" * len(header))
    print("LEGENDE:")
    print("  GAP    = Abweichung vom Auslastungsziel (0.0 = Perfekt)")
    print("  DROP   = Nachfragerückgang (0.1 = 10% weniger Autos)")
    print("  NUTZER = Nutzergruppenverteilung (1.0 = Preis passt perfekt zur Struktur)")

if __name__ == "__main__":
    run_ultimate_table_test()