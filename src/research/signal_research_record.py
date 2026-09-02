"""
Phase 3 Signal Research Record.

Comprehensive, immutable point-in-time research snapshot for every historical signal
opportunity.  All fields are sealed at signal-generation time (T).  Outcome fields
are populated strictly from future candles (> T).

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Research versioning — bump when schema changes
RESEARCH_VERSION = "3.0"
SCHEMA_VERSION = "3.0"


# ---------------------------------------------------------------------------
# Enum-like constants (plain strings for easy JSON serialisation)
# ---------------------------------------------------------------------------

class SignalDecision:
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    INVALID = "INVALID"


class OpportunityStatus:
    """What happened at an evaluation slot."""
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"          # Engine decided WAIT
    INVALID = "INVALID"    # Data unavailable / engine error
    SKIPPED = "SKIPPED"    # Duplicate / cooldown


class OutcomeLabel:
    WIN = "WIN"
    LOSS = "LOSS"
    EXPIRED = "EXPIRED"
    OPEN = "OPEN"
    INVALID = "INVALID"
    WAIT = "WAIT"          # No trade taken (WAIT signals)


class QualificationStatus:
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AssetClass:
    BTC = "BTC/USD"
    XAU = "XAU/USD"


# ---------------------------------------------------------------------------
# Sub-records (all frozen dataclasses for immutability)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MTFSnapshot:
    """Multi-timeframe alignment state at signal time T."""
    htf_trend: str = "UNKNOWN"       # BULLISH / BEARISH / NEUTRAL
    htf_aligned: bool = False
    mtf_trend: str = "UNKNOWN"       # 1h trend
    mtf_aligned: bool = False
    ltf_trend: str = "UNKNOWN"       # 15m/5m trend
    ltf_aligned: bool = False
    alignment_score: int = 0         # 0-3 (count of aligned TFs)
    alignment_state: str = "UNKNOWN" # FULLY_ALIGNED / PARTIALLY_ALIGNED / CONFLICTING / UNKNOWN


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Point-in-time technical indicator values."""
    rsi_1h: Optional[float] = None
    rsi_15m: Optional[float] = None
    rsi_5m: Optional[float] = None
    macd_histogram_1h: Optional[float] = None
    macd_state_1h: Optional[str] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    ema_aligned: bool = False
    vwap: Optional[float] = None
    vwap_aligned: bool = False
    vwap_state: str = "UNKNOWN"       # ABOVE / BELOW / AT / UNKNOWN
    atr_1h: Optional[float] = None
    support_nearest: Optional[float] = None
    resistance_nearest: Optional[float] = None
    sr_aligned: bool = False
    sr_state: str = "UNKNOWN"
    momentum_direction: str = "UNKNOWN"
    momentum_aligned: bool = False
    volume_relative: Optional[float] = None   # vol / 20-bar avg
    volatility_state: str = "UNKNOWN"         # HIGH / LOW / NORMAL
    market_structure: str = "UNKNOWN"         # HH_HL / LH_LL / RANGING
    ms_aligned: bool = False
    smc_aligned: bool = False
    smc_state: str = "UNKNOWN"
    ict_state: str = "UNKNOWN"
    order_block_type: Optional[str] = None    # BULLISH_OB / BEARISH_OB / NONE
    order_block_level: Optional[float] = None
    liquidity_sweep_detected: bool = False
    liquidity_state: str = "INSIDE_RANGE"


@dataclass(frozen=True)
class StrategyScoreSnapshot:
    """Decomposed strategy score at signal time T."""
    trend_score: int = 0
    momentum_score: int = 0
    sr_score: int = 0
    vwap_score: int = 0
    ema_score: int = 0
    smc_score: int = 0
    ict_score: int = 0
    htf_score: int = 0
    gemini_score: int = 0
    confluence_score: int = 0        # 0-100 final score
    technical_score: int = 0         # 0-90 technical only
    confirmation_score: int = 0      # 0-N (count of confirming factors)
    total_strategy_score: int = 0


