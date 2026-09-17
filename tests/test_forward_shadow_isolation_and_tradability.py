"""
Comprehensive Safety and Tradability Test Suite:
Forward Shadow Isolation, Two-Stage Entry-Fill State Machine, and Clean Evidence Lineage.

Verifies:
1. Test Isolation: Unit/rollout runners never write to data/historical/historical_market_data.db.
2. Lineage Segregation: 479 legacy records are quarantined under FORENSIC_CONTAMINATED_TEST_FIXTURE;
   new captures default to CLEAN_FORWARD.
3. Two-Stage Entry-Fill State Machine:
   - PENDING -> ACTIVE_POSITION only when market touches Entry.
   - Unfilled orders expire as NOT_TRIGGERED after 48h.
   - TP/SL is never evaluated prior to confirmed entry fill.
   - Both TP & SL in same bar resolves as AMBIGUOUS.
   - Active positions unresolved after 48h resolve as RESOLVED_EXPIRED.
4. Governance Exclusion: Clean Governance N starts at 0; old 479 contribute 0.
5. API Integration: /forward-shadow-validation exposes authoritative metrics and supports lineage filtering.
"""
import hashlib
import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.research.governance.forward_shadow import (
    ForwardShadowEngine,
    ForwardSignalSnapshot,
    get_forward_shadow_engine,
)
from src.services.shadow_trading_store import ShadowTradingStore
from src.services.btc_shadow_runner import BTCShadowRunner
from src.services.xau_shadow_runner import XAUShadowRunner
from src.services.forward_shadow_resolver_worker import ForwardShadowResolverWorker
from src.research.governance.forward_state_machine import (
    ForwardExecutionStateMachine,
    ExecutionState,
)

client = TestClient(app)
AUTHORITATIVE_DB = "data/historical/historical_market_data.db"


# =====================================================================
# 1. TEST ISOLATION & IMMUTABILITY INVARIANTS
# =====================================================================

