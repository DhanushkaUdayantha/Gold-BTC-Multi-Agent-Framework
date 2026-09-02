"""
Phase 3 Failure & Success Analyzer.

Deterministic taxonomy engine for classifying why historical trades won or lost.
Classification is based strictly on point-in-time recorded features and outcome data.
NO LLM labeling.  Every reason is deterministic and explainable.

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Failure Taxonomy  (28 categories)
# ---------------------------------------------------------------------------

class FailureReason(str, Enum):
    WRONG_DIRECTION          = "WRONG_DIRECTION"
    TREND_FAILURE            = "TREND_FAILURE"
    REGIME_MISMATCH          = "REGIME_MISMATCH"
    MTF_CONFLICT             = "MTF_CONFLICT"
    MOMENTUM_FAILURE         = "MOMENTUM_FAILURE"
    VWAP_FAILURE             = "VWAP_FAILURE"
    EMA_FAILURE              = "EMA_FAILURE"
    SUPPORT_FAILURE          = "SUPPORT_FAILURE"
    RESISTANCE_FAILURE       = "RESISTANCE_FAILURE"
    BREAKOUT_FAILURE         = "BREAKOUT_FAILURE"
    FALSE_BREAKOUT           = "FALSE_BREAKOUT"
    LIQUIDITY_SWEEP_FAILURE  = "LIQUIDITY_SWEEP_FAILURE"
    SMC_FAILURE              = "SMC_FAILURE"
    ICT_FAILURE              = "ICT_FAILURE"
    LOW_CONFLUENCE           = "LOW_CONFLUENCE"
    LOW_CONFIRMATION         = "LOW_CONFIRMATION"
    AI_OVERCONFIDENCE        = "AI_OVERCONFIDENCE"
    AI_UNDERCONFIDENCE       = "AI_UNDERCONFIDENCE"
    HIGH_VOLATILITY          = "HIGH_VOLATILITY"
    LOW_VOLATILITY           = "LOW_VOLATILITY"
    SESSION_FAILURE          = "SESSION_FAILURE"
    NEWS_LIKE_VOLATILITY     = "NEWS_LIKE_VOLATILITY"
    ENTRY_TOO_LATE           = "ENTRY_TOO_LATE"
    POOR_RISK_REWARD         = "POOR_RISK_REWARD"
    EXHAUSTION               = "EXHAUSTION"
    RANGE_CHOP               = "RANGE_CHOP"
    EXECUTION_SENSITIVITY    = "EXECUTION_SENSITIVITY"
    UNKNOWN                  = "UNKNOWN"


# ---------------------------------------------------------------------------
# Success Taxonomy  (14 categories)
# ---------------------------------------------------------------------------

class SuccessReason(str, Enum):
    TREND_ALIGNMENT          = "TREND_ALIGNMENT"
    MTF_ALIGNMENT            = "MTF_ALIGNMENT"
    MOMENTUM_CONFIRMATION    = "MOMENTUM_CONFIRMATION"
    VWAP_CONFIRMATION        = "VWAP_CONFIRMATION"
    EMA_ALIGNMENT            = "EMA_ALIGNMENT"
    S_R_REACTION             = "S_R_REACTION"
    BREAKOUT_CONTINUATION    = "BREAKOUT_CONTINUATION"
    SMC_CONFIRMATION         = "SMC_CONFIRMATION"
    ICT_CONFIRMATION         = "ICT_CONFIRMATION"
    HIGH_AI_PROBABILITY      = "HIGH_AI_PROBABILITY"
    HIGH_CONFLUENCE          = "HIGH_CONFLUENCE"
    REGIME_ALIGNMENT         = "REGIME_ALIGNMENT"
    SESSION_ALIGNMENT        = "SESSION_ALIGNMENT"
    MULTI_FACTOR_CONFIRMATION = "MULTI_FACTOR_CONFIRMATION"


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

@dataclass
class FailureClassification:
    primary_reason: FailureReason
    secondary_reasons: List[FailureReason] = field(default_factory=list)
    confidence: str = "HIGH"     # HIGH / MEDIUM / LOW
    evidence: List[str] = field(default_factory=list)


@dataclass
class SuccessClassification:
    primary_reason: SuccessReason
    secondary_reasons: List[SuccessReason] = field(default_factory=list)
    confidence: str = "HIGH"
    evidence: List[str] = field(default_factory=list)


@dataclass
class FailurePatternSummary:
    """Aggregate frequency of failure reasons across a trade cohort."""
    cohort_name: str
    total_losses: int
    reason_counts: Dict[str, int] = field(default_factory=dict)
    reason_pct: Dict[str, float] = field(default_factory=dict)
    top_3_reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Failure Analyzer
# ---------------------------------------------------------------------------

class FailureAnalyzer:
    """
    Deterministic failure classifier.

    Decision tree based on point-in-time features and outcome data.
    Executes every rule in priority order; first match wins the PRIMARY reason,
    subsequent matches become secondary reasons.
    """

    # Probability threshold above which AI is considered "over-confident"
    AI_OVERCONFIDENCE_THRESHOLD = 0.75
    # Probability threshold below which AI is considered "under-confident"
    AI_UNDERCONFIDENCE_THRESHOLD = 0.35
    # Confluence score below which LOW_CONFLUENCE applies
    LOW_CONFLUENCE_THRESHOLD = 60

    @classmethod
    def classify_failure(cls, record: Any) -> FailureClassification:
        """
        Classify the primary failure reason for a losing or expired trade.

        ``record`` should be a SignalResearchRecord (or any duck-typed object
        exposing the same attribute names).
        """
        reasons: List[FailureReason] = []
        evidence: List[str] = []

        # Guard: only classify actual losses / expired
        outcome = getattr(record, "outcome", "LOSS")
        if outcome not in ("LOSS", "EXPIRED"):
            return FailureClassification(
                primary_reason=FailureReason.UNKNOWN,
                confidence="LOW",
                evidence=["Not a loss/expired outcome"],
            )

        indicators = getattr(record, "indicators", None)
        mtf = getattr(record, "mtf", None)
        scores = getattr(record, "strategy_scores", None)
        ai = getattr(record, "ai", None)
        decision = getattr(record, "decision", "WAIT")
        regime = getattr(record, "regime", "UNKNOWN")
        session = getattr(record, "session", "UNKNOWN")
        volatility = getattr(record, "volatility_state", "UNKNOWN")

        # ---- Rule 1: MTF conflict ----
        if mtf is not None and getattr(mtf, "alignment_score", 3) == 0:
            reasons.append(FailureReason.MTF_CONFLICT)
            evidence.append("Zero MTF alignment at signal time")

        # ---- Rule 2: Regime mismatch ----
        if "HIGH_VOL" in regime or "HIGH_VOLATILITY" in regime:
            reasons.append(FailureReason.HIGH_VOLATILITY)
            evidence.append(f"Signal taken in high-volatility regime: {regime}")

        # ---- Rule 3: Volatility low (choppy range) ----
        if "LOW_VOL" in regime or "LOW_VOLATILITY" in regime:
            reasons.append(FailureReason.LOW_VOLATILITY)
            evidence.append(f"Signal taken in low-volatility / ranging regime: {regime}")

        # ---- Rule 4: RANGING regime ----
        if "RANG" in regime:
            reasons.append(FailureReason.RANGE_CHOP)
            evidence.append(f"Ranging regime: {regime}")

        # ---- Rule 5: Trend conflict ----
        if mtf is not None:
            htf_trend = getattr(mtf, "htf_trend", "UNKNOWN")
            if decision == "BUY" and "BEAR" in htf_trend.upper():
                reasons.append(FailureReason.WRONG_DIRECTION)
                evidence.append(f"BUY against HTF bearish trend: {htf_trend}")
            elif decision == "SELL" and "BULL" in htf_trend.upper():
                reasons.append(FailureReason.WRONG_DIRECTION)
                evidence.append(f"SELL against HTF bullish trend: {htf_trend}")

        # ---- Rule 6: VWAP failure ----
        if indicators is not None:
            if not getattr(indicators, "vwap_aligned", True):
                reasons.append(FailureReason.VWAP_FAILURE)
                evidence.append("VWAP not aligned with signal direction")

        # ---- Rule 7: EMA failure ----
        if indicators is not None:
            if not getattr(indicators, "ema_aligned", True):
                reasons.append(FailureReason.EMA_FAILURE)
                evidence.append("EMA not aligned with signal direction")

        # ---- Rule 8: Momentum failure ----
        if indicators is not None:
            if not getattr(indicators, "momentum_aligned", True):
                reasons.append(FailureReason.MOMENTUM_FAILURE)
                evidence.append("Momentum not aligned with signal direction")

        # ---- Rule 9: S/R failure ----
        if indicators is not None:
            if not getattr(indicators, "sr_aligned", True):
                sr_state = getattr(indicators, "sr_state", "UNKNOWN")
                if decision == "BUY":
                    reasons.append(FailureReason.RESISTANCE_FAILURE)
                    evidence.append(f"BUY into resistance: {sr_state}")
                else:
                    reasons.append(FailureReason.SUPPORT_FAILURE)
                    evidence.append(f"SELL into support: {sr_state}")

        # ---- Rule 10: Low confluence ----
        if scores is not None:
            cscore = getattr(scores, "confluence_score", 100)
            if cscore < cls.LOW_CONFLUENCE_THRESHOLD:
                reasons.append(FailureReason.LOW_CONFLUENCE)
                evidence.append(f"Confluence score {cscore} < {cls.LOW_CONFLUENCE_THRESHOLD}")

        # ---- Rule 11: Low confirmation ----
        if scores is not None:
            conf = getattr(scores, "confirmation_score", 10)
            if conf <= 1:
                reasons.append(FailureReason.LOW_CONFIRMATION)
                evidence.append(f"Confirmation score {conf} ≤ 1")

        # ---- Rule 12: AI overconfidence ----
        if ai is not None:
            prob = getattr(ai, "ai_probability", 0.5)
            if prob >= cls.AI_OVERCONFIDENCE_THRESHOLD:
                reasons.append(FailureReason.AI_OVERCONFIDENCE)
                evidence.append(f"AI probability {prob:.2%} ≥ {cls.AI_OVERCONFIDENCE_THRESHOLD:.2%}")

        # ---- Rule 13: SMC / ICT failure ----
        if indicators is not None:
            if not getattr(indicators, "smc_aligned", True):
                reasons.append(FailureReason.SMC_FAILURE)
                evidence.append("SMC not aligned")

        # ---- Rule 14: Session failure ----
        low_liquidity_sessions = {"ASIA"}
        if session.upper() in low_liquidity_sessions:
            reasons.append(FailureReason.SESSION_FAILURE)
            evidence.append(f"Low-liquidity session: {session}")

        # ---- Rule 15: Liquidity sweep mismatch ----
        if indicators is not None:
            if getattr(indicators, "liquidity_sweep_detected", False):
                reasons.append(FailureReason.LIQUIDITY_SWEEP_FAILURE)
                evidence.append("Entered after liquidity sweep (potential false signal)")

        if not reasons:
            return FailureClassification(
                primary_reason=FailureReason.UNKNOWN,
                secondary_reasons=[],
                confidence="LOW",
                evidence=["No deterministic pattern detected from recorded features"],
            )

        primary = reasons[0]
        secondary = list(dict.fromkeys(reasons[1:]))  # deduplicate, preserve order

        confidence = "HIGH" if len(evidence) >= 2 else "MEDIUM" if evidence else "LOW"
        return FailureClassification(
            primary_reason=primary,
            secondary_reasons=secondary,
            confidence=confidence,
            evidence=evidence,
        )


# ---------------------------------------------------------------------------
# Success Analyzer
# ---------------------------------------------------------------------------

class SuccessAnalyzer:
    """Deterministic success classifier for winning trades."""

    AI_HIGH_PROBABILITY_THRESHOLD = 0.60
    HIGH_CONFLUENCE_THRESHOLD = 70

    @classmethod
    def classify_success(cls, record: Any) -> SuccessClassification:
        outcome = getattr(record, "outcome", "WIN")
        if outcome != "WIN":
            return SuccessClassification(
                primary_reason=SuccessReason.MULTI_FACTOR_CONFIRMATION,
                confidence="LOW",
                evidence=["Not a WIN outcome"],
            )

        reasons: List[SuccessReason] = []
        evidence: List[str] = []

        indicators = getattr(record, "indicators", None)
        mtf = getattr(record, "mtf", None)
        scores = getattr(record, "strategy_scores", None)
        ai = getattr(record, "ai", None)
        session = getattr(record, "session", "UNKNOWN")
        regime = getattr(record, "regime", "UNKNOWN")

        # ---- Multi-factor check (shortcut) ----
        alignment_count = 0
        if mtf is not None:
            alignment_count += getattr(mtf, "alignment_score", 0)
        if indicators is not None:
            alignment_count += int(getattr(indicators, "vwap_aligned", False))
            alignment_count += int(getattr(indicators, "ema_aligned", False))
            alignment_count += int(getattr(indicators, "momentum_aligned", False))
            alignment_count += int(getattr(indicators, "sr_aligned", False))

        if alignment_count >= 5:
            reasons.append(SuccessReason.MULTI_FACTOR_CONFIRMATION)
            evidence.append(f"Multi-factor alignment: {alignment_count} indicators aligned")

        # ---- Individual factor checks ----
        if mtf is not None and getattr(mtf, "htf_aligned", False):
            reasons.append(SuccessReason.MTF_ALIGNMENT)
            evidence.append("HTF trend aligned with signal")

        if indicators is not None:
            if getattr(indicators, "vwap_aligned", False):
                reasons.append(SuccessReason.VWAP_CONFIRMATION)
                evidence.append("VWAP confirmed signal direction")

            if getattr(indicators, "ema_aligned", False):
                reasons.append(SuccessReason.EMA_ALIGNMENT)
                evidence.append("EMA stack confirmed direction")

            if getattr(indicators, "momentum_aligned", False):
                reasons.append(SuccessReason.MOMENTUM_CONFIRMATION)
                evidence.append("Momentum confirmed direction")

            if getattr(indicators, "sr_aligned", False):
                reasons.append(SuccessReason.S_R_REACTION)
                evidence.append("S/R reaction at key level")

            if getattr(indicators, "smc_aligned", False):
                reasons.append(SuccessReason.SMC_CONFIRMATION)
                evidence.append("SMC/ICT structure confirmed")

        # ---- Regime alignment ----
        if "TREND" in regime.upper():
            reasons.append(SuccessReason.REGIME_ALIGNMENT)
            evidence.append(f"Trending regime supported direction: {regime}")

        # ---- Session alignment ----
        if session.upper() in {"LONDON", "NEW_YORK", "OVERLAP"}:
            reasons.append(SuccessReason.SESSION_ALIGNMENT)
            evidence.append(f"High-liquidity session: {session}")

        # ---- AI ----
        if ai is not None:
            prob = getattr(ai, "ai_probability", 0.0)
            if prob >= cls.AI_HIGH_PROBABILITY_THRESHOLD:
                reasons.append(SuccessReason.HIGH_AI_PROBABILITY)
                evidence.append(f"High AI probability: {prob:.2%}")

        # ---- Confluence ----
        if scores is not None:
            cscore = getattr(scores, "confluence_score", 0)
            if cscore >= cls.HIGH_CONFLUENCE_THRESHOLD:
                reasons.append(SuccessReason.HIGH_CONFLUENCE)
                evidence.append(f"Confluence score {cscore} ≥ {cls.HIGH_CONFLUENCE_THRESHOLD}")

        if not reasons:
            reasons.append(SuccessReason.MULTI_FACTOR_CONFIRMATION)
            evidence.append("No single dominant factor; combination contributed")

        primary = reasons[0]
        secondary = list(dict.fromkeys(reasons[1:]))
        confidence = "HIGH" if len(evidence) >= 3 else "MEDIUM"
        return SuccessClassification(
            primary_reason=primary,
            secondary_reasons=secondary,
            confidence=confidence,
            evidence=evidence,
        )


# ---------------------------------------------------------------------------
# Failure Pattern Aggregator
# ---------------------------------------------------------------------------

class FailurePatternAggregator:
    """Aggregates failure classifications across a cohort of research records."""

    @staticmethod
    def aggregate(
        records: List[Any],
        cohort_name: str = "ALL",
    ) -> FailurePatternSummary:
        """
        Classify every loss/expired record and produce aggregated frequency table.
        """
        losses = [
            r for r in records
            if getattr(r, "outcome", "") in ("LOSS", "EXPIRED") and getattr(r, "is_trade", True)
        ]
        counts: Dict[str, int] = {}
        for rec in losses:
            fc = FailureAnalyzer.classify_failure(rec)
            key = fc.primary_reason.value
            counts[key] = counts.get(key, 0) + 1

        total = len(losses)
        pct = {k: round(v / total * 100, 1) if total > 0 else 0.0 for k, v in counts.items()}
        sorted_reasons = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top3 = [r[0] for r in sorted_reasons[:3]]

        return FailurePatternSummary(
            cohort_name=cohort_name,
            total_losses=total,
            reason_counts=dict(sorted_reasons),
            reason_pct=pct,
            top_3_reasons=top3,
        )

    @staticmethod
    def aggregate_by_asset(records: List[Any]) -> Dict[str, FailurePatternSummary]:
        """Returns failure pattern summaries keyed by asset."""
        result: Dict[str, FailurePatternSummary] = {}
        assets = set(getattr(r, "asset", "UNKNOWN") for r in records)
        for asset in sorted(assets):
            subset = [r for r in records if getattr(r, "asset", "") == asset]
            result[asset] = FailurePatternAggregator.aggregate(subset, cohort_name=asset)
        return result

    @staticmethod
    def aggregate_by_regime(records: List[Any]) -> Dict[str, FailurePatternSummary]:
        """Returns failure pattern summaries keyed by market regime."""
        result: Dict[str, FailurePatternSummary] = {}
        regimes = set(getattr(r, "regime", "UNKNOWN") for r in records)
        for regime in sorted(regimes):
            subset = [r for r in records if getattr(r, "regime", "") == regime]
            result[regime] = FailurePatternAggregator.aggregate(subset, cohort_name=regime)
        return result

    @staticmethod
    def aggregate_by_session(records: List[Any]) -> Dict[str, FailurePatternSummary]:
        """Returns failure pattern summaries keyed by session."""
        result: Dict[str, FailurePatternSummary] = {}
        sessions = set(getattr(r, "session", "UNKNOWN") for r in records)
        for session in sorted(sessions):
            subset = [r for r in records if getattr(r, "session", "") == session]
            result[session] = FailurePatternAggregator.aggregate(subset, cohort_name=session)
        return result
