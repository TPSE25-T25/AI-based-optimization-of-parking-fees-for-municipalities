"""
Solution Selection Service
Provides weight-based selection of optimal scenarios from Pareto front.
"""

from typing import List
from backend.services.optimizer.schemas.optimization_schema import PricingScenario


class SolutionSelector:
    """
    Selects the best solution from optimization results based on user preferences.
    Uses min-max normalization to ensure fair comparison between different objective units.
    """

    @staticmethod
    def select_best_by_weights(response: List[PricingScenario], weights: dict) -> PricingScenario:
        """
        Selects the single best scenario from the Pareto Front based on user preferences.
        It normalizes all objective values to a 0-1 scale to ensure fair comparison
        between different units (Euros vs. Percentages).
        
        Args:
            response: List of PricingScenario objects from optimize()
            weights: A dictionary with user weights (0-100), e.g., {"revenue": 50, "occupancy": 50}
            
        Returns:
            The scenario with the highest weighted score
        """
        scenarios = response
        if not scenarios:
            return None

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
