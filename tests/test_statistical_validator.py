"""
Unit and Integration Tests for Phase 2 Statistical Validation Hardening.

Verifies:
1. Bootstrap validation (real N preservation, 10,000 resamples, reproducibility)
2. Spread modeling (explicit SPREAD_DATA_UNAVAILABLE handling)
3. Execution stress (slippage 0.00R-0.20R, latency 0-2 bars, classification)
4. Calibration reliability & sample sufficiency
5. Monte Carlo 10,000 path simulation
6. Holdout sample milestone monitoring (XAU N=42 sufficiency)
7. Asset isolation (BTC vs XAU independent partitions)
8. Production decision isolation (decision outputs identical before and after research execution)
"""
import pytest
import numpy as np

from src.research.statistical_validation.bootstrap import run_bootstrap_validation
from src.research.statistical_validation.spread_model import record_spread_observation
from src.research.statistical_validation.execution_stress import run_execution_stress_analysis
from src.research.statistical_validation.calibration import evaluate_probability_calibration
from src.research.statistical_validation.monte_carlo import run_monte_carlo_simulation
from src.research.statistical_validation.holdout_monitor import evaluate_holdout_milestones
from src.research.statistical_validation.validator import run_full_statistical_validation


class TestBootstrapValidation:
    """Tests for 10,000-resample bootstrap confidence intervals."""

    def test_bootstrap_real_n_preservation(self):
        sample_r = [1.5, -1.0, 1.5, -1.0, 1.5, -1.0, 1.5]
        res = run_bootstrap_validation(sample_r, symbol="BTC/USD", n_resamples=10000, seed=42)
        assert res.real_n == 7
        assert res.bootstrap_resamples == 10000
        assert res.expectancy_r.real_n == 7
        assert res.expectancy_r.bootstrap_resamples == 10000

    def test_bootstrap_reproducibility_with_fixed_seed(self):
        sample_r = [1.5, -1.0, 1.5, -1.0, 1.5, 1.5, -1.0, 1.5, -1.0, 1.5]
        res1 = run_bootstrap_validation(sample_r, symbol="BTC/USD", n_resamples=5000, seed=123)
        res2 = run_bootstrap_validation(sample_r, symbol="BTC/USD", n_resamples=5000, seed=123)
        assert res1.expectancy_r.ci_lower_2_5 == res2.expectancy_r.ci_lower_2_5
        assert res1.expectancy_r.ci_upper_97_5 == res2.expectancy_r.ci_upper_97_5
        assert res1.expectancy_r.mean == res2.expectancy_r.mean

    def test_bootstrap_ci_ordering(self):
        sample_r = [1.5, -1.0, 1.5, 1.5, -1.0, 1.5, -1.0, 1.5, -1.0, 1.5, 1.5, -1.0]
        res = run_bootstrap_validation(sample_r, symbol="XAU/USD", n_resamples=10000, seed=42)
        assert res.expectancy_r.ci_lower_2_5 <= res.expectancy_r.median <= res.expectancy_r.ci_upper_97_5
        assert res.total_r.ci_lower_2_5 <= res.total_r.median <= res.total_r.ci_upper_97_5
        assert res.win_rate_pct.ci_lower_2_5 <= res.win_rate_pct.median <= res.win_rate_pct.ci_upper_97_5


class TestSpreadModel:
    """Tests for bid/ask spread tracking and missing spread handling."""

    def test_valid_bid_ask_spread_calculation(self):
        rec = record_spread_observation(
            symbol="BTC-USD",
            bid=76500.0,
            ask=76501.5,
            current_price=76500.75,
            risk_r_usd=300.0,
        )
        assert rec.status == "AVAILABLE"
        assert rec.research_limitation == "NONE"
        assert rec.spread_usd == 1.5
        assert rec.mid == 76500.75
        assert rec.spread_r == round(1.5 / 300.0, 4)

    def test_missing_spread_explicit_unavailable_status(self):
        rec = record_spread_observation(
            symbol="XAU-USD-SPOT",
            bid=None,
            ask=None,
            current_price=4320.0,
        )
        assert rec.status == "SPREAD_DATA_UNAVAILABLE"
        assert rec.research_limitation == "LIMITED"
        assert rec.spread_usd is None
        assert rec.spread_r is None


