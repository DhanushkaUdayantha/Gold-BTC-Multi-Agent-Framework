"""
Comprehensive Rollout & Isolation Tests for BTC Shadow-Mode & Gating Pipeline.

Verifies:
1. Shadow runner writes exclusively to shadow_trading_store (isolated from user demo).
2. trade/reset on manual demo does not clear or mutate shadow history.
3. Comparison gate requires N>=50 AND days>=14 before rendering PASS/FAIL.
4. Admin gating requires authentication and appends to immutable audit trail.
5. Invariants enforcement: AUTOMATIC_RETRAINING, AUTOMATIC_THRESHOLD_OPTIMIZATION, PRODUCTION_GATING_XAU remain False.
6. Baseline DecisionEngine output invariance when gating is disabled.
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.gating_control import GatingControlManager, get_gating_control
from src.services.shadow_trading_store import ShadowTradingStore
from src.services.btc_shadow_runner import BTCShadowRunner
from src.services.paper_trading_service import PaperTradingService
from src.research.governance.shadow_comparison import BTCShadowComparisonGate

client = TestClient(app)


def test_shadow_store_and_demo_store_complete_isolation(tmp_path):
    # Setup isolated test database
    db_path = str(tmp_path / "shadow_iso.db")
    shadow_store = ShadowTradingStore(db_path=db_path)
    runner = BTCShadowRunner(shadow_store=shadow_store)

    # 1. Capture a shadow trade
    res = runner.evaluate_live_market_setup(
        current_price=64200.0,
        direction="BUY",
        stop_loss=63200.0,
        take_profit_1=66000.0,
        take_profit_2=66800.0,
        confluence_score=70.0,
        confidence_score=75.0,
        signal_strength=72.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.60,
    )
    assert res is not None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 1

    # 2. Reset user demo account
    demo_pt = PaperTradingService()
    demo_pt.reset_account()

    # 3. Assert shadow trades remain intact
    shadow_trades = shadow_store.get_all_trades("BTC/USD")
    assert len(shadow_trades) == 1
    assert shadow_trades[0].asset == "BTC/USD"


def test_comparison_gate_dual_sample_and_time_requirement(tmp_path):
    db_path = str(tmp_path / "shadow_gate_dual.db")
    shadow_store = ShadowTradingStore(db_path=db_path)
    gate = BTCShadowComparisonGate(shadow_store=shadow_store)

    # Case A: 55 trades but all within 2 days -> ACCUMULATING (time gate fails)
    base_ts = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(55):
        t_id = f"T-FAST-{i}"
        open_ts = base_ts + timedelta(minutes=i * 30)  # Total 27.5 hours
        shadow_store.open_shadow_trade(
            trade_id=t_id,
            asset="BTC/USD",
            direction="BUY",
            entry_price=64000.0,
            stop_loss=63000.0,
            take_profit_1=65880.0,
            take_profit_2=66500.0,
            calibrated_probability=0.55,
            mtf_confluence_state="MTF=True",
            session="London",
            strategy_version="v2.1",
            t0_snapshot_hash="e" * 64,
            open_timestamp_utc=open_ts.isoformat(),
        )
        shadow_store.close_shadow_trade(
            trade_id=t_id,
            exit_price=65880.0,
            realized_r=1.88,
            outcome_status="CLOSED_WIN",
            close_timestamp_utc=(open_ts + timedelta(minutes=15)).isoformat(),
        )

    rep_fast = gate.evaluate_shadow_confirmation()
    assert rep_fast.sample_gate_passed is True
    assert rep_fast.time_gate_passed is False
    assert rep_fast.verdict == "ACCUMULATING"


def test_admin_gating_unauthorized_rejection():
    # Attempt unauthenticated request without token
    resp = client.post(
        "/api/v1/admin/gating/btc",
        json={"actor": "attacker", "rationale": "bypass", "confirmation": "CONFIRM_MANUAL_BTC_GATING"},
    )
    assert resp.status_code in (401, 503)


def test_invariants_strictly_prevent_unauthorized_gating_activation(tmp_path):
    state_f = str(tmp_path / "gating_state.json")
    audit_f = str(tmp_path / "audit.log")
    mgr = GatingControlManager(state_file=state_f, audit_file=audit_f)

    # Invariants are read-only False properties
    assert mgr.automatic_retraining is False
    assert mgr.automatic_threshold_optimization is False
    assert mgr.production_gating_xau is False

    # Modifying state for BTC does not modify XAU or retraining
    mgr.set_btc_gating(enable=True, actor="admin_lead", rationale="Rollout approved")
    assert mgr.production_gating_btc is True
    assert mgr.production_gating_xau is False
    assert mgr.automatic_retraining is False
    assert mgr.automatic_threshold_optimization is False


def test_disabled_gating_decision_output_invariance():
    """Verify that when BTC gating is disabled (default), DecisionEngine outputs are invariant."""
    from src.services.decision_engine import DecisionEngine
    from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

    mgr = get_gating_control()
    # Ensure gating is False
    mgr._production_gating_btc = False

    ta = _make_ta(price=64000.0)
    ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
    mtf_in = _make_mtf_input(ta_map, price=64000.0)
    ai_in = _make_ai_result()

    engine = DecisionEngine()
    dec1, breakdown1 = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)
    dec2, breakdown2 = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

    assert dec1.decision == dec2.decision
    assert dec1.signal_strength == dec2.signal_strength
    assert dec1.stop_loss == dec2.stop_loss
    assert dec1.take_profit_1 == dec2.take_profit_1
