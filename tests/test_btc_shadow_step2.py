"""
Step 2 Tests: BTC Shadow Comparison Gate (Pre-Registered Criteria & Human Review).
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.services.shadow_trading_store import ShadowTradingStore
from src.research.governance.shadow_comparison import BTCShadowComparisonGate


def test_comparison_gate_accumulating_state(tmp_path):
    test_db = str(tmp_path / "test_comp_acc.db")
    store = ShadowTradingStore(db_path=test_db)
    gate = BTCShadowComparisonGate(shadow_store=store)

    # Empty store -> ACCUMULATING
    report = gate.evaluate_shadow_confirmation()
    assert report.verdict == "ACCUMULATING"
    assert report.sample_gate_passed is False
    assert report.time_gate_passed is False

    # Insert 10 trades (N=10 < 50) -> Still ACCUMULATING
    for i in range(10):
        t_id = f"T-ACC-{i}"
        store.open_shadow_trade(
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
            t0_snapshot_hash="b" * 64,
        )
        store.close_shadow_trade(trade_id=t_id, exit_price=65880.0, realized_r=1.88, outcome_status="CLOSED_WIN")

    report10 = gate.evaluate_shadow_confirmation()
    assert report10.verdict == "ACCUMULATING"
    assert report10.sample_size_n == 10
    assert report10.sample_gate_passed is False


def test_comparison_gate_pass_state(tmp_path):
    test_db = str(tmp_path / "test_comp_pass.db")
    store = ShadowTradingStore(db_path=test_db)
    gate = BTCShadowComparisonGate(shadow_store=store)

    # Insert 52 trades spanning 16 days
    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(52):
        t_id = f"T-PASS-{i}"
        # Stagger open times over 16 days
        open_dt = base_time + timedelta(hours=i * 7.5)
        close_dt = open_dt + timedelta(hours=2)
        store.open_shadow_trade(
            trade_id=t_id,
            asset="BTC/USD",
            direction="BUY",
            entry_price=64000.0,
            stop_loss=63000.0,
            take_profit_1=65880.0,
            take_profit_2=66500.0,
            calibrated_probability=0.56,
            mtf_confluence_state="MTF=True",
            session="London",
            strategy_version="v2.1",
            t0_snapshot_hash="c" * 64,
            open_timestamp_utc=open_dt.isoformat(),
        )
        # 30 wins (1.88R) and 22 losses (-1.0R) -> WR=57.69%, Total R = +34.4R, EV = +0.66R
        is_win = i < 30
        status = "CLOSED_WIN" if is_win else "CLOSED_LOSS"
        r_val = 1.88 if is_win else -1.0
        exit_p = 65880.0 if is_win else 63000.0
        store.close_shadow_trade(
            trade_id=t_id,
            exit_price=exit_p,
            realized_r=r_val,
            outcome_status=status,
            close_timestamp_utc=close_dt.isoformat(),
        )

    report_pass = gate.evaluate_shadow_confirmation()
    assert report_pass.sample_gate_passed is True
    assert report_pass.time_gate_passed is True
    assert report_pass.ev_gate_passed is True
    assert report_pass.wr_gate_passed is True
    assert report_pass.drift_gate_passed is True
    assert report_pass.verdict == "PASS"
    assert "Shadow validation passed" in report_pass.verdict_summary


def test_comparison_gate_fail_state(tmp_path):
    test_db = str(tmp_path / "test_comp_fail.db")
    store = ShadowTradingStore(db_path=test_db)
    gate = BTCShadowComparisonGate(shadow_store=store)

    # 52 trades spanning 16 days but mostly losses (WR=20%, negative EV)
    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(52):
        t_id = f"T-FAIL-{i}"
        open_dt = base_time + timedelta(hours=i * 7.5)
        close_dt = open_dt + timedelta(hours=2)
        store.open_shadow_trade(
            trade_id=t_id,
            asset="BTC/USD",
            direction="BUY",
            entry_price=64000.0,
            stop_loss=63000.0,
            take_profit_1=65880.0,
            take_profit_2=66500.0,
            calibrated_probability=0.52,
            mtf_confluence_state="MTF=True",
            session="London",
            strategy_version="v2.1",
            t0_snapshot_hash="d" * 64,
            open_timestamp_utc=open_dt.isoformat(),
        )
        is_win = i < 10  # Only 10 wins out of 52 -> WR=19.23%
        status = "CLOSED_WIN" if is_win else "CLOSED_LOSS"
        r_val = 1.88 if is_win else -1.0
        exit_p = 65880.0 if is_win else 63000.0
        store.close_shadow_trade(
            trade_id=t_id,
            exit_price=exit_p,
            realized_r=r_val,
            outcome_status=status,
            close_timestamp_utc=close_dt.isoformat(),
        )

    report_fail = gate.evaluate_shadow_confirmation()
    assert report_fail.sample_gate_passed is True
    assert report_fail.time_gate_passed is True
    assert report_fail.ev_gate_passed is False
    assert report_fail.wr_gate_passed is False
    assert report_fail.verdict == "FAIL"
