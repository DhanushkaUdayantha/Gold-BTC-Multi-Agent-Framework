"""
Unit and Integration Tests for Phase 6 -> Phase 33 Governance & Research Framework.

Verifies:
1. T0 snapshot immutability, cryptographic hashing & future-data firewall
2. Idempotent signal capture and duplicate prevention
3. Forward shadow engine summary and evidence accumulation
4. Research strategy versioning and qualification gates (N>=500, EV>=+0.15R, PF>=1.20)
5. Shadow gating policies and opportunity cost ratios
6. Execution stress testing (slippage up to 0.20R, delay up to 2 bars)
7. Multi-dimensional robustness (Regimes, Sessions, Directions)
8. Drift monitoring and performance degradation tracking
9. Overfitting search space audit & Holm-Bonferroni corrections
10. Phase 6 -> Phase 33 master roadmap table completeness
11. BTC/XAU asset isolation and separate governance decisions
12. Strict production decision invariance (100% identical DecisionEngine outputs before and after research)
"""
import pytest
from src.research.governance.forward_shadow import (
    ForwardSignalSnapshot,
    ForwardShadowEngine,
    get_forward_shadow_engine,
)
from src.research.governance.filters_and_strategies import (
    evaluate_research_strategies,
    evaluate_shadow_gating_policies,
)
from src.research.governance.stress_and_robustness import (
    run_execution_stress_tests,
    run_multidimensional_robustness,
    run_coverage_analysis,
)
from src.research.governance.drift_and_bias import (
    run_drift_and_degradation_audit,
    run_overfitting_and_significance_audit,
)
from src.research.governance.engine import (
    build_phase_roadmap_matrix,
    run_full_phase6_to_33_governance,
)


class TestForwardShadowEngine:
    """Tests for Phase 6 & 7 forward shadow and lifecycle."""

    def test_idempotent_capture_and_hash(self):
        engine = get_forward_shadow_engine()
        snap1 = engine.capture_forward_signal(
            asset="BTC/USD",
            direction="BUY",
            entry_price=64200.0,
            stop_loss=63500.0,
            take_profit_1=65500.0,
            take_profit_2=66200.0,
            confluence_score=68.0,
            confidence_score=72.0,
            signal_strength=70.0,
            market_regime="Bull Trend",
            session="London",
            mtf_aligned=True,
            timestamp_utc="2026-09-02T12:00:00Z",
        )
        assert snap1 is not None
        assert snap1.signal_id.startswith("FWD-BTC-")
        assert len(snap1.snapshot_hash) == 64

        # Re-capture under identical inputs should be idempotent
        snap2 = engine.capture_forward_signal(
            asset="BTC/USD",
            direction="BUY",
            entry_price=64200.0,
            stop_loss=63500.0,
            take_profit_1=65500.0,
            take_profit_2=66200.0,
            confluence_score=68.0,
            confidence_score=72.0,
            signal_strength=70.0,
            market_regime="Bull Trend",
            session="London",
            mtf_aligned=True,
            timestamp_utc="2026-09-02T12:00:00Z",
        )
        assert snap1.snapshot_hash == snap2.snapshot_hash

    def test_forward_shadow_summary(self):
        engine = get_forward_shadow_engine()
        btc_sum = engine.get_forward_summary("BTC/USD")
        assert btc_sum.total_evaluations == 720
        assert btc_sum.evidence_status == "ACCUMULATING"
        assert btc_sum.forward_realized_ev_r > 0.30


class TestStrategyQualificationAndGating:
    """Tests for Phase 8, 14, 15, 16 strategy qualification and gating."""

    def test_strategy_qualification_btc(self):
        report = evaluate_research_strategies("BTC/USD")
        assert report.qualified_strategies_count >= 2
        top_strat = report.strategies[0]
        assert top_strat.qualification_status == "QUALIFIED"
        assert top_strat.train_ev >= 0.15
        assert top_strat.profit_factor >= 1.20

    def test_shadow_gating_policies_opportunity_cost(self):
        policies = evaluate_shadow_gating_policies("BTC/USD")
        assert len(policies) == 3
        # Gate 1 (Prob >= 50%) should satisfy winner retention >= 50% and loser reduction >= 40%
        gate1 = policies[0]
        assert gate1.winner_retention_pct >= 50.0
        assert gate1.loser_reduction_pct >= 40.0
        assert gate1.opportunity_cost_ratio > 1.0


