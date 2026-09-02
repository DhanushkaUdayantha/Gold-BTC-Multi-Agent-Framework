"""
Unit tests for CounterfactualEngine — Phase 4.
"""
import pytest
from src.research.counterfactual_engine import CounterfactualEngine, CounterfactualReport
from src.research.signal_research_record import (
    SignalResearchRecord,
    StrategyScoreSnapshot,
    OutcomeLabel,
)


def _make_dummy_records(n=60) -> list:
    records = []
    for i in range(n):
        is_win = (i % 2 == 0)
        records.append(SignalResearchRecord(
            signal_id=f"SIG_{i:04d}",
            asset="BTC/USD",
            decision="BUY",
            outcome=OutcomeLabel.WIN if is_win else OutcomeLabel.LOSS,
            realized_r=1.5 if is_win else -1.0,
            mae_r=0.4 if is_win else 1.2,
            mfe_r=2.2 if is_win else 0.5,
            strategy_scores=StrategyScoreSnapshot(confluence_score=75 if is_win else 50, confirmation_score=3 if is_win else 1),
        ))
    return records


class TestCounterfactualEngine:
    def test_run_counterfactual_analysis(self):
        records = _make_dummy_records(60)
        report = CounterfactualEngine.run_counterfactual_analysis(records)
        assert isinstance(report, CounterfactualReport)
        assert report.total_trades_analyzed == 60
        assert report.total_scenarios_tested >= 4

    def test_generate_counterfactual_reports(self):
        records = _make_dummy_records(60)
        json_path, md_path = CounterfactualEngine.generate_counterfactual_reports(records)
        assert json_path.endswith("COUNTERFACTUAL_RESEARCH.json")
        assert md_path.endswith("COUNTERFACTUAL_RESEARCH.md")
