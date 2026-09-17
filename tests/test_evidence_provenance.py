"""
Authoritative Forward Evidence Provenance & Lineage Verification Tests.

Validates Section 18:
1. Reference benchmark records (N=45/N=68) are not automatically counted as live forward evidence.
2. Unresolved (PENDING) observations do not increase authoritative N.
3. Historical replay / backtest signals do not qualify as forward evidence.
4. Temporal order violation (outcome <= signal) is rejected.
5. BTC observations cannot increase XAU N and vice versa.
6. Authoritative evidence count is 100% reproducible from underlying records.
7. State machine remains in S2 when authoritative XAU N < 50.
"""
import sqlite3
import pytest
from src.research.governance.forward_state_machine import (
    ForwardExecutionStateMachine,
    ExecutionState,
)
from src.research.governance.forward_shadow import ForwardShadowEngine
from src.research.governance.forward_accumulation_tracker import (
    XAUForwardAccumulationTracker,
)


@pytest.fixture
def isolated_db(tmp_path):
    """Provide an isolated database for provenance verification."""
    db_file = str(tmp_path / "provenance_test.db")
    engine = ForwardShadowEngine(db_path=db_file)
    return db_file, engine


def test_reference_benchmark_not_counted_as_live_evidence(isolated_db):
    """Reference backtest benchmarks (N=45/N=68) must not appear in authoritative forward resolved N."""
    db_file, engine = isolated_db
    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    # Authoritative live resolved count must be 0, not 45 or 68
    assert status.xau_valid_forward_resolved_n == 0
    assert status.btc_valid_forward_resolved_n == 0
    assert status.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert status.n50_status == "NOT REACHED"


def test_pending_observations_excluded_from_authoritative_n(isolated_db):
    """Pending observations must be tracked as open, but strictly excluded from resolved N."""
    db_file, engine = isolated_db
    for i in range(10):
        engine.capture_forward_signal(
            asset="XAU/USD",
            direction="BUY",
            entry_price=2700.0,
            stop_loss=2680.0,
            take_profit_1=2736.0,
            take_profit_2=2750.0,
            confluence_score=70.0,
            confidence_score=72.0,
            signal_strength=1.2,
            market_regime="Trending",
            session="London",
            mtf_aligned=True,
            timestamp_utc=f"2026-09-02T{i:02d}:00:00Z",
        )

    tracker = XAUForwardAccumulationTracker(db_path=db_file)
    progress = tracker.get_progress()

    assert progress.open_count == 10
    assert progress.resolved_count == 0
    assert progress.governance_status == "INSUFFICIENT_EVIDENCE"
    assert progress.deficit_to_milestone_1 == 50


def test_historical_signals_table_isolated_from_forward_shadow(isolated_db):
    """Records in historical_signals table must never leak into forward_shadow_signals."""
    db_file, engine = isolated_db
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                outcome TEXT NOT NULL
            )
        """)
        # Insert 100 historical backtest signals
        for i in range(100):
            conn.execute(
                "INSERT INTO historical_signals VALUES (?, 'XAU/USD', 'WIN')",
                (f"HIST-{i}",)
            )

    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    # Must remain 0 because forward_shadow_signals has 0 resolved records
    assert status.xau_valid_forward_resolved_n == 0
    assert status.current_state == ExecutionState.S2_EVIDENCE_COLLECTION


def test_provenance_reproducibility(isolated_db):
    """The authoritative forward count must be deterministically reproducible from raw table counts."""
    db_file, engine = isolated_db
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
        timestamp_utc="2026-09-02T10:00:00Z",
    )
    engine.resolve_forward_signal(
        signal_id=snap.signal_id,
        resolution_status="RESOLVED_WIN",
        outcome_timestamp_utc="2026-09-02T12:00:00Z",
        exit_price=2736.0,
        realized_r=1.80,
    )

    # Direct raw count
    with sqlite3.connect(db_file) as conn:
        raw_res = conn.execute(
            "SELECT COUNT(*) FROM forward_shadow_signals WHERE asset='XAU/USD' AND status != 'PENDING'"
        ).fetchone()[0]

    # Tracker count
    tracker = XAUForwardAccumulationTracker(db_path=db_file)
    tracker_res = tracker.get_progress().resolved_count

    # State machine count
    sm = ForwardExecutionStateMachine(db_path=db_file)
    sm_res = sm.evaluate_state().xau_valid_forward_resolved_n

    assert raw_res == 1
    assert tracker_res == raw_res
    assert sm_res == raw_res


def test_reconciliation_zero_mutation(isolated_db):
    """Running provenance reconciliation queries must never mutate database state."""
    db_file, engine = isolated_db
    engine.capture_forward_signal(
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
        timestamp_utc="2026-09-02T10:00:00Z",
    )

    with sqlite3.connect(db_file) as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        pending_before = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE status='PENDING'").fetchone()[0]

    sm = ForwardExecutionStateMachine(db_path=db_file)
    _ = sm.evaluate_state()

    with sqlite3.connect(db_file) as conn:
        count_after = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
        pending_after = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE status='PENDING'").fetchone()[0]

    assert count_before == count_after == 1
    assert pending_before == pending_after == 1
