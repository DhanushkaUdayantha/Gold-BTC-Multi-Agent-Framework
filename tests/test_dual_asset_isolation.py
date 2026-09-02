"""
Dual-Asset Cross-Contamination & Store Isolation Tests.

Verifies:
1. BTC shadow operations never touch XAU shadow records.
2. XAU shadow operations never touch BTC shadow records.
3. User demo account reset (POST /trade/reset) never affects either BTC or XAU shadow ledger.
"""
import pytest
from src.services.shadow_trading_store import ShadowTradingStore
from src.services.btc_shadow_runner import BTCShadowRunner
from src.services.xau_shadow_runner import XAUShadowRunner
from src.services.paper_trading_service import PaperTradingService


def test_dual_asset_complete_isolation(tmp_path):
    test_db = str(tmp_path / "dual_iso.db")
    store = ShadowTradingStore(db_path=test_db)
    btc_runner = BTCShadowRunner(shadow_store=store)
    xau_runner = XAUShadowRunner(shadow_store=store)

    # 1. Open a BTC shadow trade
    btc_res = btc_runner.evaluate_live_market_setup(
        current_price=64000.0,
        direction="BUY",
        stop_loss=63000.0,
        take_profit_1=65880.0,
        take_profit_2=66500.0,
        confluence_score=70.0,
        confidence_score=72.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ml_calibrated_prob=0.58,
    )
    assert btc_res is not None

    # 2. Open an XAU shadow trade
    xau_res = xau_runner.evaluate_live_market_setup(
        current_price=2700.0,
        direction="SELL",
        stop_loss=2720.0,
        take_profit_1=2664.0,
        take_profit_2=2650.0,
        confluence_score=68.0,
        confidence_score=70.0,
        signal_strength=66.0,
        market_regime="Bear Trend",
        session="New York",
        mtf_aligned=True,
        ml_calibrated_prob=0.56,
    )
    assert xau_res is not None

    # Verify counts per asset
    btc_trades = store.get_all_trades("BTC/USD")
    xau_trades = store.get_all_trades("XAU/USD")
    assert len(btc_trades) == 1
    assert len(xau_trades) == 1
    assert btc_trades[0].asset == "BTC/USD"
    assert xau_trades[0].asset == "XAU/USD"

    # 3. Close BTC trade (does not affect XAU)
    closed_btc = btc_runner.update_open_shadow_trades(current_price=66000.0, high_price=66000.0, low_price=63900.0)
    assert len(closed_btc) == 1

    xau_after = store.get_all_trades("XAU/USD")
    assert len(xau_after) == 1
    assert xau_after[0].status == "OPEN"

    # 4. User resets manual demo account
    demo_pt = PaperTradingService()
    demo_pt.reset_account()

    # Verify both shadow ledgers remain completely intact
    assert len(store.get_all_trades("BTC/USD")) == 1
    assert len(store.get_all_trades("XAU/USD")) == 1
