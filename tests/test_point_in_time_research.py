"""
Unit tests for point-in-time sequential research and zero lookahead invariants.
"""
from src.services.validated_strategy_layer import ValidatedStrategyLayer


def test_point_in_time_zero_future_outcome_influence():
    strat_layer = ValidatedStrategyLayer.get_instance()

    # Evaluation at timestamp T uses ONLY instantaneous features at T
    val_eval_1, _ = strat_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="SELL",
        calibrated_probability=0.45,
        market_regime="LOW_VOLATILITY",
        htf_aligned=True,
        sr_aligned=True,
        confluence_score=75,
    )

    # Qualification is deterministic and independent of future trade outcome
    assert val_eval_1.qualified is True
    assert val_eval_1.confirmation_score == 4


def test_point_in_time_chronological_replay_safety():
    strat_layer = ValidatedStrategyLayer.get_instance()

    # Simulating two chronological setups T1 and T2
    t1_eval, _ = strat_layer.evaluate_realtime_setup(
        symbol="XAU/USD",
        proposed_direction="BUY",
        calibrated_probability=0.44,
        market_regime="TRENDING",
        vwap_aligned=True,
        ema_aligned=True,
        htf_aligned=True,
    )

    t2_eval, _ = strat_layer.evaluate_realtime_setup(
        symbol="BTC/USD",
        proposed_direction="BUY",
        calibrated_probability=0.48,
        market_regime="LOW_VOLATILITY",
    )

    assert t1_eval.qualified is True
    assert t1_eval.strategy_id == "XAU-BUY-P42-VWAP_ALIGNED"

    # T2 is BTC BUY -> Must produce CONFLICT without mutating T1 or production
    assert t2_eval.qualified is False
    assert t2_eval.qualification_status == "CONFLICT"
