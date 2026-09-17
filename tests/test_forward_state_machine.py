"""
Comprehensive test suite for Forward Evidence Execution State Machine & Ownership Authority.

Validates Sections 20, 26A, and 26B:
- State progression: S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7
- Failure transitions to S8 (Remediate / Defer)
- Invariant: live execution is ALWAYS DISABLED across all states
- Invariant: N based solely on valid resolved records (unresolved excluded)
- Invariant: BTC and XAU separation
- Invariant: Idempotent and reproducible state evaluation
- Invariant: State ownership boundaries (no self-approval)
"""
import os
import sqlite3
import pytest
from src.research.governance.forward_state_machine import (
    ForwardExecutionStateMachine,
    ExecutionState,
    STATE_OWNERSHIP_MAP,
)
from src.research.governance.forward_shadow import ForwardShadowEngine


@pytest.fixture
def test_db(tmp_path):
    """Provide an isolated database for state machine testing."""
    db_file = str(tmp_path / "test_state_machine.db")
    engine = ForwardShadowEngine(db_path=db_file)
    return db_file, engine


def test_state_ownership_matrix_complete():
    """Verify all states S0-S8 have defined owners and authority rules."""
    for state in ExecutionState:
        assert state in STATE_OWNERSHIP_MAP
        info = STATE_OWNERSHIP_MAP[state]
        assert "owner" in info
        assert "primary_authority" in info
        assert "may_approve_transition" in info


def test_baseline_failure_transitions_to_s8(test_db):
    """S0 failure must transition directly to S8 (Remediate/Defer)."""
    db_file, _ = test_db
    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state(baseline_passed=False)
    assert status.current_state == ExecutionState.S8_REMEDIATE_OR_DEFER
    assert status.transition == "S0 -> S8"
    assert status.live_execution == "DISABLED"


def test_pipeline_failure_transitions_to_s8(test_db):
    """S1 failure must transition directly to S8."""
    db_file, _ = test_db
    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state(baseline_passed=True, pipeline_passed=False)
    assert status.current_state == ExecutionState.S8_REMEDIATE_OR_DEFER
    assert status.transition == "S1 -> S8"
    assert status.live_execution == "DISABLED"


def test_n_less_than_50_remains_in_s2_evidence_collection(test_db):
    """When valid resolved XAU N < 50, state remains in S2 (Evidence Collection)."""
    db_file, engine = test_db
    # Insert 45 pending observations (none resolved)
    for i in range(45):
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
            timestamp_utc=f"2026-09-01T{i:02d}:00:00Z",
        )

    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    # Unresolved observations do not count toward N
    assert status.xau_valid_forward_resolved_n == 0
    assert status.xau_unresolved_n == 45
    assert status.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert status.n50_status == "NOT REACHED"
    assert status.production_gating == "DISABLED"
    assert status.live_execution == "DISABLED"


def test_n50_milestone_transition_to_s3_when_resolved(test_db):
    """When XAU resolved N == 50, state progresses to S3 (N50 Milestone Audit)."""
    db_file, engine = test_db
    # Create and resolve 50 observations
    for i in range(50):
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
            timestamp_utc=f"2026-09-01T{i%24:02d}:{i%60:02d}:00Z",
        )
        engine.resolve_forward_signal(
            signal_id=snap.signal_id,
            resolution_status="RESOLVED_WIN",
            outcome_timestamp_utc=f"2026-09-02T{i%24:02d}:{i%60:02d}:00Z",
            exit_price=2736.0,
            realized_r=1.80,
        )

    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    assert status.xau_valid_forward_resolved_n == 50
    assert status.current_state == ExecutionState.S3_N50_MILESTONE_AUDIT
    assert status.n50_status == "PASS"
    assert status.n100_status == "NOT REACHED"
    assert status.production_gating == "DISABLED"
    assert status.live_execution == "DISABLED"


def test_n_greater_than_50_progresses_to_s4(test_db):
    """When XAU resolved N > 50 (e.g. 51), state progresses to S4 (N100 Accumulation)."""
    db_file, engine = test_db
    for i in range(51):
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
            timestamp_utc=f"2026-09-01T{i%24:02d}:{i%60:02d}:00Z",
        )
        engine.resolve_forward_signal(
            signal_id=snap.signal_id,
            resolution_status="RESOLVED_WIN",
            outcome_timestamp_utc=f"2026-09-02T{i%24:02d}:{i%60:02d}:00Z",
            exit_price=2736.0,
            realized_r=1.80,
        )

    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    assert status.xau_valid_forward_resolved_n == 51
    assert status.current_state == ExecutionState.S4_N100_ACCUMULATION
    assert status.n50_status == "PASS"
    assert status.n100_status == "NOT REACHED"


def test_btc_observations_do_not_increase_xau_n(test_db):
    """BTC forward resolved observations must NEVER count toward XAU N."""
    db_file, engine = test_db
    # Resolve 60 BTC signals
    for i in range(60):
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
            timestamp_utc=f"2026-09-01T{i%24:02d}:{i%60:02d}:00Z",
        )
        engine.resolve_forward_signal(
            signal_id=snap.signal_id,
            resolution_status="RESOLVED_WIN",
            outcome_timestamp_utc=f"2026-09-02T{i%24:02d}:{i%60:02d}:00Z",
            exit_price=82000.0,
            realized_r=2.0,
        )

    sm = ForwardExecutionStateMachine(db_path=db_file)
    status = sm.evaluate_state()

    assert status.btc_valid_forward_resolved_n == 60
    assert status.xau_valid_forward_resolved_n == 0
    # XAU is still at 0, must remain in S2
    assert status.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert status.n50_status == "NOT REACHED"


