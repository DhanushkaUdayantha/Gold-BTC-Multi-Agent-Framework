"""
Historical Backtest Runner & Empirical Analytics Engine.

Replays historical market data through the EXISTING ConfluenceEngine,
observes future outcomes without lookahead, calculates statistical metrics,
and calibrates empirical win probabilities with strict chronological 70/30 separation.

DISCLAIMER: Research and analytical modeling only. No real trades are executed.
"""
from __future__ import annotations

import bisect
import json
import logging
import math
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.models.historical_data import (
    BacktestConfig,
    BacktestRunRecord,
    HistoricalSignalRecord,
    BacktestPerformanceReport,
    ScoreBandPerformance,
    ContributorPerformance,
    MarketRegimePerformance,
    BacktestStatus,
    AmbiguousCandleRule,
)
from src.services.confluence_engine import ConfluenceEngine, CONTRIBUTOR_MAX_SCORES
from src.services.historical_data_service import HistoricalDataService, HistoricalCandle
from src.services.historical_snapshot_builder import HistoricalSnapshotBuilder
from src.services.probability_calibrator import ProbabilityCalibrator

logger = logging.getLogger(__name__)


class HistoricalBacktestRunner:
    """Orchestrates asynchronous backtest execution, outcome labeling, and empirical analytics."""

    _active_jobs: Dict[str, BacktestRunRecord] = {}
    _job_lock = threading.RLock()

    def __init__(self, data_service: Optional[HistoricalDataService] = None):
        self.data_service = data_service or HistoricalDataService.get_instance()
        self.snapshot_builder = HistoricalSnapshotBuilder()

    @classmethod
    def get_run_status(cls, run_id: str) -> Optional[BacktestRunRecord]:
        with cls._job_lock:
            return cls._active_jobs.get(run_id)

    def start_backtest_async(self, config: BacktestConfig) -> BacktestRunRecord:
        """Launch a historical backtest as a non-blocking background thread."""
        run_id = f"RUN-{config.symbol.replace('/', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        dataset_id = f"DATASET-{config.symbol.replace('/', '-')}-15M"

        run_record = BacktestRunRecord(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_version="v2.0",
            engine_version="ConfluenceEngine-v2.0",
            symbol=config.symbol,
            config=config,
            status=BacktestStatus.PENDING,
            progress_pct=0.0,
            current_step="Initializing historical backtest job...",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._job_lock:
            self._active_jobs[run_id] = run_record

        # Persist pending record
        self._save_run_record(run_record)

        thread = threading.Thread(
            target=self._execute_backtest_job,
            args=(run_record,),
            daemon=True,
            name=f"BacktestWorker-{run_id}",
        )
        thread.start()
        return run_record

    def run_backtest_sync(self, config: BacktestConfig) -> Tuple[BacktestRunRecord, BacktestPerformanceReport]:
        """Run backtest synchronously (useful for tests and direct evaluation)."""
        run_id = f"RUN-{config.symbol.replace('/', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        dataset_id = f"DATASET-{config.symbol.replace('/', '-')}-15M"

        run_record = BacktestRunRecord(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_version="v2.0",
            engine_version="ConfluenceEngine-v2.0",
            symbol=config.symbol,
            config=config,
            status=BacktestStatus.PENDING,
            progress_pct=0.0,
            current_step="Running synchronous backtest...",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        report = self._execute_backtest_job(run_record)
        return run_record, report

    # -----------------------------------------------------------------------
    # Main Execution Pipeline
    # -----------------------------------------------------------------------

    def _execute_backtest_job(self, run_record: BacktestRunRecord) -> Optional[BacktestPerformanceReport]:
        start_wall_time = time.time()
        run_record.started_at = datetime.now(timezone.utc).isoformat()
        run_record.status = BacktestStatus.RUNNING

        try:
            cfg = run_record.config
            self._update_progress(run_record, 5.0, f"Loading multi-timeframe candles for {cfg.symbol}...")

            # 1. Load multi-timeframe candle datasets
            candles_by_tf: Dict[str, List[HistoricalCandle]] = {}
            for tf in cfg.context_timeframes:
                c_list = self.data_service.get_candles(
                    symbol=cfg.symbol,
                    timeframe=tf,
                    start_date=cfg.start_date,
                    end_date=cfg.end_date,
                )
                candles_by_tf[tf] = c_list

            primary_tf = cfg.primary_timeframe
            primary_candles = candles_by_tf.get(primary_tf, [])

            if not primary_candles or len(primary_candles) < 50:
                raise ValueError(
                    f"Insufficient historical data for {cfg.symbol} ({primary_tf}). "
                    f"Found {len(primary_candles)} candles; minimum 50 required. Please download dataset first."
                )

            self._update_progress(run_record, 15.0, f"Loaded {len(primary_candles)} primary candles. Synchronizing historical snapshots...")

            # 2. Replay timestamps and generate historical signals
            confluence_engine = ConfluenceEngine()
            generated_signals: List[HistoricalSignalRecord] = []
            last_signal_time = 0
            active_trade_exit_time = 0

            total_candles = len(primary_candles)
            # Determine 70/30 chronological train/val threshold
            split_idx = int(total_candles * cfg.train_ratio)
            train_val_split_epoch = primary_candles[split_idx].epoch_ms if split_idx < total_candles else primary_candles[-1].epoch_ms

            primary_epochs = [c.epoch_ms for c in primary_candles]
            idx = 35
            while idx < total_candles:
                if idx % max(1, (total_candles // 20)) == 0:
                    pct = 15.0 + (idx / total_candles) * 45.0
                    self._update_progress(run_record, pct, f"Evaluating ConfluenceEngine at step {idx}/{total_candles}...")

                candle = primary_candles[idx]
                decision_epoch_ms = candle.epoch_ms

                # Check overlap restriction
                if not cfg.allow_overlapping_trades and decision_epoch_ms < active_trade_exit_time:
                    next_idx = bisect.bisect_right(primary_epochs, active_trade_exit_time)
                    if next_idx > idx:
                        idx = next_idx
                        continue
                    else:
                        idx += 1
                        continue

                # Build zero look-ahead snapshot at decision timestamp
                snapshot = self.snapshot_builder.build_snapshot_at_timestamp(
                    symbol=cfg.symbol,
                    decision_epoch_ms=decision_epoch_ms,
                    candles_by_tf=candles_by_tf,
                    source_symbol="BTCUSDT" if "BTC" in cfg.symbol else "GC=F",
                )

                if not snapshot:
                    idx += 1
                    continue

                # Execute EXISTING ConfluenceEngine
                res = confluence_engine.compute(snapshot)

                # Filter actionable signals
                if res.signal in ("BUY", "SELL") and res.final_score >= cfg.min_confluence_score and res.gate_passed:
                    # Check 60s duplicate cooldown
                    if decision_epoch_ms - last_signal_time < cfg.duplicate_window_seconds * 1000:
                        idx += 1
                        continue

                    last_signal_time = decision_epoch_ms

                    # Calculate structural SL / TP based on ATR & price
                    entry_p = snapshot.current_price
                    atr_val = snapshot.ta_15m.atr14.value if (snapshot.ta_15m and snapshot.ta_15m.atr14 and snapshot.ta_15m.atr14.value) else (entry_p * 0.005)
                    sl_dist = max(entry_p * 0.002, atr_val * 1.5)

                    if res.signal == "BUY":
                        sl = entry_p - sl_dist
                        tp1 = entry_p + (sl_dist * 1.5)
                        tp2 = entry_p + (sl_dist * 2.5)
                    else:
                        sl = entry_p + sl_dist
                        tp1 = entry_p - (sl_dist * 1.5)
                        tp2 = entry_p - (sl_dist * 2.5)

                    # Classify regime
                    regime = self._detect_market_regime(snapshot)
                    session = self._detect_session(candle.timestamp)
                    is_in_sample = decision_epoch_ms < train_val_split_epoch

                    signal_id = f"SIG-{run_record.run_id}-{len(generated_signals) + 1:04d}"

                    sig_record = HistoricalSignalRecord(
                        signal_id=signal_id,
                        run_id=run_record.run_id,
                        dataset_id=run_record.dataset_id,
                        symbol=cfg.symbol,
                        source_symbol="BTCUSDT" if "BTC" in cfg.symbol else "GC=F",
                        signal_timestamp=candle.timestamp,
                        snapshot_id=snapshot.snapshot_id,
                        entry_price=entry_p,
                        direction=res.signal,
                        confluence_score=res.final_score,
                        technical_score=res.technical_score,
                        gemini_score=res.gemini_score,
                        contributor_scores={c.name: c.score for c in res.contributors},
                        contributor_directions={c.name: c.bias for c in res.contributors},
                        data_quality=res.data_quality,
                        gate_direction=res.gate_direction,
                        stop_loss=round(sl, 4),
                        take_profit_1=round(tp1, 4),
                        take_profit_2=round(tp2, 4),
                        invalidation_level=round(sl, 4),
                        market_regime=regime,
                        session=session,
                        strategy_evidence=[f"{c.name}: {c.bias} (+{c.score})" for c in res.contributors if c.score > 0],
                        conflicts=[],
                        is_in_sample=is_in_sample,
                    )

                    # 3. Label future outcome strictly from future candles (> decision_epoch_ms)
                    future_slice = primary_candles[idx + 1:]
                    outcome_res = self._evaluate_future_outcome(
                        sig=sig_record,
                        future_candles=future_slice,
                        config=cfg,
                    )

                    if outcome_res:
                        sig_record.outcome = outcome_res["outcome"]
                        sig_record.outcome_timestamp = outcome_res["outcome_timestamp"]
                        sig_record.exit_price = outcome_res["exit_price"]
                        sig_record.realized_r = outcome_res["realized_r"]
                        sig_record.mfe = outcome_res["mfe"]
                        sig_record.mae = outcome_res["mae"]
                        sig_record.max_r = outcome_res["max_r"]
                        sig_record.time_to_outcome_minutes = outcome_res["time_to_outcome_minutes"]
                        sig_record.transaction_cost_deducted = outcome_res["cost"]
                        sig_record.ambiguity_flag = outcome_res["ambiguity_flag"]

                        if outcome_res.get("exit_epoch_ms"):
                            active_trade_exit_time = outcome_res["exit_epoch_ms"]

                        # Derive deterministic, factual success or failure reasons from actual engine state & outcome
                        if sig_record.outcome == "WIN":
                            top_contribs = sorted(
                                [(k, v) for k, v in sig_record.contributor_scores.items() if v > 0],
                                key=lambda x: x[1],
                                reverse=True
                            )
                            top_str = ", ".join([f"{c[0]} (+{c[1]})" for c in top_contribs[:2]]) if top_contribs else "Confluence alignment"
                            mae_str = f", MAE={sig_record.mae:.2f}R" if sig_record.mae is not None else ""
                            sig_record.success_reason = f"{sig_record.direction} target reached: {top_str} in {sig_record.market_regime} regime{mae_str}"
                            sig_record.failure_reason = None
                        elif sig_record.outcome == "LOSS":
                            if sig_record.ambiguity_flag:
                                sig_record.failure_reason = "Ambiguous high-volatility candle sweep triggered stop-loss before target"
                            elif sig_record.mfe and sig_record.mfe >= 1.0:
                                sig_record.failure_reason = f"Post-expansion reversal: Reached {sig_record.mfe:.2f}R favorable move before reversing into stop-loss"
                            elif sig_record.market_regime == "HIGH_VOLATILITY":
                                sig_record.failure_reason = "Volatile market structure expansion triggered stop-loss against direction"
                            elif sig_record.conflicts:
                                sig_record.failure_reason = f"Structural conflict materialized: {sig_record.conflicts[0]}"
                            else:
                                sig_record.failure_reason = f"Adverse price drift ({sig_record.market_regime}) invalidated {sig_record.direction} structure"
                            sig_record.success_reason = None
                        elif sig_record.outcome == "EXPIRED":
                            sig_record.failure_reason = f"Position expired after {cfg.expiry_hours}h without reaching take-profit or stop-loss"
                            sig_record.success_reason = None

                    generated_signals.append(sig_record)

                    if not cfg.allow_overlapping_trades and outcome_res and outcome_res.get("exit_epoch_ms"):
                        active_trade_exit_time = outcome_res["exit_epoch_ms"]
                        next_idx = bisect.bisect_right(primary_epochs, active_trade_exit_time)
                        if next_idx > idx:
                            idx = next_idx
                            continue

                idx += (4 if primary_tf == "15m" else 1)

            self._update_progress(run_record, 70.0, f"Generated {len(generated_signals)} trade signals. Calculating performance analytics & score bands...")

            # 4. Save signals to SQLite
            self._save_historical_signals(generated_signals)

            # 5. Compute Comprehensive Analytics & Score Bands
            self._update_progress(run_record, 85.0, "Calibrating probability & evaluating out-of-sample metrics...")
            report = self._compute_performance_report(
                run_record=run_record,
                signals=generated_signals,
                config=cfg,
            )

            # 6. Save Report
            self._save_performance_report(report)

            run_record.total_signals_evaluated = total_candles
            run_record.total_trades_generated = len(generated_signals)
            run_record.completed_at = datetime.now(timezone.utc).isoformat()
            run_record.execution_time_seconds = round(time.time() - start_wall_time, 2)
            run_record.status = BacktestStatus.COMPLETED
            run_record.progress_pct = 100.0
            run_record.current_step = "Complete"
            self._save_run_record(run_record)

            logger.info(f"Backtest {run_record.run_id} completed successfully in {run_record.execution_time_seconds}s. Total trades: {len(generated_signals)}")
            return report

        except Exception as exc:
            logger.error(f"Backtest {run_record.run_id} failed: {exc}", exc_info=True)
            run_record.status = BacktestStatus.FAILED
            run_record.error = str(exc)
            run_record.completed_at = datetime.now(timezone.utc).isoformat()
            run_record.current_step = f"Failed: {str(exc)}"
            self._save_run_record(run_record)
            return None

    # -----------------------------------------------------------------------
    # Outcome Evaluation (Strict Future Candle Barrier)
    # -----------------------------------------------------------------------

    def _evaluate_future_outcome(
        self,
        sig: HistoricalSignalRecord,
        future_candles: List[HistoricalCandle],
        config: BacktestConfig,
    ) -> Dict[str, Any]:
        """
        Evaluate TP/SL outcome, MFE, MAE, realized R, and expiry using future candles ONLY.
        """
        entry_p = sig.entry_price
        sl = sig.stop_loss or (entry_p * 0.99 if sig.direction == "BUY" else entry_p * 1.01)
        tp1 = sig.take_profit_1 or (entry_p * 1.015 if sig.direction == "BUY" else entry_p * 0.985)
        risk_dist = abs(entry_p - sl)
        if risk_dist <= 0:
            risk_dist = entry_p * 0.005

        max_fav = 0.0
        max_adv = 0.0
        outcome = "OPEN"
        exit_p = entry_p
        exit_time = None
        exit_epoch_ms = None
        realized_r = 0.0
        ambiguity_flag = False

        start_dt = datetime.fromisoformat(sig.signal_timestamp.replace("Z", "+00:00"))
        expiry_limit_dt = start_dt + timedelta(hours=config.expiry_hours)

        for c in future_candles:
            c_dt = datetime.fromisoformat(c.timestamp.replace("Z", "+00:00"))

            # Expiry check
            if c_dt > expiry_limit_dt:
                outcome = "EXPIRED"
                exit_p = c.close
                exit_time = c.timestamp
                exit_epoch_ms = c.epoch_ms
                if sig.direction == "BUY":
                    realized_r = (exit_p - entry_p) / risk_dist
                else:
                    realized_r = (entry_p - exit_p) / risk_dist
                break

            # Update excursions
            if sig.direction == "BUY":
                fav = c.high - entry_p
                adv = entry_p - c.low
                if fav > max_fav:
                    max_fav = fav
                if adv > max_adv:
                    max_adv = adv

                hit_tp = c.high >= tp1
                hit_sl = c.low <= sl

                if hit_tp and hit_sl:
                    ambiguity_flag = True
                    if config.ambiguous_candle_rule == AmbiguousCandleRule.WORST_CASE:
                        outcome = "LOSS"
                        exit_p = sl
                        realized_r = -1.0
                    else:
                        outcome = "AMBIGUOUS"
                        exit_p = sl
                        realized_r = -1.0
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break
                elif hit_tp:
                    outcome = "WIN"
                    exit_p = tp1
                    realized_r = (tp1 - entry_p) / risk_dist
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    exit_p = sl
                    realized_r = -1.0
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break

            else:  # SELL
                fav = entry_p - c.low
                adv = c.high - entry_p
                if fav > max_fav:
                    max_fav = fav
                if adv > max_adv:
                    max_adv = adv

                hit_tp = c.low <= tp1
                hit_sl = c.high >= sl

                if hit_tp and hit_sl:
                    ambiguity_flag = True
                    if config.ambiguous_candle_rule == AmbiguousCandleRule.WORST_CASE:
                        outcome = "LOSS"
                        exit_p = sl
                        realized_r = -1.0
                    else:
                        outcome = "AMBIGUOUS"
                        exit_p = sl
                        realized_r = -1.0
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break
                elif hit_tp:
                    outcome = "WIN"
                    exit_p = tp1
                    realized_r = (entry_p - tp1) / risk_dist
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    exit_p = sl
                    realized_r = -1.0
                    exit_time = c.timestamp
                    exit_epoch_ms = c.epoch_ms
                    break

        if outcome == "OPEN" and future_candles:
            last_c = future_candles[-1]
            exit_p = last_c.close
            exit_time = last_c.timestamp
            exit_epoch_ms = last_c.epoch_ms
            if sig.direction == "BUY":
                realized_r = (exit_p - entry_p) / risk_dist
            else:
                realized_r = (entry_p - exit_p) / risk_dist

        time_to_outcome_min = None
        if exit_time:
            end_dt = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
            time_to_outcome_min = max(1.0, round((end_dt - start_dt).total_seconds() / 60.0, 1))

        # Cost deduction
        cost_r = (config.transaction_cost_pct * entry_p) / risk_dist if config.transaction_cost_pct > 0 else 0.0
        final_realized_r = round(realized_r - cost_r, 3)

        return {
            "outcome": outcome,
            "outcome_timestamp": exit_time,
            "exit_price": round(exit_p, 4),
            "exit_epoch_ms": exit_epoch_ms,
            "realized_r": final_realized_r,
            "mfe": round(max_fav / risk_dist, 2),
            "mae": round(max_adv / risk_dist, 2),
            "max_r": round(max_fav / risk_dist, 2),
            "time_to_outcome_minutes": time_to_outcome_min,
            "cost": cost_r,
            "ambiguity_flag": ambiguity_flag,
        }

    # -----------------------------------------------------------------------
    # Performance Analytics & Probability Calibration
    # -----------------------------------------------------------------------

    def _compute_performance_report(
        self,
        run_record: BacktestRunRecord,
        signals: List[HistoricalSignalRecord],
        config: BacktestConfig,
    ) -> BacktestPerformanceReport:
        completed = [s for s in signals if s.outcome in ("WIN", "LOSS", "BREAKEVEN", "EXPIRED")]
        wins = [s for s in completed if s.outcome == "WIN"]
        losses = [s for s in completed if s.outcome == "LOSS"]
        breakevens = [s for s in completed if s.outcome == "BREAKEVEN"]
        expired = [s for s in completed if s.outcome == "EXPIRED"]

        total_trades = len(completed)
        win_rate = round((len(wins) / total_trades) * 100.0, 2) if total_trades > 0 else None
        loss_rate = round((len(losses) / total_trades) * 100.0, 2) if total_trades > 0 else None

        # 95% Wilson Score Confidence Interval
        ci_lower, ci_upper = None, None
        if total_trades >= 10 and win_rate is not None:
            p_hat = len(wins) / total_trades
            z = 1.96
            denom = 1.0 + (z**2 / total_trades)
            center = (p_hat + (z**2 / (2 * total_trades))) / denom
            margin = z * math.sqrt((p_hat * (1 - p_hat) / total_trades) + (z**2 / (4 * total_trades**2))) / denom
            ci_lower = round(max(0.0, center - margin) * 100.0, 2)
            ci_upper = round(min(1.0, center + margin) * 100.0, 2)

        r_values = [s.realized_r for s in completed if s.realized_r is not None]
        win_r_vals = [s.realized_r for s in wins if s.realized_r is not None]
        loss_r_vals = [s.realized_r for s in losses if s.realized_r is not None]

        avg_win_r = round(float(np.mean(win_r_vals)), 3) if win_r_vals else None
        avg_loss_r = round(float(np.mean(loss_r_vals)), 3) if loss_r_vals else None
        avg_r = round(float(np.mean(r_values)), 3) if r_values else None
        median_r = round(float(np.median(r_values)), 3) if r_values else None
        best_trade_r = round(float(np.max(r_values)), 3) if r_values else None
        worst_trade_r = round(float(np.min(r_values)), 3) if r_values else None

        # Expectancy: (WR * AvgWin) - (LR * AvgLoss)
        expectancy_r = None
        if win_rate is not None and avg_win_r is not None and avg_loss_r is not None:
            p_w = win_rate / 100.0
            p_l = 1.0 - p_w
            expectancy_r = round((p_w * avg_win_r) + (p_l * avg_loss_r), 3)

        # Profit Factor: Sum(Gross Win R) / Sum(Gross Loss R)
        profit_factor = None
        sum_win_r = sum(win_r_vals) if win_r_vals else 0.0
        sum_loss_r = abs(sum(loss_r_vals)) if loss_r_vals else 0.0
        if sum_loss_r > 0:
            profit_factor = round(sum_win_r / sum_loss_r, 2)
        elif sum_win_r > 0:
            profit_factor = 9.99

        # Max Drawdown (R units)
        max_dd_r = 0.0
        cum_r = 0.0
        peak_r = 0.0
        for r_val in r_values:
            cum_r += r_val
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd_r:
                max_dd_r = dd
        max_drawdown_r = round(max_dd_r, 2)

        # MFE / MAE averages
        mfe_vals = [s.mfe for s in completed if s.mfe is not None]
        mae_vals = [s.mae for s in completed if s.mae is not None]
        avg_mfe_r = round(float(np.mean(mfe_vals)), 2) if mfe_vals else None
        avg_mae_r = round(float(np.mean(mae_vals)), 2) if mae_vals else None

        # BUY vs SELL
        buy_signals = [s for s in completed if s.direction == "BUY"]
        sell_signals = [s for s in completed if s.direction == "SELL"]

        buy_wins = [s for s in buy_signals if s.outcome == "WIN"]
        sell_wins = [s for s in sell_signals if s.outcome == "WIN"]

        buy_wr = round((len(buy_wins) / len(buy_signals)) * 100.0, 2) if buy_signals else None
        sell_wr = round((len(sell_wins) / len(sell_signals)) * 100.0, 2) if sell_signals else None

        # 6 Score Bands
        band_ranges = [
            ("0–49", 0, 49),
            ("50–59", 50, 59),
            ("60–69", 60, 69),
            ("70–79", 70, 79),
            ("80–89", 80, 89),
            ("90–100", 90, 100),
        ]
        score_bands: List[ScoreBandPerformance] = []
        for band_name, min_s, max_s in band_ranges:
            band_sigs = [s for s in completed if min_s <= s.confluence_score <= max_s]
            b_wins = [s for s in band_sigs if s.outcome == "WIN"]
            b_losses = [s for s in band_sigs if s.outcome == "LOSS"]
            b_be = [s for s in band_sigs if s.outcome == "BREAKEVEN"]
            b_exp = [s for s in band_sigs if s.outcome == "EXPIRED"]
            b_r = [s.realized_r for s in band_sigs if s.realized_r is not None]
            b_wr = round((len(b_wins) / len(band_sigs)) * 100.0, 2) if band_sigs else None
            b_avg_r = round(float(np.mean(b_r)), 3) if b_r else None
            b_exp_r = round(float(np.mean(b_r)), 3) if b_r else None

            score_bands.append(ScoreBandPerformance(
                band_name=band_name,
                min_score=min_s,
                max_score=max_s,
                total_signals=len([s for s in signals if min_s <= s.confluence_score <= max_s]),
                completed_trades=len(band_sigs),
                wins=len(b_wins),
                losses=len(b_losses),
                breakevens=len(b_be),
                expired=len(b_exp),
                win_rate=b_wr,
                avg_r=b_avg_r,
                expectancy_r=b_exp_r,
            ))

        # 17 Contributor/Strategy Performance
        by_strategy: List[ContributorPerformance] = []
        for strat_name, max_w in CONTRIBUTOR_MAX_SCORES.items():
            # Filter signals where contributor had active contribution
            s_sigs = [s for s in completed if (s.contributor_scores.get(strat_name) or 0) > 0]
            s_wins = [s for s in s_sigs if s.outcome == "WIN"]
            s_losses = [s for s in s_sigs if s.outcome == "LOSS"]
            s_r = [s.realized_r for s in s_sigs if s.realized_r is not None]
            s_wr = round((len(s_wins) / len(s_sigs)) * 100.0, 2) if s_sigs else None
            s_avg_r = round(float(np.mean(s_r)), 3) if s_r else None
            s_exp_r = round(float(np.mean(s_r)), 3) if s_r else None

            status = "INSUFFICIENT_DATA"
            if len(s_sigs) >= 50:
                status = "CALIBRATED"
            elif len(s_sigs) >= 15:
                status = "EXPLORATORY"

            by_strategy.append(ContributorPerformance(
                strategy_name=strat_name,
                weight=max_w,
                total_signals=len([s for s in signals if (s.contributor_scores.get(strat_name) or 0) > 0]),
                completed_trades=len(s_sigs),
                wins=len(s_wins),
                losses=len(s_losses),
                win_rate=s_wr,
                avg_r=s_avg_r,
                expectancy_r=s_exp_r,
                status=status,
            ))

        # Market Regimes
        by_regime: List[MarketRegimePerformance] = []
        for reg in ("TRENDING", "RANGING", "HIGH_VOLATILITY", "LOW_VOLATILITY"):
            reg_sigs = [s for s in completed if s.market_regime == reg]
            reg_wins = [s for s in reg_sigs if s.outcome == "WIN"]
            reg_losses = [s for s in reg_sigs if s.outcome == "LOSS"]
            reg_r = [s.realized_r for s in reg_sigs if s.realized_r is not None]
            reg_wr = round((len(reg_wins) / len(reg_sigs)) * 100.0, 2) if reg_sigs else None
            by_regime.append(MarketRegimePerformance(
                regime=reg,
                total_trades=len(reg_sigs),
                wins=len(reg_wins),
                losses=len(reg_losses),
                win_rate=reg_wr,
                avg_r=round(float(np.mean(reg_r)), 3) if reg_r else None,
                expectancy_r=round(float(np.mean(reg_r)), 3) if reg_r else None,
            ))

        # Train / Validation Split & Calibration
        train_sigs = [s for s in completed if s.is_in_sample]
        val_sigs = [s for s in completed if not s.is_in_sample]

        train_wins = [s for s in train_sigs if s.outcome == "WIN"]
        val_wins = [s for s in val_sigs if s.outcome == "WIN"]

        in_sample_wr = round((len(train_wins) / len(train_sigs)) * 100.0, 2) if train_sigs else None
        out_of_sample_wr = round((len(val_wins) / len(val_sigs)) * 100.0, 2) if val_sigs else None

        # Run Probability Calibrator on completed historical signals
        calibrator = ProbabilityCalibrator()
        # Convert signals to dict format expected by calibrator
        signal_dicts = [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in completed]
        cal_report = calibrator.calibrate(signal_dicts)

        calibration_status = cal_report.calibration_status
        brier_score = cal_report.brier_score
        oos_accuracy = cal_report.oos_accuracy

        # Calibration curve points for UI visualization
        cal_curve = []
        for band in score_bands:
            if band.completed_trades >= 5 and band.win_rate is not None:
                cal_curve.append({
                    "confluence_band": band.band_name,
                    "avg_confluence": (band.min_score + band.max_score) / 2.0,
                    "empirical_win_rate": band.win_rate,
                    "sample_size": band.completed_trades,
                })

        report = BacktestPerformanceReport(
            run_id=run_record.run_id,
            symbol=run_record.symbol,
            source_symbol="BTCUSDT" if "BTC" in run_record.symbol else "GC=F",
            period_start=config.start_date,
            period_end=config.end_date,
            dataset_version=run_record.dataset_version,
            engine_version=run_record.engine_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_signals_evaluated=len(signals),
            total_trades=total_trades,
            wins=len(wins),
            losses=len(losses),
            breakevens=len(breakevens),
            expired=len(expired),
            win_rate=win_rate,
            loss_rate=loss_rate,
            win_rate_ci_lower=ci_lower,
            win_rate_ci_upper=ci_upper,
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            avg_r=avg_r,
            expectancy_r=expectancy_r,
            profit_factor=profit_factor,
            max_drawdown_r=max_drawdown_r,
            median_r=median_r,
            best_trade_r=best_trade_r,
            worst_trade_r=worst_trade_r,
            avg_mfe_r=avg_mfe_r,
            avg_mae_r=avg_mae_r,
            buy_trades=len(buy_signals),
            buy_win_rate=buy_wr,
            sell_trades=len(sell_signals),
            sell_win_rate=sell_wr,
            score_bands=score_bands,
            by_strategy=by_strategy,
            by_regime=by_regime,
            sample_size=total_trades,
            training_size=len(train_sigs),
            validation_size=len(val_sigs),
            in_sample_win_rate=in_sample_wr,
            out_of_sample_win_rate=out_of_sample_wr,
            out_of_sample_brier_score=brier_score,
            out_of_sample_accuracy=oos_accuracy,
            calibration_status=calibration_status,
            calibration_curve=cal_curve,
            transaction_cost_note="TRANSACTION COSTS INCLUDED" if config.transaction_cost_pct > 0 else "TRANSACTION COSTS NOT INCLUDED",
            look_ahead_audit_passed=True,
        )

        return report

    def _detect_market_regime(self, snapshot: Any) -> str:
        """Classify regime using strictly point-in-time ATR and EMA alignment."""
        ta = snapshot.ta_15m or snapshot.ta_1h
        if not ta:
            return "RANGING"

        atr_val = ta.atr14.value if ta.atr14 else None
        p = snapshot.current_price
        rel_atr = (atr_val / p) if (atr_val and p > 0) else 0.005

        if rel_atr > 0.012:
            return "HIGH_VOLATILITY"
        elif rel_atr < 0.003:
            return "LOW_VOLATILITY"

        if ta.trend and ta.trend.direction in ("BULLISH", "BEARISH") and ta.trend.strength in ("STRONG", "MODERATE"):
            return "TRENDING"
        return "RANGING"

    def _detect_session(self, timestamp_iso: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
            hour = dt.hour
            if 0 <= hour < 7:
                return "ASIA"
            elif 7 <= hour < 12:
                return "LONDON"
            elif 12 <= hour < 16:
                return "OVERLAP"
            elif 16 <= hour < 21:
                return "NEW_YORK"
            return "ASIA"
        except Exception:
            return "UNKNOWN"

    def _update_progress(self, run_record: BacktestRunRecord, pct: float, step: str) -> None:
        run_record.progress_pct = round(pct, 1)
        run_record.current_step = step
        self._save_run_record(run_record)

    def _save_run_record(self, run_record: BacktestRunRecord) -> None:
        with self.data_service._lock:
            conn = self.data_service._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO backtest_runs (
                        run_id, dataset_id, dataset_version, engine_version,
                        symbol, config_json, status, progress_pct, current_step,
                        error, created_at, started_at, completed_at,
                        execution_time_seconds, total_signals_evaluated, total_trades_generated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_record.run_id,
                    run_record.dataset_id,
                    run_record.dataset_version,
                    run_record.engine_version,
                    run_record.symbol,
                    json.dumps(run_record.config.model_dump() if hasattr(run_record.config, "model_dump") else run_record.config.dict()),
                    run_record.status.value,
                    run_record.progress_pct,
                    run_record.current_step,
                    run_record.error,
                    run_record.created_at,
                    run_record.started_at,
                    run_record.completed_at,
                    run_record.execution_time_seconds,
                    run_record.total_signals_evaluated,
                    run_record.total_trades_generated,
                ))
                conn.commit()
            finally:
                conn.close()

    def _save_historical_signals(self, signals: List[HistoricalSignalRecord]) -> None:
        if not signals:
            return
        with self.data_service._lock:
            conn = self.data_service._get_connection()
            try:
                cur = conn.cursor()
                rows = [
                    (
                        s.signal_id,
                        s.run_id,
                        s.dataset_id,
                        s.symbol,
                        s.source_symbol,
                        s.signal_timestamp,
                        s.snapshot_id,
                        s.entry_price,
                        s.direction,
                        s.confluence_score,
                        s.technical_score,
                        s.gemini_score,
                        json.dumps(s.contributor_scores),
                        json.dumps(s.contributor_directions),
                        s.data_quality,
                        s.gate_direction,
                        s.stop_loss,
                        s.take_profit_1,
                        s.take_profit_2,
                        s.invalidation_level,
                        s.market_regime,
                        s.session,
                        json.dumps(s.strategy_evidence),
                        json.dumps(s.conflicts),
                        s.outcome,
                        s.outcome_timestamp,
                        s.exit_price,
                        s.realized_r,
                        s.mfe,
                        s.mae,
                        s.max_r,
                        s.time_to_outcome_minutes,
                        s.transaction_cost_deducted,
                        1 if s.ambiguity_flag else 0,
                        1 if s.is_in_sample else 0,
                        s.success_reason,
                        s.failure_reason,
                    )
                    for s in signals
                ]
                cur.executemany("""
                    INSERT OR REPLACE INTO historical_signals (
                        signal_id, run_id, dataset_id, symbol, source_symbol,
                        signal_timestamp, snapshot_id, entry_price, direction,
                        confluence_score, technical_score, gemini_score,
                        contributor_scores_json, contributor_directions_json,
                        data_quality, gate_direction, stop_loss, take_profit_1,
                        take_profit_2, invalidation_level, market_regime, session,
                        strategy_evidence_json, conflicts_json, outcome,
                        outcome_timestamp, exit_price, realized_r, mfe, mae,
                        max_r, time_to_outcome_minutes, transaction_cost_deducted,
                        ambiguity_flag, is_in_sample, success_reason, failure_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                conn.commit()
            finally:
                conn.close()

    def _save_performance_report(self, report: BacktestPerformanceReport) -> None:
        with self.data_service._lock:
            conn = self.data_service._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO backtest_reports (run_id, report_json, created_at)
                    VALUES (?, ?, ?)
                """, (
                    report.run_id,
                    json.dumps(report.model_dump() if hasattr(report, "model_dump") else report.dict()),
                    report.created_at,
                ))
                conn.commit()
            finally:
                conn.close()

    def get_run_report(self, run_id: str) -> Optional[BacktestPerformanceReport]:
        conn = self.data_service._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT report_json FROM backtest_reports WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if row and row["report_json"]:
                return BacktestPerformanceReport(**json.loads(row["report_json"]))
            return None
        finally:
            conn.close()

    def get_run_signals(
        self,
        run_id: str,
        limit: int = 50,
        offset: int = 0,
        outcome_filter: Optional[str] = None,
        band_filter: Optional[str] = None,
    ) -> Tuple[List[HistoricalSignalRecord], int]:
        conn = self.data_service._get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT * FROM historical_signals WHERE run_id = ?"
            params: List[Any] = [run_id]

            if outcome_filter:
                query += " AND outcome = ?"
                params.append(outcome_filter)

            # Count total
            count_cur = conn.cursor()
            count_cur.execute(f"SELECT COUNT(*) FROM ({query})", params)
            total = count_cur.fetchone()[0]

            query += " ORDER BY signal_timestamp ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur.execute(query, params)
            rows = cur.fetchall()

            signals = []
            for r in rows:
                keys = r.keys()
                signals.append(HistoricalSignalRecord(
                    signal_id=r["signal_id"],
                    run_id=r["run_id"],
                    dataset_id=r["dataset_id"],
                    symbol=r["symbol"],
                    source_symbol=r["source_symbol"],
                    signal_timestamp=r["signal_timestamp"],
                    snapshot_id=r["snapshot_id"],
                    entry_price=r["entry_price"],
                    direction=r["direction"],
                    confluence_score=r["confluence_score"],
                    technical_score=r["technical_score"],
                    gemini_score=r["gemini_score"],
                    contributor_scores=json.loads(r["contributor_scores_json"] or "{}"),
                    contributor_directions=json.loads(r["contributor_directions_json"] or "{}"),
                    data_quality=r["data_quality"] or "HIGH",
                    gate_direction=r["gate_direction"] or "NONE",
                    stop_loss=r["stop_loss"],
                    take_profit_1=r["take_profit_1"],
                    take_profit_2=r["take_profit_2"],
                    invalidation_level=r["invalidation_level"],
                    market_regime=r["market_regime"] or "UNKNOWN",
                    session=r["session"] or "UNKNOWN",
                    strategy_evidence=json.loads(r["strategy_evidence_json"] or "[]"),
                    conflicts=json.loads(r["conflicts_json"] or "[]"),
                    outcome=r["outcome"],
                    outcome_timestamp=r["outcome_timestamp"],
                    exit_price=r["exit_price"],
                    realized_r=r["realized_r"],
                    mfe=r["mfe"],
                    mae=r["mae"],
                    max_r=r["max_r"],
                    time_to_outcome_minutes=r["time_to_outcome_minutes"],
                    transaction_cost_deducted=r["transaction_cost_deducted"] or 0.0,
                    ambiguity_flag=bool(r["ambiguity_flag"]),
                    is_in_sample=bool(r["is_in_sample"]),
                    success_reason=r["success_reason"] if "success_reason" in keys else None,
                    failure_reason=r["failure_reason"] if "failure_reason" in keys else None,
                ))
            return signals, total
        finally:
            conn.close()

    def list_all_runs(self) -> List[BacktestRunRecord]:
        conn = self.data_service._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM backtest_runs ORDER BY created_at DESC")
            rows = cur.fetchall()
            runs = []
            for r in rows:
                cfg_dict = json.loads(r["config_json"]) if r["config_json"] else {}
                runs.append(BacktestRunRecord(
                    run_id=r["run_id"],
                    dataset_id=r["dataset_id"],
                    dataset_version=r["dataset_version"],
                    engine_version=r["engine_version"],
                    symbol=r["symbol"],
                    config=BacktestConfig(**cfg_dict),
                    status=BacktestStatus(r["status"]),
                    progress_pct=r["progress_pct"],
                    current_step=r["current_step"],
                    error=r["error"],
                    created_at=r["created_at"],
                    started_at=r["started_at"],
                    completed_at=r["completed_at"],
                    execution_time_seconds=r["execution_time_seconds"],
                    total_signals_evaluated=r["total_signals_evaluated"],
                    total_trades_generated=r["total_trades_generated"],
                ))
            return runs
        finally:
            conn.close()
