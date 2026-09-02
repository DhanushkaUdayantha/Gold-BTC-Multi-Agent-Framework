"""
Data Integrity Verification Tests for Live Candle Ingestion.

Tests:
1. Original baseline OHLCV values unchanged after ingestion
2. Duplicate candles are rejected (INSERT OR IGNORE)
3. Only COMPLETED (closed) candles are inserted
4. Singleton guard: calling start() multiple times does not create extra threads
5. Live candles have source='binance_live' or 'yahoo_live'
"""
from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timezone

import pytest

from src.services.historical_data_service import HistoricalDataService
from src.services.live_candle_ingestion_service import (
    LiveCandleIngestionService,
    _latest_completed_5m_epoch_ms,
    CANDLE_INTERVAL_MS,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Create an isolated SQLite database with the historical schema for tests."""
    db_file = str(tmp_path / "test_historical.db")
    svc = HistoricalDataService(db_path=db_file)
    svc._init_db()   # _init_db creates all tables including candles
    return db_file



@pytest.fixture
def populated_db(tmp_db):
    """
    Populate the temp database with a handful of 'kaggle' source 5m candles
    for BTC/USD as the baseline.  These are our immutable reference candles.
    """
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    try:
        # Insert 5 synthetic 'kaggle' candles (2022-01-01 00:00 UTC onwards, 5m apart)
        base_epoch_ms = 1640995200000  # 2022-01-01 00:00:00 UTC
        rows = []
        for i in range(5):
            epoch_ms = base_epoch_ms + i * CANDLE_INTERVAL_MS
            ts = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
            rows.append((
                "BTC/USD", "BTCUSDT", "5m", ts, epoch_ms,
                float(40000 + i),   # open
                float(40100 + i),   # high
                float(39900 + i),   # low
                float(40050 + i),   # close
                float(100 + i),     # volume
                1,                  # is_closed
                "kaggle",           # source (original baseline)
            ))
        conn.executemany(
            """
            INSERT OR IGNORE INTO candles (
                symbol, source_symbol, timeframe, timestamp, epoch_ms,
                open, high, low, close, volume, is_closed, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return tmp_db, rows  # return db path and inserted rows


# ── Test 1: Baseline OHLCV immutability ─────────────────────────────────────

def test_baseline_ohlcv_immutable_after_live_insert(populated_db):
    """
    Original kaggle candles must have identical OHLCV values before AND after
    a live INSERT OR IGNORE for the same timestamps.
    """
    db_path, baseline_rows = populated_db
    svc = HistoricalDataService(db_path=db_path)

    # Snapshot original values
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT epoch_ms, open, high, low, close, volume FROM candles "
        "WHERE symbol='BTC/USD' AND timeframe='5m' ORDER BY epoch_ms"
    )
    original = {row["epoch_ms"]: dict(row) for row in cur.fetchall()}
    conn.close()

    assert len(original) == 5, "Expected 5 baseline candles"

    # Now attempt to insert the SAME timestamps with DIFFERENT OHLCV via live path
    from src.models.historical_data import HistoricalCandle
    override_candles = []
    for epoch_ms in sorted(original.keys()):
        ts = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
        override_candles.append(HistoricalCandle(
            symbol="BTC/USD",
            source_symbol="BTCUSDT",
            timeframe="5m",
            timestamp=ts,
            epoch_ms=epoch_ms,
            open=99999.0,   # ← deliberately different
            high=99999.0,
            low=99999.0,
            close=99999.0,
            volume=0.001,
            is_closed=True,
            source="binance_live",
        ))

    inserted = svc.save_live_candles(override_candles)

    # READ BACK and assert nothing changed
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT epoch_ms, open, high, low, close, volume, source FROM candles "
        "WHERE symbol='BTC/USD' AND timeframe='5m' ORDER BY epoch_ms"
    )
    after = {row["epoch_ms"]: dict(row) for row in cur.fetchall()}
    conn.close()

    assert len(after) == 5, "No new rows should have been added (same timestamps)"
    assert inserted == 0, f"Expected 0 new insertions; got {inserted}"

    for epoch_ms, orig_vals in original.items():
        assert after[epoch_ms]["open"]   == orig_vals["open"],   f"open changed at {epoch_ms}"
        assert after[epoch_ms]["high"]   == orig_vals["high"],   f"high changed at {epoch_ms}"
        assert after[epoch_ms]["low"]    == orig_vals["low"],    f"low changed at {epoch_ms}"
        assert after[epoch_ms]["close"]  == orig_vals["close"],  f"close changed at {epoch_ms}"
        assert after[epoch_ms]["volume"] == orig_vals["volume"], f"volume changed at {epoch_ms}"
        assert after[epoch_ms]["source"] == "kaggle",            f"source changed at {epoch_ms}"