def test_temporal_integrity_rejection(test_db):
    """Resolution with outcome_timestamp <= signal_timestamp must be rejected."""
    db_file, engine = test_db
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

    # Attempt to resolve using earlier timestamp -> must return False
    success = engine.resolve_forward_signal(
        signal_id=snap.signal_id,
        resolution_status="RESOLVED_WIN",
        outcome_timestamp_utc="2026-09-02T11:59:00Z",
        exit_price=2736.0,
        realized_r=1.80,
    )
    assert success is False

    # Verify status remains PENDING in database
    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT status FROM forward_shadow_signals WHERE signal_id=?", (snap.signal_id,)).fetchone()
        assert row[0] == "PENDING"


def test_state_machine_idempotence(test_db):
    """Evaluating state repeatedly without data changes yields identical results."""
    db_file, _ = test_db
    sm = ForwardExecutionStateMachine(db_path=db_file)
    res1 = sm.evaluate_state().to_dict()
    res2 = sm.evaluate_state().to_dict()
    assert res1 == res2


def test_state_machine_milestone_progression_invariants(tmp_path):
    """
    Formal state machine regression test proving:
    1. XAU resolved N = 0   -> CURRENT STATE = S2 (Evidence Collection)
    2. XAU resolved N = 49  -> CURRENT STATE = S2 (Evidence Collection)
    3. XAU resolved N = 50  -> CURRENT STATE = S3 (N50 Milestone Audit)
    4. XAU resolved N = 100 -> CURRENT STATE = S5 (N100 Milestone Audit)
    5. NOT automatically S6 unless N100 milestone audit passes
    6. Strict rejection: NO path XAU < 100 -> S6 even if state_file claims S6/S7
    """
    import json

    db_file = str(tmp_path / "invariants_test.db")
    engine = ForwardShadowEngine(db_path=db_file)
    state_file = str(tmp_path / "governance_state.json")

    # Helper to add resolved signals
    def add_resolved_signals(count: int, start_idx: int = 0):
        for i in range(start_idx, start_idx + count):
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
                timestamp_utc=f"2026-09-01T{i%24:02d}:{i%60:02d}:00Z",
            )
            engine.resolve_forward_signal(
                signal_id=snap.signal_id,
                resolution_status="RESOLVED_WIN",
                outcome_timestamp_utc=f"2026-09-02T{i%24:02d}:{i%60:02d}:00Z",
                exit_price=2736.0,
                realized_r=1.80,
            )

    # 1. N = 0 -> S2
    sm0 = ForwardExecutionStateMachine(db_path=db_file, state_file=state_file)
    st0 = sm0.evaluate_state()
    assert st0.xau_valid_forward_resolved_n == 0
    assert st0.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert st0.n50_status == "NOT REACHED"
    assert st0.n100_status == "NOT REACHED"
    assert st0.production_readiness == "PENDING"
    assert st0.production_gating == "DISABLED"
    assert st0.live_execution == "DISABLED"

    # 2. Even if state_file fraudulently claims S6 or S7 when N = 0, system MUST REMAIN S2!
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"current_state": "S6: PRODUCTION_READINESS_AUDIT"}, f)
    st0_fraud = sm0.evaluate_state()
    assert st0_fraud.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert st0_fraud.n50_status == "NOT REACHED"

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"current_state": "S7: APPROVED_ADVISORY"}, f)
    st0_fraud_s7 = sm0.evaluate_state()
    assert st0_fraud_s7.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert st0_fraud_s7.n50_status == "NOT REACHED"

    # 3. Add 49 resolved signals -> N = 49 -> S2
    add_resolved_signals(49, start_idx=0)
    st49 = sm0.evaluate_state()
    assert st49.xau_valid_forward_resolved_n == 49
    assert st49.current_state == ExecutionState.S2_EVIDENCE_COLLECTION
    assert st49.n50_status == "NOT REACHED"
    assert st49.n100_status == "NOT REACHED"

    # 4. Add 1 more resolved signal -> N = 50 -> S3 (N50 Milestone Audit)
    add_resolved_signals(1, start_idx=49)
    st50 = sm0.evaluate_state()
    assert st50.xau_valid_forward_resolved_n == 50
    assert st50.current_state == ExecutionState.S3_N50_MILESTONE_AUDIT
    assert st50.n50_status == "PASS"
    assert st50.n100_status == "NOT REACHED"

    # 5. Add 50 more resolved signals -> N = 100 -> S5 (N100 Milestone Audit)
    # NOT automatically S6!
    add_resolved_signals(50, start_idx=50)
    # Clear state_file so no fraudulent pre-approval exists
    if os.path.exists(state_file):
        os.remove(state_file)
    st100 = sm0.evaluate_state()
    assert st100.xau_valid_forward_resolved_n == 100
    assert st100.current_state == ExecutionState.S5_N100_MILESTONE_AUDIT
    assert st100.current_state != ExecutionState.S6_PRODUCTION_READINESS_AUDIT
    assert st100.n50_status == "PASS"
    assert st100.n100_status == "PASS"
    assert st100.production_readiness == "PENDING"