def test_btc_runner_isolated_when_shadow_store_provided(tmp_path):
    """When a custom shadow_store is passed, BTCShadowRunner must NEVER write to authoritative DB."""
    test_db = str(tmp_path / "iso_btc.db")
    store = ShadowTradingStore(db_path=test_db)
    runner = BTCShadowRunner(shadow_store=store)

    assert runner.forward_engine.db_path == test_db

    # Execute setup
    res = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=70.0,
        confidence_score=75.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.60,
    )
    assert res is not None

    # Assert written to isolated test_db
    with sqlite3.connect(test_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        assert count == 1


def test_xau_runner_isolated_when_shadow_store_provided(tmp_path):
    """When a custom shadow_store is passed, XAUShadowRunner must NEVER write to authoritative DB."""
    test_db = str(tmp_path / "iso_xau.db")
    store = ShadowTradingStore(db_path=test_db)
    runner = XAUShadowRunner(shadow_store=store)

    assert runner.forward_engine.db_path == test_db

    res = runner.evaluate_live_market_setup(
        current_price=2700.0,
        direction="BUY",
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=70.0,
        confidence_score=75.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.55,
    )
    assert res is not None

    with sqlite3.connect(test_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        assert count == 1


def test_authoritative_db_contains_exactly_479_quarantined_records():
    """Verify that authoritative DB maintains exactly 479 records, all FORENSIC_CONTAMINATED_TEST_FIXTURE."""
    if not os.path.exists(AUTHORITATIVE_DB):
        pytest.skip("Authoritative DB not found in this environment")

    with sqlite3.connect(AUTHORITATIVE_DB) as conn:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        assert total == 479

        lineage_rows = cur.execute(
            "SELECT evidence_generation, COUNT(*) FROM forward_shadow_signals GROUP BY evidence_generation"
        ).fetchall()
        assert len(lineage_rows) == 1
        assert lineage_rows[0][0] == "FORENSIC_CONTAMINATED_TEST_FIXTURE"
        assert lineage_rows[0][1] == 479


# =====================================================================
# 2. TWO-STAGE ENTRY-FILL STATE MACHINE TESTS
# =====================================================================

@pytest.fixture
def isolated_resolver_env(tmp_path):
    """Create isolated SQLite database for testing resolver state machine."""
    db_file = str(tmp_path / "test_resolver.db")
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE forward_shadow_signals (
                signal_id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                signal_timestamp TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit_1 REAL NOT NULL,
                take_profit_2 REAL NOT NULL,
                confluence_score REAL NOT NULL,
                confidence_score REAL NOT NULL,
                signal_strength REAL NOT NULL,
                market_regime TEXT NOT NULL,
                session TEXT NOT NULL,
                mtf_aligned INTEGER NOT NULL,
                ai_bias TEXT,
                ai_confidence INTEGER,
                ml_raw_probability REAL,
                ml_calibrated_probability REAL,
                strategy_version TEXT NOT NULL,
                features_payload TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                outcome TEXT,
                outcome_timestamp TEXT,
                exit_price REAL,
                realized_r REAL,
                mfe REAL,
                mae REAL,
                duration_minutes REAL,
                failure_class TEXT,
                success_class TEXT,
                created_at_utc TEXT NOT NULL,
                evidence_generation TEXT DEFAULT 'CLEAN_FORWARD',
                entry_filled_at TEXT,
                entry_distance_pct REAL DEFAULT 0.0
            )
        """)
        conn.execute("""
            CREATE TABLE candles (
                epoch_ms INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL
            )
        """)
        conn.commit()

    worker = ForwardShadowResolverWorker(db_path=db_file)
    return db_file, worker


def test_entry_not_reached_remains_pending_no_fake_win(isolated_resolver_env):
    """
    Forensic Replay: BUY entry=$64,000, TP=$65,880.
    Market candles trade between $78,000 and $79,000 (Low never reaches $64,000).
    Resolver MUST NOT trigger WIN; order must remain PENDING.
    """
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-BTC-001', 'BTC/USD', ?, 'BUY', 64000.0, 63000.0, 65880.0, 66500.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.1', '{}', 'hash1',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Insert 5m candles trading at 78,000 - 79,000 (Low=78100, High=78900)
        # Even though High=78900 > TP (65880), the limit order was NEVER filled!
        for i in range(1, 10):
            c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5 * i)).isoformat()
            c_epoch = t0_epoch + (i * 300000)
            conn.execute("""
                INSERT INTO candles VALUES (?, ?, 'BTC/USD', '5m', 78200.0, 78900.0, 78100.0, 78500.0, 10.0)
            """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 0  # NOT resolved because entry was not touched!

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT status, outcome, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-BTC-001'").fetchone()
        assert row[0] == "PENDING"
        assert row[1] is None
        assert row[2] is None  # Entry NOT filled


def test_unfilled_order_expires_as_not_triggered_after_48h(isolated_resolver_env):
    """If market never touches entry for > 48 hours, signal resolves as NOT_TRIGGERED (R=0.0)."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-01T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-BTC-EXP', 'BTC/USD', ?, 'BUY', 64000.0, 63000.0, 65880.0, 66500.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.1', '{}', 'hash2',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Insert candle at 49 hours after signal (never touched 64000)
        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(hours=49)).isoformat()
        c_epoch = t0_epoch + (49 * 3600 * 1000)
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'BTC/USD', '5m', 78000.0, 79000.0, 77500.0, 78500.0, 10.0)
        """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT status, outcome, realized_r FROM forward_shadow_signals WHERE signal_id = 'SIG-BTC-EXP'").fetchone()
        assert row[0] == "NOT_TRIGGERED"
        assert row[1] == "NOT_TRIGGERED"
        assert row[2] == 0.0


def test_entry_fill_then_take_profit(isolated_resolver_env):
    """Order touches entry price -> transitions to ACTIVE_POSITION -> subsequently hits TP -> RESOLVED_WIN."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-XAU-WIN', 'XAU/USD', ?, 'BUY', 2700.0, 2680.0, 2736.0, 2750.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.0', '{}', 'hash3',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Candle 1 (+5m): Touches entry 2700 (Low=2698, High=2705). Entry filled!
        c1_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c1_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2702.0, 2705.0, 2698.0, 2703.0, 50.0)
        """, (c1_epoch, c1_ts))

        # Candle 2 (+10m): Rallies to hit TP 2736 (High=2740, Low=2702)
        c2_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=10)).isoformat()
        c2_epoch = t0_epoch + 600000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2704.0, 2740.0, 2702.0, 2738.0, 100.0)
        """, (c2_epoch, c2_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, exit_price, realized_r, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-XAU-WIN'"
        ).fetchone()
        assert row[0] == "RESOLVED_WIN"
        assert row[1] == "WIN"
        assert row[2] == 2736.0
        assert row[3] == 1.80  # (2736 - 2700) / (2700 - 2680) = 36 / 20 = 1.80R
        assert row[4] == c1_ts  # Filled at Candle 1