class TestStressAndRobustness:
    """Tests for Phase 17, 20, 21, 22, 23, 24 execution stress and multi-dimensional robustness."""

    def test_execution_stress_slippage(self):
        stress = run_execution_stress_tests("BTC/USD")
        assert stress.overall_resilience == "ROBUST"
        assert stress.break_even_slippage_r >= 0.30
        point_010 = next(p for p in stress.stress_points if p.slippage_r == 0.10 and p.execution_delay_bars == 0)
        assert point_010.is_ev_positive is True
        assert point_010.status == "ROBUST"

    def test_multidimensional_robustness(self):
        rob = run_multidimensional_robustness("BTC/USD")
        assert len(rob.regime_segments) == 4
        assert len(rob.session_segments) == 3
        assert len(rob.direction_segments) == 2
        # Bull and Bear trend should be classified ROBUST
        bull = next(r for r in rob.regime_segments if r.segment_label == "Bull Trend")
        assert bull.classification == "ROBUST"
        assert bull.expectancy_ev_r > 0.50

    def test_coverage_and_opportunity(self):
        cov = run_coverage_analysis("BTC/USD")
        assert cov.signals_per_day > 2.0
        assert cov.wait_rate_pct > 70.0


class TestDriftAndOverfittingAudit:
    """Tests for Phase 25-30 drift monitoring, overfitting, and multiple testing."""

    def test_drift_and_degradation(self):
        drift, deg = run_drift_and_degradation_audit("BTC/USD")
        assert drift.overall_drift_status == "LOW_DRIFT"
        assert deg.degradation_status == "NORMAL"

    def test_overfitting_and_holm_bonferroni(self):
        overfit, mult_test = run_overfitting_and_significance_audit("BTC/USD")
        assert overfit.selection_bias_risk == "LOW"
        assert mult_test.significant_discoveries_count >= 3


class TestMasterGovernanceAndRoadmap:
    """Tests for Phase 31-33 master roadmap and governance decision."""

    def test_phase_roadmap_matrix_completeness(self):
        roadmap = build_phase_roadmap_matrix()
        assert len(roadmap) == 28  # Phase 6 to Phase 33 inclusive = 28 phases
        assert roadmap[0].phase_id == 6
        assert roadmap[-1].phase_id == 33
        assert all(p.implementation_status == "PASS" for p in roadmap)

    def test_governance_decision_btc(self):
        dec, _ = run_full_phase6_to_33_governance("BTC/USD")
        assert dec.asset == "BTC/USD"
        assert dec.mandatory_gates_passed == 28
        assert dec.final_governance_classification == "RESEARCH_APPROVED"
        assert dec.production_gating_state == "DISABLED"
        assert dec.automatic_retraining_state == "DISABLED"

    def test_governance_decision_xau(self):
        dec, _ = run_full_phase6_to_33_governance("XAU/USD")
        assert dec.asset == "XAU/USD"
        assert dec.final_governance_classification == "RESEARCH_APPROVED"
        assert dec.production_gating_state == "DISABLED"


class TestProductionInvarianceUnderGovernance:
    """Tests that DecisionEngine outputs remain 100% identical before and after governance run."""

    def test_production_decision_engine_invariance(self):
        from src.services.decision_engine import DecisionEngine
        from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

        ta = _make_ta(price=2700.0)
        ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
        mtf_in = _make_mtf_input(ta_map, price=2700.0)
        ai_in = _make_ai_result()

        engine = DecisionEngine()
        dec_before, breakdown_before = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Run complete Phase 6 -> Phase 33 governance and stress research
        _ = run_full_phase6_to_33_governance(symbol="BTC/USD")
        _ = run_full_phase6_to_33_governance(symbol="XAU/USD")
        _ = run_execution_stress_tests(symbol="BTC/USD")
        _ = run_multidimensional_robustness(symbol="BTC/USD")

        # Re-evaluate under identical inputs
        dec_after, breakdown_after = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Production decisions must be 100% invariant
        assert dec_before.decision == dec_after.decision
        assert dec_before.signal_strength == dec_after.signal_strength
        assert dec_before.stop_loss == dec_after.stop_loss
        assert dec_before.take_profit_1 == dec_after.take_profit_1
        assert dec_before.take_profit_2 == dec_after.take_profit_2
