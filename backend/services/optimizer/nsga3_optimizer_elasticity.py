"""
NSGA-3 Optimizer using elasticity model.

This optimizer uses price elasticity calculations for fast evaluation,
incorporating behavioral economics (loss aversion, user groups).
"""

from typing import Tuple
import numpy as np

from backend.services.optimizer.schemas.optimization_schema import OptimizationRequest
from backend.services.optimizer.nsga3_optimizer import NSGA3Optimizer


class NSGA3OptimizerElasticity(NSGA3Optimizer):
    """
    NSGA-3 Optimizer using elasticity-based evaluation.

    Fast optimizer suitable for:
    - Rapid prototyping and testing
    - Large-scale optimizations (many zones, long runs)
    - Initial exploration of solution space
    - When computational resources are limited

    Uses price elasticity model with:
    - Loss aversion (asymmetric sensitivity to price changes)
    - User groups (short-term vs long-term parkers)
    - Physical constraints (occupancy bounded to 0.05-1.0)
    """

    def __init__(self, random_seed: int = 1):
        """
        Initialize the elasticity-based optimizer.

        Args:
            random_seed: Seed for reproducibility (default: 1 for backward compatibility)
        """
        super().__init__(random_seed=random_seed)

    def _calculate_physics(self, prices: np.ndarray, data: dict) -> dict:
        """
        Central Physics Engine using price elasticity model.

        Simulates user behavior based on price elasticity, loss aversion, and user groups.
        Uses NumPy vectorization for high-performance batch processing.

        Args:
            prices: New price vector for all zones
            data: Dictionary with current state (from _convert_request_to_numpy)

        Returns:
            Dictionary with objectives, occupancy, revenue, and demand_change arrays
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

    def _get_detailed_results(self, prices: np.ndarray, data: dict) -> dict:
        """
        Get detailed results (occupancy, revenue) for a price vector using elasticity model.

        Args:
            prices: Price vector for all zones
            data: Dictionary with zone data

        Returns:
            Dictionary with occupancy and revenue arrays
        """
        results = self._calculate_physics(prices, data)
        return {
            "occupancy": results["occupancy"],
            "revenue": results["revenue"]
        }

    def _simulate_scenario(self, prices: np.ndarray, request: OptimizationRequest) -> Tuple[float, float, float, float]:
        """
        Evaluate a price vector using elasticity model.

        Args:
            prices: Price vector for all zones
            request: Optimization request

        Returns:
            Tuple of (revenue, occupancy_gap, demand_drop, user_balance)
        """
        # 1. Data Preparation
        data = self._convert_request_to_numpy(request)

        # 2. Physics Simulation using elasticity
        results = self._calculate_physics(prices, data)

        # 3. Objective Extraction
        objs = results["objectives"]

        # 4. Return objectives
        return objs[0], objs[1], objs[2], objs[3]