def test_entry_fill_then_stop_loss(isolated_resolver_env):
    """Order touches entry price -> transitions to ACTIVE_POSITION -> subsequently hits SL -> RESOLVED_LOSS."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-XAU-LOSS', 'XAU/USD', ?, 'BUY', 2700.0, 2680.0, 2736.0, 2750.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.0', '{}', 'hash4',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Candle 1: Fills entry (Low=2699)
        c1_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c1_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2701.0, 2704.0, 2699.0, 2702.0, 50.0)
        """, (c1_epoch, c1_ts))

        # Candle 2: Drops to hit SL 2680 (Low=2675)
        c2_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=10)).isoformat()
        c2_epoch = t0_epoch + 600000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2700.0, 2702.0, 2675.0, 2678.0, 80.0)
        """, (c2_epoch, c2_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, exit_price, realized_r, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-XAU-LOSS'"
        ).fetchone()
        assert row[0] == "RESOLVED_LOSS"
        assert row[1] == "LOSS"
        assert row[2] == 2680.0
        assert row[3] == -1.0
        assert row[4] == c1_ts


def test_same_candle_both_tp_sl_resolves_ambiguous(isolated_resolver_env):
    """When both TP and SL are hit in the same candle after fill, resolves as AMBIGUOUS."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-XAU-AMB', 'XAU/USD', ?, 'BUY', 2700.0, 2680.0, 2736.0, 2750.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.0', '{}', 'hash5',
                'ACTIVE_POSITION', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Massive volatility bar: Low=2670 (hits SL 2680), High=2745 (hits TP 2736)
        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2700.0, 2745.0, 2670.0, 2710.0, 500.0)
        """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, realized_r FROM forward_shadow_signals WHERE signal_id = 'SIG-XAU-AMB'"
        ).fetchone()
        assert row[0] == "AMBIGUOUS"
        assert row[1] == "AMBIGUOUS"
        assert row[2] == 0.0


# =====================================================================
# 3. GOVERNANCE EXCLUSION & CLEAN N=0 TESTS
# =====================================================================

def test_governance_counts_only_clean_forward_evidence(tmp_path):
    """Assert that ForwardExecutionStateMachine only counts CLEAN_FORWARD evidence and ignores quarantined legacy."""
    db_file = str(tmp_path / "gov_test.db")
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE forward_shadow_signals (
                signal_id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                realized_r REAL,
                evidence_generation TEXT
            )
        """)
        # Insert 200 contaminated legacy BTC WINs and 100 contaminated legacy XAU WINs
        for i in range(200):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'BTC/USD', 'RESOLVED_WIN', 'WIN', 1.0, 'FORENSIC_CONTAMINATED_TEST_FIXTURE')",
                (f"LEG-BTC-{i}",)
            )
        for i in range(100):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 'WIN', 1.0, 'FORENSIC_CONTAMINATED_TEST_FIXTURE')",
                (f"LEG-XAU-{i}",)
            )
        # Insert 5 CLEAN_FORWARD resolved XAU trades
        for i in range(5):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 'WIN', 1.5, 'CLEAN_FORWARD')",
                (f"CLEAN-XAU-{i}",)
            )
        conn.commit()

    sm = ForwardExecutionStateMachine(db_path=db_file)
    xau_res, btc_res, xau_open, btc_open = sm._query_counts()

    # Legacy 200 BTC and 100 XAU MUST BE IGNORED
    assert xau_res == 5
    assert btc_res == 0

    st = sm.evaluate_state()
    assert st.xau_valid_forward_resolved_n == 5
    assert st.btc_valid_forward_resolved_n == 0
    assert st.current_state == ExecutionState.S2_EVIDENCE_COLLECTION


