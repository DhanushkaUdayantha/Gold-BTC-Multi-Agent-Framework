"""
Authoritative Trade & Outcome Semantics Specification.

Defines exact, deterministic definitions for:
- Signals (BUY, SELL, WAIT)
- Trades (Executed positions with valid entry, SL, TP)
- Outcomes (WIN, LOSS, BREAKEVEN, EXPIRED, INVALID, AMBIGUOUS)
- Realized R (Initial risk unit R = |entry - SL|)
- Ambiguous Candle Resolution Policy (Conservative: never assumes favorable execution)

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class OutcomeStatus(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


class AmbiguousCandleResolution(str, Enum):
    """Conservative policy for resolving candles that touch both TP and SL."""
    WORST_CASE_LOSS = "WORST_CASE_LOSS"      # Assume SL hit first (strictly conservative)
    TREAT_AMBIGUOUS = "TREAT_AMBIGUOUS"      # Mark explicitly as AMBIGUOUS / excluded
    HALF_R_PENALTY = "HALF_R_PENALTY"        # -0.5R haircut


@dataclass(frozen=True)
class AuthoritativeSignal:
    """Timestamped directional output from analysis engine."""
    signal_id: str
    timestamp: str
    symbol: str
    direction: SignalDirection
    probability: float
    entry_price: float
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float] = None
    market_regime: str = "UNKNOWN"
    session: str = "UNKNOWN"
    htf_state: str = "UNKNOWN"
    sr_state: str = "UNKNOWN"
    vwap_state: str = "UNKNOWN"
    ema_state: str = "UNKNOWN"
    strategy_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """A signal is actionable only if direction is BUY or SELL."""
        return self.direction in (SignalDirection.BUY, SignalDirection.SELL)


@dataclass(frozen=True)
class AuthoritativeTrade:
    """An executed trade position derived from an actionable signal."""
    trade_id: str
    signal_id: str
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_timestamp: str
    initial_risk_r: float  # |entry - SL|
    
    def __post_init__(self) -> None:
        if self.direction not in (SignalDirection.BUY, SignalDirection.SELL):
            raise ValueError(f"Trade direction must be BUY or SELL, got {self.direction}")
        if self.initial_risk_r <= 0:
            raise ValueError(f"Initial risk must be positive, got {self.initial_risk_r}")


@dataclass
class TradeOutcomeRecord:
    """Deterministic evaluation of a trade outcome."""
    trade_id: str
    symbol: str
    direction: SignalDirection
    outcome: OutcomeStatus
    realized_r: float
    mfe_r: float
    mae_r: float
    exit_price: float
    exit_timestamp: str
    bars_held: int
    ambiguous_resolution: Optional[AmbiguousCandleResolution] = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Core Semantic Helpers
# ---------------------------------------------------------------------------

def calculate_initial_risk_distance(direction: SignalDirection, entry: float, sl: float) -> float:
    """
    Calculate the initial risk distance (1R).
    Must be strictly positive.
    """
    if direction == SignalDirection.BUY:
        risk = entry - sl
    elif direction == SignalDirection.SELL:
        risk = sl - entry
    else:
        risk = abs(entry - sl)
    
    if risk <= 0:
        raise ValueError(f"Invalid SL for {direction}: Entry={entry}, SL={sl}, Risk={risk}")
    return risk


def resolve_realized_r(
    direction: SignalDirection,
    entry: float,
    sl: float,
    exit_price: float,
    outcome: OutcomeStatus,
) -> float:
    """
    Calculate standardized Realized R:
    - WIN: +1.0R (or distance based if full TP2/trailing, standardized to +1.0R for 1:1 TP)
    - LOSS: -1.0R
    - BREAKEVEN: 0.0R
    - EXPIRED: Realized distance / Initial Risk
    - INVALID / AMBIGUOUS: Handled conservatively
    """
    risk_dist = calculate_initial_risk_distance(direction, entry, sl)
    
    if outcome == OutcomeStatus.WIN:
        if direction == SignalDirection.BUY:
            raw_r = (exit_price - entry) / risk_dist
        else:
            raw_r = (entry - exit_price) / risk_dist
        return max(1.0, round(raw_r, 4))
    
    elif outcome == OutcomeStatus.LOSS:
        return -1.0
    
    elif outcome == OutcomeStatus.BREAKEVEN:
        return 0.0
    
    elif outcome == OutcomeStatus.EXPIRED:
        if direction == SignalDirection.BUY:
            raw_r = (exit_price - entry) / risk_dist
        else:
            raw_r = (entry - exit_price) / risk_dist
        return round(raw_r, 4)
    
    elif outcome == OutcomeStatus.AMBIGUOUS:
        # Conservative policy: treat as loss
        return -1.0
    
    elif outcome == OutcomeStatus.INVALID:
        return 0.0
    
    return 0.0
