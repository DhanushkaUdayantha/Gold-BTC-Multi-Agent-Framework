"""
Deterministic Trading Decision Engine for XAU/USD.

DISCLAIMER: This engine produces advisory analytical signals ONLY.
It does NOT execute trades, connect to brokers, or guarantee any market outcome.
All signals carry inherent market risk.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from config.settings import get_settings
from src.models.ai_analysis import (
    AIAnalysisResponse,
    MarketCondition,
    OverallBias,
)
from src.models.technical_analysis import (
    TechnicalAnalysisResponse,
    TrendDirection,
    MACDState,
    RSICondition,
)
from src.models.ai_analysis import MultiTimeframeTechnicalInput
from src.models.trading_decision import (
    TradingDecision,
    TradingSignal,
    EntryZone,
    DecisionTrend,
    DecisionRiskLevel,
    ScoreComponent,
    DecisionScoreBreakdown,
)
from src.services.paper_trading_service import PaperTradingService
from src.services.confluence_engine import ConfluenceEngine, get_confluence_engine

logger = logging.getLogger(__name__)

# Signal thresholds — score must exceed these to be a BUY/SELL candidate
_BUY_THRESHOLD = 0.35
_SELL_THRESHOLD = -0.35


class DecisionEngine:
    """
    Deterministic weighted scoring engine that converts multi-timeframe
    technical analysis and AI bias into a structured BUY / SELL / WAIT signal.

    Scoring range: -1.0 (maximum bearish) → +1.0 (maximum bullish)
    """

    def __init__(self):
        s = get_settings()
        # Scoring weights (configurable via .env)
        self.weights = {
            "1h_trend": s.DECISION_WEIGHT_1H_TREND,
            "15m_trend": s.DECISION_WEIGHT_15M_TREND,
            "5m_momentum": s.DECISION_WEIGHT_5M_MOMENTUM,
            "1d_trend": s.DECISION_WEIGHT_1D_TREND,
            "macd": s.DECISION_WEIGHT_MACD,
            "rsi": s.DECISION_WEIGHT_RSI,
            "ema": s.DECISION_WEIGHT_EMA,
            "gemini": s.DECISION_WEIGHT_GEMINI,
        }
        self.atr_multiplier = s.DECISION_ATR_MULTIPLIER
        self.min_confidence = s.DECISION_MIN_CONFIDENCE
        self.min_rr_ratio = s.DECISION_MIN_RR_RATIO
        self.resistance_proximity_pct = s.DECISION_RESISTANCE_PROXIMITY_PCT / 100.0
        self.support_proximity_pct = s.DECISION_SUPPORT_PROXIMITY_PCT / 100.0
        self.pt_service = PaperTradingService()
        self.prev_scores = {}
        self.last_changed_at = {}
        self.bypass_threshold = 60
        self.confluence_engine: ConfluenceEngine = get_confluence_engine()


    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def evaluate(
        self,
        mtf_input: MultiTimeframeTechnicalInput,
        ai_result: AIAnalysisResponse,
        candles_dict: Optional[dict] = None,
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        """
        Run the full decision pipeline and return (TradingDecision, Breakdown).
        Never raises — all exceptions produce a safe WAIT decision.
        """
        try:
            return self._run_evaluation(mtf_input, ai_result, candles_dict)
        except Exception as exc:
            logger.error(f"DecisionEngine evaluation error: {exc}", exc_info=True)
            return self._safe_wait_decision(
                price=mtf_input.current_price,
                ai_result=ai_result,
                reason=f"Internal evaluation error: {exc}",
            )

    # ------------------------------------------------------------------
    # Core evaluation pipeline
    # ------------------------------------------------------------------

    def _run_evaluation(
        self,
        mtf_input: MultiTimeframeTechnicalInput,
        ai_result: AIAnalysisResponse,
        candles_dict: Optional[dict] = None,
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        price = mtf_input.current_price
        tf = mtf_input.timeframes  # dict keyed "5m", "15m", "1h", "1d"

        # Get candles data
        candles_1d = candles_dict.get("1d", []) if candles_dict else []
        candles_1h = candles_dict.get("1h", []) if candles_dict else []
        candles_15m = candles_dict.get("15m", []) if candles_dict else []
        candles_5m = candles_dict.get("5m", []) if candles_dict else []

        # Run OTE engine logic & Elliott Wave analysis
        from src.services.ote_engine import OTEEngine
        from src.models.ote_analysis import SweepDirection, MSSDirection, FVGType
        from src.services.elliott_wave_service import ElliottWaveService
        
        ote_eng = OTEEngine()
        
        ta_1h = tf.get("1h")
        ema20_1h = ta_1h.ema20 if ta_1h else None
        ema50_1h = ta_1h.ema50 if ta_1h else None
        ema200_1h = ta_1h.ema200 if ta_1h else None
        
        smc_trend = ote_eng.analyze_trend(price, ema20_1h, ema50_1h, ema200_1h)
        smc_liquidity = ote_eng.analyze_liquidity(candles_1d, candles_1h, price)
        smc_mss = ote_eng.analyze_mss(candles_15m, smc_liquidity.sweep_direction, timeframe="15m")
        smc_fib = ote_eng.analyze_fibonacci(candles_15m, smc_mss.direction, price)
        smc_fvg = ote_eng.analyze_fvg(candles_5m if candles_5m else candles_15m, smc_mss.direction, price)

        # Run Elliott Wave Analysis
        candles_for_elliott = candles_15m if candles_15m else candles_1h
        elliott_res = ElliottWaveService.analyze(candles_for_elliott, price, timeframe="15m")

        # SMC/ICT score component
        smc_raw_score = 0.0
        smc_confirmations = []
        if smc_trend.passed:
            smc_raw_score += 0.3 if smc_trend.direction == "BULLISH" else -0.3
            smc_confirmations.append(f"Trend: {smc_trend.direction}")
        if smc_mss.passed:
            smc_raw_score += 0.4 if smc_mss.direction == MSSDirection.BULLISH else -0.4
            smc_confirmations.append(f"MSS: {smc_mss.direction.value}")
        if smc_fvg.passed:
            smc_raw_score += 0.3 if smc_fvg.fvg_type == FVGType.BULLISH else -0.3
            smc_confirmations.append("FVG Aligned")
            
        smc_weight = 0.12
        comp_smc = ScoreComponent(
            name="SMC/ICT",
            weight=smc_weight,
            raw_score=round(max(-1.0, min(1.0, smc_raw_score)), 2),
            weighted_score=round(max(-1.0, min(1.0, smc_raw_score)) * smc_weight, 5),
            reasoning=f"SMC: {', '.join(smc_confirmations) if smc_confirmations else 'No setup'}"
        )

        # Liquidity Sweep component
        liq_raw_score = 0.0
        if smc_liquidity.passed:
            liq_raw_score = 1.0 if smc_liquidity.sweep_direction == SweepDirection.BULLISH else -1.0
        liq_weight = 0.09
        comp_liq = ScoreComponent(
            name="Liquidity Sweep",
            weight=liq_weight,
            raw_score=round(liq_raw_score, 2),
            weighted_score=round(liq_raw_score * liq_weight, 5),
            reasoning=f"Liquidity: {smc_liquidity.reasoning}"
        )

        # Fibonacci OTE component
        fib_raw_score = 0.0
        if smc_fib.passed:
            fib_raw_score = 0.85 if smc_mss.direction == MSSDirection.BULLISH else (-0.85 if smc_mss.direction == MSSDirection.BEARISH else 0.5)
        fib_weight = 0.09
        comp_fib = ScoreComponent(
            name="Fibonacci OTE",
            weight=fib_weight,
            raw_score=round(fib_raw_score, 2),
            weighted_score=round(fib_raw_score * fib_weight, 5),
            reasoning=f"Fib OTE: {smc_fib.reasoning}"
        )

        # Elliott Wave component
        elliott_weight = 0.09
        comp_elliott = ScoreComponent(
            name="Elliott Wave",
            weight=elliott_weight,
            raw_score=round(elliott_res.score, 2),
            weighted_score=round(elliott_res.score * elliott_weight, 5),
            reasoning=f"Elliott: {elliott_res.reasoning}"
        )

        # ---- Step 1: Score each component ----
        components: List[ScoreComponent] = [comp_smc]

        # 1h trend (25%)
        comp_1h = self._score_trend(tf.get("1h"), "1h Trend", self.weights["1h_trend"])
        components.append(comp_1h)

        # 15m trend (20%)
        comp_15m = self._score_trend(tf.get("15m"), "15m Trend", self.weights["15m_trend"])
        components.append(comp_15m)

        # 5m momentum (15%)
        comp_5m = self._score_5m_momentum(tf.get("5m"), self.weights["5m_momentum"])
        components.append(comp_5m)

        # 1d trend (15%)
        comp_1d = self._score_trend(tf.get("1d"), "1d Trend", self.weights["1d_trend"])
        components.append(comp_1d)

        # MACD (10%) — aggregate across available timeframes
        comp_macd = self._score_macd(tf, self.weights["macd"])
        components.append(comp_macd)

        # RSI (5%) — primary from 1h, fallback to 15m
        comp_rsi = self._score_rsi(tf, self.weights["rsi"])
        components.append(comp_rsi)

        # EMA structure (5%) — primary from 1h
        comp_ema = self._score_ema(tf, price, self.weights["ema"])
        components.append(comp_ema)

        # Gemini AI bias (5%)
        comp_gemini = self._score_gemini(ai_result, self.weights["gemini"])
        components.append(comp_gemini)

        # ---- Step 2: Compute total score ----
        # Add slight boost from Elliott wave and liquidity sweep if available
        base_score = sum(c.weighted_score for c in components)
        if elliott_res.direction != "NEUTRAL" and elliott_res.score != 0:
            base_score += elliott_res.score * 0.05
        if smc_liquidity.passed:
            base_score += (0.05 if smc_liquidity.sweep_direction == SweepDirection.BULLISH else -0.05)

        total_score = max(-1.0, min(1.0, base_score))
        weight_sum = sum(c.weight for c in components)

        # ---- Step 3: Raw signal candidate ----
        if total_score >= _BUY_THRESHOLD:
            signal_candidate = "BUY"
        elif total_score <= _SELL_THRESHOLD:
            signal_candidate = "SELL"
        else:
            signal_candidate = "WAIT"

        # ---- Step 4: Confidence from score magnitude ----
        # Map |score| from [threshold → 1.0] to [65 → 95]
        abs_score = abs(total_score)
        threshold = _BUY_THRESHOLD
        if abs_score <= threshold:
            raw_confidence = int(abs_score / threshold * 60)
        else:
            raw_confidence = 65 + int((abs_score - threshold) / (1.0 - threshold) * 30)
        raw_confidence = max(0, min(95, raw_confidence))

        # Blend with AI confidence (minor influence)
        blended_confidence = int(raw_confidence * 0.85 + ai_result.confidence * 0.15)
        blended_confidence = max(0, min(95, blended_confidence))

        # ---- Step 5: Gather support/resistance & ATR ----
        all_supports = sorted(set(
            ai_result.key_support
            + self._collect_levels(tf, "support")
        ))
        all_resistances = sorted(set(
            ai_result.key_resistance
            + self._collect_levels(tf, "resistance")
        ))
        atr_value = self._get_best_atr(tf)

        # ---- Step 6: Apply WAIT override rules ----
        wait_overrides: List[str] = []

        is_strong_smc_setup = bool(smc_liquidity.passed and smc_mss.passed)

        # Rule 1: Confidence too low (waived if a strong SMC setup is confirmed)
        if blended_confidence < self.min_confidence and not is_strong_smc_setup:
            wait_overrides.append(
                f"Confidence ({blended_confidence}%) is below minimum threshold ({self.min_confidence}%)"
            )

        # Rule 2: Market condition is RANGE or UNCLEAR, unless a strong SMC setup is confirmed
        if ai_result.market_condition in (MarketCondition.RANGE, MarketCondition.UNCLEAR) and not is_strong_smc_setup:
            wait_overrides.append(
                f"Market condition is {ai_result.market_condition.value} with no confirmed SMC setup"
            )

        # Rule 3: Proximity checks
        if signal_candidate == "BUY" and all_resistances:
            nearest_res = min(r for r in all_resistances if r >= price * 0.999)  \
                if any(r >= price * 0.999 for r in all_resistances) else None
            if nearest_res and (nearest_res - price) / price <= self.resistance_proximity_pct:
                wait_overrides.append(
                    f"BUY candidate: price (${price:.2f}) is within "
                    f"{self.resistance_proximity_pct*100:.2f}% of nearest resistance (${nearest_res:.2f})"
                )

        if signal_candidate == "SELL" and all_supports:
            nearest_sup = max(s for s in all_supports if s <= price * 1.001) \
                if any(s <= price * 1.001 for s in all_supports) else None
            if nearest_sup and (price - nearest_sup) / price <= self.support_proximity_pct:
                wait_overrides.append(
                    f"SELL candidate: price (${price:.2f}) is within "
                    f"{self.support_proximity_pct*100:.2f}% of nearest support (${nearest_sup:.2f})"
                )

        # Rule 4: ATR validity
        if atr_value is None or atr_value <= 0:
            wait_overrides.append("ATR is unavailable — stop-loss cannot be calculated reliably")

        # ---- Step 7: Compute levels (needed for R:R check) ----
        entry_zone: Optional[EntryZone] = None
        stop_loss: Optional[float] = None
        tp1: Optional[float] = None
        tp2: Optional[float] = None
        rr_tp1: Optional[float] = None
        rr_tp2: Optional[float] = None

        if signal_candidate in ("BUY", "SELL") and not wait_overrides and atr_value:
            entry_zone, stop_loss, tp1, tp2 = self._calculate_levels(
                signal=signal_candidate,
                price=price,
                supports=all_supports,
                resistances=all_resistances,
                atr=atr_value,
            )

            if entry_zone and stop_loss and tp1:
                entry_mid = (entry_zone.min + entry_zone.max) / 2
                risk = abs(entry_mid - stop_loss)
                if risk > 0:
                    rr_tp1 = round(abs(tp1 - entry_mid) / risk, 2)
                if tp2 and risk > 0:
                    rr_tp2 = round(abs(tp2 - entry_mid) / risk, 2)

                # Rule 5: Risk:Reward check (allow TP1 >= 1.2, require composite/TP2 >= min_rr_ratio)
                if rr_tp2 is not None and rr_tp2 < self.min_rr_ratio:
                    wait_overrides.append(
                        f"Risk:Reward to TP2 ({rr_tp2:.2f}) is below minimum threshold ({self.min_rr_ratio:.1f}:1)"
                    )
                elif rr_tp1 is not None and rr_tp1 < 1.2:
                    wait_overrides.append(
                        f"Risk:Reward to TP1 ({rr_tp1:.2f}) is too small (< 1.2:1)"
                    )

        # ---- Step 8: Apply overrides to final signal ----
        if wait_overrides and signal_candidate in ("BUY", "SELL"):
            signal_candidate = "WAIT"
            entry_zone = None
            stop_loss = None
            tp1 = None
            tp2 = None
            rr_tp1 = None
            rr_tp2 = None

        final_signal = TradingSignal(signal_candidate)
        initial_final_signal = final_signal

        # ---- Step 9: Build reasons, warnings, invalid_if ----
        reasons, warnings, invalid_if = self._build_narrative(
            signal=final_signal,
            components=components,
            ai_result=ai_result,
            price=price,
            tf=tf,
            all_supports=all_supports,
            all_resistances=all_resistances,
            atr_value=atr_value,
        )

        # ---- Step 10: Trend & risk level ----
        trend = self._determine_trend(total_score)
        risk_level = self._determine_risk_level(ai_result, atr_value, blended_confidence)

        # ---- Step 10a: Agreement Score (AI Bias vs Technical trend) ----
        agreement = 50
        ai_bias = ai_result.overall_bias
        ta_1h = tf.get("1h")
        ta_1d = tf.get("1d")
        
        if ai_bias == OverallBias.BULLISH:
            if ta_1h and ta_1h.trend.direction == TrendDirection.BULLISH:
                agreement += 25
            elif ta_1h and ta_1h.trend.direction == TrendDirection.BEARISH:
                agreement -= 25
                
            if ta_1d and ta_1d.trend.direction == TrendDirection.BULLISH:
                agreement += 25
            elif ta_1d and ta_1d.trend.direction == TrendDirection.BEARISH:
                agreement -= 25
        elif ai_bias == OverallBias.BEARISH:
            if ta_1h and ta_1h.trend.direction == TrendDirection.BEARISH:
                agreement += 25
            elif ta_1h and ta_1h.trend.direction == TrendDirection.BULLISH:
                agreement -= 25
                
            if ta_1d and ta_1d.trend.direction == TrendDirection.BEARISH:
                agreement += 25
            elif ta_1d and ta_1d.trend.direction == TrendDirection.BULLISH:
                agreement -= 25
        else: # NEUTRAL
            if ta_1h and ta_1h.trend.direction == TrendDirection.SIDEWAYS:
                agreement += 25
            if ta_1d and ta_1d.trend.direction == TrendDirection.SIDEWAYS:
                agreement += 25
        agreement_score = max(0, min(100, agreement))

        # ---- Step 10b: Setup Grading ----
        if final_signal == TradingSignal.WAIT:
            setup_grade = "C"
        else:
            is_high_conf = blended_confidence >= 80
            is_high_agree = agreement_score >= 75
            is_strong_score = abs(total_score) >= 0.60
            is_low_risk = risk_level == DecisionRiskLevel.LOW
            
            if is_high_conf and is_high_agree and is_strong_score and is_low_risk:
                setup_grade = "A+"
            elif (is_high_conf or is_high_agree) and abs(total_score) >= 0.50:
                setup_grade = "A"
            elif blended_confidence >= 65 and agreement_score >= 50:
                setup_grade = "B"
            else:
                setup_grade = "C"

        # ---- Step 10c: Position Sizing (advisory lots) ----
        position_size = None
        if final_signal in (TradingSignal.BUY, TradingSignal.SELL) and stop_loss:
            position_size = self.pt_service.calculate_position_size(
                entry=price,
                stop_loss=stop_loss,
                risk_pct=1.0  # 1% default risk
            )

        # ---- Step 10d: S/R Strength & Fake Breakout Detection ----
        candles_1h = candles_dict.get("1h", []) if candles_dict else []
        sr_strengths = self._calculate_sr_strengths(all_supports + all_resistances, candles_1h)
        fake_breakout, breakout_details = self._detect_fake_breakout(price, all_supports, all_resistances, candles_1h)

        if fake_breakout and breakout_details:
            warnings.append(breakout_details)

        # pt_stats and pt_history will be calculated at the end of the evaluation.

        # ---- Step 10f: Calculate Confluence metrics & Directional Scores ----
        target_sign = 1 if (final_signal == TradingSignal.BUY or (final_signal == TradingSignal.WAIT and total_score >= 0)) else -1
        confluence_direction = "Bullish" if target_sign == 1 else "Bearish"
        
        agree_count = 0
        total_techs = 0
        for c in components:
            total_techs += 1
            if target_sign == 1 and c.raw_score > 0:
                agree_count += 1
            elif target_sign == -1 and c.raw_score < 0:
                agree_count += 1
                
        confluence_pct = int(agree_count / total_techs * 100) if total_techs > 0 else 50
        
        tf_aligned_count = 0
        tf_total = 0
        for tf_name in ["5m", "15m", "1h", "1d"]:
            ta_item = tf.get(tf_name)
            if ta_item:
                tf_total += 1
                if target_sign == 1 and ta_item.trend.direction == TrendDirection.BULLISH:
                    tf_aligned_count += 1
                elif target_sign == -1 and ta_item.trend.direction == TrendDirection.BEARISH:
                    tf_aligned_count += 1
                    
        mtf_confluence_pct = int(tf_aligned_count / tf_total * 100) if tf_total > 0 else 50
        mtf_alignment_summary = f"{tf_aligned_count}/{tf_total} TF aligned"

        # ---- Step 10g: 17-Contributor Confluence Engine ----
        # Build a synchronized snapshot from the existing data (no new data fetches)
        confluence_snapshot = self.confluence_engine.build_snapshot(
            mtf_input=mtf_input,
            ai_result=ai_result,
            candles_dict=candles_dict,
        )
        # Attach already-computed SMC/Elliott results to avoid redundant calculation
        confluence_snapshot.smc_trend = smc_trend
        confluence_snapshot.smc_liquidity = smc_liquidity
        confluence_snapshot.smc_mss = smc_mss
        confluence_snapshot.smc_fib = smc_fib
        confluence_snapshot.smc_fvg = smc_fvg
        confluence_snapshot.elliott_result = elliott_res

        confluence_result = self.confluence_engine.compute(confluence_snapshot)

        # Map ConfluenceResult contributors to the existing dict format expected by frontend
        contributors: List[dict] = []
        for c_state in confluence_result.contributors:
            contributor_dict = {
                "name": c_state.name,
                "points": c_state.score,
                "prev_points": c_state.prev_score,
                "description": c_state.evidence[0] if c_state.evidence else c_state.bias,
                "direction": c_state.direction,
                "last_changed_at": c_state.last_changed_at,
                "bias": c_state.bias,
                "status": c_state.status,
                "timeframe": c_state.timeframe,
                "evidence": c_state.evidence,
                "conflicts": c_state.conflicts,
                "max_score": c_state.max_score,
                "snapshot_id": c_state.snapshot_id,
                "data_freshness": c_state.data_freshness,
            }
            contributors.append(contributor_dict)

        # Sort by most recently changed first (keeps UI consistent with prior behaviour)
        contributors.sort(key=lambda x: x.get("last_changed_at", ""), reverse=True)

        # Map confluence signal/scores to the existing final_signal / buy_score / sell_score
        c_signal = confluence_result.signal
        final_score_100 = confluence_result.final_score
        gate_dir = confluence_result.gate_direction

        # Derive legacy scores from 100pt model
        if c_signal == "BUY":
            final_signal = TradingSignal.BUY
            signal_candidate = "BUY"
            buy_score = final_score_100
            sell_score = max(10, 100 - final_score_100)
            signal_strength = final_score_100
            confluence_direction = "Bullish"
            confluence_pct = final_score_100
            trend = DecisionTrend.BULLISH
        elif c_signal == "SELL":
            final_signal = TradingSignal.SELL
            signal_candidate = "SELL"
            sell_score = final_score_100
            buy_score = max(10, 100 - final_score_100)
            signal_strength = final_score_100
            confluence_direction = "Bearish"
            confluence_pct = final_score_100
            trend = DecisionTrend.BEARISH
        else:
            # WAIT — keep existing trend from score calculation above
            buy_score = max(10, final_score_100 if gate_dir == "BULLISH" else 30)
            sell_score = max(10, final_score_100 if gate_dir == "BEARISH" else 30)
            signal_strength = final_score_100
            confluence_pct = final_score_100

        buy_score = max(0, min(100, buy_score))
        sell_score = max(0, min(100, sell_score))

        # Ensure valid ATR for exact levels
        safe_atr = atr_value if (atr_value and atr_value > 0) else max(2.5, price * 0.0035)

        # If initial evaluation was WAIT, check if signal_strength >= bypass_threshold (60%) to bypass.
        # Otherwise retain the valid BUY or SELL initial signal from the confluence engine.
        if initial_final_signal == TradingSignal.WAIT:
            if signal_strength >= self.bypass_threshold and final_signal in (TradingSignal.BUY, TradingSignal.SELL):
                pass  # confluence engine already set final_signal to BUY or SELL
            else:
                final_signal = TradingSignal.WAIT
        else:
            final_signal = initial_final_signal

        # ---- Step 10g.1: Validated Empirical Signal Quality Gates (BTC & XAU Separated) ----
        if final_signal in (TradingSignal.BUY, TradingSignal.SELL):
            sym_str = (mtf_input.symbol or "").upper()
            is_btc = "BTC" in sym_str
            is_xau = "XAU" in sym_str or "GOLD" in sym_str

            def _get_contrib_bias(contrib) -> str:
                if not contrib:
                    return "NEUTRAL"
                b = getattr(contrib, "bias", "")
                if b in ("BULLISH", "BEARISH", "NEUTRAL"):
                    return b
                d = getattr(contrib, "direction", "")
                if d in ("BULLISH", "BEARISH", "NEUTRAL"):
                    return d
                return "NEUTRAL"

            mtf_contrib = next((c for c in confluence_result.contributors if getattr(c, "name", "") == "MTF Alignment"), None)
            vwap_contrib = next((c for c in confluence_result.contributors if getattr(c, "name", "") == "VWAP"), None)
            vol_contrib = next((c for c in confluence_result.contributors if getattr(c, "name", "") == "Volume Confirmation"), None)
            mom_contrib = next((c for c in confluence_result.contributors if getattr(c, "name", "") == "Momentum"), None)

            expected_bias = "BULLISH" if final_signal == TradingSignal.BUY else "BEARISH"
            mtf_aligned = (_get_contrib_bias(mtf_contrib) == expected_bias)
            vwap_aligned = (_get_contrib_bias(vwap_contrib) == expected_bias)

            # Detect UTC session
            utc_hour = datetime.now(timezone.utc).hour
            is_asia = (0 <= utc_hour < 7)

            if is_btc:
                # BTC Gate 1: Minimum validated confluence score 58%
                if signal_strength < 58:
                    final_signal = TradingSignal.WAIT
                    wait_overrides.append(f"BTC Quality Gate: Confluence score ({signal_strength}%) below minimum validated threshold (58%).")
                # BTC Gate 2: Multi-timeframe alignment required
                elif not mtf_aligned:
                    final_signal = TradingSignal.WAIT
                    wait_overrides.append(f"BTC Quality Gate: MTF Alignment not aligned with {final_signal.value} direction.")
                # BTC Gate 3: Exclude unconfirmed Asia session BUYs
                elif final_signal == TradingSignal.BUY and is_asia:
                    vol_bullish = (_get_contrib_bias(vol_contrib) == "BULLISH")
                    mom_bullish = (_get_contrib_bias(mom_contrib) == "BULLISH")
                    if not (vol_bullish or (mom_bullish and signal_strength >= 65)):
                        final_signal = TradingSignal.WAIT
                        wait_overrides.append("BTC Quality Gate: Unconfirmed Asia session BUY rejected (requires Volume or high-momentum confirmation).")

            elif is_xau:
                # XAU Gate 1: Minimum validated confluence score 58%
                if signal_strength < 58:
                    final_signal = TradingSignal.WAIT
                    wait_overrides.append(f"XAU Quality Gate: Confluence score ({signal_strength}%) below minimum validated threshold (58%).")
                # XAU Gate 2: Multi-timeframe alignment required
                elif not mtf_aligned:
                    final_signal = TradingSignal.WAIT
                    wait_overrides.append(f"XAU Quality Gate: MTF Alignment not aligned with {final_signal.value} direction.")
                # XAU Gate 3: VWAP directional alignment required
                elif not vwap_aligned:
                    final_signal = TradingSignal.WAIT
                    wait_overrides.append(f"XAU Quality Gate: VWAP position not aligned with {final_signal.value} direction.")

        # Calculate full institutional Trade Setup Matrix levels
        if final_signal == TradingSignal.BUY:
            entry_min = round(price - safe_atr * 0.35, 2)
            entry_max = round(price, 2)
            entry_zone = EntryZone(min=entry_min, max=entry_max)
            stop_loss = round(price - safe_atr * 1.5, 2)
            tp1 = round(price + safe_atr * 2.4, 2)
            tp2 = round(price + safe_atr * 4.2, 2)
            rr_tp1 = 1.6
            rr_tp2 = 2.8
            position_size = 0.10
            setup_grade = "A+" if signal_strength >= 75 else "A"
            risk_level = DecisionRiskLevel.LOW
            blended_confidence = signal_strength
        elif final_signal == TradingSignal.SELL:
            entry_min = round(price, 2)
            entry_max = round(price + safe_atr * 0.35, 2)
            entry_zone = EntryZone(min=entry_min, max=entry_max)
            stop_loss = round(price + safe_atr * 1.5, 2)
            tp1 = round(price - safe_atr * 2.4, 2)
            tp2 = round(price - safe_atr * 4.2, 2)
            rr_tp1 = 1.6
            rr_tp2 = 2.8
            position_size = 0.10
            setup_grade = "A+" if signal_strength >= 75 else "A"
            risk_level = DecisionRiskLevel.LOW
            blended_confidence = signal_strength
        else:
            entry_zone = None
            stop_loss = None
            tp1 = None
            tp2 = None
            rr_tp1 = None
            rr_tp2 = None
            position_size = None
            setup_grade = "C"
            risk_level = DecisionRiskLevel.LOW
            blended_confidence = signal_strength

        # ---- Step 10h: Liquidity Range & True Sweep Status ----
        pdh_val = round(smc_liquidity.prev_day_high, 2) if smc_liquidity and smc_liquidity.prev_day_high else None
        pdl_val = round(smc_liquidity.prev_day_low, 2) if smc_liquidity and smc_liquidity.prev_day_low else None
        
        is_true_sweep = bool(smc_liquidity and smc_liquidity.passed and smc_liquidity.sweep_direction != SweepDirection.NONE)
        
        if is_true_sweep:
            if smc_liquidity.sweep_direction == SweepDirection.BEARISH:
                liq_status = "PDH_SWEPT"
                liq_detail = f"PDH Liquidity Swept (${pdh_val:.2f})" if pdh_val else "PDH Liquidity Swept"
            else:
                liq_status = "PDL_SWEPT"
                liq_detail = f"PDL Liquidity Swept (${pdl_val:.2f})" if pdl_val else "PDL Liquidity Swept"
        elif pdh_val and pdl_val:
            if price > pdh_val:
                liq_status = "ABOVE_PDH"
                liq_detail = f"Price trading above PDH (${pdh_val:.2f})"
            elif price < pdl_val:
                liq_status = "BELOW_PDL"
                liq_detail = f"Price trading below PDL (${pdl_val:.2f})"
            else:
                liq_status = "INSIDE_RANGE"
                liq_detail = f"Price inside PDH/PDL range (${pdl_val:.2f} - ${pdh_val:.2f})"
        else:
            liq_status = "INSIDE_RANGE"
            liq_detail = "Price inside standard daily range"

        # ---- Step 10e: Paper Trading Log Position & Get Stats ----
        if final_signal in (TradingSignal.BUY, TradingSignal.SELL) and stop_loss and tp1 and tp2:
            self.pt_service.log_new_signal(
                direction=final_signal.value,
                current_price=price,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                position_size=position_size or 0.1,
                setup_grade=setup_grade,
            )
        pt_stats, pt_history = self.pt_service.update_and_get_stats(price)

        # ---- Build output models ----
        now_iso = datetime.now(timezone.utc).isoformat()

        decision = TradingDecision(
            symbol=mtf_input.symbol or "XAU/USD",
            decision=final_signal,
            confidence=blended_confidence,
            signal_strength=signal_strength,
            buy_score=buy_score,
            sell_score=sell_score,
            signal_contributors=contributors,
            pdh=pdh_val,
            pdl=pdl_val,
            liquidity_status=liq_status,
            sweep_detected=is_true_sweep,
            sweep_detail=liq_detail,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_reward_tp1=rr_tp1,
            risk_reward_tp2=rr_tp2,
            trend=trend,
            risk_level=risk_level,
            composite_score=round(total_score, 4),
            reasons=reasons,
            warnings=warnings,
            invalid_if=invalid_if,
            timestamp=now_iso,
            ai_provider_used=ai_result.provider_used,
            position_size=position_size,
            setup_grade=setup_grade,
            agreement_score=agreement_score,
            confluence_pct=confluence_pct,
            confluence_direction=confluence_direction,
            mtf_confluence_pct=mtf_confluence_pct,
            mtf_alignment_summary=mtf_alignment_summary,
            fake_breakout_detected=fake_breakout,
            fake_breakout_details=breakout_details,
            support_resistance_strengths=sr_strengths,
            paper_trading_stats=pt_stats,
            trade_history=pt_history,
            # Confluence Engine extended fields
            snapshot_id=confluence_result.snapshot_id,
            technical_score=confluence_result.technical_score,
            gemini_score=confluence_result.gemini_score,
            final_confluence=confluence_result.final_score,
            data_quality=confluence_result.data_quality,
            data_completeness=confluence_result.data_completeness,
            market_regime=confluence_result.market_regime,
            conflicts=confluence_result.conflicts if confluence_result.conflicts else None,
            top_confirmations=confluence_result.top_confirmations if confluence_result.top_confirmations else None,
            entry_quality=confluence_result.entry_quality,
            invalidation_conditions=invalid_if if invalid_if else None,
            spread_status=confluence_result.spread_status,
            news_status=confluence_result.news_status,
            gate_direction=confluence_result.gate_direction,
            gate_passed=confluence_result.gate_passed,
        )

        breakdown = DecisionScoreBreakdown(
            symbol=mtf_input.symbol or "XAU/USD",
            timestamp=now_iso,
            total_score=round(total_score, 4),
            signal_candidate=signal_candidate,
            final_signal=final_signal,
            confidence=decision.confidence,
            components=components,
            wait_overrides_triggered=wait_overrides,
            weight_sum=round(weight_sum, 4),
        )

        return decision, breakdown

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_trend(
        self,
        ta: Optional[TechnicalAnalysisResponse],
        label: str,
        weight: float,
    ) -> ScoreComponent:
        """Convert a timeframe's TrendAnalysis into a weighted score component."""
        if ta is None:
            return ScoreComponent(
                name=label, weight=weight, raw_score=0.0, weighted_score=0.0,
                reasoning="No data available for this timeframe"
            )
        direction = ta.trend.direction
        strength = ta.trend.strength
        score_map = {
            TrendDirection.BULLISH: {"STRONG": 1.0, "MODERATE": 0.65, "WEAK": 0.30},
            TrendDirection.BEARISH: {"STRONG": -1.0, "MODERATE": -0.65, "WEAK": -0.30},
            TrendDirection.SIDEWAYS: {"STRONG": 0.0, "MODERATE": 0.0, "WEAK": 0.0},
        }
        raw = score_map.get(direction, {}).get(strength, 0.0)
        reasoning = (
            f"{direction.value} trend ({strength}) — score {raw:+.2f}. "
            f"Confirmations: {', '.join(ta.trend.confirmations[:3]) if ta.trend.confirmations else 'none'}"
        )
        return ScoreComponent(
            name=label, weight=weight, raw_score=raw,
            weighted_score=round(raw * weight, 5), reasoning=reasoning
        )

    def _score_5m_momentum(
        self,
        ta: Optional[TechnicalAnalysisResponse],
        weight: float,
    ) -> ScoreComponent:
        """Score 5m momentum using trend score + MACD histogram sign."""
        label = "5m Momentum"
        if ta is None:
            return ScoreComponent(
                name=label, weight=weight, raw_score=0.0, weighted_score=0.0,
                reasoning="5m data unavailable"
            )
        trend_raw = {"BULLISH": 0.6, "BEARISH": -0.6, "SIDEWAYS": 0.0}.get(
            ta.trend.direction.value, 0.0
        )
        macd_bonus = 0.0
        macd_note = ""
        if ta.macd and ta.macd.histogram is not None:
            macd_bonus = 0.4 if ta.macd.histogram > 0 else (-0.4 if ta.macd.histogram < 0 else 0.0)
            macd_note = f" MACD histogram {ta.macd.histogram:+.4f} adds {macd_bonus:+.2f}."
        raw = max(-1.0, min(1.0, trend_raw + macd_bonus))
        reasoning = (
            f"5m: {ta.trend.direction.value} ({ta.trend.strength}), "
            f"trend contributes {trend_raw:+.2f}.{macd_note}"
        )
        return ScoreComponent(
            name=label, weight=weight, raw_score=round(raw, 4),
            weighted_score=round(raw * weight, 5), reasoning=reasoning
        )

    def _score_macd(
        self,
        tf: dict,
        weight: float,
    ) -> ScoreComponent:
        """Aggregate MACD state across 15m and 1h timeframes."""
        label = "MACD"
        votes = []
        notes = []
        for tf_key in ("15m", "1h"):
            ta = tf.get(tf_key)
            if ta and ta.macd:
                state = ta.macd.state
                if state == MACDState.BULLISH:
                    votes.append(1.0)
                    notes.append(f"{tf_key}: BULLISH")
                elif state == MACDState.BEARISH:
                    votes.append(-1.0)
                    notes.append(f"{tf_key}: BEARISH")
                else:
                    votes.append(0.0)
                    notes.append(f"{tf_key}: NEUTRAL")

        raw = sum(votes) / len(votes) if votes else 0.0
        reasoning = (
            f"MACD across {', '.join(notes) if notes else 'no data'}. "
            f"Average: {raw:+.2f}"
        )
        return ScoreComponent(
            name=label, weight=weight, raw_score=round(raw, 4),
            weighted_score=round(raw * weight, 5), reasoning=reasoning
        )

    def _score_rsi(self, tf: dict, weight: float) -> ScoreComponent:
        """Score RSI — overbought/oversold adds mild contrary pressure, neutral is zero."""
        label = "RSI"
        ta_1h = tf.get("1h") or tf.get("15m")
        if ta_1h is None or ta_1h.rsi14 is None or ta_1h.rsi14.value is None:
            return ScoreComponent(
                name=label, weight=weight, raw_score=0.0, weighted_score=0.0,
                reasoning="RSI data unavailable"
            )
        rsi_val = ta_1h.rsi14.value
        condition = ta_1h.rsi14.condition
        # Overbought: mild bearish pressure; Oversold: mild bullish pressure; Neutral: no signal
        if condition == RSICondition.OVERBOUGHT:
            raw = -0.5
            note = f"RSI {rsi_val:.1f} — OVERBOUGHT (mild bearish pressure, not a reversal signal)"
        elif condition == RSICondition.OVERSOLD:
            raw = 0.5
            note = f"RSI {rsi_val:.1f} — OVERSOLD (mild bullish pressure, not a reversal signal)"
        else:
            raw = 0.0
            note = f"RSI {rsi_val:.1f} — NEUTRAL (no RSI pressure)"
        return ScoreComponent(
            name=label, weight=weight, raw_score=raw,
            weighted_score=round(raw * weight, 5), reasoning=note
        )

    def _score_ema(
        self,
        tf: dict,
        price: float,
        weight: float,
    ) -> ScoreComponent:
        """Score EMA stack alignment: price vs EMA20, EMA50, EMA200 on 1h."""
        label = "EMA Structure"
        ta = tf.get("1h") or tf.get("15m")
        if ta is None:
            return ScoreComponent(
                name=label, weight=weight, raw_score=0.0, weighted_score=0.0,
                reasoning="EMA data unavailable"
            )
        e20, e50, e200 = ta.ema20, ta.ema50, ta.ema200
        bullish_checks = 0
        bearish_checks = 0
        total_checks = 0
        notes = []

        if e20 is not None:
            total_checks += 1
            if price > e20:
                bullish_checks += 1
                notes.append(f"Price > EMA20 ({e20:.1f})")
            else:
                bearish_checks += 1
                notes.append(f"Price < EMA20 ({e20:.1f})")
        if e50 is not None:
            total_checks += 1
            if price > e50:
                bullish_checks += 1
                notes.append(f"Price > EMA50 ({e50:.1f})")
            else:
                bearish_checks += 1
                notes.append(f"Price < EMA50 ({e50:.1f})")
        if e200 is not None:
            total_checks += 1
            if price > e200:
                bullish_checks += 1
                notes.append(f"Price > EMA200 ({e200:.1f})")
            else:
                bearish_checks += 1
                notes.append(f"Price < EMA200 ({e200:.1f})")

        if total_checks == 0:
            return ScoreComponent(
                name=label, weight=weight, raw_score=0.0, weighted_score=0.0,
                reasoning="No EMA values computed"
            )

        raw = (bullish_checks - bearish_checks) / total_checks
        reasoning = f"EMA structure ({', '.join(notes)}). Score: {raw:+.2f}"
        return ScoreComponent(
            name=label, weight=weight, raw_score=round(raw, 4),
            weighted_score=round(raw * weight, 5), reasoning=reasoning
        )

    def _score_gemini(self, ai: AIAnalysisResponse, weight: float) -> ScoreComponent:
        """Convert Gemini's overall bias + confidence into a mild scoring contribution."""
        label = "Gemini AI Bias"
        bias_map = {OverallBias.BULLISH: 1.0, OverallBias.BEARISH: -1.0, OverallBias.NEUTRAL: 0.0}
        raw_bias = bias_map.get(ai.overall_bias, 0.0)
        # Scale by confidence (0-100 → 0-1) and cap contribution
        confidence_scale = ai.confidence / 100.0
        raw = raw_bias * confidence_scale
        raw = max(-1.0, min(1.0, raw))
        provider_note = " (fallback heuristic)" if ai.is_fallback else f" ({ai.provider_used})"
        reasoning = (
            f"Gemini bias: {ai.overall_bias.value} (confidence {ai.confidence}%){provider_note}. "
            f"Contribution: {raw:+.3f}"
        )
        return ScoreComponent(
            name=label, weight=weight, raw_score=round(raw, 4),
            weighted_score=round(raw * weight, 5), reasoning=reasoning
        )

    # ------------------------------------------------------------------
    # Level calculation helpers
    # ------------------------------------------------------------------

    def _calculate_levels(
        self,
        signal: str,
        price: float,
        supports: List[float],
        resistances: List[float],
        atr: float,
    ) -> Tuple[Optional[EntryZone], Optional[float], Optional[float], Optional[float]]:
        """
        Compute entry zone, stop-loss, TP1, TP2 for BUY or SELL.
        Returns (entry_zone, stop_loss, tp1, tp2).
        """
        if signal == "BUY":
            # Entry zone: nearest support below → current price
            supports_below = [s for s in supports if s < price]
            nearest_sup = max(supports_below) if supports_below else price * 0.9985
            entry_min = round(nearest_sup, 2)
            entry_max = round(price, 2)
            entry_zone = EntryZone(min=entry_min, max=entry_max)
            entry_mid = (entry_min + entry_max) / 2

            # Stop loss: ATR below entry_mid, but also consider the nearest support buffer
            atr_sl = entry_mid - atr * self.atr_multiplier
            # Don't go higher than 0.3 ATR below the nearest support
            if supports_below:
                support_sl = nearest_sup - atr * 0.3
                stop_loss = round(min(atr_sl, support_sl), 2)
            else:
                stop_loss = round(atr_sl, 2)

            # TP1: first resistance above entry_max
            res_above = [r for r in resistances if r > entry_max * 1.001]
            tp1 = round(min(res_above), 2) if res_above else round(entry_mid + atr * 2.0, 2)

            # TP2: second resistance, or TP1 + 1×risk
            risk = abs(entry_mid - stop_loss)
            if len(res_above) >= 2:
                sorted_res = sorted(res_above)
                tp2 = round(sorted_res[1], 2)
            else:
                tp2 = round(tp1 + risk, 2)

            return entry_zone, stop_loss, tp1, tp2

        elif signal == "SELL":
            # Entry zone: current price → nearest resistance above
            res_above = [r for r in resistances if r > price]
            nearest_res = min(res_above) if res_above else price * 1.0015
            entry_min = round(price, 2)
            entry_max = round(nearest_res, 2)
            entry_zone = EntryZone(min=entry_min, max=entry_max)
            entry_mid = (entry_min + entry_max) / 2

            # Stop loss: ATR above entry_mid
            atr_sl = entry_mid + atr * self.atr_multiplier
            if res_above:
                resistance_sl = nearest_res + atr * 0.3
                stop_loss = round(max(atr_sl, resistance_sl), 2)
            else:
                stop_loss = round(atr_sl, 2)

            # TP1: first support below entry_min
            sups_below = [s for s in supports if s < entry_min * 0.999]
            tp1 = round(max(sups_below), 2) if sups_below else round(entry_mid - atr * 2.0, 2)

            # TP2: second support below, or TP1 − 1×risk
            risk = abs(entry_mid - stop_loss)
            if len(sups_below) >= 2:
                sorted_sups = sorted(sups_below, reverse=True)
                tp2 = round(sorted_sups[1], 2)
            else:
                tp2 = round(tp1 - risk, 2)

            return entry_zone, stop_loss, tp1, tp2

        return None, None, None, None

    # ------------------------------------------------------------------
    # Narrative builders
    # ------------------------------------------------------------------

    def _build_narrative(
        self,
        signal: TradingSignal,
        components: List[ScoreComponent],
        ai_result: AIAnalysisResponse,
        price: float,
        tf: dict,
        all_supports: List[float],
        all_resistances: List[float],
        atr_value: Optional[float],
    ) -> Tuple[List[str], List[str], List[str]]:
        """Build human-readable reasons, warnings, and invalid_if lists."""
        reasons = []
        warnings = []
        invalid_if = []

        # Sort components by absolute weighted score contribution
        sorted_comps = sorted(components, key=lambda x: abs(x.weighted_score), reverse=True)
        # Take up to 4 significant components
        sig_comps = [c for c in sorted_comps if abs(c.weighted_score) >= 0.02][:4]
        
        for c in sig_comps:
            clean_reason = c.reasoning.split(".")[0].split("—")[0].strip()
            reasons.append(f"{c.name}: {clean_reason}")

        # Add AI summary
        reasons.append(f"AI Bias: {ai_result.overall_bias.value} ({ai_result.confidence}% confidence)")

        if signal == TradingSignal.WAIT:
            reasons.insert(0, "Market structure conflict or flat trend")


        # Warnings
        ta_1d = tf.get("1d")
        if ta_1d and ta_1d.rsi14 and ta_1d.rsi14.condition == RSICondition.OVERBOUGHT:
            warnings.append(f"Daily RSI is OVERBOUGHT ({ta_1d.rsi14.value:.1f}) — elevated pullback risk")
        if ta_1d and ta_1d.rsi14 and ta_1d.rsi14.condition == RSICondition.OVERSOLD:
            warnings.append(f"Daily RSI is OVERSOLD ({ta_1d.rsi14.value:.1f}) — elevated bounce risk")
        if ai_result.is_fallback:
            warnings.append("AI analysis used the built-in deterministic fallback engine (no Gemini key)")
        if ai_result.market_condition in (MarketCondition.HIGH_VOLATILITY,):
            warnings.append("High market volatility detected — risk sizing should be reduced")
        if all_resistances:
            nearest_res = min((r for r in all_resistances if r >= price), default=None)
            if nearest_res and (nearest_res - price) / price < 0.003:
                warnings.append(f"Immediate resistance at ${nearest_res:.2f} — price may face rejection soon")
        for factor in ai_result.key_bearish_factors:
            warnings.append(factor)

        # Invalid if
        ta_15m = tf.get("15m")
        ta_1h = tf.get("1h")
        if signal == TradingSignal.BUY:
            if ta_15m:
                invalid_if.append("15m trend turns BEARISH")
            if ta_1h:
                invalid_if.append("1h trend turns BEARISH")
            if all_supports:
                nearest_sup = max((s for s in all_supports if s <= price), default=None)
                if nearest_sup:
                    invalid_if.append(f"Price closes below key support at ${nearest_sup:.2f}")
            invalid_if.append("Significant bearish news event or macro shock occurs")
        elif signal == TradingSignal.SELL:
            if ta_15m:
                invalid_if.append("15m trend turns BULLISH")
            if ta_1h:
                invalid_if.append("1h trend turns BULLISH")
            if all_resistances:
                nearest_res = min((r for r in all_resistances if r >= price), default=None)
                if nearest_res:
                    invalid_if.append(f"Price closes above key resistance at ${nearest_res:.2f}")
            invalid_if.append("Significant bullish news event or macro shock occurs")

        return reasons, warnings, invalid_if

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _collect_levels(self, tf: dict, level_type: str) -> List[float]:
        """Collect support or resistance levels from all available timeframes."""
        levels = []
        for ta in tf.values():
            if ta is None:
                continue
            if level_type == "support":
                levels.extend(ta.support_levels or [])
            else:
                levels.extend(ta.resistance_levels or [])
        return levels

    def _get_best_atr(self, tf: dict) -> Optional[float]:
        """Get ATR from the best available timeframe (prefer 1h, then 15m, then 5m)."""
        for key in ("1h", "15m", "5m"):
            ta = tf.get(key)
            if ta and ta.atr14 and ta.atr14.value and ta.atr14.value > 0:
                return ta.atr14.value
        return None

    def _determine_trend(self, score: float) -> DecisionTrend:
        if score >= 0.25:
            return DecisionTrend.BULLISH
        elif score <= -0.25:
            return DecisionTrend.BEARISH
        return DecisionTrend.NEUTRAL

    def _determine_risk_level(
        self,
        ai: AIAnalysisResponse,
        atr: Optional[float],
        confidence: int,
    ) -> DecisionRiskLevel:
        if ai.market_condition in (MarketCondition.HIGH_VOLATILITY, MarketCondition.UNCLEAR):
            return DecisionRiskLevel.HIGH
        if confidence < 70 or ai.risk_level.value == "HIGH":
            return DecisionRiskLevel.MEDIUM
        return DecisionRiskLevel.LOW

    def _safe_wait_decision(
        self,
        price: float,
        ai_result: AIAnalysisResponse,
        reason: str,
    ) -> Tuple[TradingDecision, DecisionScoreBreakdown]:
        """Return a safe WAIT decision when evaluation fails."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            pt_stats, pt_history = self.pt_service.update_and_get_stats(price)
        except Exception:
            pt_stats = {
                "starting_balance": 10000.0,
                "current_balance": 10000.0,
                "net_profit": 0.0,
                "total_trades": 0,
                "open_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "equity": 10000.0,
                "unrealized_pnl": 0.0,
            }
            pt_history = []

        decision = TradingDecision(
            symbol="XAU/USD",
            decision=TradingSignal.WAIT,
            confidence=35,
            signal_strength=35,
            buy_score=35,
            sell_score=35,
            signal_contributors=[
                {"name": "Engine Status", "points": 35, "description": "Safe neutral fallback mode active"}
            ],
            pdh=None,
            pdl=None,
            liquidity_status="INSIDE_RANGE",
            sweep_detected=False,
            sweep_detail="Standard range monitoring",
            trend=DecisionTrend.NEUTRAL,
            risk_level=DecisionRiskLevel.HIGH,
            composite_score=0.0,
            reasons=[f"WAIT — evaluation failed: {reason}"],
            warnings=["Decision engine encountered an error. Do not trade on this output."],
            invalid_if=[],
            timestamp=now,
            ai_provider_used=ai_result.provider_used if ai_result else "unknown",
            position_size=0.10,
            setup_grade="C",
            confluence_pct=50,
            confluence_direction="Neutral",
            mtf_confluence_pct=50,
            mtf_alignment_summary="0/4 TF aligned",
            paper_trading_stats=pt_stats,
            trade_history=pt_history,
        )

        breakdown = DecisionScoreBreakdown(
            symbol="XAU/USD",
            timestamp=now,
            total_score=0.0,
            signal_candidate="WAIT",
            final_signal=TradingSignal.WAIT,
            confidence=0,
            components=[],
            wait_overrides_triggered=[reason],
            weight_sum=0.0,
        )
        return decision, breakdown


    def _calculate_sr_strengths(self, levels: List[float], candles: List[Any]) -> Dict[str, int]:
        """Count how many times price has touched each S/R level within 0.15% proximity."""
        strengths = {}
        if not candles:
            return {f"{l:.2f}": 1 for l in levels}
        for l in levels:
            touches = 0
            for c in candles:
                h = getattr(c, "high", getattr(c, "get", lambda x: 0)("high"))
                l_val = getattr(c, "low", getattr(c, "get", lambda x: 0)("low"))
                if h <= 0 or l_val <= 0:
                    try:
                        h = c.high
                        l_val = c.low
                    except Exception:
                        continue
                if abs(h - l) / l <= 0.0015 or abs(l_val - l) / l <= 0.0015:
                    touches += 1
            strengths[f"{l:.2f}"] = max(1, touches)
        return strengths

    def _detect_fake_breakout(self, price: float, supports: List[float], resistances: List[float], candles: List[Any]) -> Tuple[bool, Optional[str]]:
        """Identify recent fake breakouts on the last few candles."""
        if not candles or len(candles) < 5:
            return False, None
        
        recent_candles = candles[-5:]
        for c in recent_candles:
            try:
                o = getattr(c, "open", getattr(c, "get", lambda x: 0)("open"))
                h = getattr(c, "high", getattr(c, "get", lambda x: 0)("high"))
                l_val = getattr(c, "low", getattr(c, "get", lambda x: 0)("low"))
                cl = getattr(c, "close", getattr(c, "get", lambda x: 0)("close"))
                if o <= 0 or h <= 0 or l_val <= 0 or cl <= 0:
                    try:
                        o = c.open
                        h = c.high
                        l_val = c.low
                        cl = c.close
                    except Exception:
                        continue
            except Exception:
                continue
                
            # Bearish Fake Breakout
            for r in resistances:
                if h > r * 1.0002 and cl < r and cl < o:
                    return True, f"Bearish fake breakout detected at resistance ${r:.2f} (wick breached but closed below)"
            
            # Bullish Fake Breakout
            for s in supports:
                if l_val < s * 0.9998 and cl > s and cl > o:
                    return True, f"Bullish fake breakout detected at support ${s:.2f} (wick breached but closed above)"
                    
        return False, None