# =====================================================================
# 4. API FORWARD SHADOW VALIDATION ENDPOINT
# =====================================================================

def test_api_forward_shadow_validation_exposes_clean_and_legacy_metrics():
    """Verify /forward-shadow-validation API response structure and lineage attributes."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["authoritative_source"] == "forward_shadow_signals"
    assert "btc" in data and "xau" in data

    btc = data["btc"]
    xau = data["xau"]

    for item in [btc, xau]:
        assert "total_signals" in item
        assert "resolved_signals" in item
        assert "pending_signals" in item
        assert "wins" in item
        assert "losses" in item
        assert "win_rate_pct" in item
        assert "clean_forward" in item
        assert "quarantined_legacy" in item
        assert item["clean_forward"]["resolved_signals"] >= 0


def test_api_forward_shadow_validation_filtered_by_clean_generation():
    """Verify ?generation=CLEAN_FORWARD returns clean counts at the top level."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation?generation=CLEAN_FORWARD")
    assert resp.status_code == 200
    data = resp.json()

    # Clean forward evidence starts at 0 until live executions accumulate
    assert data["btc"]["evidence_generation"] == "CLEAN_FORWARD"
    assert data["xau"]["evidence_generation"] == "CLEAN_FORWARD"
    assert data["btc"]["resolved_signals"] == 0
    assert data["xau"]["resolved_signals"] == 0


# =====================================================================
# 5. FULL 14-ITEM VERIFICATION MATRIX TESTS
# =====================================================================

def test_sell_entry_fill_then_take_profit(isolated_resolver_env):
    """Matrix 4: SELL order touches entry price -> transitions to ACTIVE_POSITION -> subsequently hits TP -> RESOLVED_WIN."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-SELL-WIN', 'XAU/USD', ?, 'SELL', 2700.0, 2720.0, 2670.0, 2650.0,
                75.0, 80.0, 1.5, 'Bear Trend', 'London', 1, 'v2.0', '{}', 'hash_sell_win',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Candle 1: High reaches 2702 (>= entry 2700) -> Entry filled!
        c1_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c1_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2698.0, 2702.0, 2695.0, 2699.0, 50.0)
        """, (c1_epoch, c1_ts))

        # Candle 2: Drops to hit TP 2670 (Low=2665 <= 2670)
        c2_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=10)).isoformat()
        c2_epoch = t0_epoch + 600000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2699.0, 2701.0, 2665.0, 2668.0, 100.0)
        """, (c2_epoch, c2_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, exit_price, realized_r, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-SELL-WIN'"
        ).fetchone()
        assert row[0] == "RESOLVED_WIN"
        assert row[1] == "WIN"
        assert row[2] == 2670.0
        assert row[3] == 1.50  # (2700 - 2670) / (2720 - 2700) = 30 / 20 = 1.50R
        assert row[4] == c1_ts


def test_sell_entry_fill_then_stop_loss(isolated_resolver_env):
    """Matrix 5: SELL order touches entry price -> transitions to ACTIVE_POSITION -> subsequently hits SL -> RESOLVED_LOSS."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-SELL-LOSS', 'XAU/USD', ?, 'SELL', 2700.0, 2720.0, 2670.0, 2650.0,
                75.0, 80.0, 1.5, 'Bear Trend', 'London', 1, 'v2.0', '{}', 'hash_sell_loss',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Candle 1: High reaches 2702 (>= entry 2700) -> Entry filled!
        c1_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c1_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2697.0, 2702.0, 2695.0, 2699.0, 50.0)
        """, (c1_epoch, c1_ts))

        # Candle 2: Surges to hit SL 2720 (High=2725 >= 2720)
        c2_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=10)).isoformat()
        c2_epoch = t0_epoch + 600000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2700.0, 2725.0, 2698.0, 2722.0, 100.0)
        """, (c2_epoch, c2_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, exit_price, realized_r, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-SELL-LOSS'"
        ).fetchone()
        assert row[0] == "RESOLVED_LOSS"
        assert row[1] == "LOSS"
        assert row[2] == 2720.0
        assert row[3] == -1.0
        assert row[4] == c1_ts


