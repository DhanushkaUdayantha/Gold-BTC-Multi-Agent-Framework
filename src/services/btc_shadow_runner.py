"""
BTC v2.1 Shadow Runner & Paper Simulation Engine.

Executes BTC v2.1 (Probabilistic + MTF Confluence) strategy against live BTC market data:
- Reuses ForwardShadowEngine for immutable T0 signal capture, SHA-256 hashing, and deduplication.
- Logs mock shadow positions into the isolated ShadowTradingStore (data/shadow_trades.db).
- Zero broker imports, zero execution credentials, zero real order placement.
- Fully isolated from live /api/v1/decision production outputs.

DISCLAIMER: Advisory shadow analytics only. No real broker orders are executed.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.research.governance.forward_shadow import ForwardShadowEngine, get_forward_shadow_engine
from src.services.shadow_trading_store import ShadowTradingStore, get_shadow_trading_store

logger = logging.getLogger(__name__)

_STRATEGY_VERSION = "STRATEGY_v2.1_BTC_CONFLUENCE"


class BTCShadowRunner:
    """
    Background runner that executes BTC v2.1 strategy logic in shadow mode.
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
        self._is_running = False
        self._loop_task: Optional[asyncio.Task] = None

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
        Evaluate a candidate BTC market setup under BTC v2.1 qualification rules:
        1. Calibrated win probability >= 50%
        2. MTF trend alignment is True
        3. Market regime is not Range Chop
        """
        ts = timestamp_utc or datetime.now(timezone.utc).isoformat()

        # Step 1: Check BTC v2.1 Qualification Gate
        is_qualified = (
            ml_calibrated_prob >= 0.50
            and mtf_aligned
            and "chop" not in market_regime.lower()
        )

        if not is_qualified:
            logger.debug(
                f"[BTC Shadow Runner] Setup filtered: P_cal={ml_calibrated_prob:.2f}, "
                f"MTF={mtf_aligned}, Regime={market_regime}"
            )
            return None

        # Step 2: Immutable T0 snapshot capture via forward_shadow engine
        snapshot = self.forward_engine.capture_forward_signal(
            asset="BTC/USD",
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
            logger.warning("[BTC Shadow Runner] Failed to capture T0 snapshot.")
            return None

        # Step 3: Record trade in the isolated shadow ledger
        trade_id = snapshot.signal_id
        trade_record = self.store.open_shadow_trade(
            trade_id=trade_id,
            asset="BTC/USD",
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
            f"[BTC Shadow Runner] Shadow trade recorded: ID={trade_id}, Dir={direction}, "
            f"Entry={current_price}, P_cal={ml_calibrated_prob:.2%}"
        )
        return trade_record.to_dict() if trade_record else None

    def update_open_shadow_trades(self, current_price: float, high_price: float, low_price: float) -> List[str]:
        """
        Deterministically resolve open shadow positions against incoming bar highs/lows.
        """
        open_trades = [t for t in self.store.get_all_trades("BTC/USD") if t.status == "OPEN"]
        closed_ids = []

        for t in open_trades:
            sl = t.stop_loss
            tp = t.take_profit_1
            direction = t.direction.upper()

            if direction == "BUY":
                risk = t.entry_price - sl
                # Check Stop Loss hit
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
                # Check Take Profit hit
                elif high_price >= tp:
                    reward = tp - t.entry_price
                    realized_r = (reward / risk) if risk > 0 else 1.88
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
                # Check Stop Loss hit
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
                # Check Take Profit hit
                elif low_price <= tp:
                    reward = t.entry_price - tp
                    realized_r = (reward / risk) if risk > 0 else 1.88
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
        Return the live shadow performance metrics alongside the historical backtest baseline.
        """
        metrics = self.store.get_summary_metrics(asset="BTC/USD")

        # Canonical backtest forward-shadow baseline for BTC
        baseline = {
            "reference_dataset": "BTC Forward Shadow Baseline (Historical)",
            "sample_size_n": 68,
            "win_rate_pct": 55.88,
            "expected_value_r": 0.3650,
            "profit_factor": 1.76,
            "max_drawdown_r": 5.5,
            "bootstrap_95_ci_ev": [0.0444, 0.3240],
            "evidence_status": "ACCUMULATING",
        }

        # Delta comparisons
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


_btc_shadow_runner_instance: Optional[BTCShadowRunner] = None


def get_btc_shadow_runner() -> BTCShadowRunner:
    global _btc_shadow_runner_instance
    if _btc_shadow_runner_instance is None:
        _btc_shadow_runner_instance = BTCShadowRunner()
    return _btc_shadow_runner_instance
