"""
Comprehensive Governance Authorization Hardening Test Suite (Phase 10 & 11).

Verifies the 16 mandatory governance authorization and production gating invariants:
 1. Arbitrary actor rejected
 2. Fake actor string rejected
 3. Missing token rejected
 4. Invalid token rejected
 5. S5 -> S7 direct bypass rejected
 6. Valid token + S6 but failed/incomplete evidence rejected
 7. Valid token + S6 + all 13 gates PASS + XAU N>=100 allowed
 8. S7 transition recorded with cryptographic HMAC signature
 9. Unauthorized API requests cannot transition (401, 403, 409, 422 checks)
10. Production gating remains OFF before formal authorization
11. Direct file tamper (unsigned or tampered S7 JSON) safely clamped to S6
12. Live execution remains permanently OFF across all states (S0-S8)
13. BTC/XAU forward evidence counts isolated
14. ML artifacts remain bit-for-bit FROZEN
15. Historical market database integrity verified
16. Governance authorization is idempotent
"""
import hashlib
import json
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from src.research.governance.forward_state_machine import (
    ForwardExecutionStateMachine,
    ExecutionState,
    AUTHORIZED_S7_ACTORS,
    REQUIRED_S7_EVIDENCE_GATES,
    verify_governance_token,
    compute_state_signature,
    verify_state_signature,
)
from src.api.main import app

TEST_GOVERNANCE_TOKEN = "test-governance-secret-token-abcdef123456"

VALID_13_GATES_EVIDENCE = {
    "all_gates": "13/13 PASS",
    "gate_1_provenance": "PASS",
    "gate_2_resolver": "PASS",
    "gate_3_quant_immutability": "PASS",
    "gate_4_ml_governance": "PASS",
    "gate_5_security_readiness": "PASS",
    "gate_6_shadow_isolation": "PASS",
    "gate_7_database_integrity": "PASS",
    "gate_8_api_backend": "PASS",
    "gate_9_frontend_build": "PASS",
    "gate_10_live_execution_hard_lock": "PASS",
    "gate_11_full_regression": "PASS",
    "gate_12_production_gating_activation": "PASS",
    "gate_13_advisory_state_transition": "PASS",
    "xau_valid_forward_resolved_n": 149,
    "btc_valid_forward_resolved_n": 211,
}