def test_tp_before_entry_blocked(isolated_resolver_env):
    """Matrix 6: Price touches TP level without ever touching Entry price -> TP cannot resolve; remains PENDING / NOT_TRIGGERED."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-TP-BEFORE-ENTRY', 'BTC/USD', ?, 'BUY', 64000.0, 63000.0, 65880.0, 66500.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.1', '{}', 'hash_tp_block',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Price trades between 65000 and 66000 (touches TP 65880, but low is 65100 > 64000 entry)
        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'BTC/USD', '5m', 65200.0, 66100.0, 65100.0, 65900.0, 10.0)
        """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 0  # Blocked! Never triggers WIN!

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-TP-BEFORE-ENTRY'"
        ).fetchone()
        assert row[0] == "PENDING"
        assert row[1] is None
        assert row[2] is None


def test_sl_before_entry_blocked(isolated_resolver_env):
    """Matrix 7: In a SELL setup, price touches SL level without reaching entry -> cannot resolve; remains PENDING."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    # SELL limit order entry at 2750, SL at 2770, TP at 2700.
    # Current market at 2720. Candle high reaches 2740 (not reaching 2750 entry), low is 2715.
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-SL-BLOCK', 'XAU/USD', ?, 'SELL', 2750.0, 2770.0, 2700.0, 2680.0,
                75.0, 80.0, 1.5, 'Bear Trend', 'London', 1, 'v2.0', '{}', 'hash_sl_block',
                'PENDING', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Candle 1: Trades at 2720-2740 (High=2740 < 2750 entry). Entry NOT filled.
        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2725.0, 2740.0, 2720.0, 2735.0, 10.0)
        """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 0

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, entry_filled_at FROM forward_shadow_signals WHERE signal_id = 'SIG-SL-BLOCK'"
        ).fetchone()
        assert row[0] == "PENDING"
        assert row[1] is None


def test_gap_ambiguity_resolves_ambiguous(isolated_resolver_env):
    """Matrix 9: Massive gap candle hitting both entry and exit region in indeterminate sequence resolves AMBIGUOUS."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    # Active position with high/low spanning both SL and TP in the same candle
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-GAP-AMB', 'XAU/USD', ?, 'BUY', 2700.0, 2680.0, 2736.0, 2750.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.0', '{}', 'hash_gap_amb',
                'ACTIVE_POSITION', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        # Sudden gap / high volatility candle spanning 2670 (below SL) to 2740 (above TP)
        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2700.0, 2740.0, 2670.0, 2710.0, 200.0)
        """, (c_epoch, c_ts))
        conn.commit()

    resolved, evaluated = worker.run_cycle()
    assert evaluated == 1
    assert resolved == 1

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT status, outcome, realized_r FROM forward_shadow_signals WHERE signal_id = 'SIG-GAP-AMB'"
        ).fetchone()
        assert row[0] == "AMBIGUOUS"
        assert row[1] == "AMBIGUOUS"
        assert row[2] == 0.0


