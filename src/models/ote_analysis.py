"""
Data models for the Gold Smart Money / OTE (Optimal Trade Entry) Strategy.

5-Step ICT execution:
  1. Trend (1H)          — EMA structure determines market direction
  2. Liquidity (1H/1D)   — Previous Day High/Low sweep detection
  3. MSS (5m/15m)        — Market Structure Shift after liquidity event
  4. Fibonacci (5m/15m)  — Swing high/low → OTE zone [0.618–0.786]
  5. FVG (5m/15m)        — Fair Value Gap confirmation inside OTE zone

DISCLAIMER: All outputs are advisory / paper-trading only.
No real orders are executed. No broker connections are made.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────

class OTESignalType(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class OTESetupGrade(str, Enum):
    A_PLUS = "A+"
    A      = "A"
    B      = "B"
    C      = "C"


class SessionName(str, Enum):
    LONDON   = "LONDON"
    NEW_YORK = "NEW_YORK"
    NONE     = "NONE"


class SweepDirection(str, Enum):
    BULLISH = "BULLISH"   # PDL swept → look for longs
    BEARISH = "BEARISH"   # PDH swept → look for shorts
    NONE    = "NONE"


class MSSDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NONE    = "NONE"


class FVGType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NONE    = "NONE"


# ─────────────────────────────────────────────────────────────
# Step Models
# ─────────────────────────────────────────────────────────────

class TrendStep(BaseModel):
    """Step 1: 1H trend direction via EMA structure."""
    direction: str = Field(description="BULLISH, BEARISH, or NEUTRAL")
    ema20: Optional[float] = Field(default=None)
    ema50: Optional[float] = Field(default=None)
    ema200: Optional[float] = Field(default=None)
    price: float = Field(description="Current price used for EMA comparison")
    passed: bool = Field(description="True when a clear BULLISH or BEARISH trend is confirmed")
    reasoning: str = Field(default="")


class LiquidityStep(BaseModel):
    """Step 2: Previous Day High/Low and sweep detection."""
    prev_day_high: Optional[float] = Field(default=None, description="Previous day's high price")
    prev_day_low:  Optional[float] = Field(default=None, description="Previous day's low price")
    sweep_direction: SweepDirection = Field(default=SweepDirection.NONE)
    swept_level: Optional[float] = Field(default=None, description="The PDH or PDL level that was swept")
    passed: bool = Field(description="True when a valid liquidity sweep is confirmed")
    reasoning: str = Field(default="")


class MSSStep(BaseModel):
    """Step 3: Market Structure Shift on 5m/15m after a liquidity sweep."""
    direction: MSSDirection = Field(default=MSSDirection.NONE)
    break_level: Optional[float] = Field(default=None, description="Price level that was broken to confirm MSS")
    timeframe: str = Field(default="15m", description="Timeframe where MSS was detected")
    passed: bool = Field(description="True when MSS direction aligns with liquidity sweep")
    reasoning: str = Field(default="")


class FibonacciStep(BaseModel):
    """Step 4: Fibonacci OTE zone [0.618–0.786] after the impulse move."""
    swing_high: Optional[float] = Field(default=None)
    swing_low:  Optional[float] = Field(default=None)
    ote_high: Optional[float] = Field(default=None, description="0.786 retracement level")
    ote_low:  Optional[float] = Field(default=None, description="0.618 retracement level")
    level_618: Optional[float] = Field(default=None)
    level_786: Optional[float] = Field(default=None)
    current_price: Optional[float] = Field(default=None)
    price_in_ote_zone: bool = Field(default=False, description="True when price is inside [0.618, 0.786]")
    passed: bool = Field(description="True when price is confirmed inside the OTE zone")
    reasoning: str = Field(default="")


class FVGStep(BaseModel):
    """Step 5: Fair Value Gap detection aligned with trade direction."""
    fvg_type: FVGType = Field(default=FVGType.NONE)
    fvg_high: Optional[float] = Field(default=None, description="Top of the FVG zone")
    fvg_low:  Optional[float] = Field(default=None, description="Bottom of the FVG zone")
    price_in_fvg: bool = Field(default=False, description="True when current price is inside the FVG")
    timeframe: str = Field(default="5m")
    passed: bool = Field(description="True when a valid FVG is present and price is inside it")
    reasoning: str = Field(default="")


class SessionStatus(BaseModel):
    """Trading session gate status."""
    active_session: SessionName = Field(default=SessionName.NONE)
    is_open: bool = Field(default=False, description="True during London or New York session")
    session_start_utc: Optional[str] = Field(default=None)
    session_end_utc:   Optional[str] = Field(default=None)
    next_session: Optional[SessionName] = Field(default=None)
    next_session_opens_in_minutes: Optional[int] = Field(default=None)
    current_time_utc: str = Field(default="")
    reasoning: str = Field(default="")


# ─────────────────────────────────────────────────────────────
# Full OTE Signal
# ─────────────────────────────────────────────────────────────

class OTESignal(BaseModel):
    """
    Complete 5-step Smart Money / OTE advisory signal.

    DISCLAIMER: Advisory only. No trades are executed. No broker connected.
    """
    symbol: str = Field(default="XAU/USD")
    timestamp: str

    # 5-Step results
    trend:     TrendStep
    liquidity: LiquidityStep
    mss:       MSSStep
    fibonacci: FibonacciStep
    fvg:       FVGStep
    session:   SessionStatus

    # Steps passed summary
    steps_passed: int = Field(description="Number of 5 steps that passed (0–5)")
    steps_detail: List[str] = Field(default_factory=list, description="Human-readable per-step pass/fail")

    # Final signal
    signal:     OTESignalType = Field(default=OTESignalType.WAIT)
    confidence: int = Field(ge=0, le=100, default=0)
    setup_grade: str = Field(default="C")

    # Trade levels (populated only for BUY/SELL)
    entry_price:  Optional[float] = Field(default=None)
    stop_loss:    Optional[float] = Field(default=None)
    take_profit_1: Optional[float] = Field(default=None)
    take_profit_2: Optional[float] = Field(default=None)
    risk_reward_tp1: Optional[float] = Field(default=None)
    risk_reward_tp2: Optional[float] = Field(default=None)
    position_size: Optional[float] = Field(default=None, description="Suggested lots (1% of $10,000 balance)")

    # AI assessment
    ai_assessment: Optional[str] = Field(default=None, description="Gemini AI evaluation of the OTE setup")
    ai_confidence: Optional[int] = Field(default=None)

    # Narrative
    reasons:  List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Paper trading data
    paper_stats:   Optional[dict] = Field(default=None)
    trade_history: Optional[List[dict]] = Field(default=None)

    disclaimer: str = Field(
        default=(
            "ADVISORY ONLY. This is not financial advice. "
            "This system does not execute trades, connect to brokers, or guarantee any outcome."
        )
    )


# ─────────────────────────────────────────────────────────────
# OTE Paper Trade Record
# ─────────────────────────────────────────────────────────────

class OTETradeStatus(str, Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"


class OTETradeResult(str, Enum):
    WIN  = "WIN"
    LOSS = "LOSS"
    OPEN = "OPEN"