@dataclass(frozen=True)
class AISnapshot:
    """AI model output at signal time T — never uses future data."""
    ai_direction: str = "UNKNOWN"       # BUY / SELL / WAIT / NEUTRAL
    ai_probability: float = 0.0         # 0.0 – 1.0 calibrated probability
    ai_confidence: str = "UNKNOWN"      # HIGH / MEDIUM / LOW
    ai_model: str = "UNKNOWN"           # e.g. "gemini-flash"
    ai_model_version: str = "UNKNOWN"
    ai_agrees_with_signal: bool = False
    ai_bias: str = "UNKNOWN"            # BULLISH / BEARISH / NEUTRAL
    input_hash: Optional[str] = None    # SHA256 of AI prompt context (for reproducibility)


@dataclass(frozen=True)
class GatingSnapshot:
    """Hypothetical gating evaluation results for all 5 policies."""
    would_qualify_policy_a: bool = False   # Strict Qualification
    would_qualify_policy_b: bool = False   # Direction Agreement
    would_qualify_policy_c: bool = False   # 3/4 Confirmation
    would_qualify_policy_d: bool = False   # Conflict Filter
    would_qualify_policy_e: bool = False   # Strategy-Specific
    qualification_status: str = QualificationStatus.INSUFFICIENT_DATA
    confirmation_count: int = 0
    conflicts: List[str] = field(default_factory=list)
    strategy_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Main Record
# ---------------------------------------------------------------------------