# ── Test 2: New live candles are properly inserted ───────────────────────────

def test_new_live_candles_inserted_with_correct_source(populated_db):
    """
    Candles with timestamps AFTER the existing baseline must be inserted
    and must carry source='binance_live'.
    """
    db_path, baseline_rows = populated_db
    svc = HistoricalDataService(db_path=db_path)

    # Timestamps 10 candles AFTER the last baseline candle
    last_epoch_ms = max(row[4] for row in baseline_rows)
    new_candles = []
    from src.models.historical_data import HistoricalCandle
    for i in range(3):
        epoch_ms = last_epoch_ms + (i + 1) * CANDLE_INTERVAL_MS
        ts = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
        new_candles.append(HistoricalCandle(
            symbol="BTC/USD",
            source_symbol="BTCUSDT",
            timeframe="5m",
            timestamp=ts,
            epoch_ms=epoch_ms,
            open=41000.0,
            high=41100.0,
            low=40900.0,
            close=41050.0,
            volume=200.0,
            is_closed=True,
            source="binance_live",
        ))

    inserted = svc.save_live_candles(new_candles)
    assert inserted == 3, f"Expected 3 insertions; got {inserted}"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT source FROM candles WHERE symbol='BTC/USD' AND timeframe='5m' "
        "AND source != 'kaggle'"
    )
    live_sources = [row["source"] for row in cur.fetchall()]
    conn.close()

    assert len(live_sources) == 3
    assert all(s in ("binance_live", "yahoo_live") for s in live_sources), (
        f"Unexpected source values: {live_sources}"
    )


# ── Test 3: No duplicate timestamps ─────────────────────────────────────────

def test_no_duplicate_timestamps_after_repeated_insert(populated_db):
    """
    Inserting the same new live candle twice must result in exactly ONE row,
    not two.
    """
    db_path, baseline_rows = populated_db
    svc = HistoricalDataService(db_path=db_path)

    last_epoch_ms = max(row[4] for row in baseline_rows)
    new_epoch_ms = last_epoch_ms + CANDLE_INTERVAL_MS

    from src.models.historical_data import HistoricalCandle
    candle = HistoricalCandle(
        symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="5m",
        timestamp=datetime.fromtimestamp(new_epoch_ms / 1000, tz=timezone.utc).isoformat(),
        epoch_ms=new_epoch_ms,
        open=41000.0, high=41100.0, low=40900.0, close=41050.0,
        volume=100.0, is_closed=True, source="binance_live",
    )

    svc.save_live_candles([candle])
    svc.save_live_candles([candle])  # second insert of same row

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol='BTC/USD' AND epoch_ms=?",
        (new_epoch_ms,),
    )
    count = cur.fetchone()[0]
    conn.close()

    assert count == 1, f"Expected exactly 1 row for epoch_ms={new_epoch_ms}; got {count}"


# ── Test 4: Only completed candles guard ─────────────────────────────────────