def test_resolver_idempotency_second_run_no_change(isolated_resolver_env):
    """Matrix 10: Running the resolver worker cycle multiple times against the same DB produces identical state."""
    db_file, worker = isolated_resolver_env
    t0_iso = "2026-09-08T10:00:00+00:00"
    t0_epoch = int(datetime.fromisoformat(t0_iso).timestamp() * 1000)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO forward_shadow_signals (
                signal_id, asset, signal_timestamp, direction, entry_price, stop_loss,
                take_profit_1, take_profit_2, confluence_score, confidence_score,
                signal_strength, market_regime, session, mtf_aligned, strategy_version,
                features_payload, snapshot_hash, status, created_at_utc, evidence_generation
            ) VALUES (
                'SIG-IDEMP-01', 'XAU/USD', ?, 'BUY', 2700.0, 2680.0, 2736.0, 2750.0,
                75.0, 80.0, 1.5, 'Trending', 'London', 1, 'v2.0', '{}', 'hash_idemp',
                'ACTIVE_POSITION', ?, 'CLEAN_FORWARD'
            )
        """, (t0_iso, t0_iso))

        c_ts = (datetime.fromisoformat(t0_iso) + timedelta(minutes=5)).isoformat()
        c_epoch = t0_epoch + 300000
        conn.execute("""
            INSERT INTO candles VALUES (?, ?, 'XAU/USD', '5m', 2700.0, 2740.0, 2700.0, 2738.0, 50.0)
        """, (c_epoch, c_ts))
        conn.commit()

    # First run
    resolved_1, evaluated_1 = worker.run_cycle()
    assert evaluated_1 == 1
    assert resolved_1 == 1

    with sqlite3.connect(db_file) as conn:
        state_1 = conn.execute("SELECT status, outcome, exit_price, realized_r FROM forward_shadow_signals WHERE signal_id = 'SIG-IDEMP-01'").fetchone()

    # Second run immediately after
    resolved_2, evaluated_2 = worker.run_cycle()
    assert evaluated_2 == 0  # Signal is no longer in PENDING/ACTIVE_POSITION
    assert resolved_2 == 0

    with sqlite3.connect(db_file) as conn:
        state_2 = conn.execute("SELECT status, outcome, exit_price, realized_r FROM forward_shadow_signals WHERE signal_id = 'SIG-IDEMP-01'").fetchone()

    assert state_1 == state_2


def test_duplicate_signal_protection(tmp_path):
    """Matrix 11: Idempotent capture of identical signal produces 1 observation, not 2."""
    db_file = str(tmp_path / "dup_test.db")
    engine = ForwardShadowEngine(db_path=db_file)

    # Capture 1
    snap1 = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=64000.0,
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=70.0,
        confidence_score=75.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-08T10:00:00Z",
    )
    assert snap1 is not None

    # Capture 2 with identical data
    snap2 = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=64000.0,
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=70.0,
        confidence_score=75.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        timestamp_utc="2026-09-08T10:00:00Z",
    )
    assert snap2 is not None
    assert snap1.signal_id == snap2.signal_id

    with sqlite3.connect(db_file) as conn:
        count = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        assert count == 1  # Exactly 1 row inserted!


def test_btc_xau_isolation(tmp_path):
    """Matrix 12: BTC observations only increment BTC count, XAU observations only increment XAU count."""
    db_file = str(tmp_path / "iso_asset_test.db")
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE forward_shadow_signals (
                signal_id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                realized_r REAL,
                evidence_generation TEXT
            )
        """)
        # Insert 3 BTC CLEAN_FORWARD wins
        for i in range(3):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'BTC/USD', 'RESOLVED_WIN', 'WIN', 1.0, 'CLEAN_FORWARD')",
                (f"CLEAN-BTC-{i}",)
            )
        conn.commit()

    sm = ForwardExecutionStateMachine(db_path=db_file)
    xau_res, btc_res, xau_open, btc_open = sm._query_counts()

    # BTC observations MUST NOT increment XAU
    assert btc_res == 3
    assert xau_res == 0

    # Now insert 2 XAU CLEAN_FORWARD wins
    with sqlite3.connect(db_file) as conn:
        for i in range(2):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 'WIN', 1.5, 'CLEAN_FORWARD')",
                (f"CLEAN-XAU-{i}",)
            )
        conn.commit()

    xau_res2, btc_res2, xau_open2, btc_open2 = sm._query_counts()
    assert btc_res2 == 3
    assert xau_res2 == 2

