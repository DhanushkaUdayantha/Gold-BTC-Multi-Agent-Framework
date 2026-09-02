"""
Unit and Integration Tests for XAU Shadow Runner & Comparison Gate.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.shadow_trading_store import ShadowTradingStore
from src.services.xau_shadow_runner import XAUShadowRunner
from src.research.governance.shadow_comparison import XAUShadowComparisonGate

client = TestClient(app)


def test_xau_shadow_runner_qualification_and_capture(tmp_path):
    test_db = str(tmp_path / "test_xau_shadow.db")
    store = ShadowTradingStore(db_path=test_db)
    runner = XAUShadowRunner(shadow_store=store)

    # 1. Low probability (<50%) -> Filtered
    res_low_p = runner.evaluate_live_market_setup(
        current_price=2700.0,
        direction="BUY",
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=65.0,
        confidence_score=68.0,
        signal_strength=60.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.45,
    )
    assert res_low_p is None
    assert len(store.get_all_trades("XAU/USD")) == 0

    # 2. Valid XAU setup -> Captured
    res_valid = runner.evaluate_live_market_setup(
        current_price=2700.0,
        direction="BUY",
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=68.0,
        confidence_score=72.0,
        signal_strength=70.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.55,
    )
    assert res_valid is not None
    assert len(store.get_all_trades("XAU/USD")) == 1


def test_xau_shadow_runner_outcome_resolution(tmp_path):
    test_db = str(tmp_path / "test_xau_shadow_res.db")
    store = ShadowTradingStore(db_path=test_db)
    runner = XAUShadowRunner(shadow_store=store)

    _ = runner.evaluate_live_market_setup(
        current_price=2700.0,
        direction="BUY",
        stop_loss=2680.0,
        take_profit_1=2736.0,
        take_profit_2=2750.0,
        confluence_score=68.0,
        confidence_score=72.0,
        signal_strength=70.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.55,
    )

    # Price hits TP1 (2736)
    closed = runner.update_open_shadow_trades(current_price=2738.0, high_price=2740.0, low_price=2695.0)
    assert len(closed) == 1

    status = runner.get_shadow_status()
    assert status["status"] == "success"
    assert status["live_shadow_metrics"]["resolved_trades_count"] == 1
    assert status["live_shadow_metrics"]["wins_count"] == 1
    assert status["backtest_reference_baseline"]["sample_size_n"] == 45


def test_xau_shadow_comparison_gate_milestone_and_pass(tmp_path):
    test_db = str(tmp_path / "test_xau_gate.db")
    store = ShadowTradingStore(db_path=test_db)
    gate = XAUShadowComparisonGate(shadow_store=store)

    # Empty -> ACCUMULATING
    rep_empty = gate.evaluate_shadow_confirmation()
    assert rep_empty.verdict == "ACCUMULATING"

    # Insert 52 trades spanning 16 days
    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(52):
        t_id = f"T-XAU-{i}"
        open_dt = base_time + timedelta(hours=i * 7.5)
        close_dt = open_dt + timedelta(hours=2)
        store.open_shadow_trade(
            trade_id=t_id,
            asset="XAU/USD",
            direction="BUY",
            entry_price=2700.0,
            stop_loss=2680.0,
            take_profit_1=2736.0,
            take_profit_2=2750.0,
            calibrated_probability=0.55,
            mtf_confluence_state="MTF=True",
            session="London",
            strategy_version="v2.0",
            t0_snapshot_hash="f" * 64,
            open_timestamp_utc=open_dt.isoformat(),
        )
        is_win = i < 28  # 28 wins, 24 losses -> WR=53.85%
        status = "CLOSED_WIN" if is_win else "CLOSED_LOSS"
        r_val = 1.80 if is_win else -1.0
        exit_p = 2736.0 if is_win else 2680.0
        store.close_shadow_trade(
            trade_id=t_id,
            exit_price=exit_p,
            realized_r=r_val,
            outcome_status=status,
            close_timestamp_utc=close_dt.isoformat(),
        )

    rep_pass = gate.evaluate_shadow_confirmation()
    assert rep_pass.sample_gate_passed is True
    assert rep_pass.time_gate_passed is True
    assert rep_pass.ev_gate_passed is True
    assert rep_pass.wr_gate_passed is True
    assert rep_pass.verdict == "PASS"
