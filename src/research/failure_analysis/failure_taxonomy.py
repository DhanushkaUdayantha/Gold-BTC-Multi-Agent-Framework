"""
Deterministic Failure & Success Taxonomy Module.

Assigns reproducible, deterministic failure and success classifications
based strictly on point-in-time signal features and outcome metrics.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

FAILURE_TAXONOMY_VERSION = "1.0"


class FailureReason(str, Enum):
    WRONG_DIRECTION = "WRONG_DIRECTION"
    TREND_FAILURE = "TREND_FAILURE"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    MTF_CONFLICT = "MTF_CONFLICT"
    MOMENTUM_FAILURE = "MOMENTUM_FAILURE"
    VWAP_FAILURE = "VWAP_FAILURE"
    EMA_FAILURE = "EMA_FAILURE"
    SUPPORT_FAILURE = "SUPPORT_FAILURE"
    RESISTANCE_FAILURE = "RESISTANCE_FAILURE"
    BREAKOUT_FAILURE = "BREAKOUT_FAILURE"
    FALSE_BREAKOUT = "FALSE_BREAKOUT"
    LIQUIDITY_SWEEP_FAILURE = "LIQUIDITY_SWEEP_FAILURE"
    SMC_FAILURE = "SMC_FAILURE"
    ICT_FAILURE = "ICT_FAILURE"
    LOW_CONFLUENCE = "LOW_CONFLUENCE"
    LOW_CONFIRMATION = "LOW_CONFIRMATION"
    AI_OVERCONFIDENCE = "AI_OVERCONFIDENCE"
    AI_UNDERCONFIDENCE = "AI_UNDERCONFIDENCE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    SESSION_FAILURE = "SESSION_FAILURE"
    NEWS_LIKE_VOLATILITY = "NEWS_LIKE_VOLATILITY"
    ENTRY_TOO_LATE = "ENTRY_TOO_LATE"
    POOR_RISK_REWARD = "POOR_RISK_REWARD"
    EXHAUSTION = "EXHAUSTION"
    RANGE_CHOP = "RANGE_CHOP"
    EXECUTION_SENSITIVITY = "EXECUTION_SENSITIVITY"
    UNKNOWN = "UNKNOWN"


class SuccessReason(str, Enum):
    TREND_ALIGNMENT = "TREND_ALIGNMENT"
    MTF_ALIGNMENT = "MTF_ALIGNMENT"
    MOMENTUM_CONFIRMATION = "MOMENTUM_CONFIRMATION"
    VWAP_CONFIRMATION = "VWAP_CONFIRMATION"
    EMA_ALIGNMENT = "EMA_ALIGNMENT"
    S_R_REACTION = "S_R_REACTION"
    BREAKOUT_CONTINUATION = "BREAKOUT_CONTINUATION"
    SMC_CONFIRMATION = "SMC_CONFIRMATION"
    ICT_CONFIRMATION = "ICT_CONFIRMATION"
    HIGH_AI_PROBABILITY = "HIGH_AI_PROBABILITY"
    HIGH_CONFLUENCE = "HIGH_CONFLUENCE"
    REGIME_ALIGNMENT = "REGIME_ALIGNMENT"
    SESSION_ALIGNMENT = "SESSION_ALIGNMENT"
    MULTI_FACTOR_CONFIRMATION = "MULTI_FACTOR_CONFIRMATION"


@dataclass
class FailureClassification:
    """Classification of a losing trade."""
    primary_reason: FailureReason
    secondary_reasons: List[FailureReason] = field(default_factory=list)
    confidence: str = "HIGH"  # "HIGH", "MEDIUM", "LOW"
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_reason": self.primary_reason.value,
            "secondary_reasons": [r.value for r in self.secondary_reasons],
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class SuccessClassification:
    """Classification of a winning trade."""
    primary_reason: SuccessReason
    secondary_reasons: List[SuccessReason] = field(default_factory=list)
    confidence: str = "HIGH"
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_reason": self.primary_reason.value,
            "secondary_reasons": [r.value for r in self.secondary_reasons],
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


def classify_trade_failure(signal_data: Dict[str, Any]) -> FailureClassification:
    """
    Deterministically classify why a trade resulted in a LOSS.
    """
    evidence: List[str] = []
    secondary: List[FailureReason] = []

    confluence = float(signal_data.get("confluence_score") or signal_data.get("signal_strength") or 50.0)
    regime = str(signal_data.get("market_regime") or signal_data.get("regime") or "UNKNOWN").upper()
    session = str(signal_data.get("session") or "UNKNOWN").upper()
    htf_aligned = signal_data.get("htf_aligned")
    mtf_aligned = signal_data.get("mtf_aligned")
    mae = float(signal_data.get("mae") or 0.0)
    mfe = float(signal_data.get("mfe") or 0.0)
    ai_prob = float(signal_data.get("calibrated_probability") or signal_data.get("ai_probability") or 0.5)

    # 1. MTF / HTF Conflict
    if htf_aligned is False or mtf_aligned is False:
        evidence.append("Higher timeframe or multi-timeframe trend was in opposition to trade direction")
        primary = FailureReason.MTF_CONFLICT
        if "HIGH_VOL" in regime or "VOLATILE" in regime:
            secondary.append(FailureReason.HIGH_VOLATILITY)
        if confluence < 55:
            secondary.append(FailureReason.LOW_CONFLUENCE)
        return FailureClassification(primary, secondary, "HIGH", evidence)

    # 2. False Breakout / Quick Inversion (High MAE with low MFE)
    if mae >= 1.0 and mfe < 0.3:
        evidence.append(f"Immediate adverse excursion (MAE: {mae:.2f}R, MFE: {mfe:.2f}R) without follow-through")
        primary = FailureReason.FALSE_BREAKOUT
        if "CHOP" in regime or "RANGE" in regime:
            secondary.append(FailureReason.RANGE_CHOP)
        return FailureClassification(primary, secondary, "HIGH", evidence)

    # 3. Low Confluence / Low Confirmation
    if confluence < 50.0:
        evidence.append(f"Trade executed with low confluence score ({confluence:.1f} < 50.0)")
        primary = FailureReason.LOW_CONFLUENCE
        if ai_prob < 0.45:
            secondary.append(FailureReason.AI_UNDERCONFIDENCE)
        return FailureClassification(primary, secondary, "HIGH", evidence)

    # 4. Regime Mismatch / Volatility
    if "HIGH_VOL" in regime or "VOLATILE" in regime:
        evidence.append(f"High volatility market regime ({regime}) led to wide adverse swings")
        primary = FailureReason.HIGH_VOLATILITY
        if "ASIA" in session:
            secondary.append(FailureReason.SESSION_FAILURE)
        return FailureClassification(primary, secondary, "HIGH", evidence)

    if "CHOP" in regime or "RANGE" in regime or "LOW_VOL" in regime:
        evidence.append(f"Range chop/compression regime ({regime}) prevented price from reaching TP")
        primary = FailureReason.RANGE_CHOP
        return FailureClassification(primary, secondary, "MEDIUM", evidence)

    # 5. Session Risk
    if "ASIA" in session:
        evidence.append(f"Execution occurred during Asian session ({session}) characterized by low liquidity sweeps")
        primary = FailureReason.SESSION_FAILURE
        return FailureClassification(primary, secondary, "MEDIUM", evidence)

    # 6. Trend Failure / Reversal (Reached >0.8R MFE but reversed to hit SL)
    if mfe >= 0.8:
        evidence.append(f"Trade reached {mfe:.2f}R MFE before suffering sharp reversal to Stop Loss")
        primary = FailureReason.TREND_FAILURE
        secondary.append(FailureReason.EXHAUSTION)
        return FailureClassification(primary, secondary, "HIGH", evidence)

    # Fallback to general WRONG_DIRECTION or UNKNOWN
    if confluence >= 50:
        evidence.append("Normal probabilistic loss against prevailing market structure")
        return FailureClassification(FailureReason.WRONG_DIRECTION, secondary, "MEDIUM", evidence)

    return FailureClassification(FailureReason.UNKNOWN, [], "LOW", ["Insufficient feature evidence to classify failure mechanism"])


def classify_trade_success(signal_data: Dict[str, Any]) -> SuccessClassification:
    """
    Deterministically classify why a trade resulted in a WIN.
    """
    evidence: List[str] = []
    secondary: List[SuccessReason] = []

    confluence = float(signal_data.get("confluence_score") or signal_data.get("signal_strength") or 50.0)
    regime = str(signal_data.get("market_regime") or signal_data.get("regime") or "UNKNOWN").upper()
    htf_aligned = signal_data.get("htf_aligned")
    mtf_aligned = signal_data.get("mtf_aligned")
    ai_prob = float(signal_data.get("calibrated_probability") or signal_data.get("ai_probability") or 0.5)

    if htf_aligned is True and mtf_aligned is True:
        evidence.append("Full multi-timeframe and higher-timeframe trend alignment")
        primary = SuccessReason.MTF_ALIGNMENT
        if confluence >= 65:
            secondary.append(SuccessReason.HIGH_CONFLUENCE)
        return SuccessClassification(primary, secondary, "HIGH", evidence)

    if confluence >= 65.0:
        evidence.append(f"High technical confluence score ({confluence:.1f} >= 65.0)")
        primary = SuccessReason.HIGH_CONFLUENCE
        if ai_prob >= 0.55:
            secondary.append(SuccessReason.HIGH_AI_PROBABILITY)
        return SuccessClassification(primary, secondary, "HIGH", evidence)

    if "TREND" in regime:
        evidence.append(f"Strong directional trend regime ({regime}) supported trade momentum")
        primary = SuccessReason.TREND_ALIGNMENT
        return SuccessClassification(primary, secondary, "MEDIUM", evidence)

    evidence.append("Multi-factor confluence confirmation at execution")
    return SuccessClassification(SuccessReason.MULTI_FACTOR_CONFIRMATION, [], "MEDIUM", evidence)
