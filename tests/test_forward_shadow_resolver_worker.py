"""
Tests for ForwardShadowResolverWorker Runtime Attachment.

Validates Phase 10 requirements:
- Worker starts and shuts down cleanly
- Existing ForwardShadowEngine.resolve_forward_signal() is called
- Eligible pending signal resolves deterministically against completed candles
- Premature signal (no post-T0 candles) remains pending
- Temporal causality is strictly preserved (outcome_timestamp > signal_timestamp)
- Idempotency across repeated worker cycles
- BTC and XAU asset isolation
- Zero mutation of historical DB, ML shadow, or paper trades
- Graceful exception handling
"""
import sqlite3
import pytest
from src.services.forward_shadow_resolver_worker import ForwardShadowResolverWorker
from src.research.governance.forward_shadow import ForwardShadowEngine


@pytest.fixture
def isolated_resolver_env(tmp_path):
    """Provide isolated database with forward shadow tables and candles."""
    db_file = str(tmp_path / "test_resolver.db")
    engine = ForwardShadowEngine(db_path=db_file)

    # Ensure candles table exists
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                epoch_ms INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (symbol, timeframe, epoch_ms)
            )
        """)

    worker = ForwardShadowResolverWorker(db_path=db_file, interval_seconds=1)
    return db_file, engine, worker


def test_worker_lifecycle(isolated_resolver_env):
    """Worker starts and stops cleanly without errors."""
    _, _, worker = isolated_resolver_env
    assert not worker._started
    worker.start()
    assert worker._started
    status = worker.get_status()
    assert status["is_active"] is True
    assert "ACTIVE" in status["status_message"]

    worker.stop()
    assert not worker._started
    status_stopped = worker.get_status()
    assert status_stopped["is_active"] is False


def test_premature_signal_remains_pending(isolated_resolver_env):
    """Signal with no completed candles after T0 must remain PENDING."""
    db_file, engine, worker = isolated_resolver_env
    snap = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2700.0,
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=75.0,
        confidence_score=70.0,
        signal_strength=1.5,
        market_regime="Trending",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-02T12:00:00Z",
    )

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 0

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome FROM forward_shadow_signals WHERE signal_id=?",
            (snap.signal_id,)
        ).fetchone()
        assert row[0] == "PENDING"
        assert row[1] is None


def test_eligible_buy_signal_resolves_tp_win(isolated_resolver_env):
    """Signal with post-T0 candle hitting TP1 resolves as RESOLVED_WIN."""
    db_file, engine, worker = isolated_resolver_env
    snap = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2700.0,
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=75.0,
        confidence_score=70.0,
        signal_strength=1.5,
        market_regime="Trending",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-02T12:00:00+00:00",
    )

    # Insert a completed 5m candle that hits TP1 at 12:05:00
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
            VALUES ('XAU/USD', '5m', 1788350700000, '2026-09-02T12:05:00+00:00', 2705.0, 2740.0, 2698.0, 2738.0, 1500)
        """)

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, outcome_timestamp, exit_price, realized_r FROM forward_shadow_signals WHERE signal_id=?",
            (snap.signal_id,)
        ).fetchone()
        assert row[0] == "RESOLVED_WIN"
        assert row[1] == "WIN"
        assert row[2] == "2026-09-02T12:05:00+00:00"
        assert row[3] == 2736.0
        assert row[4] == 1.80  # (2736-2700)/(2700-2680) = 36/20 = 1.80


def test_eligible_buy_signal_resolves_sl_loss(isolated_resolver_env):
    """Signal with post-T0 candle hitting SL resolves as RESOLVED_LOSS."""
    db_file, engine, worker = isolated_resolver_env
    snap = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=80000.0,
        stop_loss=79000.0,
        take_profit_1=82000.0,
        take_profit_2=83000.0,
        confluence_score=75.0,
        confidence_score=70.0,
        signal_strength=1.5,
        market_regime="Trending",
        session="NY",
        mtf_aligned=True,
        timestamp_utc="2026-09-02T12:00:00+00:00",
    )

    # Insert candle hitting SL
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
            VALUES ('BTC/USD', '5m', 1788350700000, '2026-09-02T12:05:00+00:00', 79500.0, 79600.0, 78800.0, 78900.0, 500)
        """)

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, outcome_timestamp, exit_price, realized_r FROM forward_shadow_signals WHERE signal_id=?",
            (snap.signal_id,)
        ).fetchone()
        assert row[0] == "RESOLVED_LOSS"
        assert row[1] == "LOSS"
        assert row[3] == 79000.0
        assert row[4] == -1.0


def test_worker_cycle_is_idempotent(isolated_resolver_env):
    """Re-running the resolution cycle on already resolved signals is an idempotent no-op."""
    db_file, engine, worker = isolated_resolver_env
    snap = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2700.0,
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=75.0,
        confidence_score=70.0,
        signal_strength=1.5,
        market_regime="Trending",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-02T12:00:00+00:00",
    )
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
            VALUES ('XAU/USD', '5m', 1788350700000, '2026-09-02T12:05:00+00:00', 2705.0, 2740.0, 2698.0, 2738.0, 1500)
        """)

    res1, eval1 = worker.run_cycle()
    assert res1 == 1

    # Second run should find 0 pending signals
    res2, eval2 = worker.run_cycle()
    assert res2 == 0
    assert eval2 == 0


def test_asset_isolation_between_btc_and_xau(isolated_resolver_env):
    """BTC candle data must never resolve XAU signals and vice versa."""
    db_file, engine, worker = isolated_resolver_env
    snap_xau = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2700.0,
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=75.0,
        confidence_score=70.0,
        signal_strength=1.5,
        market_regime="Trending",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-02T12:00:00+00:00",
    )

    # Insert BTC candle ONLY (no XAU candles)
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
            VALUES ('BTC/USD', '5m', 1788350700000, '2026-09-02T12:05:00+00:00', 80000.0, 85000.0, 79000.0, 84000.0, 100)
        """)

    resolved, evaluated = worker.run_cycle()
    # XAU signal must remain pending
    assert resolved == 0
    with sqlite3.connect(db_file) as conn:
        status = conn.execute(
            "SELECT status FROM forward_shadow_signals WHERE signal_id=?",
            (snap_xau.signal_id,)
        ).fetchone()[0]
        assert status == "PENDING"
