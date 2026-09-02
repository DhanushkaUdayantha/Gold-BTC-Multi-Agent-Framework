"""
Tests for failure_analyzer.py — Phase 3.
"""
import pytest
from src.research.failure_analyzer import (
    FailureAnalyzer,
    FailurePatternAggregator,
    SuccessAnalyzer,
    FailureReason,
    SuccessReason,
)
from src.research.signal_research_record import (
    SignalResearchRecord,
    MTFSnapshot,
    IndicatorSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    OutcomeLabel,
)


def _make_loss(
    decision="BUY",
    regime="UNKNOWN",
    session="NEW_YORK",
    htf_trend="BEARISH",
    htf_aligned=False,
    vwap_aligned=False,
    ema_aligned=False,
    sr_aligned=False,
    mom_aligned=False,
    smc_aligned=True,
    confluence=75,
    confirmation=2,
    ai_prob=0.5,
    outcome=OutcomeLabel.LOSS,
    liquidity_sweep=False,
):
    return SignalResearchRecord(
        decision=decision,
        regime=regime,
        session=session,
        outcome=outcome,
        mtf=MTFSnapshot(
            htf_trend=htf_trend,
            htf_aligned=htf_aligned,
            alignment_score=0 if not htf_aligned else 1,
        ),
        indicators=IndicatorSnapshot(
            vwap_aligned=vwap_aligned,
            ema_aligned=ema_aligned,
            sr_aligned=sr_aligned,
            momentum_aligned=mom_aligned,
            smc_aligned=smc_aligned,
            liquidity_sweep_detected=liquidity_sweep,
        ),
        strategy_scores=StrategyScoreSnapshot(
            confluence_score=confluence,
            confirmation_score=confirmation,
        ),
        ai=AISnapshot(ai_probability=ai_prob),
        realized_r=-1.0,
    )


def _make_win(**kwargs):
    rec = _make_loss(**kwargs)
    object.__setattr__(rec, "outcome", OutcomeLabel.WIN) if hasattr(type(rec), "__setattr__") else None
    rec.outcome = OutcomeLabel.WIN
    rec.realized_r = 1.5
    return rec


class TestFailureAnalyzer:
    def test_returns_unknown_for_non_loss(self):
        rec = _make_loss(outcome=OutcomeLabel.WIN)
        fc = FailureAnalyzer.classify_failure(rec)
        assert fc.primary_reason == FailureReason.UNKNOWN

    def test_detects_wrong_direction_buy_against_bearish(self):
        rec = _make_loss(decision="BUY", htf_trend="BEARISH", htf_aligned=False)
        fc = FailureAnalyzer.classify_failure(rec)
        assert fc.primary_reason in (FailureReason.WRONG_DIRECTION, FailureReason.MTF_CONFLICT, FailureReason.VWAP_FAILURE)

    def test_detects_high_volatility(self):
        rec = _make_loss(regime="HIGH_VOLATILITY")
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.HIGH_VOLATILITY in [fc.primary_reason] + fc.secondary_reasons

    def test_detects_range_chop(self):
        rec = _make_loss(regime="RANGING")
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.RANGE_CHOP in [fc.primary_reason] + fc.secondary_reasons

    def test_detects_low_confluence(self):
        rec = _make_loss(confluence=50)
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.LOW_CONFLUENCE in [fc.primary_reason] + fc.secondary_reasons

    def test_detects_ai_overconfidence(self):
        rec = _make_loss(ai_prob=0.90)
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.AI_OVERCONFIDENCE in [fc.primary_reason] + fc.secondary_reasons

    def test_detects_session_failure(self):
        rec = _make_loss(session="ASIA")
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.SESSION_FAILURE in [fc.primary_reason] + fc.secondary_reasons

    def test_detects_vwap_failure(self):
        rec = _make_loss(vwap_aligned=False)
        fc = FailureAnalyzer.classify_failure(rec)
        assert FailureReason.VWAP_FAILURE in [fc.primary_reason] + fc.secondary_reasons

    def test_at_least_one_reason_produced(self):
        rec = _make_loss(vwap_aligned=False, confluence=45, regime="RANGING")
        fc = FailureAnalyzer.classify_failure(rec)
        assert fc.primary_reason != FailureReason.UNKNOWN
        assert len(fc.evidence) > 0

    def test_confidence_levels(self):
        rec = _make_loss(vwap_aligned=False, confluence=45)
        fc = FailureAnalyzer.classify_failure(rec)
        assert fc.confidence in ("HIGH", "MEDIUM", "LOW")


class TestSuccessAnalyzer:
    def test_high_confluence_win(self):
        rec = SignalResearchRecord(
            outcome=OutcomeLabel.WIN,
            realized_r=2.0,
            regime="TRENDING_BULLISH",
            session="LONDON",
            mtf=MTFSnapshot(htf_aligned=True, alignment_score=3),
            indicators=IndicatorSnapshot(vwap_aligned=True, ema_aligned=True,
                                          sr_aligned=True, momentum_aligned=True,
                                          smc_aligned=True),
            strategy_scores=StrategyScoreSnapshot(confluence_score=80),
            ai=AISnapshot(ai_probability=0.70),
        )
        sc = SuccessAnalyzer.classify_success(rec)
        assert sc.primary_reason in list(SuccessReason)
        assert len(sc.evidence) > 0

    def test_not_win_returns_low_confidence(self):
        rec = SignalResearchRecord(outcome=OutcomeLabel.LOSS)
        sc = SuccessAnalyzer.classify_success(rec)
        assert sc.confidence == "LOW"


class TestFailurePatternAggregator:
    def _make_records(self, n=20):
        records = []
        for i in range(n):
            records.append(_make_loss(
                outcome=OutcomeLabel.LOSS if i % 3 != 0 else OutcomeLabel.WIN,
                confluence=50 + (i % 30),
                session="ASIA" if i % 2 == 0 else "LONDON",
                regime="RANGING" if i % 3 == 0 else "TRENDING_BULLISH",
            ))
        return records

    def test_aggregate_returns_summary(self):
        records = self._make_records(30)
        summary = FailurePatternAggregator.aggregate(records, "TEST")
        assert summary.total_losses >= 0
        assert isinstance(summary.reason_counts, dict)
        assert isinstance(summary.top_3_reasons, list)

    def test_aggregate_by_asset(self):
        records = []
        for i in range(40):
            r = _make_loss(outcome=OutcomeLabel.LOSS)
            r.asset = "BTC/USD" if i < 20 else "XAU/USD"
            records.append(r)
        by_asset = FailurePatternAggregator.aggregate_by_asset(records)
        assert "BTC/USD" in by_asset
        assert "XAU/USD" in by_asset

    def test_aggregate_by_regime(self):
        records = self._make_records(30)
        by_regime = FailurePatternAggregator.aggregate_by_regime(records)
        assert len(by_regime) >= 1

    def test_aggregate_by_session(self):
        records = self._make_records(30)
        by_session = FailurePatternAggregator.aggregate_by_session(records)
        assert "ASIA" in by_session or "LONDON" in by_session

    def test_pct_sums_to_100(self):
        records = self._make_records(40)
        summary = FailurePatternAggregator.aggregate(records, "TEST")
        if summary.total_losses > 0:
            total_pct = sum(summary.reason_pct.values())
            assert abs(total_pct - 100.0) < 0.5
