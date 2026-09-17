"""
XAU/USD Shadow Runner & Paper Simulation Engine.

Executes XAU Strategy (Probabilistic + Session-Aware MTF Confluence) in shadow mode:
- Reuses ForwardShadowEngine for immutable T0 signal capture, SHA-256 hashing, and deduplication.
- Logs mock shadow positions into the isolated ShadowTradingStore (data/shadow_trades.db) under asset='XAU/USD'.
- Zero broker imports, zero execution credentials, zero real order placement.
- Fully isolated from live /api/v1/decision production outputs.

DISCLAIMER: Advisory shadow analytics only. No real broker orders are executed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.research.governance.forward_shadow import ForwardShadowEngine, get_forward_shadow_engine
from src.services.shadow_trading_store import ShadowTradingStore, get_shadow_trading_store

logger = logging.getLogger(__name__)

_STRATEGY_VERSION = "STRATEGY_v2.0_XAU_CONFLUENCE"


class XAUShadowRunner:
    """
    Background runner that executes XAU strategy logic in shadow mode.
    """

    def __init__(
        self,
        shadow_store: Optional[ShadowTradingStore] = None,
        forward_engine: Optional[ForwardShadowEngine] = None,
    ):
        self.store = shadow_store or get_shadow_trading_store()
        if forward_engine is not None:
            self.forward_engine = forward_engine
        elif shadow_store is not None:
            # Test or custom runner isolation: NEVER write to production DB when a custom shadow_store is provided
            self.forward_engine = ForwardShadowEngine(db_path=shadow_store.db_path)
        else:
            self.forward_engine = get_forward_shadow_engine()

    def evaluate_live_market_setup(
        self,
        current_price: float,
        direction: str,
        stop_loss: float,
        take_profit_1: float,
        take_profit_2: float,
        confluence_score: float,
        confidence_score: float,
        signal_strength: float,
        market_regime: str,
        session: str,
        mtf_aligned: bool,
        ml_calibrated_prob: float,
        timestamp_utc: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a candidate XAU market setup under XAU qualification rules:
        1. Calibrated win probability >= 50%
        2. MTF trend alignment is True
        3. Market regime is not Range Chop
        """
        ts = timestamp_utc or datetime.now(timezone.utc).isoformat()

        is_qualified = (
            ml_calibrated_prob >= 0.50
            and mtf_aligned
            and "chop" not in market_regime.lower()
        )

        if not is_qualified:
            logger.debug(
                f"[XAU Shadow Runner] Setup filtered: P_cal={ml_calibrated_prob:.2f}, "
                f"MTF={mtf_aligned}, Regime={market_regime}"
            )
            return None

        # Immutable T0 snapshot capture via forward_shadow engine
        snapshot = self.forward_engine.capture_forward_signal(
            asset="XAU/USD",
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confluence_score=confluence_score,
            confidence_score=confidence_score,
            signal_strength=signal_strength,
            market_regime=market_regime,
            session=session,
            mtf_aligned=mtf_aligned,
            ml_raw_probability=ml_calibrated_prob,
            ml_calibrated_probability=ml_calibrated_prob,
            strategy_version=_STRATEGY_VERSION,
            features_dict={
                "confluence": confluence_score,
                "confidence": confidence_score,
                "regime": market_regime,
                "session": session,
                "mtf_aligned": mtf_aligned,
            },
            timestamp_utc=ts,
            evidence_generation="CLEAN_FORWARD",
        )

        if not snapshot:
            logger.warning("[XAU Shadow Runner] Failed to capture T0 snapshot.")
            return None

        trade_id = snapshot.signal_id
        trade_record = self.store.open_shadow_trade(
            trade_id=trade_id,
            asset="XAU/USD",
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            calibrated_probability=ml_calibrated_prob,
            mtf_confluence_state=f"MTF_ALIGNED={mtf_aligned}|CONFLUENCE={confluence_score}",
            session=session,
            strategy_version=_STRATEGY_VERSION,
            t0_snapshot_hash=snapshot.snapshot_hash,
            open_timestamp_utc=ts,
        )

        logger.info(
            f"[XAU Shadow Runner] Shadow trade recorded: ID={trade_id}, Dir={direction}, "
            f"Entry={current_price}, P_cal={ml_calibrated_prob:.2%}"
        )
        return trade_record.to_dict() if trade_record else None

    def update_open_shadow_trades(self, current_price: float, high_price: float, low_price: float) -> List[str]:
        """
        Deterministically resolve open XAU shadow positions against incoming bar highs/lows.
        """
        open_trades = [t for t in self.store.get_all_trades("XAU/USD") if t.status == "OPEN"]
        closed_ids = []

        for t in open_trades:
            sl = t.stop_loss
            tp = t.take_profit_1
            direction = t.direction.upper()

            if direction == "BUY":
                risk = t.entry_price - sl
                if low_price <= sl:
                    realized_r = -1.0
                    self.store.close_shadow_trade(
                        trade_id=t.trade_id,
                        exit_price=sl,
                        realized_r=realized_r,
                        outcome_status="CLOSED_LOSS",
                        outcome_notes="Stop loss reached",
                    )
                    closed_ids.append(t.trade_id)
                elif high_price >= tp:
                    reward = tp - t.entry_price
                    realized_r = (reward / risk) if risk > 0 else 1.80
                    self.store.close_shadow_trade(
                        trade_id=t.trade_id,
                        exit_price=tp,
                        realized_r=round(realized_r, 2),
                        outcome_status="CLOSED_WIN",
                        outcome_notes="Take profit 1 reached",
                    )
                    closed_ids.append(t.trade_id)

            elif direction == "SELL":
                risk = sl - t.entry_price
                if high_price >= sl:
                    realized_r = -1.0
                    self.store.close_shadow_trade(
                        trade_id=t.trade_id,
                        exit_price=sl,
                        realized_r=realized_r,
                        outcome_status="CLOSED_LOSS",
                        outcome_notes="Stop loss reached",
                    )
                    closed_ids.append(t.trade_id)
                elif low_price <= tp:
                    reward = t.entry_price - tp
                    realized_r = (reward / risk) if risk > 0 else 1.80
                    self.store.close_shadow_trade(
                        trade_id=t.trade_id,
                        exit_price=tp,
                        realized_r=round(realized_r, 2),
                        outcome_status="CLOSED_WIN",
                        outcome_notes="Take profit 1 reached",
                    )
                    closed_ids.append(t.trade_id)

        return closed_ids

    def get_shadow_status(self) -> Dict[str, Any]:
        """
        Return the live XAU shadow performance metrics alongside the historical backtest baseline.
        """
        metrics = self.store.get_summary_metrics(asset="XAU/USD")

        baseline = {
            "reference_dataset": "XAU Forward Shadow Baseline (Historical)",
            "sample_size_n": 45,
            "win_rate_pct": 51.11,
            "expected_value_r": 0.2450,
            "profit_factor": 1.48,
            "max_drawdown_r": 4.0,
            "bootstrap_95_ci_ev": [0.0444, 0.6500],
            "evidence_status": "ACCUMULATING",
            "holdout_milestone_target_n": 50,
        }

        res_count = metrics["resolved_trades_count"]
        live_ev = metrics["ev_r"]
        live_wr = metrics["win_rate_pct"]
        live_pf = metrics["profit_factor"]

        comparison = {
            "ev_delta_vs_baseline": round(live_ev - baseline["expected_value_r"], 4) if res_count > 0 else None,
            "wr_delta_vs_baseline": round(live_wr - baseline["win_rate_pct"], 2) if res_count > 0 else None,
            "pf_delta_vs_baseline": round(live_pf - baseline["profit_factor"], 2) if res_count > 0 else None,
            "sample_progress_pct": round((res_count / 50.0) * 100.0, 1),
            "sample_milestone_met": res_count >= 50,
        }

        return {
            "status": "success",
            "strategy_version": _STRATEGY_VERSION,
            "disclaimer": "Advisory shadow analytics only. Zero real broker connections or executions.",
            "live_shadow_metrics": metrics,
            "backtest_reference_baseline": baseline,
            "comparison_vs_baseline": comparison,
        }


_xau_shadow_runner_instance: Optional[XAUShadowRunner] = None


def get_xau_shadow_runner() -> XAUShadowRunner:
    global _xau_shadow_runner_instance
    if _xau_shadow_runner_instance is None:
        _xau_shadow_runner_instance = XAUShadowRunner()
    return _xau_shadow_runner_instance
