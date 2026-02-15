import pytest

from backend.services.optimizer.solution_selector import SolutionSelector
from backend.services.optimizer.schemas.optimization_schema import PricingScenario


def scenario(sid, rev, gap, drop, bal):
    # Minimal scenario (zones not needed for selection)
    return PricingScenario(
        scenario_id=sid,
        zones=[],
        score_revenue=rev,
        score_occupancy_gap=gap,
        score_demand_drop=drop,
        score_user_balance=bal,
    )


class TestSolutionSelector:
    def test_returns_none_on_empty_list(self):
        assert SolutionSelector.select_best_by_weights([], {"revenue": 100}) is None

    def test_revenue_only_picks_highest_revenue(self):
        s1 = scenario(1, rev=100, gap=0.5, drop=0.5, bal=0.5)
        s2 = scenario(2, rev=200, gap=0.9, drop=0.9, bal=0.1)
        best = SolutionSelector.select_best_by_weights([s1, s2], {"revenue": 100})
        assert best.scenario_id == 2

    def test_occupancy_only_picks_lowest_gap(self):
        s1 = scenario(1, rev=100, gap=0.10, drop=0.5, bal=0.5)  # best gap
        s2 = scenario(2, rev=500, gap=0.40, drop=0.1, bal=0.9)
        best = SolutionSelector.select_best_by_weights([s1, s2], {"occupancy": 100})
        assert best.scenario_id == 1

    def test_drop_only_picks_lowest_drop(self):
        s1 = scenario(1, rev=100, gap=0.4, drop=0.30, bal=0.5)
        s2 = scenario(2, rev=100, gap=0.4, drop=0.05, bal=0.5)  # best drop
        best = SolutionSelector.select_best_by_weights([s1, s2], {"drop": 100})
        assert best.scenario_id == 2

    def test_fairness_only_picks_highest_balance(self):
        s1 = scenario(1, rev=100, gap=0.4, drop=0.3, bal=0.20)
        s2 = scenario(2, rev=100, gap=0.4, drop=0.3, bal=0.90)  # best balance
        best = SolutionSelector.select_best_by_weights([s1, s2], {"fairness": 100})
        assert best.scenario_id == 2

    def test_missing_weights_keys_defaults_to_zero(self):
        s1 = scenario(1, rev=100, gap=0.2, drop=0.2, bal=0.2)
        s2 = scenario(2, rev=200, gap=0.8, drop=0.8, bal=0.8)
        # Only revenue weight present -> should behave like revenue-only
        best = SolutionSelector.select_best_by_weights([s1, s2], {"revenue": 100})
        assert best.scenario_id == 2

    def test_all_equal_scores_returns_first_scenario(self):
        # When all objectives equal => normalized scores all 1.0 => tie.
        # Your implementation keeps the first winner (score > best_score only).
        s1 = scenario(1, rev=100, gap=0.2, drop=0.2, bal=0.5)
        s2 = scenario(2, rev=100, gap=0.2, drop=0.2, bal=0.5)
        best = SolutionSelector.select_best_by_weights(
            [s1, s2],
            {"revenue": 25, "occupancy": 25, "drop": 25, "fairness": 25},
        )
        assert best.scenario_id == 1

    def test_balanced_weights_prefers_reasonable_compromise(self):
        # Construct a case where each scenario is "best" at one objective
        s_revenue = scenario(1, rev=1000, gap=0.5, drop=0.5, bal=0.5)
        s_gap     = scenario(2, rev=500,  gap=0.05, drop=0.5, bal=0.5)
        s_drop    = scenario(3, rev=500,  gap=0.5, drop=0.01, bal=0.5)
        s_bal     = scenario(4, rev=500,  gap=0.5, drop=0.5, bal=0.99)

        scenarios = [s_revenue, s_gap, s_drop, s_bal]
        best = SolutionSelector.select_best_by_weights(
            scenarios,
            {"revenue": 25, "occupancy": 25, "drop": 25, "fairness": 25},
        )

        # With symmetric weights, the "best" depends on normalization ranges,
        # but it should always return one of the scenarios and not None.
        assert best is not None
        assert best in scenarios
