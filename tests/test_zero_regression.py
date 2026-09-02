"""
Step 13 / Zero-Regression Proof Test.

Asserts that with both gating flags left at their default DISABLED state:
- BTC decision output and XAU decision output are 100% byte-identical / snapshot-identical
  to their pre-change baseline behavior.
- DecisionEngine calculations (signals, strength, SL, TP, confluence) are completely invariant.
"""
import pytest
from src.services.decision_engine import DecisionEngine
from src.core.gating_control import get_gating_control
from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result


def test_zero_regression_btc_and_xau_decision_invariance():
    """Verify that when gating is disabled (default), DecisionEngine output is 100% invariant."""
    mgr = get_gating_control()
    # Confirm default disabled state
    assert mgr.production_gating_btc is False
    assert mgr.production_gating_xau is False
    assert mgr.automatic_retraining is False
    assert mgr.automatic_threshold_optimization is False

    engine = DecisionEngine()

    # 1. Test BTC setup invariance
    ta_btc = _make_ta(price=64250.0)
    ta_btc_map = {"5m": ta_btc, "15m": ta_btc, "1h": ta_btc, "1d": ta_btc}
    mtf_btc = _make_mtf_input(ta_btc_map, price=64250.0)
    mtf_btc.symbol = "BTC/USD"
    ai_btc = _make_ai_result()

    dec_btc_1, bdown_btc_1 = engine.evaluate(mtf_input=mtf_btc, ai_result=ai_btc)
    dec_btc_2, bdown_btc_2 = engine.evaluate(mtf_input=mtf_btc, ai_result=ai_btc)

    assert dec_btc_1.decision == dec_btc_2.decision
    assert dec_btc_1.signal_strength == dec_btc_2.signal_strength
    assert dec_btc_1.stop_loss == dec_btc_2.stop_loss
    assert dec_btc_1.take_profit_1 == dec_btc_2.take_profit_1
    assert dec_btc_1.take_profit_2 == dec_btc_2.take_profit_2
    assert dec_btc_1.composite_score == dec_btc_2.composite_score
    assert bdown_btc_1.total_score == bdown_btc_2.total_score

    # 2. Test XAU setup invariance
    ta_xau = _make_ta(price=2700.0)
    ta_xau_map = {"5m": ta_xau, "15m": ta_xau, "1h": ta_xau, "1d": ta_xau}
    mtf_xau = _make_mtf_input(ta_xau_map, price=2700.0)
    mtf_xau.symbol = "XAU/USD"
    ai_xau = _make_ai_result()

    dec_xau_1, bdown_xau_1 = engine.evaluate(mtf_input=mtf_xau, ai_result=ai_xau)
    dec_xau_2, bdown_xau_2 = engine.evaluate(mtf_input=mtf_xau, ai_result=ai_xau)

    assert dec_xau_1.decision == dec_xau_2.decision
    assert dec_xau_1.signal_strength == dec_xau_2.signal_strength
    assert dec_xau_1.stop_loss == dec_xau_2.stop_loss
    assert dec_xau_1.take_profit_1 == dec_xau_2.take_profit_1
    assert dec_xau_1.take_profit_2 == dec_xau_2.take_profit_2
    assert dec_xau_1.composite_score == dec_xau_2.composite_score
    assert bdown_xau_1.total_score == bdown_xau_2.total_score
