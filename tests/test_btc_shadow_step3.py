"""
Step 3 Tests: Production Gating Controller, Admin Authentication & Invariants Enforcement.
"""
import os
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.gating_control import GatingControlManager, get_gating_control

client = TestClient(app)


def test_gating_control_invariants(tmp_path):
    state_f = str(tmp_path / "gating_state.json")
    audit_f = str(tmp_path / "audit.log")
    mgr = GatingControlManager(state_file=state_f, audit_file=audit_f)

    # Invariants must always be False
    assert mgr.automatic_retraining is False
    assert mgr.automatic_threshold_optimization is False
    assert mgr.production_gating_xau is False
    assert mgr.production_gating_btc is False

    # Status dictionary
    status = mgr.get_status()
    assert status["invariants_ok"] is True
    assert status["production_gating_xau"] is False
    assert status["automatic_retraining"] is False


def test_manual_btc_gating_persistence_and_audit(tmp_path):
    state_f = str(tmp_path / "gating_state.json")
    audit_f = str(tmp_path / "audit.log")
    mgr = GatingControlManager(state_file=state_f, audit_file=audit_f)

    # Enable BTC gating
    entry = mgr.set_btc_gating(enable=True, actor="admin_alice", rationale="Shadow gate satisfied")
    assert entry.new_state_btc is True
    assert mgr.production_gating_btc is True

    # Re-instantiate manager from same file -> Persisted state is True
    mgr2 = GatingControlManager(state_file=state_f, audit_file=audit_f)
    assert mgr2.production_gating_btc is True

    # Disable BTC gating via kill switch
    entry2 = mgr2.set_btc_gating(enable=False, actor="admin_bob", rationale="Emergency stop")
    assert entry2.new_state_btc is False
    assert mgr2.production_gating_btc is False

    # Audit log should have 2 entries
    with open(audit_f, "r") as f:
        lines = f.readlines()
    assert len(lines) == 2


def test_admin_api_endpoints_auth_and_kill_switch(monkeypatch):
    # Set mock admin token in environment
    monkeypatch.setenv("ADMIN_AUTH_TOKEN", "secure_test_admin_token_xyz123")

    # 1. Unauthenticated request -> 401
    resp_unauth = client.post(
        "/api/v1/admin/gating/btc",
        json={"actor": "test_user", "rationale": "test", "confirmation": "CONFIRM_MANUAL_BTC_GATING"},
    )
    assert resp_unauth.status_code == 401

    # 2. Invalid token -> 401
    resp_bad_token = client.post(
        "/api/v1/admin/gating/btc",
        headers={"X-Admin-Token": "wrong_token"},
        json={"actor": "test_user", "rationale": "test", "confirmation": "CONFIRM_MANUAL_BTC_GATING"},
    )
    assert resp_bad_token.status_code == 401

    # 3. Valid token, bad confirmation string -> 400
    resp_bad_conf = client.post(
        "/api/v1/admin/gating/btc",
        headers={"X-Admin-Token": "secure_test_admin_token_xyz123"},
        json={"actor": "test_user", "rationale": "test", "confirmation": "WRONG_STRING"},
    )
    assert resp_bad_conf.status_code == 400

    # 4. Valid token and valid confirmation -> 200 OK
    resp_ok = client.post(
        "/api/v1/admin/gating/btc",
        headers={"X-Admin-Token": "secure_test_admin_token_xyz123"},
        json={"actor": "authorized_admin", "rationale": "All criteria met", "confirmation": "CONFIRM_MANUAL_BTC_GATING"},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["status"] == "success"
    assert get_gating_control().production_gating_btc is True

    # 5. Kill switch -> 200 OK
    resp_kill = client.post(
        "/api/v1/admin/gating/btc/disable",
        headers={"X-Admin-Token": "secure_test_admin_token_xyz123"},
        json={"actor": "authorized_admin", "rationale": "Revert to baseline"},
    )
    assert resp_kill.status_code == 200
    assert resp_kill.json()["status"] == "success"
    assert get_gating_control().production_gating_btc is False