class TestExecutionStress:
    """Tests for slippage and latency degradation modeling."""

    def test_slippage_degradation_levels(self):
        sample_r = [1.5, -1.0, 1.5, 1.5, -1.0, 1.5, -1.0, 1.5]
        rep = run_execution_stress_analysis(sample_r, symbol="BTC/USD")
        assert len(rep.slippage_scenarios) == 5
        slippage_vals = [s.slippage_r for s in rep.slippage_scenarios]
        assert slippage_vals == [0.00, 0.05, 0.10, 0.15, 0.20]

        # Expectancy must strictly decrease with higher slippage
        expectancies = [s.effective_expectancy_r for s in rep.slippage_scenarios]
        for i in range(len(expectancies) - 1):
            assert expectancies[i] > expectancies[i + 1]

    def test_strategy_classification(self):
        # Highly positive series -> ROBUST
        robust_r = [1.5, 1.5, 1.5, 1.5, 1.5, -1.0, 1.5, 1.5]
        rep_robust = run_execution_stress_analysis(robust_r, symbol="BTC/USD")
        assert rep_robust.classification in ("ROBUST", "SENSITIVE")

        # Weak positive series -> FRAGILE under 0.10R slippage
        weak_r = [1.5, -1.0, 1.5, -1.0, -1.0, 1.5, -1.0, -1.0]
        rep_weak = run_execution_stress_analysis(weak_r, symbol="BTC/USD")
        assert rep_weak.classification == "FRAGILE"


class TestProbabilityCalibration:
    """Tests for Brier score, ECE, and reliability binning."""

    def test_calibration_metrics(self):
        probs = [0.40, 0.45, 0.55, 0.60, 0.70, 0.35, 0.52, 0.65]
        outcomes = [0, 0, 1, 1, 1, 0, 1, 1]
        cal = evaluate_probability_calibration(probs, outcomes, symbol="BTC/USD")
        assert cal.sample_size == 8
        assert cal.calibrated_brier_score >= 0.0
        assert cal.calibrated_ece_pct >= 0.0
        assert len(cal.buckets) > 0


class TestMonteCarloSimulation:
    """Tests for 10,000-path Monte Carlo risk modeling."""

    def test_monte_carlo_10000_paths(self):
        sample_r = [1.5, -1.0, 1.5, -1.0, 1.5, 1.5, -1.0]
        mc = run_monte_carlo_simulation(sample_r, symbol="BTC/USD", n_paths=10000, seed=42)
        assert mc.real_n == 7
        assert mc.simulated_paths == 10000
        assert mc.percentile_1st_final_r <= mc.percentile_5th_final_r <= mc.median_final_r
        assert mc.median_max_drawdown_r <= mc.percentile_95th_drawdown_r <= mc.percentile_99th_drawdown_r


class TestHoldoutMilestones:
    """Tests for progressive sample milestone monitoring."""

    def test_xau_holdout_insufficient_sample_below_50(self):
        rep = evaluate_holdout_milestones(symbol="XAU/USD", current_holdout_n=42, forward_shadow_resolved_n=0)
        assert rep.current_holdout_n == 42
        assert rep.sample_sufficiency_status == "INSUFFICIENT_SAMPLE"
        assert rep.active_milestone_target == 50

    def test_xau_holdout_preliminary_above_50(self):
        rep = evaluate_holdout_milestones(symbol="XAU/USD", current_holdout_n=42, forward_shadow_resolved_n=15)
        assert rep.total_evaluable_n == 57
        assert rep.sample_sufficiency_status == "PRELIMINARY"
        assert rep.active_milestone_target == 75


class TestAssetAndProductionIsolation:
    """Tests proving strict asset isolation and zero production decision impact."""

    def test_asset_isolation(self):
        btc_val = run_full_statistical_validation(symbol="BTC/USD", n_bootstrap=1000, n_monte_carlo=1000)
        xau_val = run_full_statistical_validation(symbol="XAU/USD", n_bootstrap=1000, n_monte_carlo=1000)
        assert btc_val.symbol == "BTC/USD"
        assert xau_val.symbol == "XAU/USD"
        assert btc_val.holdout_milestones.current_holdout_n == 152
        assert xau_val.holdout_milestones.current_holdout_n == 42

    def test_production_isolation_unaffected_by_research(self):
        from src.services.decision_engine import DecisionEngine
        from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

        ta = _make_ta(price=2700.0)
        ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
        mtf_in = _make_mtf_input(ta_map, price=2700.0)
        ai_in = _make_ai_result()

        engine = DecisionEngine()
        dec_before, breakdown_before = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Run heavy research execution (bootstrap, stress, Monte Carlo)
        _ = run_full_statistical_validation(symbol="XAU/USD", n_bootstrap=2000, n_monte_carlo=2000)

        # Re-evaluate under identical inputs
        dec_after, breakdown_after = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Must be 100% identical in all production decision logic
        assert dec_before.decision == dec_after.decision
        assert dec_before.signal_strength == dec_after.signal_strength
        assert dec_before.stop_loss == dec_after.stop_loss
        assert dec_before.take_profit_1 == dec_after.take_profit_1
        assert dec_before.take_profit_2 == dec_after.take_profit_2
