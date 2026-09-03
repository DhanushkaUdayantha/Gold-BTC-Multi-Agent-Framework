"""
High-level orchestration service for the Trading Decision Engine.

Coordinates:
  1. Multi-timeframe technical analysis (TechnicalAnalysisService)
  2. AI market analysis (AIMarketAnalysisService) — called with current signal state
     so the MeaningfulChangeDetector can gate unnecessary Gemini calls.
  3. Deterministic decision scoring (DecisionEngine)

Concurrency:
  A threading.Lock prevents multiple simultaneous decision builds.
  If a build is already running, the waiting thread receives the same
  cached result once the build completes.

DISCLAIMER: All outputs are advisory analytical signals only.
No trades are executed. No broker connections are made.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict

from config.settings import get_settings
from src.models.trading_decision import (
    TradingDecision,
    DecisionScoreBreakdown,
    TradingSignal,
    DecisionTrend,
    DecisionRiskLevel,
    HistoricalMarketSignal,
    NowMarketSignal,
    OverallTradingSignal,
    HourlyStrongSignal,
)
from src.services.decision_engine import DecisionEngine
from src.services.ai_service import get_ai_service
from src.services.technical_service import TechnicalAnalysisService, get_technical_service
from src.models.market_data import Timeframe
from src.models.ai_analysis import MultiTimeframeTechnicalInput, AIAnalysisResponse
from src.services.signal_repository import get_signal_repository
from src.services.outcome_tracker import get_outcome_tracker

logger = logging.getLogger(__name__)

_TIMEFRAMES = ["5m", "15m", "1h", "1d"]


class DecisionService:
    """Orchestrates the full BUY/SELL/WAIT decision pipeline."""

    def __init__(self):
        settings = get_settings()
        self._ttl = settings.DECISION_CACHE_TTL_SECONDS
        self._cache: Dict[str, Tuple[float, Tuple[TradingDecision, DecisionScoreBreakdown]]] = {}
        self._engine = DecisionEngine()
        self._ai_service = get_ai_service()
        self._tech_service: TechnicalAnalysisService = get_technical_service()
        self._hourly_strong_signals: Dict[str, HourlyStrongSignal] = {}
        # Concurrency lock: prevents duplicate decision builds when the cache expires
        self._build_lock = threading.Lock()

        # Automated background historical learning trigger (additive, non-blocking)
        try:
            from src.services.historical_evidence_service import get_historical_evidence_service
            get_historical_evidence_service().ensure_historical_learning_ready()
        except Exception as _ev_init_exc:
            logger.debug(f"Historical learning startup hook skipped: {_ev_init_exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_decision(
        self, symbol: Optional[str] = None, force_refresh: bool = False
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        """
        Return the latest trading decision and score breakdown for the requested symbol.
        Results are cached for DECISION_CACHE_TTL_SECONDS.

        Thread-safety: only one build runs at a time; concurrent callers
        receive the newly computed result once the lock is released.
        """
        sym = symbol or "XAU-USD-SPOT"
        now = time.monotonic()

        # Fast path — serve from cache without acquiring the lock
        if not force_refresh and sym in self._cache:
            cache_time, cached_res = self._cache[sym]
            if (now - cache_time) < self._ttl:
                logger.debug(f"Returning cached decision for {sym}.")
                return cached_res

        # Slow path — acquire lock to prevent duplicate concurrent builds
        with self._build_lock:
            # Re-check under lock (another thread may have just built it)
            now = time.monotonic()
            if not force_refresh and sym in self._cache:
                cache_time, cached_res = self._cache[sym]
                if (now - cache_time) < self._ttl:
                    logger.debug(f"Returning cached decision for {sym} (built by concurrent thread).")
                    return cached_res

            try:
                result = self._build_decision(symbol=sym, force_refresh=force_refresh)
            except Exception as exc:
                logger.error(f"DecisionService pipeline error for {sym}: {exc}", exc_info=True)
                result = self._emergency_wait(str(exc), symbol=sym)

            self._cache[sym] = (time.monotonic(), result)
            return result

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _build_decision(
        self, symbol: str = "XAU-USD-SPOT", force_refresh: bool = False
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        """Collect data, run AI analysis, run decision engine."""

        # Step 1: Collect technical analysis for all timeframes concurrently
        tf_map = {}
        current_price = 0.0

        def _fetch_analysis(tf_str: str):
            tf_enum = Timeframe(tf_str)
            try:
                ta = self._tech_service.analyze(symbol=symbol, timeframe=tf_enum, force_refresh=force_refresh)
                return tf_str, ta
            except Exception as exc:
                logger.warning(f"Technical analysis failed for {symbol} {tf_str}: {exc}")
                return tf_str, None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_fetch_analysis, tf_s) for tf_s in _TIMEFRAMES]
            for fut in as_completed(futures):
                tf_s, ta = fut.result()
                tf_map[tf_s] = ta
                if ta and ta.current_price > 0 and current_price == 0.0:
                    current_price = ta.current_price

        # Fallback to any valid current price if first one was 0
        if current_price <= 0:
            for ta in tf_map.values():
                if ta and ta.current_price > 0:
                    current_price = ta.current_price
                    break

        if current_price <= 0:
            raise ValueError(f"Could not obtain a valid current price for {symbol} from any timeframe.")

        # Determine alignment summary
        bullish = sum(1 for t in tf_map.values() if t and t.trend.direction.value == "BULLISH")
        bearish = sum(1 for t in tf_map.values() if t and t.trend.direction.value == "BEARISH")
        total = sum(1 for t in tf_map.values() if t is not None)
        if bullish == total and total > 0:
            alignment = f"Full Bullish Alignment ({bullish}/{total} timeframes bullish)"
        elif bearish == total and total > 0:
            alignment = f"Full Bearish Alignment ({bearish}/{total} timeframes bearish)"
        else:
            alignment = (
                f"Mixed Alignment ({bullish} bullish, {bearish} bearish, "
                f"{total - bullish - bearish} sideways)"
            )

        display_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"

        mtf_input = MultiTimeframeTechnicalInput(
            symbol=display_symbol,
            current_price=current_price,
            timestamp=datetime.now(timezone.utc).isoformat(),
            timeframes={k: v for k, v in tf_map.items() if v is not None},
            timeframe_count=total,
            alignment_summary=alignment,
        )

        # Attach factual empirical context to mtf_input so Gemini can review historical performance
        try:
            from src.services.historical_evidence_service import get_historical_evidence_service
            prelim_ev = get_historical_evidence_service().get_evidence_for_setup(
                symbol=display_symbol,
                direction="BUY" if bullish > bearish else ("SELL" if bearish > bullish else "WAIT"),
                confluence_score=75 if (bullish == total or bearish == total) else 50,
                mtf_alignment=alignment,
            )
            if prelim_ev and prelim_ev.status in ("AVAILABLE", "LIMITED"):
                mtf_input.historical_evidence = {
                    "status": prelim_ev.status,
                    "sample_size": prelim_ev.sample_size,
                    "win_rate": prelim_ev.win_rate,
                    "expectancy": prelim_ev.expectancy,
                    "top_success_reasons": prelim_ev.top_success_reasons,
                    "top_failure_reasons": prelim_ev.top_failure_reasons,
                    "historical_confirmations": prelim_ev.historical_confirmations,
                    "historical_conflicts": prelim_ev.historical_conflicts,
                }
        except Exception as _ev_prep_exc:
            logger.debug(f"Historical evidence prompt context skipped: {_ev_prep_exc}")

        # Step 2: Derive the current signal from last cached decision (if any)
        prev_signal = "WAIT"
        prev_strength = 50
        if symbol in self._cache:
            prev_decision, _ = self._cache[symbol][1]
            prev_signal = prev_decision.decision.value
            prev_strength = prev_decision.signal_strength

        # Step 3: Get AI analysis — passes current signal state and pre-collected mtf_input
        # so no duplicate timeframe analysis is needed!
        ai_result: AIAnalysisResponse = self._ai_service.analyze_market(
            symbol=symbol,
            force_refresh=force_refresh,
            current_signal=prev_signal,
            current_strength=prev_strength,
            raw_input=mtf_input,
        )

        # Step 4: Get candles for SMC / S/R strengths / fake breakouts
        candles_dict = {}
        for tf_str, tf_enum, limit in [
            ("1d", Timeframe.D1, 5),
            ("1h", Timeframe.H1, 100),
            ("15m", Timeframe.M15, 50),
            ("5m", Timeframe.M5, 30),
        ]:
            try:
                candles_dict[tf_str] = self._tech_service.market_service.get_candles(
                    symbol=symbol, timeframe=tf_enum, limit=limit, force_refresh=False
                ).candles
            except Exception as e:
                logger.warning(f"Could not retrieve {symbol} {tf_str} candles: {e}")

        # Step 5: Run deterministic decision engine
        decision, breakdown = self._engine.evaluate(mtf_input, ai_result, candles_dict)

        # Step 6: Automated Historical Evidence & Pattern Matching (additive, non-blocking)
        ev_pkg = None
        try:
            from src.services.historical_evidence_service import get_historical_evidence_service
            ev_svc = get_historical_evidence_service()
            ev_pkg = ev_svc.get_evidence_for_setup(
                symbol=display_symbol,
                direction=decision.decision.value,
                confluence_score=decision.signal_strength,
                technical_score=decision.technical_score if decision.technical_score is not None else int(decision.signal_strength * 0.9),
                gemini_score=decision.gemini_score if decision.gemini_score is not None else 0,
                mtf_alignment=decision.mtf_alignment_summary,
                market_regime=decision.market_regime or "UNCLEAR",
                contributors=decision.signal_contributors,
                force_refresh=force_refresh,
            )

            # Populate additive empirical evidence fields on the decision
            decision.historical_evidence_status = ev_pkg.status
            decision.historical_sample_size = ev_pkg.sample_size
            decision.historical_win_rate = ev_pkg.win_rate
            decision.calibrated_probability = ev_pkg.calibrated_probability
            decision.historical_expectancy = ev_pkg.expectancy
            decision.historical_profit_factor = ev_pkg.profit_factor
            decision.historical_drawdown = ev_pkg.drawdown
            decision.similar_setup_count = ev_pkg.similar_count
            decision.historical_wins = ev_pkg.wins
            decision.historical_losses = ev_pkg.losses
            decision.score_band_win_rate = ev_pkg.score_band_win_rate
            decision.win_rate_ci_lower = ev_pkg.ci_lower
            decision.win_rate_ci_upper = ev_pkg.ci_upper
            decision.buy_strength = ev_pkg.buy_strength
            decision.sell_strength = ev_pkg.sell_strength
            decision.similarity_strength = ev_pkg.similarity_strength
            decision.historical_bias = ev_pkg.historical_bias
            decision.strategy_confirmations = ev_pkg.strategy_confirmations
            decision.strategy_conflicts = ev_pkg.strategy_conflicts
            decision.historical_confirmations = ev_pkg.historical_confirmations
            decision.historical_conflicts = ev_pkg.historical_conflicts
            decision.top_success_reasons = ev_pkg.top_success_reasons
            decision.top_failure_reasons = ev_pkg.top_failure_reasons
            decision.success_matches_count = ev_pkg.success_matches_count
            decision.failure_matches_count = ev_pkg.failure_matches_count
            decision.recommendation_strength = ev_pkg.recommendation_strength
            decision.overall_reasoning = ev_pkg.overall_reasoning
            decision.evidence_refresh_at = ev_pkg.evidence_refresh_at
            decision.dataset_version = ev_pkg.dataset_version
            decision.backtest_run_id = ev_pkg.backtest_run_id
            decision.evidence_quality = ev_pkg.evidence_quality

            if ev_pkg.historical_confirmations:
                for hc in ev_pkg.historical_confirmations:
                    if hc not in decision.reasons:
                        decision.reasons.append(hc)
            if ev_pkg.historical_conflicts:
                for hc in ev_pkg.historical_conflicts:
                    if hc not in decision.warnings:
                        decision.warnings.append(hc)
        except Exception as _ev_exc:
            logger.debug(f"Historical evidence integration skipped: {_ev_exc}")

        # Step 7: Validated Strategy Layer (Advisory & Additive Only — Zero Decision Gating)
        try:
            from src.services.validated_strategy_layer import ValidatedStrategyLayer
            strat_layer = ValidatedStrategyLayer.get_instance()

            htf_aligned = False
            sr_aligned = False
            vwap_aligned = False
            ema_aligned = False

            if decision.signal_contributors:
                for c in decision.signal_contributors:
                    name = str(c.get("name", "")).upper()
                    dir_val = str(c.get("direction", "")).upper()
                    if "HTF" in name or "1H" in name or "1D" in name:
                        if dir_val == decision.decision.value or (dir_val == "BULLISH" and decision.decision.value == "BUY") or (dir_val == "BEARISH" and decision.decision.value == "SELL"):
                            htf_aligned = True
                    if "S/R" in name or "SUPPORT" in name or "RESISTANCE" in name:
                        if dir_val == decision.decision.value or (dir_val == "BULLISH" and decision.decision.value == "BUY") or (dir_val == "BEARISH" and decision.decision.value == "SELL"):
                            sr_aligned = True
                    if "VWAP" in name:
                        if dir_val == decision.decision.value or (dir_val == "BULLISH" and decision.decision.value == "BUY") or (dir_val == "BEARISH" and decision.decision.value == "SELL"):
                            vwap_aligned = True
                    if "EMA" in name or "MA STACK" in name:
                        if dir_val == decision.decision.value or (dir_val == "BULLISH" and decision.decision.value == "BUY") or (dir_val == "BEARISH" and decision.decision.value == "SELL"):
                            ema_aligned = True

            prob_val = decision.calibrated_probability
            if prob_val is None:
                prob_val = decision.signal_strength / 100.0 if decision.signal_strength else 0.50

            strat_eval, deg_report = strat_layer.evaluate_realtime_setup(
                symbol=display_symbol,
                proposed_direction=decision.decision.value,
                calibrated_probability=prob_val,
                market_regime=decision.market_regime or "UNKNOWN",
                htf_aligned=htf_aligned,
                sr_aligned=sr_aligned,
                vwap_aligned=vwap_aligned,
                ema_aligned=ema_aligned,
                confluence_score=decision.signal_strength,
            )

            decision.validated_strategy = strat_eval
            decision.degradation_monitoring = deg_report

            if strat_eval.qualified:
                reason_str = (
                    f"Validated Strategy Match: {strat_eval.strategy_name} "
                    f"(Score: {strat_eval.confirmation_score}/{strat_eval.max_confirmation_score}, "
                    f"Research Exp: {strat_eval.research_expectancy_r:+.2f}R)"
                )
                if reason_str not in decision.reasons:
                    decision.reasons.append(reason_str)

            if strat_eval.conflict_reason:
                if strat_eval.conflict_reason not in decision.warnings:
                    decision.warnings.append(strat_eval.conflict_reason)
        except Exception as _strat_exc:
            logger.debug(f"Validated strategy layer skipped: {_strat_exc}")

        # Step 8: Build 3-Layer AI Trading Signal System & Hourly Opportunity Tracking
        try:
            hist_sig, now_sig, overall_sig = self._build_three_layer_signals(
                decision=decision,
                breakdown=breakdown,
                mtf_input=mtf_input,
                ai_result=ai_result,
                ev_pkg=ev_pkg,
            )
            decision.historical_signal = hist_sig
            decision.now_signal = now_sig
            decision.overall_signal = overall_sig

            self._update_hourly_strong_signal(decision, symbol)
            decision.hourly_strong_signal = self.get_hourly_strong_signal(symbol)
        except Exception as _three_layer_exc:
            logger.error(f"3-Layer signal synthesis error for {symbol}: {_three_layer_exc}", exc_info=True)

        # ---- Empirical performance hooks (additive, non-blocking) ----
        # Hook 1: Record this signal if it is actionable (BUY or SELL)
        if decision.decision.value in ("BUY", "SELL"):
            try:
                get_signal_repository().record_signal(decision)
            except Exception as _exc:
                logger.debug(f"Signal recording skipped: {_exc}")

        # Hook 2: Label outcomes for previously open signals (uses current price and symbol)
        try:
            _candles_5m = candles_dict.get("5m", [])
            get_outcome_tracker().label_outcomes(
                current_price=current_price,
                candles_history=_candles_5m,
                symbol=display_symbol,
            )
        except Exception as _exc:
            logger.debug(f"Outcome tracking skipped: {_exc}")

        # Hook 3: ML Shadow Validation Observer (Downstream Research Only — Zero Decision Gating)
        try:
            from src.research.ml_shadow.shadow_service import get_ml_shadow_service
            shadow_svc = get_ml_shadow_service()

            c_scores = {}
            c_biases = {}
            if decision.signal_contributors:
                for c in decision.signal_contributors:
                    c_name = str(c.get("name", ""))
                    c_scores[c_name] = int(c.get("score", 0))
                    c_biases[c_name] = str(c.get("direction", "NEUTRAL"))

            # Determine session from UTC hour
            utc_hour = datetime.now(timezone.utc).hour
            session_str = "ASIA" if 0 <= utc_hour < 8 else ("LONDON" if 8 <= utc_hour < 14 else "NY")

            shadow_pred = shadow_svc.generate_prediction(
                symbol=display_symbol,
                timestamp_t0=datetime.now(timezone.utc).isoformat(),
                production_decision=decision.decision.value,
                confluence_score=decision.signal_strength,
                technical_score=decision.technical_score if decision.technical_score is not None else int(decision.signal_strength * 0.9),
                gemini_score=decision.gemini_score if decision.gemini_score is not None else 0,
                entry_price=current_price,
                stop_loss=decision.stop_loss,
                take_profit_1=decision.take_profit_1,
                take_profit_2=decision.take_profit_2,
                session=session_str,
                market_regime=decision.market_regime or "UNCLEAR",
                contributor_scores=c_scores,
                contributor_biases=c_biases,
                data_quality=decision.data_quality or "HIGH",
                gate_direction=decision.gate_direction or "NONE",
                quality_gate_passed=bool(getattr(decision, "quality_gate_status", "") in ("PASSED", "CONFIRMED"))
            )

            # Resolve forward outcomes for previously pending ML shadow observations
            _candles_15m = candles_dict.get("15m", [])
            if _candles_15m:
                shadow_svc.resolve_pending_observations(
                    symbol=display_symbol,
                    forward_candles=[
                        {
                            "timestamp": getattr(c, "timestamp", ""),
                            "high": getattr(c, "high", 0.0),
                            "low": getattr(c, "low", 0.0),
                            "close": getattr(c, "close", 0.0)
                        }
                        for c in _candles_15m
                    ]
                )
        except Exception as _ml_shadow_exc:
            logger.debug(f"[ML SHADOW] Observer hook skipped: {_ml_shadow_exc}")

        # Hook 4: BTC Production Gating Pre-Filter (Policy B: Calibrated Prob >= 50%)
        # Applied ONLY when PRODUCTION_GATING_BTC is explicitly enabled by authenticated admin action.
        if "BTC" in display_symbol.upper():
            try:
                from src.core.gating_control import get_gating_control
                if get_gating_control().production_gating_btc:
                    cal_prob = getattr(decision, "calibrated_probability", None)
                    if cal_prob is not None and cal_prob < 50.0 and decision.decision.value in ("BUY", "SELL"):
                        logger.info(
                            f"[BTC Gating Active] Overriding {decision.decision.value} to WAIT: "
                            f"Calibrated probability {cal_prob}% < 50% threshold."
                        )
                        decision.decision = TradingSignal.WAIT
                        decision.reasons.append("POLICY_B_GATING_FILTER: Calibrated probability below 50% threshold.")
                        decision.gate_reason = "POLICY_B_GATING_FILTER"
            except Exception as _gate_exc:
                logger.error(f"[BTC Gating] Error evaluating production gating: {_gate_exc}")

        # Hook 5: Shadow Runner Integration — feed live qualifying signals into BTC/XAU shadow capture.
        # ADDITIVE-ONLY: this hook NEVER modifies decision, breakdown, or any production output.
        # Wrapped in its own try/except so shadow capture failure can NEVER propagate to the caller.
        try:
            if decision.decision.value in ("BUY", "SELL"):
                _shadow_cal_prob = getattr(decision, "calibrated_probability", None) or 0.0
                _shadow_session = "ASIA" if 0 <= datetime.now(timezone.utc).hour < 8 else (
                    "LONDON" if 8 <= datetime.now(timezone.utc).hour < 14 else "NY"
                )
                _shadow_mtf_aligned = (
                    "Full Bullish" in mtf_input.alignment_summary
                    or "Full Bearish" in mtf_input.alignment_summary
                )
                _shadow_signal_strength = float(decision.signal_strength or 50)
                _shadow_confluence = float(decision.signal_strength or 50)
                _shadow_confidence = float(decision.confidence or 50)
                _shadow_regime = decision.market_regime or "UNKNOWN"
                _shadow_sl = float(decision.stop_loss) if decision.stop_loss else 0.0
                _shadow_tp1 = float(decision.take_profit_1) if decision.take_profit_1 else 0.0
                _shadow_tp2 = float(decision.take_profit_2) if decision.take_profit_2 else 0.0

                if "BTC" in display_symbol.upper():
                    from src.services.btc_shadow_runner import get_btc_shadow_runner
                    get_btc_shadow_runner().evaluate_live_market_setup(
                        current_price=current_price,
                        direction=decision.decision.value,
                        stop_loss=_shadow_sl,
                        take_profit_1=_shadow_tp1,
                        take_profit_2=_shadow_tp2,
                        confluence_score=_shadow_confluence,
                        confidence_score=_shadow_confidence,
                        signal_strength=_shadow_signal_strength,
                        market_regime=_shadow_regime,
                        session=_shadow_session,
                        mtf_aligned=_shadow_mtf_aligned,
                        ml_calibrated_prob=_shadow_cal_prob,
                    )
                elif "XAU" in display_symbol.upper():
                    from src.services.xau_shadow_runner import get_xau_shadow_runner
                    get_xau_shadow_runner().evaluate_live_market_setup(
                        current_price=current_price,
                        direction=decision.decision.value,
                        stop_loss=_shadow_sl,
                        take_profit_1=_shadow_tp1,
                        take_profit_2=_shadow_tp2,
                        confluence_score=_shadow_confluence,
                        confidence_score=_shadow_confidence,
                        signal_strength=_shadow_signal_strength,
                        market_regime=_shadow_regime,
                        session=_shadow_session,
                        mtf_aligned=_shadow_mtf_aligned,
                        ml_calibrated_prob=_shadow_cal_prob,
                    )
        except Exception as _shadow_exc:
            logger.debug(f"[Shadow Hook] Shadow capture skipped (non-blocking): {_shadow_exc}")

        logger.info(
            f"Decision ({display_symbol}): {decision.decision.value} | Score: {decision.composite_score:+.4f} | "
            f"Confidence: {decision.confidence}% | Evidence: {decision.historical_evidence_status} | AI: {ai_result.provider_used}"
        )
        return decision, breakdown

    # ------------------------------------------------------------------
    # 3-Layer Signal Synthesis & Hourly Strong Signal Methods
    # ------------------------------------------------------------------

    def _build_three_layer_signals(
        self,
        decision: TradingDecision,
        breakdown: DecisionScoreBreakdown,
        mtf_input: MultiTimeframeTechnicalInput,
        ai_result: AIAnalysisResponse,
        ev_pkg: Any,
    ) -> Tuple[HistoricalMarketSignal, NowMarketSignal, OverallTradingSignal]:
        """
        Synthesize the 3 distinct AI signal layers:
        1. HISTORICAL MARKET ANALYSE AI TRADING SIGNAL (Empirical backtest/research evidence only)
        2. NOW MARKET ANALYSE AI TRADING SIGNAL (Real-time live multi-timeframe technical confluence)
        3. OVERALL AI TRADING SIGNAL (Evidence fusion combining 1 + 2, primary decision)
        """
        # --- Layer 1: Historical Signal ---
        hist_sample = getattr(ev_pkg, "sample_size", 0) or 0
        hist_status = getattr(ev_pkg, "status", "INSUFFICIENT_SAMPLE") or "INSUFFICIENT_SAMPLE"
        hist_win_rate = getattr(ev_pkg, "win_rate", None)
        hist_prob = getattr(ev_pkg, "calibrated_probability", None)
        hist_exp = getattr(ev_pkg, "expectancy", None)
        hist_bias = getattr(ev_pkg, "historical_bias", None) or "WAIT"
        buy_str = getattr(ev_pkg, "buy_strength", None)
        sell_str = getattr(ev_pkg, "sell_strength", None)

        if hist_sample >= 20 and hist_status in ("AVAILABLE", "LIMITED", "STALE"):
            if hist_bias in ("BUY", "SELL"):
                hist_dir = hist_bias
            elif buy_str and buy_str > 55 and (not sell_str or buy_str > sell_str):
                hist_dir = "BUY"
            elif sell_str and sell_str > 55 and (not buy_str or sell_str > buy_str):
                hist_dir = "SELL"
            else:
                hist_dir = "WAIT"

            if hist_prob is not None and hist_prob >= 0:
                hist_pct = round(hist_prob)
            elif hist_win_rate is not None and hist_win_rate >= 0:
                hist_pct = round(hist_win_rate)
            elif hist_dir == "BUY" and buy_str is not None:
                hist_pct = buy_str
            elif hist_dir == "SELL" and sell_str is not None:
                hist_pct = sell_str
            else:
                hist_pct = None

            if hist_pct is not None:
                if hist_pct >= 80:
                    hist_strength_label = "VERY STRONG"
                elif hist_pct >= 60:
                    hist_strength_label = "STRONG"
                elif hist_pct >= 40:
                    hist_strength_label = "MODERATE"
                else:
                    hist_strength_label = "WEAK"
            else:
                hist_strength_label = "WEAK"

            hist_reasons = []
            if hist_win_rate is not None:
                hist_reasons.append(f"Historical {hist_dir} win rate on matching setups: {hist_win_rate:.1f}% ({hist_sample} trades).")
            if hist_exp is not None:
                pf_val = getattr(ev_pkg, 'profit_factor', None)
                pf_str = f" (Profit factor: {pf_val:.2f})" if pf_val is not None else ""
                hist_reasons.append(f"Empirical expectancy: {hist_exp:+.2f}R{pf_str}.")
            if getattr(ev_pkg, "historical_confirmations", None):
                hist_reasons.extend(ev_pkg.historical_confirmations[:2])

            hist_sig = HistoricalMarketSignal(
                signal=hist_dir,
                percentage=hist_pct,
                strength=hist_strength_label,
                status="AVAILABLE" if hist_status in ("AVAILABLE", "STALE") else hist_status,
                sample_size=hist_sample,
                win_rate=hist_win_rate,
                calibrated_probability=hist_prob,
                expectancy=hist_exp,
                reasons=hist_reasons,
            )
        else:
            hist_sig = HistoricalMarketSignal(
                signal="WAIT",
                percentage=None,
                strength="WEAK",
                status="INSUFFICIENT_SAMPLE",
                sample_size=hist_sample,
                win_rate=None,
                calibrated_probability=None,
                expectancy=None,
                reasons=[f"Historical sample size ({hist_sample} trades) below significance threshold (min 20). Status: INSUFFICIENT_SAMPLE."],
            )

        # --- Layer 2: Now Market Signal ---
        now_pct = round(decision.signal_strength) if decision.signal_strength is not None else None
        if breakdown.signal_candidate in ("BUY", "SELL"):
            now_dir = breakdown.signal_candidate
        elif decision.decision.value in ("BUY", "SELL"):
            now_dir = decision.decision.value
        elif "Full Bullish" in mtf_input.alignment_summary:
            now_dir = "BUY"
        elif "Full Bearish" in mtf_input.alignment_summary:
            now_dir = "SELL"
        elif "Bullish" in str(getattr(decision.trend, "value", "")):
            now_dir = "BUY"
        elif "Bearish" in str(getattr(decision.trend, "value", "")):
            now_dir = "SELL"
        else:
            now_dir = "WAIT"

        if now_pct is not None:
            if now_pct >= 80:
                now_strength_label = "VERY STRONG"
            elif now_pct >= 60:
                now_strength_label = "STRONG"
            elif now_pct >= 40:
                now_strength_label = "MODERATE"
            else:
                now_strength_label = "WEAK"
        else:
            now_strength_label = "AWAITING_EVALUATION"

        now_reasons = []
        if decision.top_confirmations:
            now_reasons.extend(decision.top_confirmations[:2])
        if decision.mtf_alignment_summary:
            now_reasons.append(f"MTF Structure: {decision.mtf_alignment_summary}")
        if decision.market_regime:
            now_reasons.append(f"Regime: {decision.market_regime}")
        if not now_reasons:
            now_reasons = decision.reasons[:2] or ["Real-time technical confluence and multi-timeframe analysis."]

        now_sig = NowMarketSignal(
            signal=now_dir,
            percentage=now_pct,
            strength=now_strength_label,
            technical_score=decision.technical_score if decision.technical_score is not None else (int(now_pct * 0.9) if now_pct is not None else 0),
            gemini_score=decision.gemini_score if decision.gemini_score is not None else 0,
            mtf_alignment=decision.mtf_alignment_summary or mtf_input.alignment_summary,
            market_regime=decision.market_regime or "UNCLEAR",
            reasons=now_reasons,
        )

        # --- Layer 3: Overall Trading Signal (Evidence Fusion) ---
        overall_dir = decision.decision.value
        conflict_detected = False

        # Direction Conflict Detection
        if hist_sig.status != "INSUFFICIENT_SAMPLE" and hist_sig.signal in ("BUY", "SELL") and now_sig.signal in ("BUY", "SELL") and hist_sig.signal != now_sig.signal:
            conflict_detected = True
            overall_dir = "WAIT"
            overall_pct = None
            overall_strength_label = "CONFLICT"
            overall_reasons = [
                f"Direction Conflict: Historical evidence favors {hist_sig.signal} ({hist_sig.percentage}%) while live market indicates {now_sig.signal} ({now_sig.percentage}%).",
                "DecisionEngine safety protocol enforces conservative WAIT on directional divergence (CONFLICT=TRUE).",
            ]
        else:
            if hist_sig.status != "INSUFFICIENT_SAMPLE" and hist_sig.percentage is not None and now_sig.percentage is not None:
                # Reliability-weighted combination: 40% historical evidence + 60% real-time technicals
                overall_pct = round(0.40 * hist_sig.percentage + 0.60 * now_sig.percentage)
            elif now_sig.percentage is not None:
                overall_pct = now_sig.percentage
            else:
                overall_pct = None

            if overall_pct is not None:
                if overall_pct >= 80:
                    overall_strength_label = "VERY STRONG"
                elif overall_pct >= 60:
                    overall_strength_label = "STRONG"
                elif overall_pct >= 40:
                    overall_strength_label = "MODERATE"
                else:
                    overall_strength_label = "WEAK"
            else:
                overall_strength_label = "AWAITING_EVALUATION"

            overall_reasons = decision.reasons[:3] or [
                f"Fused overall {overall_dir} decision aligning live confluence ({now_sig.percentage}%) with historical evidence."
            ]

        overall_sig = OverallTradingSignal(
            signal=overall_dir,
            percentage=overall_pct,
            strength=overall_strength_label,
            conflict_detected=conflict_detected,
            primary_highlight=True,
            reasons=overall_reasons,
        )

        return hist_sig, now_sig, overall_sig

    def _update_hourly_strong_signal(self, decision: TradingDecision, symbol: str) -> None:
        """Track the single strongest valid opportunity during each UTC hour (zero forced)."""
        now_utc = datetime.now(timezone.utc)
        hour_window = now_utc.strftime("%Y-%m-%dT%H:00:00Z")
        key = f"{symbol}:{hour_window}"

        # Only qualify actionable signals (BUY/SELL) with strong confluence >= 60 and gate passed
        is_qualifying = (
            decision.decision.value in ("BUY", "SELL")
            and (decision.signal_strength or 0) >= 60
            and getattr(decision, "gate_passed", True) is not False
        )

        existing = self._hourly_strong_signals.get(key)

        if is_qualifying:
            cur_score = decision.signal_strength or 60
            if existing is None or (existing.strength or 0) < cur_score:
                self._hourly_strong_signals[key] = HourlyStrongSignal(
                    hour_window=hour_window,
                    status="ACTIVE_OPPORTUNITY",
                    signal=decision.decision.value,
                    strength=cur_score,
                    confidence=decision.confidence,
                    timestamp=decision.timestamp,
                    asset=symbol,
                    reasons=decision.reasons[:2] or [f"Strongest {decision.decision.value} setup observed in {hour_window}."],
                )

    def get_hourly_strong_signal(self, symbol: str = "XAU-USD-SPOT") -> HourlyStrongSignal:
        """Return the strongest opportunity in the current hour window, or WAIT if none qualified."""
        now_utc = datetime.now(timezone.utc)
        hour_window = now_utc.strftime("%Y-%m-%dT%H:00:00Z")
        key = f"{symbol}:{hour_window}"
        if key in self._hourly_strong_signals:
            return self._hourly_strong_signals[key]
        return HourlyStrongSignal(
            hour_window=hour_window,
            status="NO_QUALIFYING_SETUP",
            signal="WAIT",
            strength=None,
            confidence=None,
            timestamp=now_utc.isoformat(),
            asset=symbol,
            reasons=["No qualifying strong setup observed in current hour window. (Zero forced signals)."],
        )

    def _emergency_wait(
        self, reason: str, symbol: str = "XAU-USD-SPOT"
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        """Return a safe WAIT decision when the pipeline fails completely."""
        now = datetime.now(timezone.utc).isoformat()
        display_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
        decision = TradingDecision(
            symbol=display_symbol,
            decision=TradingSignal.WAIT,
            confidence=0,
            trend=DecisionTrend.NEUTRAL,
            risk_level=DecisionRiskLevel.HIGH,
            composite_score=0.0,
            reasons=[f"WAIT — decision pipeline failed: {reason}"],
            warnings=["Pipeline error. Do not act on this output."],
            invalid_if=[],
            timestamp=now,
            ai_provider_used="unknown",
            historical_signal=HistoricalMarketSignal(
                signal="WAIT",
                percentage=None,
                strength="WEAK",
                status="INSUFFICIENT_SAMPLE",
                sample_size=0,
                reasons=[f"Pipeline error: {reason}"],
            ),
            now_signal=NowMarketSignal(
                signal="WAIT",
                percentage=None,
                strength="WEAK",
                reasons=[f"Pipeline error: {reason}"],
            ),
            overall_signal=OverallTradingSignal(
                signal="WAIT",
                percentage=None,
                strength="WEAK",
                reasons=[f"Pipeline error: {reason}"],
            ),
            hourly_strong_signal=HourlyStrongSignal(
                hour_window=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z"),
                status="NO_QUALIFYING_SETUP",
                signal="WAIT",
                asset=symbol,
                reasons=[f"Pipeline error: {reason}"],
            ),
        )
        breakdown = DecisionScoreBreakdown(
            symbol=display_symbol,
            timestamp=now,
            total_score=0.0,
            signal_candidate="WAIT",
            final_signal=TradingSignal.WAIT,
            confidence=0,
            components=[],
            wait_overrides_triggered=[f"Pipeline error: {reason}"],
            weight_sum=0.0,
        )
        return decision, breakdown


# ---------------------------------------------------------------------------
# Module-level singleton factory
# ---------------------------------------------------------------------------
_decision_service_instance: Optional[DecisionService] = None


def get_decision_service() -> DecisionService:
    """Return a module-level singleton DecisionService instance."""
    global _decision_service_instance
    if _decision_service_instance is None:
        _decision_service_instance = DecisionService()
    return _decision_service_instance
