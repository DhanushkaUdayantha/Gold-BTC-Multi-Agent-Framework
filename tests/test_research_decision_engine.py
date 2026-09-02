"""
Tests for research_decision_engine.py — Phase 3.
"""
import pytest
from src.research.research_decision_engine import (
    ResearchDecisionEngine,
    ResearchDecision,
    EvidenceInput,
)


def _make_evidence(
    total_trades: int = 200,
    expectancy_r: float = 0.15,
    profit_factor: float = 1.35,
    max_drawdown_r: float = 12.0,
    oos_expectancy_r: float = 0.10,
    oos_trades: int = 50,
    wf_positive_ratio: float = 0.80,
    wf_median_expectancy: float = 0.08,
    holdout_expectancy_r: float = 0.08,
    holdout_trades: int = 30,
    stress_passes_slippage: bool = True,
    stress_passes_execution: bool = True,
    mc_p5_drawdown_r: float = 18.0,
    p_value: float = 0.005,
    overfitting_risk: str = "LOW",
    robustness_score: float = 85.0,
    robustness_grade: str = "A",
    brier_score: float = 0.18,
    benefit_cost_ratio: float = 1.6,
) -> EvidenceInput:
    return EvidenceInput(
        expectancy_r=expectancy_r,
        profit_factor=profit_factor,
        max_drawdown_r=max_drawdown_r,
        total_trades=total_trades,
        oos_expectancy_r=oos_expectancy_r,
        oos_trades=oos_trades,
        wf_positive_ratio=wf_positive_ratio,
        wf_median_expectancy=wf_median_expectancy,
        holdout_expectancy_r=holdout_expectancy_r,
        holdout_trades=holdout_trades,
        stress_passes_slippage=stress_passes_slippage,
        stress_passes_execution=stress_passes_execution,
        mc_p5_drawdown_r=mc_p5_drawdown_r,
        p_value=p_value,
        expectancy_ci_lower=0.08,
        expectancy_ci_upper=0.22,
        overfitting_risk=overfitting_risk,
        robustness_score=robustness_score,
        robustness_grade=robustness_grade,
        btc_robustness="ROBUST",
        xau_robustness="ROBUST",
        brier_score=brier_score,
        calibration_classification="WELL_CALIBRATED",
        winner_retention_pct=88.0,
        loser_reduction_pct=65.0,
        benefit_cost_ratio=benefit_cost_ratio,
        filters_adds_value=["VWAP_ALIGNMENT", "EMA_ALIGNMENT"],
        filters_hurts=[],
    )


class TestResearchDecisionEngine:
    def test_production_candidate_requires_top_evidence(self):
        ev = _make_evidence()
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision == ResearchDecision.PRODUCTION_CANDIDATE
        assert rec.evidence_level == "STRONG"
        assert rec.confidence == "HIGH"
        assert rec.gates_failed == 0

    def test_production_candidate_never_auto_deploys(self):
        ev = _make_evidence()
        rec = ResearchDecisionEngine.evaluate(ev)
        assert "RESEARCH ADVISORY ONLY" in rec.disclaimer
        assert "DOES NOT authorize any production change" in rec.disclaimer

    def test_reject_on_negative_expectancy(self):
        ev = _make_evidence(expectancy_r=-0.05)
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision == ResearchDecision.REJECT

    def test_reject_on_insufficient_sample(self):
        ev = _make_evidence(total_trades=40)
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision == ResearchDecision.REJECT

    def test_reject_on_failing_profit_factor(self):
        ev = _make_evidence(profit_factor=0.95)
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision == ResearchDecision.REJECT

    def test_reject_on_excessive_drawdown(self):
        ev = _make_evidence(mc_p5_drawdown_r=45.0)
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision == ResearchDecision.REJECT

    def test_promising_on_moderate_evidence(self):
        ev = _make_evidence(
            robustness_score=60.0,
            robustness_grade="C",
            holdout_trades=10,  # Small holdout
            holdout_expectancy_r=0.01,
            wf_positive_ratio=0.60,
        )
        rec = ResearchDecisionEngine.evaluate(ev)
        assert rec.decision in (ResearchDecision.PROMISING, ResearchDecision.RESEARCH_APPROVED, ResearchDecision.KEEP_ADVISORY)

    def test_12_gates_evaluated(self):
        ev = _make_evidence()
        rec = ResearchDecisionEngine.evaluate(ev)
        assert len(rec.gates) == 12
        gate_names = {g.gate_name for g in rec.gates}
        assert "SAMPLE_SIZE" in gate_names
        assert "POSITIVE_EXPECTANCY" in gate_names
        assert "OOS_POSITIVE" in gate_names
        assert "WALK_FORWARD" in gate_names
        assert "PROFIT_FACTOR" in gate_names
        assert "MONTE_CARLO_DD" in gate_names
        assert "OVERFITTING_RISK" in gate_names
