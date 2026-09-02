"""
Unit tests for SignalQualityOptimizer — Phase 4.
"""
import pytest
from src.research.signal_quality_optimizer import (
    SignalQualityOptimizer,
    RankedCandidateSignal,
)
from src.research.signal_research_record import (
    SignalResearchRecord,
    MTFSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    OutcomeLabel,
)


def _make_dummy_records(n=100) -> list:
    records = []
    for i in range(n):
        is_win = (i % 2 == 0)
        records.append(SignalResearchRecord(
            signal_id=f"SIG_{i:04d}",
            asset="BTC/USD" if i % 2 == 0 else "XAU/USD",
            signal_timestamp=f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
            decision="BUY" if i % 3 != 0 else "SELL",
            outcome=OutcomeLabel.WIN if is_win else OutcomeLabel.LOSS,
            realized_r=1.5 if is_win else -1.0,
            mae_r=0.3 if is_win else 1.1,
            mfe_r=2.0 if is_win else 0.4,
            mtf=MTFSnapshot(htf_aligned=is_win, alignment_score=3 if is_win else 0),
            strategy_scores=StrategyScoreSnapshot(confluence_score=75 if is_win else 50, confirmation_score=3 if is_win else 1),
            ai=AISnapshot(ai_probability=0.65 if is_win else 0.45, ai_confidence="HIGH" if is_win else "LOW"),
        ))
    return records


class TestSignalQualityOptimizer:
    def test_analyze_asset_directions(self):
        records = _make_dummy_records(100)
        metrics = SignalQualityOptimizer.analyze_asset_directions(records)
        assert len(metrics) == 6  # 2 assets * 3 directions (BUY, SELL, ALL)
        for m in metrics:
            assert m.asset in ("BTC/USD", "XAU/USD")
            assert m.direction in ("BUY", "SELL", "ALL")

    def test_rank_daily_signals_never_forces_24(self):
        records = _make_dummy_records(100)
        ranked = SignalQualityOptimizer.rank_daily_signals(records, max_daily_signals=24)
        selected = [r for r in ranked if r.is_selected_daily_24]
        assert len(selected) <= 24
        assert all(s.tier in ("TIER_1", "TIER_2") for s in selected)

    def test_evaluate_candidate_improvements(self):
        records = _make_dummy_records(100)
        candidates = SignalQualityOptimizer.evaluate_candidate_improvements(records)
        assert len(candidates) == 2
        cand_ids = [c.candidate_id for c in candidates]
        assert "CANDIDATE_A" in cand_ids
        assert "CANDIDATE_B" in cand_ids

    def test_generate_governance_report(self):
        records = _make_dummy_records(100)
        json_path, md_path = SignalQualityOptimizer.generate_governance_report(records)
        assert json_path.endswith("FINAL_SIGNAL_QUALITY_GOVERNANCE.json")
        assert md_path.endswith("FINAL_SIGNAL_QUALITY_GOVERNANCE.md")
