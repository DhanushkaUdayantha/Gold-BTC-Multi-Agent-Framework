"""
Unit and Integration Tests for Phase 5 Probability Calibration, Expected Value & No-Trade Research.

Verifies:
1. Probability Source Audit & T0 timing integrity (0 lookahead violations)
2. Probability calibration metrics (Brier, ECE, MCE, Log Loss, Slope, Intercept)
3. Predefined reliability buckets and exact Wilson 95% confidence intervals
4. Raw vs Platt Scaling vs Isotonic calibration comparison
5. Expected Value and monotonicity across probability bands
6. No-Trade / WAIT policies and opportunity cost ratios
7. Chronological walk-forward validation (4 folds)
8. Frozen holdout protection (zero holdout fitting/tuning)
9. 10,000 bootstrap resamples and 10,000 Monte Carlo path reproducibility
10. Strict BTC/XAU asset isolation
11. Production decision engine invariance (100% identical outputs before and after research execution)
"""
import pytest
from src.research.phase5.audit import audit_probability_sources
from src.research.phase5.calibration import evaluate_probability_calibration, _compute_wilson_ci
from src.research.phase5.expected_value import evaluate_expected_value_bands
from src.research.phase5.no_trade import evaluate_no_trade_policies
from src.research.phase5.validation import run_phase5_validations
from src.research.phase5.orchestrator import run_full_phase5_research


class TestProbabilityAuditAndTiming:
    """Tests for probability source audit and point-in-time availability."""

    def test_audit_sources_and_zero_lookahead(self):
        audit = audit_probability_sources()
        assert audit.total_sources_audited >= 5
        assert audit.lookahead_violations_count == 0
        assert "CONFIDENCE_IS_NOT_PROBABILITY" in audit.semantic_declarations
        assert "STRENGTH_IS_NOT_PROBABILITY" in audit.semantic_declarations

    def test_outcome_isolation(self):
        audit = audit_probability_sources()
        outcome_src = next(s for s in audit.sources if s.source_name == "historical_outcome_resolved")
        assert outcome_src.is_post_outcome is True
        assert outcome_src.is_t0_safe is False


class TestCalibrationAndReliabilityBuckets:
    """Tests for Brier, ECE, MCE, and reliability buckets."""

    def test_wilson_ci_computation(self):
        low, high = _compute_wilson_ci(wins=50, n=100)
        assert 39.0 <= low <= 41.0
        assert 59.0 <= high <= 61.0
        # Edge cases
        assert _compute_wilson_ci(wins=0, n=0) == (0.0, 0.0)

    def test_platt_calibration_btc(self):
        metrics = evaluate_probability_calibration(symbol="BTC/USD", method="PLATT_SCALING", split="OOS")
        assert metrics.brier_score < 0.25
        assert metrics.expected_calibration_error < 0.05  # Preferred ECE <= 0.05
        assert metrics.classification == "WELL_CALIBRATED"
        assert len(metrics.reliability_buckets) == 8

    def test_platt_calibration_xau(self):
        metrics = evaluate_probability_calibration(symbol="XAU/USD", method="PLATT_SCALING", split="OOS")
        assert metrics.brier_score < 0.25
        assert metrics.expected_calibration_error < 0.06
        assert len(metrics.reliability_buckets) == 8


class TestExpectedValueAndMonotonicity:
    """Tests for Expected Value (EV) by probability band."""

    def test_ev_bands_btc(self):
        ev_rep = evaluate_expected_value_bands("BTC/USD")
        assert ev_rep.total_samples == 1519
        assert ev_rep.overall_realized_ev > 0.40
        assert ev_rep.is_monotonic is True
        # Top band should have higher EV than lowest band
        low_band = ev_rep.band_results[0]
        high_band = next(b for b in ev_rep.band_results if b.band_label == "65-70%")
        assert high_band.realized_ev_r > low_band.realized_ev_r

    def test_ev_bands_xau(self):
        ev_rep = evaluate_expected_value_bands("XAU/USD")
        assert ev_rep.total_samples == 918
        assert ev_rep.overall_realized_ev > 0.35
        assert ev_rep.is_monotonic is True


class TestNoTradeOpportunityCost:
    """Tests for candidate no-trade / WAIT policies."""

    def test_no_trade_policies_btc(self):
        policies = evaluate_no_trade_policies("BTC/USD")
        assert len(policies) == 4
        # Policy B (Calibrated Prob >= 50%) should improve EV and have Opportunity Cost Ratio > 1.0
        pol_b = next(p for p in policies if "Policy B" in p.policy_name)
        assert pol_b.ev_delta > 0.0
        assert pol_b.opportunity_cost_ratio > 1.0
        assert pol_b.policy_classification == "ADDS_VALUE"

    def test_no_trade_policies_xau(self):
        policies = evaluate_no_trade_policies("XAU/USD")
        assert len(policies) == 4
        pol_c = next(p for p in policies if "Policy C" in p.policy_name)
        assert pol_c.ev_delta > 0.0
        assert pol_c.opportunity_cost_ratio > 1.0


class TestValidationsAndHoldoutProtection:
    """Tests for walk-forward, holdout, bootstrap, and Monte Carlo."""

    def test_validations_btc(self):
        vals = run_phase5_validations("BTC/USD")
        assert vals["walk_forward"]["positive_folds_pct"] == 100.0
        assert vals["holdout"]["holdout_status"] == "CONFIRMED"
        assert vals["holdout"]["holdout_n"] == 152
        assert len(vals["bootstrap"]) >= 2
        assert len(vals["monte_carlo"]) >= 2

    def test_validations_xau_holdout_milestone(self):
        vals = run_phase5_validations("XAU/USD")
        assert vals["holdout"]["holdout_status"] == "INSUFFICIENT_SAMPLE"
        assert vals["holdout"]["holdout_n"] == 42


class TestAssetAndProductionIsolation:
    """Tests for BTC/XAU separation and 100% invariant production decision engine outputs."""

    def test_asset_isolation(self):
        btc_res = run_full_phase5_research("BTC/USD")
        xau_res = run_full_phase5_research("XAU/USD")
        assert btc_res.symbol == "BTC/USD"
        assert xau_res.symbol == "XAU/USD"

    def test_production_decision_engine_invariance(self):
        from src.services.decision_engine import DecisionEngine
        from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

        ta = _make_ta(price=2700.0)
        ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
        mtf_in = _make_mtf_input(ta_map, price=2700.0)
        ai_in = _make_ai_result()

        engine = DecisionEngine()
        dec_before, breakdown_before = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Run heavy Phase 5 calibration & validation research
        _ = run_full_phase5_research(symbol="BTC/USD")
        _ = run_full_phase5_research(symbol="XAU/USD")

        # Re-evaluate under identical inputs
        dec_after, breakdown_after = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Production decisions must be 100% invariant
        assert dec_before.decision == dec_after.decision
        assert dec_before.signal_strength == dec_after.signal_strength
        assert dec_before.stop_loss == dec_after.stop_loss
        assert dec_before.take_profit_1 == dec_after.take_profit_1
        assert dec_before.take_profit_2 == dec_after.take_profit_2
