"""
Tests for filter_ablation.py — Phase 3.
"""
import pytest
import numpy as np
from src.research.filter_ablation import FilterAblationEngine, FilterVerdict
from src.research.signal_research_record import (
    SignalResearchRecord,
    IndicatorSnapshot,
    MTFSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    GatingSnapshot,
    OutcomeLabel,
)


def _make_record(
    outcome: str,
    realized_r: float,
    vwap_aligned: bool = True,
    ema_aligned: bool = True,
    sr_aligned: bool = True,
    momentum_aligned: bool = True,
    htf_aligned: bool = True,
    smc_aligned: bool = True,
    confluence: int = 70,
    ai_prob: float = 0.55,
    ts_idx: int = 0,
) -> SignalResearchRecord:
    return SignalResearchRecord(
        decision="BUY",
        signal_timestamp=f"2024-01-{(ts_idx % 28)+1:02d}T{(ts_idx % 24):02d}:00:00Z",
        outcome=outcome,
        realized_r=realized_r,
        session="LONDON",
        regime="TRENDING",
        indicators=IndicatorSnapshot(
            vwap_aligned=vwap_aligned,
            ema_aligned=ema_aligned,
            sr_aligned=sr_aligned,
            momentum_aligned=momentum_aligned,
            smc_aligned=smc_aligned,
        ),
        mtf=MTFSnapshot(htf_aligned=htf_aligned, alignment_score=3 if htf_aligned else 0),
        strategy_scores=StrategyScoreSnapshot(confluence_score=confluence, confirmation_score=3),
        ai=AISnapshot(ai_probability=ai_prob),
    )


def _build_ablation_records(n: int = 200, seed: int = 42) -> list:
    rng = np.random.default_rng(seed)
    records = []
    for i in range(n):
        r_val   = float(rng.choice([-1.0, 1.5], p=[0.43, 0.57]))
        outcome = OutcomeLabel.WIN if r_val > 0 else OutcomeLabel.LOSS
        # Misaligned when losing
        vwap_a  = bool(outcome == OutcomeLabel.WIN or rng.random() > 0.6)
        ema_a   = bool(outcome == OutcomeLabel.WIN or rng.random() > 0.5)
        records.append(_make_record(
            outcome, r_val,
            vwap_aligned=vwap_a,
            ema_aligned=ema_a,
            ts_idx=i,
        ))
    return records


class TestFilterAblationEngine:
    def test_run_ablation_returns_report(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        assert report is not None
        assert report.total_filters_tested == 12

    def test_all_filters_tested(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        filter_names = [r.filter_name for r in report.results]
        assert "VWAP_ALIGNMENT" in filter_names
        assert "EMA_ALIGNMENT" in filter_names
        assert "MTF_ALIGNMENT" in filter_names

    def test_verdict_in_valid_values(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        valid = {FilterVerdict.ADDS_VALUE, FilterVerdict.MARGINAL, FilterVerdict.NO_VALUE,
                 FilterVerdict.HURTS, FilterVerdict.INSUFFICIENT_DATA}
        for result in report.results:
            assert result.verdict in valid

    def test_winner_retention_in_range(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        for result in report.results:
            assert 0.0 <= result.winner_retention_pct <= 100.0

    def test_loser_reduction_in_range(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        for result in report.results:
            assert 0.0 <= result.loser_reduction_pct <= 100.0

    def test_bcr_non_negative(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        for result in report.results:
            assert result.benefit_cost_ratio >= 0.0

    def test_experiment_id_unique(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        exp_ids = [r.experiment_id for r in report.results]
        assert len(exp_ids) == len(set(exp_ids))

    def test_best_and_worst_filter_set(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        # These are set to filter names (strings), not None
        assert report.best_filter is not None
        assert report.worst_filter is not None

    def test_summary_lists_categorized(self):
        records = _build_ablation_records(200)
        report = FilterAblationEngine.run_ablation(records)
        # All filters should be in exactly one category
        all_categorized = (
            set(report.adds_value) |
            set(report.marginal) |
            set(report.no_value) |
            set(report.hurts) |
            set(r.filter_name for r in report.results if r.verdict == FilterVerdict.INSUFFICIENT_DATA)
        )
        # Every result should appear in one of the category lists
        for res in report.results:
            assert res.filter_name in all_categorized

    def test_passes_filter_vwap(self):
        rec_pass = _make_record(OutcomeLabel.WIN, 1.0, vwap_aligned=True)
        rec_fail = _make_record(OutcomeLabel.WIN, 1.0, vwap_aligned=False)
        assert FilterAblationEngine._passes_filter(rec_pass, "indicators.vwap_aligned", True)
        assert not FilterAblationEngine._passes_filter(rec_fail, "indicators.vwap_aligned", True)

    def test_passes_filter_confluence(self):
        rec = _make_record(OutcomeLabel.WIN, 1.0, confluence=70)
        assert FilterAblationEngine._passes_filter(rec, "_confluence_ge65", True)
        rec2 = _make_record(OutcomeLabel.WIN, 1.0, confluence=50)
        assert not FilterAblationEngine._passes_filter(rec2, "_confluence_ge65", True)
