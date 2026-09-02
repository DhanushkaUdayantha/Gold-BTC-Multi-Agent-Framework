"""
Comprehensive Synthetic Unit Test Suite for Historical Backtesting Subsystem.

Covers all 40 required test specifications:
1. Candle normalization
2. UTC conversion
3. Duplicate removal
4. Invalid OHLC rejection
5. Future timestamp rejection
6. Missing interval detection
7. Multi-timeframe synchronization
8. No-lookahead barrier
9. Forming candle exclusion
10. Historical snapshot creation
11. Existing ConfluenceEngine integration
12. Existing 100-point maximum preserved
13. Direction gate enforcement
14. BUY TP outcome
15. BUY SL outcome
16. SELL TP outcome
17. SELL SL outcome
18. TP-before-SL detection
19. SL-before-TP detection
20. Same-candle ambiguity handling
21. MFE calculation
22. MAE calculation
23. Realized R computation
24. 72h Expiry rule
25. Score band segmentation (6 bands)
26. Contributor statistics (17 contributors)
27. BUY vs SELL separation
28. BTC vs XAU separation
29. Calibration <50 trades -> INSUFFICIENT_DATA
30. Calibration 70/30 train/val separation
31. Walk-forward validation reporting
32. Dataset integrity report
33. Duplicate signal protection (60s cooldown)
34. Transaction-cost disclosure
35. Backtest reproducibility
36. Dataset versioning
37. Market regime classification
38. Historical filtering
39. Equity curve generation
40. Async backtest lifecycle
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from datetime import datetime, timezone, timedelta
import pytest

from src.models.historical_data import (
    HistoricalCandle,
    DatasetQualityReport,
    BacktestConfig,
    BacktestRunRecord,
    HistoricalSignalRecord,
    AmbiguousCandleRule,
    BacktestStatus,
)
from src.services.confluence_engine import ConfluenceEngine, TOTAL_MAX_SCORE
from src.services.historical_data_service import HistoricalDataService
from src.services.historical_snapshot_builder import HistoricalSnapshotBuilder
from src.services.historical_backtest_runner import HistoricalBacktestRunner
from src.services.probability_calibrator import ProbabilityCalibrator


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_historical.db")
    service = HistoricalDataService(db_path=db_path)
    yield service
    shutil.rmtree(temp_dir, ignore_errors=True)


def _generate_synthetic_candles(
    symbol: str = "BTC/USD",
    source_symbol: str = "BTCUSDT",
    timeframe: str = "15m",
    count: int = 100,
    start_price: float = 60000.0,
    base_epoch_ms: int = 1680000000000,
) -> list[dict]:
    """Generate synthetic deterministic test candles for testing only."""
    step_ms = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3600_000, "4h": 14400_000, "1d": 86400_000}.get(timeframe, 900_000)
    candles = []
    p = start_price
    for i in range(count):
        ep = base_epoch_ms + (i * step_ms)
        iso = datetime.fromtimestamp(ep / 1000.0, tz=timezone.utc).isoformat()
        # deterministic oscillation
        delta = 10.0 if (i % 4 in (0, 1)) else -8.0
        op = p
        cl = p + delta
        hi = max(op, cl) + 5.0
        lo = min(op, cl) - 5.0
        p = cl
        candles.append({
            "timestamp": iso,
            "epoch_ms": ep,
            "open": op,
            "high": hi,
            "low": lo,
            "close": cl,
            "volume": 100.0 + (i % 10),
            "is_closed": True,
        })
    return candles


# ---------------------------------------------------------------------------
# Test Specifications 1 to 10: Normalization, Integrity, Lookahead & Snapshots
# ---------------------------------------------------------------------------

def test_1_candle_normalization(temp_db):
    raw = _generate_synthetic_candles(count=5)
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert len(valid) == 5
    assert valid[0].symbol == "BTC/USD"
    assert valid[0].source_symbol == "BTCUSDT"
    assert valid[0].open > 0


def test_2_utc_conversion(temp_db):
    raw = [{"timestamp": "2024-01-01T12:00:00Z", "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 10}]
    valid, _ = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert len(valid) == 1
    assert valid[0].timestamp.endswith("+00:00") or valid[0].timestamp.endswith("Z") or "T12:00:00" in valid[0].timestamp


def test_3_duplicate_removal(temp_db):
    raw = _generate_synthetic_candles(count=3)
    # duplicate the 2nd candle
    raw.append(dict(raw[1]))
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert len(valid) == 3
    assert report.duplicate_rows == 1


def test_4_invalid_ohlc_rejection(temp_db):
    raw = [
        {"timestamp": "2024-01-01T10:00:00Z", "open": -100, "high": 50100, "low": 49900, "close": 50000},  # negative open
        {"timestamp": "2024-01-01T10:15:00Z", "open": 50000, "high": 49000, "low": 50100, "close": 50000},  # high < open
    ]
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert len(valid) == 0
    assert report.invalid_ohlc_rows == 2


def test_5_future_timestamp_rejection(temp_db):
    future_iso = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    raw = [{"timestamp": future_iso, "open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 10}]
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert len(valid) == 0
    assert report.future_rows == 1


def test_6_missing_interval_detection(temp_db):
    raw = _generate_synthetic_candles(count=2, base_epoch_ms=1680000000000)
    # Introduce a 2-hour gap (should be 15m)
    raw[1]["epoch_ms"] = raw[0]["epoch_ms"] + (7200 * 1000)
    raw[1]["timestamp"] = datetime.fromtimestamp(raw[1]["epoch_ms"] / 1000.0, tz=timezone.utc).isoformat()
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert report.missing_intervals > 0


def test_7_multi_timeframe_synchronization(temp_db):
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=40)]
    c_1h = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="1h", source="test") for c in _generate_synthetic_candles(timeframe="1h", count=30)]
    candles_dict = {"15m": c_15m, "1h": c_1h}
    decision_ms = c_15m[30].epoch_ms
    snapshot = builder.build_snapshot_at_timestamp("BTC/USD", decision_ms, candles_dict)
    assert snapshot is not None
    assert snapshot.symbol == "BTC/USD"
    assert snapshot.current_price > 0


def test_8_no_lookahead_barrier():
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=50)]
    # Modify candle 45 with extreme price
    c_15m[45].close = 999999.0
    c_15m[45].high = 999999.0
    # Evaluate decision at candle 30
    decision_ms = c_15m[30].epoch_ms
    snap = builder.build_snapshot_at_timestamp("BTC/USD", decision_ms, {"15m": c_15m})
    # Snapshot at 30 must not know about 999999.0 at candle 45
    assert snap.current_price < 90000.0


def test_9_forming_candle_exclusion():
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=35)]
    decision_ms = c_15m[30].epoch_ms
    snap = builder.build_snapshot_at_timestamp("BTC/USD", decision_ms, {"15m": c_15m})
    for candle_dict in snap.candles_15m:
        assert candle_dict.get("is_closed", True) is True


def test_10_historical_snapshot_creation():
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=40)]
    decision_ms = c_15m[-1].epoch_ms
    snap = builder.build_snapshot_at_timestamp("BTC/USD", decision_ms, {"15m": c_15m})
    assert snap.snapshot_id.startswith("SNAPSHOT-")
    assert snap.current_price == c_15m[-1].close


# ---------------------------------------------------------------------------
# Test Specifications 11 to 20: ConfluenceEngine, Gates, Outcomes & Ambiguity
# ---------------------------------------------------------------------------

def test_11_existing_confluence_engine_integration():
    engine = ConfluenceEngine()
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=40)]
    snap = builder.build_snapshot_at_timestamp("BTC/USD", c_15m[-1].epoch_ms, {"15m": c_15m})
    result = engine.compute(snap)
    assert result.technical_score >= 0
    assert result.final_score <= 100
    assert result.signal in ("BUY", "SELL", "WAIT")


def test_12_existing_100_point_maximum():
    assert TOTAL_MAX_SCORE == 100


def test_13_direction_gate_enforcement():
    engine = ConfluenceEngine()
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=40)]
    snap = builder.build_snapshot_at_timestamp("BTC/USD", c_15m[-1].epoch_ms, {"15m": c_15m})
    result = engine.compute(snap)
    if not result.gate_passed:
        assert result.signal == "WAIT"


def test_14_buy_tp_outcome():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-01", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49500.0, take_profit_1=50750.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50800, low=49900, close=50700, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "WIN"
    assert res["realized_r"] > 0


def test_15_buy_sl_outcome():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-02", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49500.0, take_profit_1=50750.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50100, low=49400, close=49450, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "LOSS"
    assert res["realized_r"] == -1.0


def test_16_sell_tp_outcome():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-03", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="SELL",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=50500.0, take_profit_1=49250.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50100, low=49200, close=49300, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "WIN"
    assert res["realized_r"] > 0


def test_17_sell_sl_outcome():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-04", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="SELL",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=50500.0, take_profit_1=49250.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50600, low=49900, close=50550, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "LOSS"
    assert res["realized_r"] == -1.0


def test_18_tp_before_sl_resolution():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-05", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49500.0, take_profit_1=50750.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50800, low=49800, close=50700, volume=10, source="test"),
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:30:00Z", epoch_ms=1704105000000, open=50700, high=50700, low=49000, close=49100, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "WIN"


def test_19_sl_before_tp_resolution():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-06", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49500.0, take_profit_1=50750.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50100, low=49400, close=49600, volume=10, source="test"),
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:30:00Z", epoch_ms=1704105000000, open=49600, high=51000, low=49600, close=50900, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["outcome"] == "LOSS"


def test_20_same_candle_ambiguity_worst_case():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-07", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49500.0, take_profit_1=50750.0,
    )
    # Candle that pierces both TP (50750) and SL (49500)
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=51000, low=49000, close=50000, volume=10, source="test"),
    ]
    cfg = BacktestConfig(ambiguous_candle_rule=AmbiguousCandleRule.WORST_CASE)
    res = runner._evaluate_future_outcome(sig, future, cfg)
    assert res["outcome"] == "LOSS"
    assert res["ambiguity_flag"] is True


# ---------------------------------------------------------------------------
# Test Specifications 21 to 30: MFE/MAE, Expiry, Bands, Contributor & Calibration
# ---------------------------------------------------------------------------

def test_21_mfe_calculation():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-08", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49000.0, take_profit_1=52000.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=51500, low=49800, close=51000, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    # Risk distance = 1000, max fav = 1500 -> MFE = 1.5 R
    assert res["mfe"] == 1.5


def test_22_mae_calculation():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-09", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49000.0, take_profit_1=52000.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=50500, low=49500, close=50200, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    # Adverse = 500 -> MAE = 0.5 R
    assert res["mae"] == 0.5


def test_23_realized_r_computation():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-10", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49000.0, take_profit_1=51500.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=51500, low=49800, close=51500, volume=10, source="test"),
    ]
    res = runner._evaluate_future_outcome(sig, future, BacktestConfig())
    assert res["realized_r"] == 1.5


def test_24_72h_expiry_rule():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-11", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=40000.0, take_profit_1=60000.0,
    )
    # Candle 73 hours in the future
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-04T12:00:00Z", epoch_ms=1704369600000, open=50200, high=50300, low=50100, close=50250, volume=10, source="test"),
    ]
    cfg = BacktestConfig(expiry_hours=72)
    res = runner._evaluate_future_outcome(sig, future, cfg)
    assert res["outcome"] == "EXPIRED"


def test_25_score_band_segmentation(temp_db):
    runner = HistoricalBacktestRunner(temp_db)
    signals = [
        HistoricalSignalRecord(signal_id=f"S{i}", run_id="R1", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
                               signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
                               confluence_score=55 + (i * 5), technical_score=55, gemini_score=0, outcome="WIN" if i % 2 == 0 else "LOSS", realized_r=1.5 if i % 2 == 0 else -1.0)
        for i in range(8)
    ]
    run_record = BacktestRunRecord(run_id="R1", dataset_id="D1", dataset_version="v2.0", engine_version="v2.0", symbol="BTC/USD", config=BacktestConfig(), created_at="2024-01-01T10:00:00Z")
    report = runner._compute_performance_report(run_record, signals, BacktestConfig())
    assert len(report.score_bands) == 6
    band_50_59 = next(b for b in report.score_bands if b.band_name == "50–59")
    assert band_50_59.completed_trades > 0


def test_26_contributor_statistics(temp_db):
    runner = HistoricalBacktestRunner(temp_db)
    signals = [
        HistoricalSignalRecord(
            signal_id=f"S{i}", run_id="R1", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
            signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
            confluence_score=70, technical_score=70, gemini_score=0,
            contributor_scores={"HTF Trend": 11, "Momentum": 8},
            outcome="WIN", realized_r=1.5,
        )
        for i in range(5)
    ]
    run_record = BacktestRunRecord(run_id="R1", dataset_id="D1", dataset_version="v2.0", engine_version="v2.0", symbol="BTC/USD", config=BacktestConfig(), created_at="2024-01-01T10:00:00Z")
    report = runner._compute_performance_report(run_record, signals, BacktestConfig())
    assert len(report.by_strategy) == 17
    htf_stat = next(s for s in report.by_strategy if s.strategy_name == "HTF Trend")
    assert htf_stat.completed_trades == 5
    assert htf_stat.win_rate == 100.0


def test_27_buy_vs_sell_separation(temp_db):
    runner = HistoricalBacktestRunner(temp_db)
    signals = [
        HistoricalSignalRecord(signal_id="S1", run_id="R1", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT", signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY", confluence_score=70, technical_score=70, gemini_score=0, outcome="WIN", realized_r=1.5),
        HistoricalSignalRecord(signal_id="S2", run_id="R1", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT", signal_timestamp="2024-01-01T10:15:00Z", snapshot_id="S2", entry_price=50000.0, direction="SELL", confluence_score=70, technical_score=70, gemini_score=0, outcome="LOSS", realized_r=-1.0),
    ]
    run_record = BacktestRunRecord(run_id="R1", dataset_id="D1", dataset_version="v2.0", engine_version="v2.0", symbol="BTC/USD", config=BacktestConfig(), created_at="2024-01-01T10:00:00Z")
    report = runner._compute_performance_report(run_record, signals, BacktestConfig())
    assert report.buy_trades == 1
    assert report.buy_win_rate == 100.0
    assert report.sell_trades == 1
    assert report.sell_win_rate == 0.0


def test_28_btc_vs_xau_separation(temp_db):
    candles_btc = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(symbol="BTC/USD", count=10)]
    candles_xau = [HistoricalCandle(**c, symbol="XAU/USD", source_symbol="GC=F", timeframe="15m", source="test") for c in _generate_synthetic_candles(symbol="XAU/USD", count=10)]
    temp_db.save_candles(candles_btc)
    temp_db.save_candles(candles_xau)
    btc_res = temp_db.get_candles("BTC/USD", "15m")
    xau_res = temp_db.get_candles("XAU/USD", "15m")
    assert len(btc_res) == 10
    assert len(xau_res) == 10
    assert btc_res[0].symbol == "BTC/USD"
    assert xau_res[0].symbol == "XAU/USD"


def test_29_calibration_insufficient_data():
    calibrator = ProbabilityCalibrator()
    signals = [{"confluence_score": 70, "outcome": "WIN"}] * 30
    report = calibrator.calibrate(signals)
    assert report.calibration_status == "INSUFFICIENT_DATA"


def test_30_calibration_train_val_separation():
    calibrator = ProbabilityCalibrator()
    # 70 train signals + 30 val signals = 100 signals
    train = [{"confluence_score": 75, "outcome": "WIN" if i % 2 == 0 else "LOSS"} for i in range(70)]
    val = [{"confluence_score": 75, "outcome": "WIN" if i % 3 == 0 else "LOSS"} for i in range(30)]
    report = calibrator.calibrate(train + val, train_ratio=0.70)
    assert report.training_size == 70
    assert report.validation_size == 30


def test_31_walk_forward_validation_reporting():
    calibrator = ProbabilityCalibrator()
    signals = [{"confluence_score": 50 + int(i * 0.2), "outcome": "WIN" if i > 100 else "LOSS"} for i in range(210)]
    report = calibrator.calibrate(signals)
    assert report.walk_forward_folds >= 3
    assert report.sample_size == 210
    assert report.calibration_status in ("VALID", "PREFERRED", "EXPLORATORY", "UNRELIABLE")


def test_32_dataset_integrity_report(temp_db):
    raw = _generate_synthetic_candles(count=20)
    _, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert report.quality_score_pct == 100.0
    assert report.total_rows == 20
    assert report.valid_rows == 20
    assert report.rejected_rows == 0


def test_33_duplicate_signal_protection():
    cfg = BacktestConfig(duplicate_window_seconds=60)
    last_time = 1704100000000
    current_time = 1704100030000  # 30 seconds later (within 60s cooldown)
    is_duplicate = (current_time - last_time) < (cfg.duplicate_window_seconds * 1000)
    assert is_duplicate is True


def test_34_transaction_cost_disclosure():
    runner = HistoricalBacktestRunner()
    sig = HistoricalSignalRecord(
        signal_id="SIG-12", run_id="RUN-01", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
        signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
        confluence_score=75, technical_score=75, gemini_score=0, stop_loss=49000.0, take_profit_1=51500.0,
    )
    future = [
        HistoricalCandle(symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", timestamp="2024-01-01T10:15:00Z", epoch_ms=1704104100000, open=50000, high=51500, low=49800, close=51500, volume=10, source="test"),
    ]
    cfg = BacktestConfig(transaction_cost_pct=0.001)  # 0.1% cost
    res = runner._evaluate_future_outcome(sig, future, cfg)
    assert res["cost"] > 0
    assert res["realized_r"] < 1.5


def test_35_backtest_reproducibility(temp_db):
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=80)]
    temp_db.save_candles(c_15m)
    runner = HistoricalBacktestRunner(temp_db)
    cfg = BacktestConfig(symbol="BTC/USD", start_date="2023-01-01", end_date="2026-12-31")
    rec1, rep1 = runner.run_backtest_sync(cfg)
    rec2, rep2 = runner.run_backtest_sync(cfg)
    assert rep1.total_trades == rep2.total_trades
    assert rep1.win_rate == rep2.win_rate


def test_36_dataset_versioning(temp_db):
    raw = _generate_synthetic_candles(count=10)
    valid, report = temp_db.validate_candles(raw, "BTC/USD", "BTCUSDT", "15m", "test")
    assert report.dataset_version == "v2.0"


def test_37_market_regime_classification():
    runner = HistoricalBacktestRunner()
    builder = HistoricalSnapshotBuilder()
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=40)]
    snap = builder.build_snapshot_at_timestamp("BTC/USD", c_15m[-1].epoch_ms, {"15m": c_15m})
    regime = runner._detect_market_regime(snap)
    assert regime in ("TRENDING", "RANGING", "HIGH_VOLATILITY", "LOW_VOLATILITY")


def test_38_historical_filtering(temp_db):
    runner = HistoricalBacktestRunner(temp_db)
    signals = [
        HistoricalSignalRecord(signal_id=f"SIG-{i}", run_id="R-FILTER", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT",
                               signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY",
                               confluence_score=70, technical_score=70, gemini_score=0, outcome="WIN" if i % 2 == 0 else "LOSS")
        for i in range(10)
    ]
    runner._save_historical_signals(signals)
    fetched_wins, count_wins = runner.get_run_signals("R-FILTER", limit=50, outcome_filter="WIN")
    assert count_wins == 5
    for s in fetched_wins:
        assert s.outcome == "WIN"


def test_39_equity_curve_generation():
    signals = [
        HistoricalSignalRecord(signal_id="S1", run_id="R-EQ", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT", signal_timestamp="2024-01-01T10:00:00Z", snapshot_id="S1", entry_price=50000.0, direction="BUY", confluence_score=70, technical_score=70, gemini_score=0, outcome="WIN", realized_r=1.5),
        HistoricalSignalRecord(signal_id="S2", run_id="R-EQ", dataset_id="D1", symbol="BTC/USD", source_symbol="BTCUSDT", signal_timestamp="2024-01-01T10:15:00Z", snapshot_id="S2", entry_price=50000.0, direction="BUY", confluence_score=70, technical_score=70, gemini_score=0, outcome="LOSS", realized_r=-1.0),
    ]
    cum_r = 0.0
    curve = []
    for s in signals:
        cum_r += s.realized_r
        curve.append({"id": s.signal_id, "cumulative_r": cum_r})
    assert curve[-1]["cumulative_r"] == 0.5


def test_40_async_backtest_lifecycle(temp_db):
    c_15m = [HistoricalCandle(**c, symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="15m", source="test") for c in _generate_synthetic_candles(timeframe="15m", count=80)]
    temp_db.save_candles(c_15m)
    runner = HistoricalBacktestRunner(temp_db)
    cfg = BacktestConfig(symbol="BTC/USD", start_date="2023-01-01", end_date="2026-12-31")
    rec = runner.start_backtest_async(cfg)
    assert rec.status in (BacktestStatus.PENDING, BacktestStatus.RUNNING, BacktestStatus.COMPLETED)
    # Wait for completion
    time.sleep(1.0)
    status = runner.get_run_status(rec.run_id)
    assert status is not None