@pytest.fixture
def mock_gov_env(monkeypatch, tmp_path):
    """Fixture providing isolated environment, database, state file, and token."""
    monkeypatch.setenv("GOVERNANCE_AUTH_TOKEN", TEST_GOVERNANCE_TOKEN)

    db_file = str(tmp_path / "mock_historical.db")
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE forward_shadow_signals (
                signal_id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                realized_r REAL
            )
        """)
        # Populate 120 resolved XAU and 200 resolved BTC signals
        for i in range(120):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'XAU/USD', 'RESOLVED_WIN', 'WIN', 1.0)",
                (f"XAU-FWD-{i}",),
            )
        for i in range(200):
            conn.execute(
                "INSERT INTO forward_shadow_signals VALUES (?, 'BTC/USD', 'RESOLVED_WIN', 'WIN', 1.0)",
                (f"BTC-FWD-{i}",),
            )
        conn.commit()

    state_file = str(tmp_path / "governance_state.json")
    audit_file = str(tmp_path / "governance_audit.log")

    return {
        "db_path": db_file,
        "state_file": state_file,
        "audit_file": audit_file,
        "token": TEST_GOVERNANCE_TOKEN,
    }


def _setup_s6_state(env) -> ForwardExecutionStateMachine:
    """Helper to initialize state machine and transition to S6."""
    sm = ForwardExecutionStateMachine(
        db_path=env["db_path"],
        state_file=env["state_file"],
        audit_log_path=env["audit_file"],
    )
    # Transition S5 -> S6
    sm.record_transition(
        target_state=ExecutionState.S6_PRODUCTION_READINESS_AUDIT,
        actor="Production Readiness Auditor",
        reason="S6 Technical Audit Gates 1-13 Verified",
        evidence=VALID_13_GATES_EVIDENCE,
    )
    return sm


# Test 1: Arbitrary actor rejected
def test_arbitrary_actor_rejected(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    with pytest.raises(PermissionError, match="not an authorized governance authority"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Arbitrary Actor",
            reason="Test arbitrary actor",
            auth_token=mock_gov_env["token"],
            evidence=VALID_13_GATES_EVIDENCE,
        )


# Test 2: Fake actor string rejected
def test_fake_actor_string_rejected(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    fake_actors = ["Admin", "Hacker", "Chief Tech Officer", "Root", ""]
    for actor in fake_actors:
        with pytest.raises(PermissionError):
            sm.record_transition(
                target_state=ExecutionState.S7_APPROVED_ADVISORY,
                actor=actor,
                reason="Test fake actor",
                auth_token=mock_gov_env["token"],
                evidence=VALID_13_GATES_EVIDENCE,
            )


# Test 3: Missing token rejected
def test_missing_token_rejected(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    for missing_tok in [None, "", "   "]:
        with pytest.raises(PermissionError, match="Missing or invalid governance authorization token"):
            sm.record_transition(
                target_state=ExecutionState.S7_APPROVED_ADVISORY,
                actor="Production Governance Authority",
                reason="Test missing token",
                auth_token=missing_tok,
                evidence=VALID_13_GATES_EVIDENCE,
            )


# Test 4: Invalid token rejected
def test_invalid_token_rejected(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    with pytest.raises(PermissionError, match="Missing or invalid governance authorization token"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Production Governance Authority",
            reason="Test wrong token",
            auth_token="wrong-token-987654",
            evidence=VALID_13_GATES_EVIDENCE,
        )


# Test 5: S5 -> S7 direct bypass rejected
def test_s5_to_s7_bypass_rejected(mock_gov_env):
    sm = ForwardExecutionStateMachine(
        db_path=mock_gov_env["db_path"],
        state_file=mock_gov_env["state_file"],
        audit_log_path=mock_gov_env["audit_file"],
    )
    # Current state without S6 record is S5
    assert sm.evaluate_state().current_state == ExecutionState.S5_N100_MILESTONE_AUDIT

    with pytest.raises(PermissionError, match="Cannot bypass S6"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Production Governance Authority",
            reason="Direct bypass attempt",
            auth_token=mock_gov_env["token"],
            evidence=VALID_13_GATES_EVIDENCE,
        )


# Test 6: Valid token + S6 but failed/incomplete evidence rejected
def test_valid_token_s6_failed_evidence_rejected(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)

    # Missing evidence entirely
    with pytest.raises(ValueError, match="non-empty technical audit evidence"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Production Governance Authority",
            reason="Empty evidence",
            auth_token=mock_gov_env["token"],
            evidence={},
        )

    # Incomplete gates
    incomplete_evidence = {"all_gates": "12/13 PASS", "gate_1_provenance": "PASS"}
    with pytest.raises(ValueError, match="failed gates|unverified"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Production Governance Authority",
            reason="Incomplete evidence",
            auth_token=mock_gov_env["token"],
            evidence=incomplete_evidence,
        )

    # Explicit gate failure
    failing_evidence = dict(VALID_13_GATES_EVIDENCE)
    failing_evidence["gate_5_security_readiness"] = "FAILED"
    with pytest.raises(ValueError, match="failed gates"):
        sm.record_transition(
            target_state=ExecutionState.S7_APPROVED_ADVISORY,
            actor="Production Governance Authority",
            reason="Failing gate",
            auth_token=mock_gov_env["token"],
            evidence=failing_evidence,
        )


# Test 7: Valid token + S6 + all 13 gates PASS + XAU N>=100 allowed
def test_valid_token_s6_all_gates_pass_allowed(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)

    status = sm.record_transition(
        target_state=ExecutionState.S7_APPROVED_ADVISORY,
        actor="Production Governance Authority",
        reason="Formal production governance approval ceremony complete",
        auth_token=mock_gov_env["token"],
        evidence=VALID_13_GATES_EVIDENCE,
    )

    assert status.current_state == ExecutionState.S7_APPROVED_ADVISORY
    assert status.production_gating == "ON"
    assert status.live_execution == "OFF"
    assert status.advisory_approved is True
    assert status.blocking_issue == "NONE"


# Test 8: S7 transition recorded with cryptographic HMAC signature
def test_s7_transition_recorded_with_hmac_signature(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    sm.record_transition(
        target_state=ExecutionState.S7_APPROVED_ADVISORY,
        actor="Production Governance Authority",
        reason="Cryptographic signature verification test",
        auth_token=mock_gov_env["token"],
        evidence=VALID_13_GATES_EVIDENCE,
    )

    with open(mock_gov_env["state_file"], "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "auth_signature" in data
    assert len(data["auth_signature"]) == 64
    assert verify_state_signature(data, mock_gov_env["token"]) is True


# Test 9: Unauthorized API requests cannot transition (401, 403, 409, 422 checks)
def test_unauthorized_api_requests_cannot_transition(mock_gov_env, monkeypatch):
    client = TestClient(app)

    # 1. Missing token -> 401
    resp = client.post(
        "/api/v1/research/governance/authorize-s7",
        json={
            "actor": "Production Governance Authority",
            "reason": "Test",
            "evidence": VALID_13_GATES_EVIDENCE,
        },
    )
    assert resp.status_code == 401

    # 2. Invalid token -> 401
    resp = client.post(
        "/api/v1/research/governance/authorize-s7",
        headers={"X-Governance-Token": "bad-token"},
        json={
            "actor": "Production Governance Authority",
            "reason": "Test",
            "evidence": VALID_13_GATES_EVIDENCE,
        },
    )
    assert resp.status_code == 401

    # 3. Unauthorized actor -> 403
    resp = client.post(
        "/api/v1/research/governance/authorize-s7",
        headers={"X-Governance-Token": mock_gov_env["token"]},
        json={
            "actor": "Arbitrary Hacker",
            "reason": "Test",
            "evidence": VALID_13_GATES_EVIDENCE,
        },
    )
    assert resp.status_code == 403

    # 4. Incomplete evidence / invalid state -> 422 or 409
    resp = client.post(
        "/api/v1/research/governance/authorize-s7",
        headers={"X-Governance-Token": mock_gov_env["token"]},
        json={
            "actor": "Production Governance Authority",
            "reason": "Test",
            "evidence": {"gate_1": "PASS"},
        },
    )
    assert resp.status_code in (409, 422)


# Test 10: Production gating remains OFF before formal authorization
def test_production_gating_remains_off_before_authorization(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)
    status = sm.evaluate_state()

    assert status.current_state == ExecutionState.S6_PRODUCTION_READINESS_AUDIT
    assert status.production_gating == "OFF"
    assert status.live_execution == "OFF"
    assert status.advisory_approved is False
    assert status.blocking_issue == "S7 FORMAL AUTHORIZATION REQUIRED"


# Test 11: Direct file tamper (unsigned or tampered S7 JSON) safely clamped to S6
def test_direct_file_tamper_unsigned_s7_json_rejected(mock_gov_env):
    # Attacker writes S7 to state file without a valid HMAC signature
    tampered = {
        "current_state": "S7: APPROVED_ADVISORY",
        "previous_state": "S6: PRODUCTION_READINESS_AUDIT",
        "actor": "Production Governance Authority",
        "production_gating": "ON",
        "live_execution": "OFF",
        "advisory_approved": True,
        "auth_signature": "0000000000000000000000000000000000000000000000000000000000000000",
    }
    with open(mock_gov_env["state_file"], "w", encoding="utf-8") as f:
        json.dump(tampered, f)

    sm = ForwardExecutionStateMachine(
        db_path=mock_gov_env["db_path"],
        state_file=mock_gov_env["state_file"],
        audit_log_path=mock_gov_env["audit_file"],
    )

    status = sm.evaluate_state()
    # Clamped to S6
    assert status.current_state == ExecutionState.S6_PRODUCTION_READINESS_AUDIT
    assert status.production_gating == "OFF"
    assert status.advisory_approved is False
    assert status.blocking_issue == "S7 FORMAL AUTHORIZATION REQUIRED"


# Test 12: Live execution remains permanently OFF across all states (S0-S8)
def test_live_execution_remains_off_across_all_states(mock_gov_env):
    sm = ForwardExecutionStateMachine(
        db_path=mock_gov_env["db_path"],
        state_file=mock_gov_env["state_file"],
        audit_log_path=mock_gov_env["audit_file"],
    )

    # Test forced failure (S8)
    s8 = sm.evaluate_state(force_failure_reason="Forced remediation")
    assert s8.live_execution in ("OFF", "DISABLED")

    # Test baseline failed (S8)
    s8_b = sm.evaluate_state(baseline_passed=False)
    assert s8_b.live_execution in ("OFF", "DISABLED")

    # Test pipeline failed (S8)
    s8_p = sm.evaluate_state(pipeline_passed=False)
    assert s8_p.live_execution in ("OFF", "DISABLED")

    # Test S6
    sm_s6 = _setup_s6_state(mock_gov_env)
    assert sm_s6.evaluate_state().live_execution == "OFF"

    # Test S7
    sm_s6.record_transition(
        target_state=ExecutionState.S7_APPROVED_ADVISORY,
        actor="Production Governance Authority",
        reason="Valid S7",
        auth_token=mock_gov_env["token"],
        evidence=VALID_13_GATES_EVIDENCE,
    )
    assert sm_s6.evaluate_state().live_execution == "OFF"


# Test 13: BTC/XAU evidence isolation remains intact
def test_btc_xau_evidence_isolation_remains_intact(mock_gov_env):
    sm = ForwardExecutionStateMachine(
        db_path=mock_gov_env["db_path"],
        state_file=mock_gov_env["state_file"],
        audit_log_path=mock_gov_env["audit_file"],
    )
    xau_res, btc_res, xau_open, btc_open = sm._query_counts()
    assert xau_res == 120
    assert btc_res == 200
    assert xau_res != btc_res


# Test 14: ML artifacts remain bit-for-bit FROZEN
def test_ml_artifacts_hashes_remain_unchanged():
    expected_btc_hash = "0978B52D9B23A12099935EEB72CC260A470C283E0E4E54FC278596EBB9F482A5"
    expected_xau_hash = "C12A0F09101DAD9547618D6DDF68F99105D539F8618486D59CFE16F586DC8F2E"

    btc_path = "research/ml/artifacts/BTC/model.joblib"
    xau_path = "research/ml/artifacts/XAU/model.joblib"

    if os.path.exists(btc_path):
        with open(btc_path, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest().upper() == expected_btc_hash

    if os.path.exists(xau_path):
        with open(xau_path, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest().upper() == expected_xau_hash


# Test 15: Historical market database integrity verified
def test_historical_db_integrity():
    db_path = "data/historical/historical_market_data.db"
    if os.path.exists(db_path):
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            result = conn.execute("PRAGMA quick_check").fetchone()
            assert result == ("ok",)


# Test 16: Governance authorization is idempotent
def test_governance_authorization_idempotency(mock_gov_env):
    sm = _setup_s6_state(mock_gov_env)

    # First authorization
    st1 = sm.record_transition(
        target_state=ExecutionState.S7_APPROVED_ADVISORY,
        actor="Production Governance Authority",
        reason="First ceremony",
        auth_token=mock_gov_env["token"],
        evidence=VALID_13_GATES_EVIDENCE,
    )
    assert st1.current_state == ExecutionState.S7_APPROVED_ADVISORY

    # Second authorization (re-ceremony under same token/actor)
    st2 = sm.record_transition(
        target_state=ExecutionState.S7_APPROVED_ADVISORY,
        actor="Production Governance Authority",
        reason="Second ceremony confirmation",
        auth_token=mock_gov_env["token"],
        evidence=VALID_13_GATES_EVIDENCE,
    )
    assert st2.current_state == ExecutionState.S7_APPROVED_ADVISORY
    assert st2.production_gating == "ON"
    assert st2.live_execution == "OFF"