def test_latest_completed_5m_excludes_forming_candle():
    """
    _latest_completed_5m_epoch_ms() must always return a candle whose
    close time is strictly in the past.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    completed = _latest_completed_5m_epoch_ms()
    close_time_ms = completed + CANDLE_INTERVAL_MS - 1

    assert completed > 0
    assert close_time_ms < now_ms, (
        f"Forming candle leaked: close_time_ms={close_time_ms} >= now_ms={now_ms}"
    )
    # The open time of the next candle (the forming one) must be > now - 5m
    next_candle_ms = completed + CANDLE_INTERVAL_MS
    assert next_candle_ms <= now_ms, (
        f"completed epoch is too far in the future: {next_candle_ms} > {now_ms}"
    )


# ── Test 5: Singleton guard ──────────────────────────────────────────────────

def test_singleton_guard_no_duplicate_threads(tmp_db):
    """
    Calling LiveCandleIngestionService.get_instance().start() multiple times
    must NOT spawn multiple worker threads.
    """
    # Reset singleton for test isolation
    LiveCandleIngestionService._instance = None

    svc = LiveCandleIngestionService(db_path=tmp_db)
    LiveCandleIngestionService._instance = svc

    svc.start()
    time.sleep(0.1)  # let thread spawn

    # Count threads named "LiveCandleIngestionWorker"
    worker_threads = [
        t for t in threading.enumerate()
        if t.name == "LiveCandleIngestionWorker"
    ]
    assert len(worker_threads) == 1, (
        f"Expected 1 worker thread; found {len(worker_threads)}"
    )

    # Call start() again — must be a no-op
    svc.start()
    time.sleep(0.05)

    worker_threads_after = [
        t for t in threading.enumerate()
        if t.name == "LiveCandleIngestionWorker"
    ]
    assert len(worker_threads_after) == 1, (
        f"Duplicate thread created after second start(); found {len(worker_threads_after)}"
    )

    # Clean up
    svc.stop()
    LiveCandleIngestionService._instance = None


# ── Test 6: save_candles() (original method) still uses INSERT OR REPLACE ───

def test_save_candles_uses_insert_or_replace(populated_db):
    """
    Verify that the original save_candles() path (used for Kaggle bulk import)
    still does INSERT OR REPLACE (for completeness / regression guard).
    We do NOT call this from live ingestion — we call save_live_candles().
    """
    db_path, baseline_rows = populated_db
    svc = HistoricalDataService(db_path=db_path)

    last_epoch_ms = max(row[4] for row in baseline_rows)
    from src.models.historical_data import HistoricalCandle
    candle = HistoricalCandle(
        symbol="BTC/USD", source_symbol="BTCUSDT", timeframe="5m",
        timestamp=datetime.fromtimestamp(last_epoch_ms / 1000, tz=timezone.utc).isoformat(),
        epoch_ms=last_epoch_ms,
        open=99999.0, high=99999.0, low=99999.0, close=99999.0,
        volume=0.001, is_closed=True, source="kaggle",
    )

    # save_candles uses INSERT OR REPLACE — it WILL overwrite
    svc.save_candles([candle])

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT close FROM candles WHERE symbol='BTC/USD' AND epoch_ms=?",
        (last_epoch_ms,),
    )
    row = cur.fetchone()
    conn.close()

    # The bulk import path replaces — this is expected and correct for init imports
    assert row["close"] == 99999.0, (
        "save_candles() should use INSERT OR REPLACE (for Kaggle bulk imports)"
    )


# ── Test 7: XAU historical gap reported as DATA GAP (not LIVE, not ERROR) ───

def test_xau_historical_gap_reported_as_data_gap(tmp_db):
    """
    When XAU/USD latest stored candle is significantly older than current time
    (e.g., historical dataset ending 2026-05-31), ingestion status must be
    'DATA GAP' (not 'LIVE', and not 'ERROR').
    """
    # Insert an old historical candle for XAU/USD (e.g. 2026-05-31)
    old_epoch_ms = 1780271700000  # 2026-05-31T23:55:00Z
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        """
        INSERT OR IGNORE INTO candles (
            symbol, source_symbol, timeframe, timestamp, epoch_ms,
            open, high, low, close, volume, is_closed, source
        ) VALUES ('XAU/USD', 'GC=F', '5m', '2026-05-31T23:55:00+00:00', ?, 4543.0, 4545.0, 4540.0, 4542.0, 100.0, 1, 'kaggle_historical')
        """,
        (old_epoch_ms,),
    )
    conn.commit()
    conn.close()

    svc = LiveCandleIngestionService(db_path=tmp_db)
    # Mock _fetch_yahoo_5m to return empty list (simulating unrecoverable gap from free provider)
    svc._fetch_yahoo_5m = lambda start_ms, end_ms: []
    svc._ingest_xau()

    status = svc.get_ingestion_status()
    xau_st = status.get("XAU/USD")
    assert xau_st is not None, "XAU/USD status must exist"
    assert xau_st["status"] == "DATA GAP", f"Expected 'DATA GAP'; got '{xau_st['status']}'"
    assert xau_st["status"] != "LIVE", "Old XAU candle must not be reported as LIVE"
    assert xau_st["status"] != "ERROR", "Missing historical period must not be reported as ERROR"
    assert xau_st["last_candle_epoch_ms"] == old_epoch_ms


# ── Test 8: Small sample (5/8) vs Large sample (247/399) directional strength ──

def test_small_sample_vs_large_sample_directional_strength():
    from src.services.historical_evidence_service import _calc_directional_strength

    # Small sample: 5 wins out of 8 (62.5% raw win rate)
    # Must produce WEAK/neutral evidence due to high binomial uncertainty (Wilson CI width > 50%)
    small_strength = _calc_directional_strength(
        wins=5, n=8, expectancy=0.10, profit_factor=1.10, calibrated_prob=62.5, similar_count=8
    )
    assert small_strength <= 60, (
        f"Small sample (5/8) must be treated as weak evidence (<=60%); got {small_strength}%"
    )

    # Large sample: 247 wins out of 399 (61.8% raw win rate)
    # Must produce SUBSTANTIALLY stronger evidence due to narrow Wilson CI and large N
    large_strength = _calc_directional_strength(
        wins=247, n=399, expectancy=0.34, profit_factor=1.47, calibrated_prob=61.8, similar_count=399
    )
    assert large_strength >= 75, (
        f"Large sample (247/399) must produce strong evidence (>=75%); got {large_strength}%"
    )
    assert large_strength > small_strength + 15, (
        f"Large sample ({large_strength}%) must be substantially stronger than small sample ({small_strength}%)"
    )


# ── Test 9: Close / Balanced Evidence Defaults to WAIT ───────────────────────

def test_close_evidence_defaults_to_wait():
    from src.services.historical_evidence_service import _calc_directional_strength

    # 50% / neutral samples
    buy_s = _calc_directional_strength(wins=50, n=100, expectancy=0.0, profit_factor=1.0)
    sell_s = _calc_directional_strength(wins=49, n=100, expectancy=0.0, profit_factor=1.0)

    assert abs(buy_s - 50) <= 5
    assert abs(sell_s - 50) <= 5

    # If evidence difference is small, bias must be WAIT
    if buy_s >= 65 and buy_s >= sell_s + 15:
        bias = "BUY"
    elif sell_s >= 65 and sell_s >= buy_s + 15:
        bias = "SELL"
    else:
        bias = "WAIT"

    assert bias == "WAIT", f"Close evidence (BUY: {buy_s}%, SELL: {sell_s}%) must result in WAIT; got {bias}"


# ── Test 10: Historical Evidence Package Contains Directional Strengths ──────

def test_historical_evidence_package_directional_strengths(tmp_db):
    """
    HistoricalEvidencePackage must contain buy_strength, sell_strength,
    similarity_strength, and historical_bias.
    """
    from src.services.historical_evidence_service import HistoricalEvidencePackage

    pkg = HistoricalEvidencePackage(
        status="AVAILABLE",
        sample_size=399,
        win_rate=61.8,
        calibrated_probability=61.8,
        expectancy=0.34,
        profit_factor=1.47,
        buy_strength=78,
        sell_strength=31,
        similarity_strength=86,
        historical_bias="BUY",
    )

    assert pkg.buy_strength == 78
    assert pkg.sell_strength == 31
    assert pkg.similarity_strength == 86
    assert pkg.historical_bias == "BUY"


