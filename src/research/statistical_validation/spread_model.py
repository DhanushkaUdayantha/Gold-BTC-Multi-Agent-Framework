"""
Spread Modeling & Execution Cost Tracking Module.

Records real bid/ask spread where market feeds provide two-way pricing,
and explicitly handles missing bid/ask data as SPREAD_DATA_UNAVAILABLE (LIMITED research).

Zero production trading logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SpreadRecord:
    """Execution spread snapshot for an observation."""
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    mid: Optional[float]
    spread_usd: Optional[float]
    spread_r: Optional[float]  # Spread cost normalized in units of Risk (R)
    status: str  # "AVAILABLE" or "SPREAD_DATA_UNAVAILABLE"
    research_limitation: str  # "NONE" or "LIMITED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def record_spread_observation(
    symbol: str,
    bid: Optional[float] = None,
    ask: Optional[float] = None,
    current_price: Optional[float] = None,
    risk_r_usd: Optional[float] = None,
) -> SpreadRecord:
    """
    Construct a research spread record from available market feed quotes.
    
    If bid or ask is missing, explicitly logs SPREAD_DATA_UNAVAILABLE.
    """
    if bid is not None and ask is not None and bid > 0 and ask >= bid:
        spread_usd = round(ask - bid, 4)
        mid = round((ask + bid) / 2.0, 4)
        spread_r = None
        if risk_r_usd is not None and risk_r_usd > 0:
            spread_r = round(spread_usd / risk_r_usd, 4)

        return SpreadRecord(
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            spread_usd=spread_usd,
            spread_r=spread_r,
            status="AVAILABLE",
            research_limitation="NONE",
        )

    # Fallback / Missing bid-ask data handling
    return SpreadRecord(
        symbol=symbol,
        bid=None,
        ask=None,
        mid=current_price,
        spread_usd=None,
        spread_r=None,
        status="SPREAD_DATA_UNAVAILABLE",
        research_limitation="LIMITED",
    )