@dataclass
class SignalResearchRecord:
    """
    Complete Phase 3 research snapshot for one historical signal opportunity.
    Sealed at generation time T; outcome fields populated from future candles > T.
    """

    # --- Identity ---
    signal_id: str = ""
    opportunity_id: str = ""          # Slot identifier (e.g. "BTC_20240115_1030")
    asset: str = ""                   # "BTC/USD" or "XAU/USD"
    signal_timestamp: str = ""        # ISO 8601 UTC — the look-ahead barrier
    research_version: str = RESEARCH_VERSION
    schema_version: str = SCHEMA_VERSION
    dataset_version: str = "v1.0"
    code_version: str = "unknown"

    # --- Market Context (sealed at T) ---
    price: float = 0.0
    regime: str = "UNKNOWN"           # TRENDING / RANGING / HIGH_VOLATILITY / LOW_VOLATILITY
    session: str = "UNKNOWN"          # ASIA / LONDON / NEW_YORK / OVERLAP
    day_of_week: str = "UNKNOWN"      # MON / TUE / WED / THU / FRI
    hour_utc: int = 0
    volatility_state: str = "UNKNOWN"
    market_structure: str = "UNKNOWN"

    # --- Direction ---
    decision: str = SignalDecision.WAIT   # BUY / SELL / WAIT / INVALID
    opportunity_status: str = OpportunityStatus.WAIT

    # --- Entry / Risk (None for WAIT) ---
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    invalidation_level: Optional[float] = None
    risk_r: Optional[float] = None        # |entry - SL|

    # --- MTF ---
    mtf: MTFSnapshot = field(default_factory=MTFSnapshot)

    # --- Indicators ---
    indicators: IndicatorSnapshot = field(default_factory=IndicatorSnapshot)

    # --- Strategy Scores ---
    strategy_scores: StrategyScoreSnapshot = field(default_factory=StrategyScoreSnapshot)

    # --- AI ---
    ai: AISnapshot = field(default_factory=AISnapshot)

    # --- Gating ---
    gating: GatingSnapshot = field(default_factory=GatingSnapshot)

    # --- Outcome (populated strictly from future candles > T) ---
    outcome: str = OutcomeLabel.OPEN
    outcome_timestamp: Optional[str] = None
    exit_price: Optional[float] = None
    realized_r: Optional[float] = None
    mfe_r: Optional[float] = None         # Maximum Favorable Excursion in R
    mae_r: Optional[float] = None         # Maximum Adverse Excursion in R
    max_favorable_price: Optional[float] = None
    max_adverse_price: Optional[float] = None
    bars_to_resolution: Optional[int] = None
    time_to_resolution_minutes: Optional[float] = None
    exit_reason: Optional[str] = None    # "SL_HIT" / "TP1_HIT" / "TP2_HIT" / "EXPIRED"
    ambiguous_candle: bool = False

    # --- Research Classification ---
    failure_reason: Optional[str] = None
    success_reason: Optional[str] = None

    # --- Data Quality ---
    data_quality: str = "HIGH"
    data_completeness_pct: float = 100.0
    is_in_sample: bool = True             # True = 70% train split
    is_holdout: bool = False              # True = untouched holdout
    lookahead_violation: bool = False     # Must be False for valid research

    # --- Metadata ---
    generation_error: Optional[str] = None

    # ---------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serialisable dict."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SignalResearchRecord":
        """Reconstruct from a dict (e.g. loaded from JSON)."""
        # Re-inflate nested dataclasses
        d = dict(d)
        if isinstance(d.get("mtf"), dict):
            d["mtf"] = MTFSnapshot(**d["mtf"])
        if isinstance(d.get("indicators"), dict):
            d["indicators"] = IndicatorSnapshot(**d["indicators"])
        if isinstance(d.get("strategy_scores"), dict):
            d["strategy_scores"] = StrategyScoreSnapshot(**d["strategy_scores"])
        if isinstance(d.get("ai"), dict):
            d["ai"] = AISnapshot(**d["ai"])
        if isinstance(d.get("gating"), dict):
            gating_d = dict(d["gating"])
            if isinstance(gating_d.get("conflicts"), list):
                pass
            d["gating"] = GatingSnapshot(**gating_d)
        return cls(**d)

    def input_fingerprint(self) -> str:
        """
        Deterministic SHA-256 fingerprint of the signal-generation inputs.
        Used by the ExperimentRegistry to detect re-runs.
        """
        key_fields = {
            "signal_id": self.signal_id,
            "asset": self.asset,
            "signal_timestamp": self.signal_timestamp,
            "decision": self.decision,
            "price": self.price,
            "regime": self.regime,
            "session": self.session,
            "confluence_score": self.strategy_scores.confluence_score,
            "ai_probability": self.ai.ai_probability,
            "research_version": self.research_version,
            "dataset_version": self.dataset_version,
        }
        raw = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def is_trade(self) -> bool:
        """True only if a BUY or SELL with valid entry/SL/TP."""
        return (
            self.decision in (SignalDecision.BUY, SignalDecision.SELL)
            and self.entry_price is not None
            and self.stop_loss is not None
            and self.take_profit_1 is not None
        )

    @property
    def is_resolved(self) -> bool:
        return self.outcome in (
            OutcomeLabel.WIN, OutcomeLabel.LOSS, OutcomeLabel.EXPIRED
        )

    @property
    def realized_r_safe(self) -> float:
        """Returns realized_r for metric calculations; 0.0 for unresolved / WAIT."""
        if self.realized_r is not None and self.is_resolved:
            return float(self.realized_r)
        return 0.0


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def build_minimal_record(
    signal_id: str,
    asset: str,
    timestamp: str,
    decision: str,
    price: float,
    regime: str = "UNKNOWN",
    session: str = "UNKNOWN",
    entry_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit_1: Optional[float] = None,
    confluence_score: int = 0,
    ai_probability: float = 0.0,
    dataset_version: str = "v1.0",
) -> SignalResearchRecord:
    """Build a minimal SignalResearchRecord from the most common source fields."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        day_of_week = dt.strftime("%A").upper()[:3]
        hour_utc = dt.hour
    except Exception:
        day_of_week = "UNKNOWN"
        hour_utc = 0

    risk_r: Optional[float] = None
    if entry_price and stop_loss and entry_price != stop_loss:
        risk_r = abs(entry_price - stop_loss)

    scores = StrategyScoreSnapshot(confluence_score=confluence_score)
    ai = AISnapshot(ai_probability=ai_probability)

    return SignalResearchRecord(
        signal_id=signal_id,
        opportunity_id=f"{asset.replace('/', '_')}_{timestamp[:16].replace(':', '').replace('-', '').replace('T', '_')}",
        asset=asset,
        signal_timestamp=timestamp,
        price=price,
        regime=regime,
        session=session,
        day_of_week=day_of_week,
        hour_utc=hour_utc,
        decision=decision,
        opportunity_status=decision,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        risk_r=risk_r,
        strategy_scores=scores,
        ai=ai,
        dataset_version=dataset_version,
    )


def build_from_research_observation(obs: Any, dataset_version: str = "v1.0") -> SignalResearchRecord:
    """
    Build a SignalResearchRecord from a ResearchObservation
    (src.services.stable_expectancy_researcher.ResearchObservation).
    """
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(obs.signal_timestamp.replace("Z", "+00:00"))
        day_of_week = dt.strftime("%A").upper()[:3]
        hour_utc = dt.hour
    except Exception:
        day_of_week = "UNKNOWN"
        hour_utc = 0

    decision = getattr(obs, "direction", "WAIT")

    mtf = MTFSnapshot(
        htf_trend=getattr(obs, "htf_direction", "UNKNOWN"),
        htf_aligned=getattr(obs, "htf_aligned", False),
        mtf_aligned=getattr(obs, "ms_aligned", False),
        ltf_aligned=getattr(obs, "mom_aligned", False),
        alignment_score=sum([
            getattr(obs, "htf_aligned", False),
            getattr(obs, "ms_aligned", False),
            getattr(obs, "mom_aligned", False),
        ]),
    )

    indicators = IndicatorSnapshot(
        vwap_aligned=getattr(obs, "vwap_aligned", False),
        ema_aligned=getattr(obs, "ema_aligned", False),
        sr_aligned=getattr(obs, "sr_aligned", False),
        smc_aligned=getattr(obs, "smc_aligned", False),
        momentum_aligned=getattr(obs, "mom_aligned", False),
        momentum_direction=getattr(obs, "momentum_direction", "UNKNOWN"),
        sr_state=getattr(obs, "sr_direction", "UNKNOWN"),
    )

    conf_count = sum([
        bool(getattr(obs, "htf_aligned", False)),
        bool(getattr(obs, "vwap_aligned", False)),
        bool(getattr(obs, "ema_aligned", False)),
        bool(getattr(obs, "sr_aligned", False)),
        bool(getattr(obs, "smc_aligned", False)),
        bool(getattr(obs, "mom_aligned", False)),
    ])

    scores = StrategyScoreSnapshot(
        confluence_score=getattr(obs, "confluence_score", 0),
        confirmation_score=conf_count,
    )

    ai = AISnapshot(
        ai_probability=getattr(obs, "calibrated_probability", 0.0),
    )

    outcome_map = {
        "WIN": OutcomeLabel.WIN,
        "LOSS": OutcomeLabel.LOSS,
        "EXPIRED": OutcomeLabel.EXPIRED,
    }
    raw_outcome = getattr(obs, "actual_outcome", "OPEN")
    outcome = outcome_map.get(raw_outcome.upper(), OutcomeLabel.OPEN)

    realized_r = getattr(obs, "realized_r", None)
    mfe_r = getattr(obs, "mfe", None)
    mae_r = getattr(obs, "mae", None)

    return SignalResearchRecord(
        signal_id=getattr(obs, "signal_id", ""),
        asset=getattr(obs, "asset", "UNKNOWN"),
        signal_timestamp=getattr(obs, "signal_timestamp", ""),
        price=0.0,  # Not always available in ResearchObservation
        regime=getattr(obs, "market_regime", "UNKNOWN"),
        session=getattr(obs, "session", "UNKNOWN"),
        day_of_week=day_of_week,
        hour_utc=hour_utc,
        volatility_state=getattr(obs, "market_regime", "UNKNOWN"),
        decision=decision,
        opportunity_status=decision,
        mtf=mtf,
        indicators=indicators,
        strategy_scores=scores,
        ai=ai,
        outcome=outcome,
        realized_r=realized_r if outcome != OutcomeLabel.OPEN else None,
        mfe_r=mfe_r,
        mae_r=mae_r,
        time_to_resolution_minutes=getattr(obs, "time_to_outcome_minutes", None),
        dataset_version=dataset_version,
    )
