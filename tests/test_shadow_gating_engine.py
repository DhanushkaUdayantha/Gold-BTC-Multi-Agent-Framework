"""
Unit tests for hypothetical shadow gating engine.
"""
from src.models.trading_decision import ValidatedStrategyEvaluation
from src.research.hypothetical_gating import (
    GatingAction,
    GatingPolicyType,
    HypotheticalGatingEngine,
    ShadowDecision,
)
from src.research.trade_semantics import SignalDirection


def test_shadow_gate_strict_policy_qualified():
    val_eval = ValidatedStrategyEvaluation(
        strategy_id="BTC-SELL-P40-REGIME_LOW_VOL",
        strategy_name="BTC SELL LOW-VOL",
        qualified=True,
        qualification_status="QUALIFIED",
        direction="SELL",
        confirmation_score=4,
        max_confirmation_score=4,
        probability=0.45,
        regime="LOW_VOLATILITY",
        confirmations=["P>=40%", "LOW_VOL", "HTF", "SR"],
        failed_conditions=[],
        research_expectancy_r=0.47,
        research_win_rate_pct=58.9,
        research_profit_factor=2.15,
        validation_score=95,
        degradation_status="NORMAL",
        disclaimer="Advisory only",
    )

    # Base SELL + Qualified SELL -> KEEP
    dec = HypotheticalGatingEngine.evaluate_shadow_gate(
        signal_id="sig_1",
        symbol="BTC-USD",
        timestamp="2026-01-01T00:00:00Z",
        base_direction="SELL",
        val_eval=val_eval,
        policy=GatingPolicyType.POLICY_A_STRICT,
    )
    assert dec.shadow_direction == SignalDirection.SELL
    assert dec.action == GatingAction.KEEP


def test_shadow_gate_btc_buy_conflict():
    val_eval = ValidatedStrategyEvaluation(
        strategy_id="BTC-SELL-P40-REGIME_LOW_VOL",
        strategy_name="BTC SELL LOW-VOL",
        qualified=False,
        qualification_status="CONFLICT",
        direction="SELL",
        confirmation_score=0,
        max_confirmation_score=4,
        probability=0.45,
        regime="LOW_VOLATILITY",
        confirmations=[],
        failed_conditions=["BTC BUY opposes validated strategy direction (SELL)"],
        research_expectancy_r=0.47,
        research_win_rate_pct=58.9,
        research_profit_factor=2.15,
        validation_score=95,
        degradation_status="NORMAL",
        conflict_reason="Historical research found negative drift on BTC BUY.",
        disclaimer="Advisory only",
    )

    # Base BUY + Validated SELL Conflict -> SHADOW WAIT (Action: CONFLICT)
    dec = HypotheticalGatingEngine.evaluate_shadow_gate(
        signal_id="sig_2",
        symbol="BTC-USD",
        timestamp="2026-01-01T00:00:00Z",
        base_direction="BUY",
        val_eval=val_eval,
        policy=GatingPolicyType.POLICY_A_STRICT,
    )
    assert dec.shadow_direction == SignalDirection.WAIT
    assert dec.action == GatingAction.CONFLICT
    assert dec.base_direction == SignalDirection.BUY


def test_shadow_gate_base_wait_passes_through():
    dec = HypotheticalGatingEngine.evaluate_shadow_gate(
        signal_id="sig_3",
        symbol="XAU-USD",
        timestamp="2026-01-01T00:00:00Z",
        base_direction="WAIT",
        val_eval=None,
        policy=GatingPolicyType.POLICY_A_STRICT,
    )
    assert dec.shadow_direction == SignalDirection.WAIT
    assert dec.action == GatingAction.NO_STRATEGY
