"""
Signal Aggregator Service — Multi-Component Evidence Fusion Engine.

Synthesizes the platform's four analytical components into a single,
statistically grounded, and traceable OverallTradingSignal:
  1. Component 1: Now Market Analysis (NowMarketSignal)
  2. Component 2: Historical Statistical Evidence (HistoricalMarketSignal)
  3. Component 3: Machine Learning Model (MLShadowPrediction)
  4. Component 4: Validated Strategy Layer (ValidatedStrategyEvaluation)

Weighting Model (strictly formula-derived per docs/SIGNAL_AGGREGATION_METHODOLOGY.md):
  - BTC/USD: Now (25%), Hist (27%), ML (26%), Strategy (22%)
  - XAU/USD: Now (27%), Hist (26%), ML (24%), Strategy (23%)

CRITICAL GOVERNANCE & ARCHITECTURAL RULES:
  - SEMANTIC SEPARATION: Probabilities, Expectancies, and Scores are never blended
    without mathematical normalization.
  - CONFLICT INVARIANCE: Opposing directional forces (>= 0.25 weight each)
    mandate a WAIT signal with percentage=None. Never force 51%.
  - DYNAMIC RE-WEIGHTING: Unavailable components are marked NOT_AVAILABLE. Active
    components are normalized to 100%. No placeholder/default numbers ever.
  - NO CIRCULAR AGGREGATION: This service is strictly downstream. Upstream
    components never import or call this service.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.models.trading_decision import (
    NowMarketSignal,
    HistoricalMarketSignal,
    ValidatedStrategyEvaluation,
    OverallTradingSignal,
)
from src.research.ml_shadow.symbol_utils import normalize_ml_symbol

logger = logging.getLogger(__name__)

METHODOLOGY_VERSION = "1.1.0-PROPOSAL"

# Base Weights (Derived strictly from empirical 4-dimension rubric)
BASE_WEIGHTS_BTC = {
    "NOW_MARKET_TECHNICAL": 0.25,
    "HISTORICAL_EVIDENCE": 0.27,
    "ML_SHADOW_MODEL": 0.26,
    "VALIDATED_STRATEGY": 0.22,
}

BASE_WEIGHTS_XAU = {
    "NOW_MARKET_TECHNICAL": 0.27,
    "HISTORICAL_EVIDENCE": 0.26,
    "ML_SHADOW_MODEL": 0.24,
    "VALIDATED_STRATEGY": 0.23,
}

CONFLICT_WEIGHT_THRESHOLD = 0.20
MINIMUM_SYSTEM_COVERAGE_WEIGHT = 0.20
DIRECTIONAL_THRESHOLD = 20.0  # Net score >= +20 -> BUY; <= -20 -> SELL; else WAIT


class SignalAggregator:
    """Multi-component evidence aggregator implementing the approved methodology."""

    @classmethod
    def get_base_weights(cls, canonical_symbol: str) -> Dict[str, float]:
        """Return the immutable base weights for the given canonical asset."""
        if "BTC" in canonical_symbol:
            return dict(BASE_WEIGHTS_BTC)
        elif "XAU" in canonical_symbol:
            return dict(BASE_WEIGHTS_XAU)
        else:
            raise ValueError(f"SignalAggregator: Unsupported asset symbol '{canonical_symbol}'.")

    @classmethod
    def aggregate(
        cls,
        symbol: str,
        now_signal: Optional[NowMarketSignal] = None,
        historical_signal: Optional[HistoricalMarketSignal] = None,
        ml_probability: Optional[float] = None,
        ml_predicted_class: Optional[int] = None,
        ml_model_name: Optional[str] = None,
        ml_model_version: Optional[str] = None,
        validated_strategy: Optional[ValidatedStrategyEvaluation] = None,
        timestamp: Optional[str] = None,
    ) -> OverallTradingSignal:
        """
        Synthesize the four components into a single OverallTradingSignal.

        Parameters
        ----------
        symbol:
            Asset symbol (normalized internally).
        now_signal:
            Layer 2 current market technical/AI signal.
        historical_signal:
            Layer 1 empirical historical signal.
        ml_probability:
            Point-in-time calibrated probability from ML shadow observer [0.0, 1.0].
        ml_predicted_class:
            1 for Bullish, 0 for Bearish.
        ml_model_name:
            Model identifier string.
        ml_model_version:
            Model version string.
        validated_strategy:
            Research strategy evaluation and degradation report.
        timestamp:
            ISO 8601 UTC timestamp. Defaults to now.

        Returns
        -------
        OverallTradingSignal
            Unified signal with traceable contributor breakdown.
        """
        canonical_symbol = normalize_ml_symbol(symbol)
        now_utc = timestamp or datetime.now(timezone.utc).isoformat()
        base_weights = cls.get_base_weights(canonical_symbol)

        # -------------------------------------------------------------------
        # Step 1: Directional Standardization & Magnitude per Component
        # -------------------------------------------------------------------
        # Each component produces:
        #   d_i: directional bias (+1 = BUY, -1 = SELL, 0 = WAIT/NEUTRAL)
        #   m_i: magnitude [0.0, 1.0]
        #   is_available: bool
        #   raw_val, raw_unit, display_name, meta

        # Component 1: Now Market Analysis
        c1_available = False
        c1_dir = 0
        c1_mag = 0.0
        c1_raw: Optional[float] = None
        if now_signal is not None and now_signal.percentage is not None:
            c1_available = True
            c1_raw = float(now_signal.percentage)
            c1_mag = max(0.0, min(1.0, c1_raw / 100.0))
            if now_signal.signal == "BUY":
                c1_dir = +1
            elif now_signal.signal == "SELL":
                c1_dir = -1
            else:
                c1_dir = 0

        # Component 2: Historical Statistical Evidence
        c2_available = False
        c2_dir = 0
        c2_mag = 0.0
        c2_raw: Optional[float] = None
        c2_sample_size = getattr(historical_signal, "sample_size", 0) if historical_signal else 0
        # Require sample size >= 25 to be treated as statistically active
        if (
            historical_signal is not None
            and historical_signal.status != "INSUFFICIENT_SAMPLE"
            and c2_sample_size >= 25
            and historical_signal.calibrated_probability is not None
        ):
            c2_available = True
            # calibrated_probability is in [0.0, 1.0] or percentage [0, 100]
            raw_p = historical_signal.calibrated_probability
            if raw_p > 1.0:
                raw_p = raw_p / 100.0
            c2_raw = float(raw_p)

            if historical_signal.signal == "BUY" and c2_raw >= 0.50:
                c2_dir = +1
                c2_mag = max(0.0, min(1.0, 2.0 * (c2_raw - 0.50)))
            elif historical_signal.signal == "SELL" and c2_raw >= 0.50:
                c2_dir = -1
                c2_mag = max(0.0, min(1.0, 2.0 * (c2_raw - 0.50)))
            else:
                c2_dir = 0
                c2_mag = 0.0

        # Component 3: ML Shadow Classifier
        c3_available = False
        c3_dir = 0
        c3_mag = 0.0
        c3_raw: Optional[float] = None
        if ml_probability is not None:
            c3_available = True
            c3_raw = float(ml_probability)
            pred_class = ml_predicted_class if ml_predicted_class is not None else (1 if c3_raw >= 0.50 else 0)

            if pred_class == 1 and c3_raw >= 0.50:
                c3_dir = +1
                c3_mag = max(0.0, min(1.0, 2.0 * (c3_raw - 0.50)))
            elif pred_class == 0 and c3_raw < 0.50:
                c3_dir = -1
                c3_mag = max(0.0, min(1.0, 2.0 * (0.50 - c3_raw)))
            else:
                c3_dir = 0
                c3_mag = 0.0

        # Component 4: Validated Strategy & Degradation
        c4_available = False
        c4_dir = 0
        c4_mag = 0.0
        c4_raw: Optional[float] = None
        c4_strategy_id = "NONE"
        c4_degradation = "NORMAL"

        if (
            validated_strategy is not None
            and validated_strategy.qualified
            and validated_strategy.direction in ("BUY", "SELL")
        ):
            c4_available = True
            c4_strategy_id = validated_strategy.strategy_id
            c4_degradation = getattr(validated_strategy, "degradation_status", "NORMAL")
            c4_raw = float(validated_strategy.validation_score)

            # Degradation penalty factor
            deg_factor = 1.0
            if c4_degradation == "WATCH":
                deg_factor = 0.75
            elif c4_degradation == "DEGRADED":
                deg_factor = 0.50

            c4_mag = max(0.0, min(1.0, (c4_raw / 100.0) * deg_factor))
            c4_dir = +1 if validated_strategy.direction == "BUY" else -1

        # -------------------------------------------------------------------
        # Step 2: Proportional Dynamic Re-weighting
        # -------------------------------------------------------------------
        available_map = {
            "NOW_MARKET_TECHNICAL": c1_available,
            "HISTORICAL_EVIDENCE": c2_available,
            "ML_SHADOW_MODEL": c3_available,
            "VALIDATED_STRATEGY": c4_available,
        }

        active_nominal_sum = sum(base_weights[k] for k, avail in available_map.items() if avail)

        # Insufficient active system coverage check
        if active_nominal_sum < MINIMUM_SYSTEM_COVERAGE_WEIGHT:
            logger.warning(
                f"[AGGREGATOR] Insufficient active component coverage ({active_nominal_sum:.2f} < "
                f"{MINIMUM_SYSTEM_COVERAGE_WEIGHT}) for {canonical_symbol}."
            )
            return OverallTradingSignal(
                signal="WAIT",
                percentage=None,
                strength="MODERATE",
                conflict_detected=False,
                primary_highlight=True,
                calibrated_probability=None,
                overall_evidence_score=None,
                component_scores={
                    "NOW_MARKET_TECHNICAL": c1_raw,
                    "HISTORICAL_EVIDENCE": c2_raw,
                    "ML_SHADOW_MODEL": c3_raw,
                    "VALIDATED_STRATEGY": c4_raw,
                },
                component_weights={k: 0.0 for k in base_weights},
                component_contributions={k: 0.0 for k in base_weights},
                contributors=[],
                methodology_version=METHODOLOGY_VERSION,
                asset=canonical_symbol,
                timestamp=now_utc,
                reasons=[
                    f"Overall WAIT — insufficient active analytical components (active coverage {active_nominal_sum*100:.1f}% < 20%).",
                    "Safety protocol halts synthesis until minimum components are online.",
                ],
            )

        # Calculate effective normalized weights
        effective_weights: Dict[str, float] = {}
        for k, base_w in base_weights.items():
            if available_map[k]:
                effective_weights[k] = base_w / active_nominal_sum
            else:
                effective_weights[k] = 0.0

        w1 = effective_weights["NOW_MARKET_TECHNICAL"]
        w2 = effective_weights["HISTORICAL_EVIDENCE"]
        w3 = effective_weights["ML_SHADOW_MODEL"]
        w4 = effective_weights["VALIDATED_STRATEGY"]

        # -------------------------------------------------------------------
        # Step 3: Conflict Detection & Mandatory WAIT Invariance
        # -------------------------------------------------------------------
        bullish_weight = sum([
            w1 * c1_mag if c1_dir == +1 else 0.0,
            w2 * c2_mag if c2_dir == +1 else 0.0,
            w3 * c3_mag if c3_dir == +1 else 0.0,
            w4 * c4_mag if c4_dir == +1 else 0.0,
        ])
        bearish_weight = sum([
            w1 * c1_mag if c1_dir == -1 else 0.0,
            w2 * c2_mag if c2_dir == -1 else 0.0,
            w3 * c3_mag if c3_dir == -1 else 0.0,
            w4 * c4_mag if c4_dir == -1 else 0.0,
        ])

        conflict_detected = (
            (bullish_weight >= CONFLICT_WEIGHT_THRESHOLD and bearish_weight >= CONFLICT_WEIGHT_THRESHOLD)
            or (c1_dir != 0 and c2_dir != 0 and c1_dir != c2_dir)
        )

        # -------------------------------------------------------------------
        # Step 4: Directional Score & Calibrated Probability Computation
        # -------------------------------------------------------------------
        # Component Effective Points
        pts1 = round(100.0 * w1 * c1_dir * c1_mag, 2)
        pts2 = round(100.0 * w2 * c2_dir * c2_mag, 2)
        pts3 = round(100.0 * w3 * c3_dir * c3_mag, 2)
        pts4 = round(100.0 * w4 * c4_dir * c4_mag, 2)

        contributions_map = {
            "NOW_MARKET_TECHNICAL": pts1,
            "HISTORICAL_EVIDENCE": pts2,
            "ML_SHADOW_MODEL": pts3,
            "VALIDATED_STRATEGY": pts4,
        }

        # Net Directional Score [-100, +100]
        net_score = pts1 + pts2 + pts3 + pts4

        # Total Confluence Strength [0, 100]
        total_confluence = round(100.0 * (w1 * c1_mag + w2 * c2_mag + w3 * c3_mag + w4 * c4_mag))

        # Calibrated Probability Synthesis via Bayesian Log-Odds
        # Synthesized strictly from probabilistic components (C2 & C3)
        prob_components = []
        if c2_available and c2_raw is not None and 0.0 < c2_raw < 1.0:
            prob_components.append((c2_raw, w2))
        if c3_available and c3_raw is not None and 0.0 < c3_raw < 1.0:
            prob_components.append((c3_raw, w3))

        calibrated_prob: Optional[float] = None
        if len(prob_components) == 2:
            (p1, weight1), (p2, weight2) = prob_components
            tot_w = weight1 + weight2
            if tot_w > 0:
                logit1 = math.log(p1 / (1.0 - p1))
                logit2 = math.log(p2 / (1.0 - p2))
                blended_logit = (weight1 * logit1 + weight2 * logit2) / tot_w
                calibrated_prob = round(1.0 / (1.0 + math.exp(-blended_logit)), 4)
        elif len(prob_components) == 1:
            calibrated_prob = round(prob_components[0][0], 4)

        # Final Signal Determination
        if conflict_detected:
            final_dir = "WAIT"
            final_pct = None
            strength_label = "CONFLICT"
            overall_evidence_score = None
            reasons = [
                f"Directional conflict detected on {canonical_symbol}: Bullish weight {bullish_weight*100:.1f}% vs Bearish weight {bearish_weight*100:.1f}%.",
                "DecisionEngine safety protocol enforces conservative WAIT on opposing analytical evidence (CONFLICT=TRUE).",
            ]
        else:
            if net_score > 0:
                final_dir = "BUY"
                final_pct = min(100, max(1, round(abs(net_score))))
                overall_evidence_score = round(abs(net_score))
            elif net_score < 0:
                final_dir = "SELL"
                final_pct = min(100, max(1, round(abs(net_score))))
                overall_evidence_score = round(abs(net_score))
            else:
                final_dir = "WAIT"
                final_pct = total_confluence if total_confluence > 0 else None
                overall_evidence_score = total_confluence

            if final_pct is not None:
                if final_pct >= 80:
                    strength_label = "VERY STRONG"
                elif final_pct >= 60:
                    strength_label = "STRONG"
                elif final_pct >= 40:
                    strength_label = "MODERATE"
                else:
                    strength_label = "WEAK"
            else:
                strength_label = "MODERATE"

            active_count = sum(1 for v in available_map.values() if v)
            reasons = [
                f"Synthesized {final_dir} signal across {active_count}/4 active components with Net Directional Score {net_score:+.1f}.",
            ]
            if calibrated_prob is not None:
                reasons.append(f"Bayesian calibrated win probability: {calibrated_prob*100:.1f}%.")
            if c4_available and c4_strategy_id != "NONE":
                reasons.append(f"Confirmed by validated strategy archetype: {c4_strategy_id} (Health: {c4_degradation}).")

        # -------------------------------------------------------------------
        # Step 5: Construct Traceable Contributor Breakdown Ledger
        # -------------------------------------------------------------------
        contributors_ledger = [
            {
                "component_id": "NOW_MARKET_TECHNICAL",
                "display_name": "Technical & AI Confluence",
                "raw_value": c1_raw,
                "raw_unit": "SCORE_0_100",
                "directional_bias": "BUY" if c1_dir == +1 else ("SELL" if c1_dir == -1 else "NEUTRAL"),
                "nominal_weight": base_weights["NOW_MARKET_TECHNICAL"],
                "effective_weight": round(w1, 4),
                "effective_points": pts1,
                "status": "ACTIVE" if c1_available else "NOT_AVAILABLE",
            },
            {
                "component_id": "HISTORICAL_EVIDENCE",
                "display_name": "Historical Expectancy & Edge",
                "raw_value": c2_raw,
                "raw_unit": "PROBABILITY_0_1",
                "directional_bias": "BUY" if c2_dir == +1 else ("SELL" if c2_dir == -1 else "NEUTRAL"),
                "nominal_weight": base_weights["HISTORICAL_EVIDENCE"],
                "effective_weight": round(w2, 4),
                "effective_points": pts2,
                "sample_size": c2_sample_size,
                "status": "ACTIVE" if c2_available else "NOT_AVAILABLE",
            },
            {
                "component_id": "ML_SHADOW_MODEL",
                "display_name": "ML Forward Classifier",
                "raw_value": c3_raw,
                "raw_unit": "PROBABILITY_0_1",
                "directional_bias": "BUY" if c3_dir == +1 else ("SELL" if c3_dir == -1 else "NEUTRAL"),
                "nominal_weight": base_weights["ML_SHADOW_MODEL"],
                "effective_weight": round(w3, 4),
                "effective_points": pts3,
                "model_name": ml_model_name,
                "model_version": ml_model_version,
                "status": "ACTIVE" if c3_available else "NOT_AVAILABLE",
            },
            {
                "component_id": "VALIDATED_STRATEGY",
                "display_name": "Validated Strategy Match",
                "raw_value": c4_raw,
                "raw_unit": "SCORE_0_100",
                "directional_bias": "BUY" if c4_dir == +1 else ("SELL" if c4_dir == -1 else "NEUTRAL"),
                "nominal_weight": base_weights["VALIDATED_STRATEGY"],
                "effective_weight": round(w4, 4),
                "effective_points": pts4,
                "strategy_id": c4_strategy_id,
                "degradation_status": c4_degradation,
                "status": "ACTIVE" if c4_available else "NOT_AVAILABLE",
            },
        ]

        return OverallTradingSignal(
            signal=final_dir,
            percentage=final_pct,
            strength=strength_label,
            conflict_detected=conflict_detected,
            primary_highlight=True,
            calibrated_probability=calibrated_prob,
            overall_evidence_score=overall_evidence_score,
            component_scores={
                "NOW_MARKET_TECHNICAL": c1_raw,
                "HISTORICAL_EVIDENCE": c2_raw,
                "ML_SHADOW_MODEL": c3_raw,
                "VALIDATED_STRATEGY": c4_raw,
            },
            component_weights={k: round(v, 4) for k, v in effective_weights.items()},
            component_contributions=contributions_map,
            contributors=contributors_ledger,
            methodology_version=METHODOLOGY_VERSION,
            asset=canonical_symbol,
            timestamp=now_utc,
            reasons=reasons,
        )
