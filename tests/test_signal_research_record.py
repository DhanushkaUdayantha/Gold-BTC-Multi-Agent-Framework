"""
Tests for signal_research_record.py — Phase 3.
"""
import pytest
from src.research.signal_research_record import (
    SignalResearchRecord,
    MTFSnapshot,
    IndicatorSnapshot,
    StrategyScoreSnapshot,
    AISnapshot,
    GatingSnapshot,
    OutcomeLabel,
    SignalDecision,
    build_minimal_record,
    RESEARCH_VERSION,
)


class TestSignalResearchRecordDefaults:
    def test_default_construction(self):
        rec = SignalResearchRecord()
        assert rec.research_version == RESEARCH_VERSION
        assert rec.outcome == OutcomeLabel.OPEN
        assert rec.decision == SignalDecision.WAIT
        assert rec.is_trade is False
        assert rec.is_resolved is False

    def test_is_trade_requires_entry_sl_tp(self):
        rec = SignalResearchRecord(
            decision="BUY",
            entry_price=1900.0,
            stop_loss=1895.0,
            take_profit_1=1915.0,
        )
        assert rec.is_trade is True

    def test_is_trade_false_for_wait(self):
        rec = SignalResearchRecord(decision="WAIT")
        assert rec.is_trade is False

    def test_is_resolved_win(self):
        rec = SignalResearchRecord(outcome=OutcomeLabel.WIN, realized_r=1.5)
        assert rec.is_resolved is True
        assert rec.realized_r_safe == 1.5

    def test_is_resolved_open(self):
        rec = SignalResearchRecord(outcome=OutcomeLabel.OPEN)
        assert rec.is_resolved is False
        assert rec.realized_r_safe == 0.0

    def test_to_dict_roundtrip(self):
        rec = build_minimal_record(
            signal_id="TEST_001",
            asset="XAU/USD",
            timestamp="2024-03-15T10:00:00Z",
            decision="BUY",
            price=2000.0,
            entry_price=2001.0,
            stop_loss=1990.0,
            take_profit_1=2020.0,
        )
        d = rec.to_dict()
        assert d["signal_id"] == "TEST_001"
        assert d["asset"] == "XAU/USD"
        assert d["decision"] == "BUY"

    def test_from_dict_roundtrip(self):
        rec = build_minimal_record(
            signal_id="TEST_002",
            asset="BTC/USD",
            timestamp="2024-06-01T12:00:00Z",
            decision="SELL",
            price=65000.0,
        )
        d = rec.to_dict()
        rec2 = SignalResearchRecord.from_dict(d)
        assert rec2.signal_id == "TEST_002"
        assert rec2.asset == "BTC/USD"
        assert rec2.decision == "SELL"

    def test_input_fingerprint_deterministic(self):
        rec = build_minimal_record("A", "XAU/USD", "2024-01-01T00:00:00Z", "BUY", 1900.0)
        fp1 = rec.input_fingerprint()
        fp2 = rec.input_fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_input_fingerprint_changes_with_data(self):
        rec1 = build_minimal_record("A", "XAU/USD", "2024-01-01T00:00:00Z", "BUY", 1900.0)
        rec2 = build_minimal_record("B", "XAU/USD", "2024-01-01T00:00:00Z", "BUY", 1900.0)
        assert rec1.input_fingerprint() != rec2.input_fingerprint()

    def test_build_minimal_sets_day_and_hour(self):
        rec = build_minimal_record("X", "XAU/USD", "2024-03-15T14:30:00Z", "BUY", 1900.0)
        assert rec.hour_utc == 14
        assert rec.day_of_week in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

    def test_risk_r_computed(self):
        rec = build_minimal_record(
            "R", "XAU/USD", "2024-01-01T00:00:00Z", "BUY", 1900.0,
            entry_price=1900.0, stop_loss=1895.0,
        )
        assert rec.risk_r == pytest.approx(5.0, abs=0.01)

    def test_nested_dataclasses_present(self):
        rec = SignalResearchRecord()
        assert isinstance(rec.mtf, MTFSnapshot)
        assert isinstance(rec.indicators, IndicatorSnapshot)
        assert isinstance(rec.strategy_scores, StrategyScoreSnapshot)
        assert isinstance(rec.ai, AISnapshot)
        assert isinstance(rec.gating, GatingSnapshot)
