"""
Unit Tests for Dual-Asset Gating Controller & Invariants.
"""
import pytest
from src.core.gating_control import GatingControlManager


def test_gating_control_dual_asset_isolation(tmp_path):
    state_f = str(tmp_path / "dual_gating_state.json")
    audit_f = str(tmp_path / "dual_audit.log")
    mgr = GatingControlManager(state_file=state_f, audit_file=audit_f)

    # Initial state
    assert mgr.production_gating_btc is False
    assert mgr.production_gating_xau is False

    # Enabling BTC gating
    mgr.set_btc_gating(enable=True, actor="admin_lead", rationale="BTC validated")
    assert mgr.production_gating_btc is True
    # XAU gating MUST remain False
    assert mgr.production_gating_xau is False
    assert mgr.automatic_retraining is False
    assert mgr.automatic_threshold_optimization is False

    # Disabling BTC gating
    mgr.set_btc_gating(enable=False, actor="admin_lead", rationale="Revert BTC")
    assert mgr.production_gating_btc is False
    assert mgr.production_gating_xau is False
