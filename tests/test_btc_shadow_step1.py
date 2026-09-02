"""
Step 1 Tests: BTC Shadow Runner & Paper Simulation Engine Isolation.
"""
import pytest
import os
from src.services.shadow_trading_store import ShadowTradingStore
from src.services.btc_shadow_runner import BTCShadowRunner
from src.services.paper_trading_service import PaperTradingService


def test_shadow_store_isolation_from_manual_demo(tmp_path):
    # Setup test shadow store
    test_db = str(tmp_path / "test_shadow.db")
    shadow_store = ShadowTradingStore(db_path=test_db)

    # 1. Open a shadow trade
    rec = shadow_store.open_shadow_trade(
        trade_id="FWD-BTC-TEST01",
        asset="BTC/USD",
        direction="BUY",
        entry_price=64000.0,
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        calibrated_probability=0.58,
        mtf_confluence_state="MTF_ALIGNED=True|CONFLUENCE=70",
        session="London",
        strategy_version="STRATEGY_v2.1_BTC_CONFLUENCE",
        t0_snapshot_hash="a" * 64,
    )
    assert rec is not None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 1

    # 2. Reset the user manual demo account
    pt = PaperTradingService()
    pt.reset_account()

    # 3. Verify shadow store was NOT affected by manual demo reset
    trades_after_reset = shadow_store.get_all_trades("BTC/USD")
    assert len(trades_after_reset) == 1
    assert trades_after_reset[0].trade_id == "FWD-BTC-TEST01"


def test_btc_shadow_runner_qualification_filter(tmp_path):
    test_db = str(tmp_path / "test_shadow2.db")
    shadow_store = ShadowTradingStore(db_path=test_db)
    runner = BTCShadowRunner(shadow_store=shadow_store)

    # Setup 1: Low probability (< 50%) -> Filtered
    res_low_p = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=65.0,
        confidence_score=70.0,
        signal_strength=60.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.42,  # Sub-50%
    )
    assert res_low_p is None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 0

    # Setup 2: MTF unaligned -> Filtered
    res_no_mtf = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=65.0,
        confidence_score=70.0,
        signal_strength=60.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=False,  # Unaligned
        ml_calibrated_prob=0.58,
    )
    assert res_no_mtf is None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 0

    # Setup 3: Range chop -> Filtered
    res_chop = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=65.0,
        confidence_score=70.0,
        signal_strength=60.0,
        market_regime="Range Chop",  # Chop
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.58,
    )
    assert res_chop is None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 0

    # Setup 4: Valid BTC v2.1 setup -> Captured
    res_valid = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=68.0,
        confidence_score=72.0,
        signal_strength=70.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.58,
    )
    assert res_valid is not None
    assert len(shadow_store.get_all_trades("BTC/USD")) == 1


def test_btc_shadow_runner_resolution_and_status(tmp_path):
    test_db = str(tmp_path / "test_shadow3.db")
    shadow_store = ShadowTradingStore(db_path=test_db)
    runner = BTCShadowRunner(shadow_store=shadow_store)

    # Capture a BUY trade: entry=64000, sl=63000, tp=65880
    _ = runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=68.0,
        confidence_score=72.0,
        signal_strength=70.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.58,
    )

    # Price moves to high 66000 (hits TP1)
    closed = runner.update_open_shadow_trades(current_price=65900.0, high_price=66000.0, low_price=63900.0)
    assert len(closed) == 1

    status = runner.get_shadow_status()
    assert status["status"] == "success"
    assert status["live_shadow_metrics"]["resolved_trades_count"] == 1
    assert status["live_shadow_metrics"]["wins_count"] == 1
    assert status["live_shadow_metrics"]["ev_r"] > 0
    assert status["backtest_reference_baseline"]["win_rate_pct"] == 55.88
