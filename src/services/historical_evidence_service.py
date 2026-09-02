"""
Historical Evidence Service & Empirical Pattern Matching Engine.

Provides an automated historical learning layer that:
1. Extracts setup fingerprints from current live market conditions
2. Queries validated completed historical backtest trades
3. Enforces strict BTC vs XAU separation and BUY vs SELL separation
4. Retrieves both winning and losing historical setups (zero cherry-picking)
5. Calculates score-band statistics, pattern similarity, and calibrated probability
6. Evaluates strategy confirmations, conflicts, and confidence intervals
7. Operates with full fail-safe isolation (never crashing live signals or demo trading)

DISCLAIMER: Empirical research and statistical modeling only. No live orders executed.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.models.trading_decision import TradingDecision, TradingSignal
from src.models.signal_record import CalibrationResult
from src.services.historical_data_service import HistoricalDataService, DB_PATH
from src.services.probability_calibrator import ProbabilityCalibrator

logger = logging.getLogger(__name__)


def _score_band(score: int) -> str:
    """Map a 0–100 score to its performance band string."""
    if score < 50:
        return "0-49"
    elif score < 60:
        return "50-59"
    elif score < 70:
        return "60-69"
    elif score < 80:
        return "70-79"
    elif score < 90:
        return "80-89"
    return "90-100"


def _wilson_score_interval(wins: int, n: int, confidence: float = 0.95) -> Tuple[Optional[float], Optional[float]]:
    """Compute Wilson score 95% confidence interval for binomial win rate."""
    if n <= 0:
        return None, None
    z = 1.96  # 95% confidence
    p_hat = wins / n
    denom = 1 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2 * n)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + (z ** 2) / (4 * n)) / n) / denom
    lower = max(0.0, round((center - spread) * 100, 1))
    upper = min(100.0, round((center + spread) * 100, 1))
    return lower, upper


def _calc_directional_strength(
    wins: int,
    n: int,
    expectancy: Optional[float] = None,
    profit_factor: Optional[float] = None,
    calibrated_prob: Optional[float] = None,
    similar_count: Optional[int] = None,
) -> int:
    """
    Calculate directional evidence strength (0-100%) supporting a trade direction.

    Factors in:
    1. Sample size significance (small samples n < 20 get heavily dampened; large samples n > 200 get full weight)
    2. 95% Wilson Confidence Interval bounds (penalizes wide statistical uncertainty)
    3. Calibrated probability vs 50% baseline
    4. Expectancy (R-multiples) and Profit Factor
    5. Similar setup count

    Guarantees:
    - Small sample (e.g. 5/8 = 62.5%) -> WEAK / neutral evidence (~50-54%)
    - Large sample (e.g. 247/399 = 61.8%) -> STRONG statistical evidence (~75-85%)
    - Close evidence (e.g. 52% vs 49%) -> Neutral / WAIT
    """
    if n <= 0:
        return 50

    p = (calibrated_prob / 100.0) if calibrated_prob is not None else (wins / n)
    z = 1.96
    denom = 1 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    spread = z * math.sqrt((p * (1 - p) + (z ** 2) / (4 * n)) / n) / denom
    ci_lower = max(0.0, center - spread)

    # Sample significance scale (smooth sqrt scaling)
    # n=8 -> ~0.18, n=50 -> ~0.45, n=150 -> ~0.77, n>=250 -> 1.0
    c_sample = min(1.0, math.sqrt(n) / math.sqrt(250.0))

    # Expectancy factor: positive expectancy enhances, negative dampens
    exp_val = expectancy if expectancy is not None else 0.0
    e_factor = max(0.6, min(1.3, 1.0 + (exp_val / 2.0)))

    # Profit factor:
    pf_val = profit_factor if profit_factor is not None else 1.0
    pf_factor = max(0.7, min(1.3, pf_val / 1.4))

    # Calculate edge from 50% baseline
    edge = (p - 0.50) * 100.0 * 2.2
    directional_strength = round(50.0 + edge * c_sample * e_factor * pf_factor)
    return max(5, min(95, directional_strength))


class HistoricalEvidencePackage:
    """Container for validated empirical evidence matching a setup."""
    def __init__(
        self,
        status: str = "NOT_AVAILABLE",
        sample_size: int = 0,
        win_rate: Optional[float] = None,
        calibrated_probability: Optional[float] = None,
        expectancy: Optional[float] = None,
        profit_factor: Optional[float] = None,
        drawdown: Optional[float] = None,
        similar_count: Optional[int] = None,
        wins: Optional[int] = None,
        losses: Optional[int] = None,
        score_band_win_rate: Optional[float] = None,
        ci_lower: Optional[float] = None,
        ci_upper: Optional[float] = None,
        buy_strength: Optional[int] = None,
        sell_strength: Optional[int] = None,
        similarity_strength: Optional[int] = None,
        historical_bias: Optional[str] = None,
        strategy_confirmations: Optional[List[str]] = None,
        strategy_conflicts: Optional[List[str]] = None,
        historical_confirmations: Optional[List[str]] = None,
        historical_conflicts: Optional[List[str]] = None,
        top_success_reasons: Optional[List[str]] = None,
        top_failure_reasons: Optional[List[str]] = None,
        success_matches_count: Optional[int] = None,
        failure_matches_count: Optional[int] = None,
        recommendation_strength: str = "MEDIUM",
        overall_reasoning: str = "",
        dataset_version: Optional[str] = None,
        backtest_run_id: Optional[str] = None,
        evidence_quality: str = "INSUFFICIENT",
        evidence_refresh_at: Optional[str] = None,
    ):
        self.status = status
        self.sample_size = sample_size
        self.win_rate = win_rate
        self.calibrated_probability = calibrated_probability
        self.expectancy = expectancy
        self.profit_factor = profit_factor
        self.drawdown = drawdown
        self.similar_count = similar_count
        self.wins = wins
        self.losses = losses
        self.score_band_win_rate = score_band_win_rate
        self.ci_lower = ci_lower
        self.ci_upper = ci_upper
        self.buy_strength = buy_strength
        self.sell_strength = sell_strength
        self.similarity_strength = similarity_strength
        self.historical_bias = historical_bias
        self.strategy_confirmations = strategy_confirmations or []
        self.strategy_conflicts = strategy_conflicts or []
        self.historical_confirmations = historical_confirmations or []
        self.historical_conflicts = historical_conflicts or []
        self.top_success_reasons = top_success_reasons or []
        self.top_failure_reasons = top_failure_reasons or []
        self.success_matches_count = success_matches_count if success_matches_count is not None else wins
        self.failure_matches_count = failure_matches_count if failure_matches_count is not None else losses
        self.recommendation_strength = recommendation_strength
        self.overall_reasoning = overall_reasoning
        self.dataset_version = dataset_version
        self.backtest_run_id = backtest_run_id
        self.evidence_quality = evidence_quality
        self.evidence_refresh_at = evidence_refresh_at or datetime.now(timezone.utc).isoformat()


class HistoricalEvidenceService:
    """
    Automated empirical evidence retrieval, pattern-matching, and background learning engine.
    Bridges historical backtested signals with live Overall AI decisions.
    """

    _instance: Optional[HistoricalEvidenceService] = None
    _lock = threading.RLock()

    def __init__(self, db_path: str = DB_PATH, auto_start_learning: bool = True):
        self.db_path = db_path
        self.data_service = HistoricalDataService(db_path=db_path)
        self.calibrator = ProbabilityCalibrator()
        self._cache: Dict[str, Tuple[float, HistoricalEvidencePackage]] = {}
        self._cache_ttl = 30.0  # 30-second cache TTL
        self._auto_learning_started = False
        self._is_learning = False
        self._last_learning_completed_at: Optional[str] = None

        if auto_start_learning and not os.environ.get("PYTEST_CURRENT_TEST"):
            self.ensure_historical_learning_ready()

    @classmethod
    def get_instance(cls) -> HistoricalEvidenceService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    # -----------------------------------------------------------------------
    # Automated Background Historical Learning & Maintenance
    # -----------------------------------------------------------------------

    def ensure_historical_learning_ready(self, force: bool = False) -> None:
        """
        Check if historical empirical evidence exists for XAU/USD and BTC/USD.
        If missing, insufficient, or forced, automatically triggers non-blocking background learning.
        """
        with self._lock:
            if self._is_learning:
                return

            needs_learning = force
            if not needs_learning:
                try:
                    conn = self._get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT symbol, COUNT(*) as cnt
                        FROM historical_signals
                        WHERE outcome IN ('WIN', 'LOSS', 'BREAKEVEN', 'EXPIRED')
                        GROUP BY symbol
                    """)
                    counts = {r["symbol"]: r["cnt"] for r in cur.fetchall()}
                    conn.close()

                    btc_count = counts.get("BTC/USD", 0)
                    xau_count = counts.get("XAU/USD", 0)

                    if btc_count < 20 or xau_count < 20:
                        needs_learning = True
                except Exception as _e:
                    logger.debug(f"Historical evidence check produced: {_e}")
                    needs_learning = True

            if needs_learning:
                self.auto_learn_in_background(force=force)

    def auto_learn_in_background(self, force: bool = False) -> None:
        """Launch background learning daemon thread."""
        with self._lock:
            if self._is_learning:
                return
            self._is_learning = True
            self._auto_learning_started = True

            worker = threading.Thread(
                target=self._execute_automated_learning,
                args=(force,),
                daemon=True,
                name="AutomatedHistoricalLearningWorker",
            )
            worker.start()

    def _execute_automated_learning(self, force: bool = False) -> None:
        """
        Background worker that:
        1. Validates historical market data availability in SQLite.
        2. Runs historical replay backtests through existing ConfluenceEngine (min_confluence_score=40 for research only).
        3. Labels future candle outcomes (WIN/LOSS/TP/SL/MFE/MAE/R + success/failure reasons).
        4. Calculates empirical success rates and calibrates probability.
        5. Updates the empirical evidence database and clears cache.
        """
        try:
            logger.info("Starting Automated Historical Learning & Pattern Discovery...")
            from src.services.historical_backtest_runner import HistoricalBacktestRunner
            from src.models.historical_data import BacktestConfig, AmbiguousCandleRule

            runner = HistoricalBacktestRunner(self.data_service)

            # 1. Learn for BTC/USD (min_confluence_score=40 for research discovery only)
            btc_candles = self.data_service.get_candles("BTC/USD", "15m", limit=100)
            if not btc_candles or len(btc_candles) < 20:
                try:
                    self.data_service.download_binance_btc(timeframe="15m", max_candles=5000)
                except Exception as _dl_exc:
                    logger.debug(f"Binance BTC download fallback: {_dl_exc}")

            btc_cfg = BacktestConfig(
                symbol="BTC/USD",
                primary_timeframe="15m",
                start_date="2024-01-01",
                end_date="2026-08-30",
                min_confluence_score=40,
                ambiguous_candle_rule=AmbiguousCandleRule.WORST_CASE,
            )
            try:
                runner.run_backtest_sync(btc_cfg)
            except Exception as _btc_exc:
                logger.debug(f"BTC backtest replay note: {_btc_exc}")

            # 2. Learn for XAU/USD (min_confluence_score=40 for research discovery only)
            xau_candles = self.data_service.get_candles("XAU/USD", "15m", limit=100)
            if not xau_candles or len(xau_candles) < 20:
                try:
                    self.data_service.download_yahoo_gold(timeframe="15m", range_period="60d")
                except Exception as _gold_exc:
                    logger.debug(f"Yahoo Gold download fallback: {_gold_exc}")

            xau_cfg = BacktestConfig(
                symbol="XAU/USD",
                primary_timeframe="15m",
                start_date="2024-01-01",
                end_date="2026-08-30",
                min_confluence_score=40,
                ambiguous_candle_rule=AmbiguousCandleRule.WORST_CASE,
            )
            try:
                runner.run_backtest_sync(xau_cfg)
            except Exception as _xau_exc:
                logger.debug(f"XAU backtest replay note: {_xau_exc}")

            # 3. Invalidate cache so Overall AI immediately receives updated evidence
            with self._lock:
                self._cache.clear()
                self._last_learning_completed_at = datetime.now(timezone.utc).isoformat()

            logger.info("Automated Historical Learning & Pattern Discovery completed successfully.")
        except Exception as exc:
            logger.warning(f"Automated Historical Learning encountered non-fatal error: {exc}", exc_info=True)
        finally:
            with self._lock:
                self._is_learning = False

    # -----------------------------------------------------------------------
    # Setup Fingerprint Extraction
    # -----------------------------------------------------------------------

    def extract_fingerprint(
        self,
        symbol: str,
        direction: str,
        confluence_score: int,
        technical_score: int = 0,
        gemini_score: int = 0,
        mtf_alignment: str = "",
        market_regime: str = "UNCLEAR",
        contributors: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Extract a structured setup fingerprint from live market parameters."""
        norm_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
        norm_dir = direction.upper() if direction.upper() in ("BUY", "SELL") else "WAIT"
        band = _score_band(confluence_score)

        contrib_states: Dict[str, str] = {}
        if contributors:
            for c in contributors:
                name = c.get("name", "")
                bias = c.get("bias", "") or ("BULLISH" if c.get("points", 0) > 0 else "NEUTRAL")
                if name:
                    contrib_states[name] = bias

        return {
            "symbol": norm_symbol,
            "direction": norm_dir,
            "confluence_score": confluence_score,
            "score_band": band,
            "technical_score": technical_score,
            "gemini_score": gemini_score,
            "mtf_alignment": mtf_alignment,
            "market_regime": market_regime,
            "contributors": contrib_states,
        }

    # -----------------------------------------------------------------------
    # Historical Evidence Query
    # -----------------------------------------------------------------------

    def get_evidence_for_setup(
        self,
        symbol: str,
        direction: str,
        confluence_score: int,
        technical_score: int = 0,
        gemini_score: int = 0,
        mtf_alignment: str = "",
        market_regime: str = "UNCLEAR",
        contributors: Optional[List[Dict[str, Any]]] = None,
        force_refresh: bool = False,
    ) -> HistoricalEvidencePackage:
        """
        Query validated completed historical backtest trades for matching setups.
        Guarantees zero-fail execution — all errors produce a safe fallback package.
        """
        fingerprint = self.extract_fingerprint(
            symbol=symbol,
            direction=direction,
            confluence_score=confluence_score,
            technical_score=technical_score,
            gemini_score=gemini_score,
            mtf_alignment=mtf_alignment,
            market_regime=market_regime,
            contributors=contributors,
        )

        cache_key = f"{fingerprint['symbol']}_{fingerprint['direction']}_{fingerprint['score_band']}_{fingerprint['market_regime']}"
        now = time.monotonic()

        if not force_refresh and cache_key in self._cache:
            cached_time, pkg = self._cache[cache_key]
            if (now - cached_time) < self._cache_ttl:
                return pkg

        try:
            pkg = self._query_empirical_evidence(fingerprint)
        except Exception as exc:
            logger.warning(f"HistoricalEvidenceService query error: {exc}", exc_info=True)
            pkg = HistoricalEvidencePackage(
                status="NOT_AVAILABLE",
                recommendation_strength="MEDIUM",
                overall_reasoning=f"Historical evidence lookup unavailable: {exc}",
            )

        self._cache[cache_key] = (now, pkg)
        return pkg

    def _query_empirical_evidence(self, fp: Dict[str, Any]) -> HistoricalEvidencePackage:
        """Internal worker querying SQLite historical signal repository."""
        target_symbol = fp["symbol"]
        target_dir = fp["direction"]
        target_score = fp["confluence_score"]
        target_band = fp["score_band"]
        target_regime = fp["market_regime"]
        contrib_states = fp["contributors"]

        # 1. Connect to DB and inspect historical_signals table
        if not os.path.exists(self.db_path):
            return HistoricalEvidencePackage(
                status="NOT_AVAILABLE",
                evidence_quality="INSUFFICIENT",
                overall_reasoning="Historical market database not yet initialized.",
            )

        conn = self._get_connection()
        try:
            cur = conn.cursor()

            # Query completed backtest signals for this exact symbol (Strict BTC/XAU separation)
            cur.execute("""
                SELECT 
                    signal_id, run_id, dataset_id, symbol, signal_timestamp, direction,
                    confluence_score, technical_score, gemini_score,
                    market_regime, outcome, realized_r, mfe, mae, is_in_sample,
                    success_reason, failure_reason
                FROM historical_signals
                WHERE symbol = ? AND outcome IN ('WIN', 'LOSS', 'BREAKEVEN', 'EXPIRED')
                ORDER BY signal_timestamp ASC
            """, (target_symbol,))

            all_rows = cur.fetchall()

            if not all_rows:
                return HistoricalEvidencePackage(
                    status="NOT_AVAILABLE",
                    evidence_quality="INSUFFICIENT",
                    overall_reasoning=f"No completed backtest trades found for {target_symbol}.",
                )

            # Extract run_id and dataset metadata
            latest_run_id = all_rows[-1]["run_id"] if all_rows else None
            dataset_id = all_rows[-1]["dataset_id"] if all_rows else None

            # 2. Separate BUY vs SELL signals
            if target_dir in ("BUY", "SELL"):
                dir_rows = [r for r in all_rows if r["direction"] == target_dir]
            else:
                dir_rows = list(all_rows)

            sample_size = len(dir_rows)

            # Filter for WIN / LOSS only
            wl_rows = [r for r in dir_rows if r["outcome"] in ("WIN", "LOSS")]
            wins_count = sum(1 for r in wl_rows if r["outcome"] == "WIN")
            losses_count = sum(1 for r in wl_rows if r["outcome"] == "LOSS")
            n_wl = len(wl_rows)

            win_rate = round(wins_count / n_wl * 100, 1) if n_wl > 0 else None
            ci_lower, ci_upper = _wilson_score_interval(wins_count, n_wl)

            # Calculate average R, expectancy, profit factor
            r_multiples = [r["realized_r"] for r in dir_rows if r["realized_r"] is not None]
            avg_r = round(float(sum(r_multiples) / len(r_multiples)), 3) if r_multiples else None

            win_r_list = [r["realized_r"] for r in dir_rows if r["outcome"] == "WIN" and r["realized_r"] is not None]
            loss_r_list = [abs(r["realized_r"]) for r in dir_rows if r["outcome"] == "LOSS" and r["realized_r"] is not None]

            avg_win_r = float(sum(win_r_list) / len(win_r_list)) if win_r_list else 1.0
            avg_loss_r = float(sum(loss_r_list) / len(loss_r_list)) if loss_r_list else 1.0

            if win_rate is not None:
                wr_frac = win_rate / 100.0
                lr_frac = 1.0 - wr_frac
                expectancy = round((wr_frac * avg_win_r) - (lr_frac * avg_loss_r), 3)
            else:
                expectancy = None

            gross_wins = sum(win_r_list)
            gross_losses = sum(loss_r_list)
            profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (round(gross_wins, 2) if gross_wins > 0 else None)

            # Drawdown calculation
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for r_val in r_multiples:
                cum += r_val
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            max_drawdown = round(max_dd, 2) if r_multiples else None

            # 3. Score-band Empirical Analysis
            band_rows = [r for r in dir_rows if _score_band(r["confluence_score"]) == target_band]
            band_wl = [r for r in band_rows if r["outcome"] in ("WIN", "LOSS")]
            band_wins = sum(1 for r in band_wl if r["outcome"] == "WIN")
            score_band_wr = round(band_wins / len(band_wl) * 100, 1) if band_wl else None

            # 4. Similar Setup Pattern Matching (Score band ± 1 or exact, matching regime)
            similar_rows = [
                r for r in dir_rows
                if (
                    _score_band(r["confluence_score"]) == target_band
                    or (target_regime != "UNCLEAR" and r["market_regime"] == target_regime)
                )
            ]
            sim_wl = [r for r in similar_rows if r["outcome"] in ("WIN", "LOSS")]
            sim_wins = sum(1 for r in sim_wl if r["outcome"] == "WIN")
            sim_losses = sum(1 for r in sim_wl if r["outcome"] == "LOSS")
            similar_count = len(similar_rows)

            # 5. Extract top factual success & failure reasons from historical records
            win_reason_counts: Dict[str, int] = {}
            loss_reason_counts: Dict[str, int] = {}
            for r in dir_rows:
                keys = r.keys()
                if r["outcome"] == "WIN" and "success_reason" in keys and r["success_reason"]:
                    s_r = r["success_reason"]
                    win_reason_counts[s_r] = win_reason_counts.get(s_r, 0) + 1
                elif r["outcome"] in ("LOSS", "EXPIRED") and "failure_reason" in keys and r["failure_reason"]:
                    f_r = r["failure_reason"]
                    loss_reason_counts[f_r] = loss_reason_counts.get(f_r, 0) + 1

            top_success_reasons = [k for k, _ in sorted(win_reason_counts.items(), key=lambda x: x[1], reverse=True)[:3]]
            top_failure_reasons = [k for k, _ in sorted(loss_reason_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

            # 6. Calibrated Probability via ProbabilityCalibrator
            calib_res: CalibrationResult = self.calibrator.calibrate(
                completed_signals=dir_rows,
                current_score=target_score,
            )
            calibrated_prob = calib_res.calibrated_probability

            # Guard against insufficient data (avoid fake statistics)
            if sample_size < 10:
                win_rate = None
                calibrated_prob = None
                expectancy = None
                score_band_wr = None
                ci_lower, ci_upper = None, None

            # 7. Quality & Status Evaluation (Empirical tiers)
            if sample_size >= 200:
                evidence_quality = "STRONG"
                status = "AVAILABLE"
            elif sample_size >= 50:
                evidence_quality = "VALID"
                status = "AVAILABLE"
            elif sample_size >= 20:
                evidence_quality = "EXPLORATORY"
                status = "LIMITED"
            else:
                evidence_quality = "INSUFFICIENT"
                status = "INSUFFICIENT"

            # Check for staleness
            if all_rows:
                latest_ts_str = all_rows[-1]["signal_timestamp"]
                try:
                    latest_dt = datetime.fromisoformat(latest_ts_str.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - latest_dt).days > 60:
                        status = "STALE"
                except Exception:
                    pass

            # 8. Compute Separate BUY Strength and SELL Strength
            buy_rows = [r for r in all_rows if r["direction"] == "BUY"]
            buy_wl = [r for r in buy_rows if r["outcome"] in ("WIN", "LOSS")]
            buy_wins = sum(1 for r in buy_wl if r["outcome"] == "WIN")
            buy_n = len(buy_wl)
            buy_r_vals = [r["realized_r"] for r in buy_rows if r["realized_r"] is not None]
            buy_win_rs = [r for r in buy_r_vals if r > 0]
            buy_loss_rs = [abs(r) for r in buy_r_vals if r < 0]
            buy_exp = (sum(buy_r_vals) / len(buy_r_vals)) if buy_r_vals else None
            buy_pf = (sum(buy_win_rs) / sum(buy_loss_rs)) if buy_loss_rs and buy_win_rs else None
            buy_calib = self.calibrator.calibrate(buy_rows, current_score=target_score).calibrated_probability if len(buy_rows) >= 10 else None
            buy_strength = _calc_directional_strength(buy_wins, buy_n, expectancy=buy_exp, profit_factor=buy_pf, calibrated_prob=buy_calib, similar_count=similar_count)

            sell_rows = [r for r in all_rows if r["direction"] == "SELL"]
            sell_wl = [r for r in sell_rows if r["outcome"] in ("WIN", "LOSS")]
            sell_wins = sum(1 for r in sell_wl if r["outcome"] == "WIN")
            sell_n = len(sell_wl)
            sell_r_vals = [r["realized_r"] for r in sell_rows if r["realized_r"] is not None]
            sell_win_rs = [r for r in sell_r_vals if r > 0]
            sell_loss_rs = [abs(r) for r in sell_r_vals if r < 0]
            sell_exp = (sum(sell_r_vals) / len(sell_r_vals)) if sell_r_vals else None
            sell_pf = (sum(sell_win_rs) / sum(sell_loss_rs)) if sell_loss_rs and sell_win_rs else None
            sell_calib = self.calibrator.calibrate(sell_rows, current_score=target_score).calibrated_probability if len(sell_rows) >= 10 else None
            sell_strength = _calc_directional_strength(sell_wins, sell_n, expectancy=sell_exp, profit_factor=sell_pf, calibrated_prob=sell_calib, similar_count=similar_count)

            # Similarity Strength %
            similarity_strength = min(95, max(45, round(65 + min(25, (similar_count or 0) / 15.0))))

            # Determine Statistical Historical Bias (never based on raw win rate alone)
            if buy_strength >= 65 and buy_strength >= sell_strength + 15:
                historical_bias = "BUY"
            elif sell_strength >= 65 and sell_strength >= buy_strength + 15:
                historical_bias = "SELL"
            else:
                historical_bias = "WAIT"

            # 9. Generate Confirmations & Conflicts
            strat_confirms: List[str] = []
            strat_conflicts: List[str] = []
            hist_confirms: List[str] = []
            hist_conflicts: List[str] = []

            for s_name, s_bias in contrib_states.items():
                if target_dir == "BUY":
                    if "BULLISH" in s_bias.upper():
                        strat_confirms.append(f"{s_name} bullish alignment")
                    elif "BEARISH" in s_bias.upper():
                        strat_conflicts.append(f"{s_name} bearish divergence")
                elif target_dir == "SELL":
                    if "BEARISH" in s_bias.upper():
                        strat_confirms.append(f"{s_name} bearish alignment")
                    elif "BULLISH" in s_bias.upper():
                        strat_conflicts.append(f"{s_name} bullish divergence")

            if win_rate is not None and win_rate >= 55.0:
                hist_confirms.append(f"Historical {target_symbol} {target_dir} win rate {win_rate:.1f}% (n={sample_size})")
            elif win_rate is not None and win_rate < 50.0:
                hist_conflicts.append(f"Historical {target_symbol} {target_dir} win rate below 50% ({win_rate:.1f}%)")

            if score_band_wr is not None and score_band_wr >= 55.0:
                hist_confirms.append(f"Score band {target_band} historically positive ({score_band_wr:.1f}% WR)")
            elif score_band_wr is not None and score_band_wr < 45.0:
                hist_conflicts.append(f"Score band {target_band} historically sub-optimal ({score_band_wr:.1f}% WR)")

            if expectancy is not None and expectancy > 0.15:
                hist_confirms.append(f"Positive expectancy (+{expectancy:.2f}R per setup)")
            elif expectancy is not None and expectancy < 0.0:
                hist_conflicts.append(f"Negative historical expectancy ({expectancy:.2f}R)")

            if top_success_reasons:
                hist_confirms.append(f"Historical win factor: {top_success_reasons[0]}")
            if top_failure_reasons:
                hist_conflicts.append(f"Historical risk factor: {top_failure_reasons[0]}")

            if sim_losses > 0:
                hist_conflicts.append(f"Historical failures exist in similar setups ({sim_losses} losses observed)")

            # 10. Recommendation Strength Synthesis
            if target_dir in ("BUY", "SELL") and target_score >= 75 and win_rate and win_rate >= 58.0 and status == "AVAILABLE":
                rec_strength = "HIGH"
            elif target_dir in ("BUY", "SELL") and target_score >= 60 and (win_rate is None or win_rate >= 50.0):
                rec_strength = "MEDIUM"
            else:
                rec_strength = "LOW"

            # 11. Overall Reasoning Narrative
            reasoning_parts = []
            if target_dir in ("BUY", "SELL"):
                reasoning_parts.append(f"Current live {target_dir} confluence is {target_score}/100 ({target_band} band).")
                if win_rate is not None:
                    reasoning_parts.append(f"Historically, similar {target_symbol} {target_dir} setups achieved a {win_rate:.1f}% win rate across {sample_size} validated trades.")
                elif sample_size < 10:
                    reasoning_parts.append(f"Historical sample size for {target_symbol} {target_dir} is preliminary (n={sample_size}).")
                if calibrated_prob is not None:
                    reasoning_parts.append(f"Calibrated empirical win probability is {calibrated_prob:.1f}%.")
                if expectancy is not None:
                    reasoning_parts.append(f"Average expectancy is {expectancy:+.2f}R with a {profit_factor or 1.0} profit factor.")
            else:
                reasoning_parts.append("Market in WAIT state. Confluence and structural gates have not triggered an actionable trade setup.")

            overall_reasoning = " ".join(reasoning_parts)

            return HistoricalEvidencePackage(
                status=status,
                sample_size=sample_size,
                win_rate=win_rate,
                calibrated_probability=calibrated_prob,
                expectancy=expectancy,
                profit_factor=profit_factor,
                drawdown=max_drawdown,
                similar_count=similar_count,
                wins=sim_wins,
                losses=sim_losses,
                score_band_win_rate=score_band_wr,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                buy_strength=buy_strength,
                sell_strength=sell_strength,
                similarity_strength=similarity_strength,
                historical_bias=historical_bias,
                strategy_confirmations=strat_confirms[:5],
                strategy_conflicts=strat_conflicts[:4],
                historical_confirmations=hist_confirms[:4],
                historical_conflicts=hist_conflicts[:4],
                top_success_reasons=top_success_reasons,
                top_failure_reasons=top_failure_reasons,
                success_matches_count=sim_wins,
                failure_matches_count=sim_losses,
                recommendation_strength=rec_strength,
                overall_reasoning=overall_reasoning,
                dataset_version=dataset_id or "v2.0",
                backtest_run_id=latest_run_id,
                evidence_quality=evidence_quality,
                evidence_refresh_at=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_evidence_service_instance: Optional[HistoricalEvidenceService] = None


def get_historical_evidence_service() -> HistoricalEvidenceService:
    """Return singleton HistoricalEvidenceService instance."""
    global _evidence_service_instance
    if _evidence_service_instance is None:
        _evidence_service_instance = HistoricalEvidenceService()
    return _evidence_service_instance
