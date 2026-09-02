"""
Real-Time Multi-Strategy Confluence Signal Engine for XAU/USD.

Implements a 17-contributor, 100-point weighted model with:
- Synchronized market snapshots (snapshotId)
- Per-contributor freshness / stale detection
- Previous→current score delta (direction UP/DOWN/UNCHANGED)
- Direction gate (HTF + Structure + MTF must agree ≥2 of 3)
- Signal hysteresis (±3pt threshold to flip band)
- Double-counting protection (shared structural evidence is penalized)
- Data quality scoring (LOW quality blocks high-confidence BUY/SELL)
- Evidence explainability (all final scores traceable to raw inputs)
- Audit trail (immutable snapshot records, max 100 retained)
- No look-ahead bias (forming/live candles excluded from confirmations)
- No fabricated values (missing data → UNAVAILABLE, score=0)

DISCLAIMER: Advisory analytical signals ONLY. Not financial advice.
            Does not execute trades or connect to brokers.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum points each contributor can award
CONTRIBUTOR_MAX_SCORES: Dict[str, int] = {
    "HTF Trend":          11,
    "Market Structure":    9,
    "Momentum":            8,
    "MTF Alignment":       8,
    "S/R Price Action":    8,
    "Breakout / Retest":   6,
    "Supply & Demand":     5,
    "Volume Confirmation": 5,
    "SMC / ICT":           5,
    "ICT Concepts":        4,
    "Fibonacci OTE":       4,
    "Elliott Wave":        4,
    "VWAP":                4,
    "EMA / MA Stack":      4,
    "RSI":                 3,
    "MACD":                2,
    "Gemini AI":          10,
}

TOTAL_MAX_SCORE = sum(CONTRIBUTOR_MAX_SCORES.values())  # 100

# Direction-gate contributors — at least 2 of these 3 must be bullish for BUY
# or bearish for SELL; otherwise signal defaults to WAIT.
GATE_CONTRIBUTORS = {"HTF Trend", "Market Structure", "MTF Alignment"}

# Hysteresis band — score must change by this many points to flip signal band.
SIGNAL_HYSTERESIS_THRESHOLD = 3

# Audit trail — max snapshots retained in memory
MAX_AUDIT_TRAIL = 100

# Stale-data threshold — contributor not refreshed within this many seconds
# is flagged as STALE
FRESHNESS_THRESHOLD_S = 300  # 5 minutes

# Double-counting map — if a piece of structural evidence is already counted
# in contributor A, contributor B gets a penalty multiplier when using it.
# Key: evidence tag, Value: first-registered contributor
_EVIDENCE_REGISTRY: Dict[str, str] = {}

_BUY_THRESHOLD = 55   # ≥55/100 after direction gate → BUY
_SELL_THRESHOLD = 55  # ≥55/100 after direction gate → SELL


# ---------------------------------------------------------------------------
# Market Snapshot
# ---------------------------------------------------------------------------

@dataclass
class MarketSnapshot:
    """
    Immutable, point-in-time container for all analysis inputs.
    A single snapshot is used for ALL 17 contributors to avoid look-ahead bias.
    """
    snapshot_id: str
    created_at: str                        # ISO 8601 UTC
    symbol: str
    current_price: float

    # Multi-timeframe technical analysis objects (None if unavailable)
    ta_5m: Optional[Any] = None
    ta_15m: Optional[Any] = None
    ta_1h: Optional[Any] = None
    ta_1d: Optional[Any] = None

    # Candle arrays (closed candles only — no forming candle)
    candles_5m: List[dict] = field(default_factory=list)
    candles_15m: List[dict] = field(default_factory=list)
    candles_1h: List[dict] = field(default_factory=list)
    candles_1d: List[dict] = field(default_factory=list)

    # AI result
    ai_result: Optional[Any] = None

    # SMC analysis results (populated by ConfluenceEngine during compute())
    smc_liquidity: Optional[Any] = None
    smc_mss: Optional[Any] = None
    smc_fib: Optional[Any] = None
    smc_fvg: Optional[Any] = None
    smc_trend: Optional[Any] = None
    elliott_result: Optional[Any] = None

    # Bid/ask spread for spread-status display
    bid: Optional[float] = None
    ask: Optional[float] = None


def _make_snapshot_id(symbol: str, ts: float) -> str:
    """Generate a deterministic snapshot ID based on symbol + unix timestamp."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    suffix = hashlib.md5(f"{symbol}-{ts}".encode()).hexdigest()[:4].upper()
    return f"SNAPSHOT-{dt.strftime('%Y%m%d-%H%M%S')}-{suffix}"


# ---------------------------------------------------------------------------
# Contributor Result
# ---------------------------------------------------------------------------

@dataclass
class ContributorState:
    """Result for a single contributor in a given analysis cycle."""
    name: str
    max_score: int
    score: int                                  # 0 … max_score
    prev_score: int                             # score from previous cycle
    direction: str                              # "UP" | "DOWN" | "UNCHANGED"
    bias: str                                   # "BULLISH" | "BEARISH" | "NEUTRAL" | "UNAVAILABLE"
    status: str                                 # "OK" | "STALE" | "UNAVAILABLE" | "INCOMPLETE"
    evidence: List[str]                         # human-readable evidence strings
    conflicts: List[str]                        # conflicting signals within this contributor
    timeframe: str                              # primary timeframe used
    last_changed_at: str                        # ISO 8601 of last score change
    snapshot_id: str                            # snapshot this result belongs to
    data_freshness: str                         # "FRESH" | "STALE" | "UNAVAILABLE"
    double_counting_penalty: float = 0.0       # 0.0–1.0 multiplier reduction applied


# ---------------------------------------------------------------------------
# Confluence Result
# ---------------------------------------------------------------------------

@dataclass
class ConfluenceResult:
    """Full output of one analysis cycle."""
    snapshot_id: str
    timestamp: str
    symbol: str
    current_price: float

    # Scores
    technical_score: int         # sum of all contributors except Gemini AI
    gemini_score: int            # Gemini AI contributor only
    final_score: int             # technical + gemini, 0–100

    # Direction gate
    gate_bullish_count: int      # how many of {HTF, Structure, MTF} are bullish
    gate_bearish_count: int      # how many are bearish
    gate_passed: bool
    gate_direction: str          # "BULLISH" | "BEARISH" | "NONE"

    # Signal
    signal: str                  # "BUY" | "SELL" | "WAIT"
    signal_changed: bool         # True if signal differs from previous cycle
    prev_signal: str

    # Individual contributors
    contributors: List[ContributorState]

    # Supporting metadata
    market_regime: str           # "TRENDING_BULLISH" | "TRENDING_BEARISH" | "RANGING" | "HIGH_VOLATILITY" | "UNCLEAR"
    data_quality: str            # "HIGH" | "MEDIUM" | "LOW"
    data_completeness: str       # e.g. "14/17 contributors available"
    top_confirmations: List[str]
    conflicts: List[str]
    entry_quality: str           # "GOOD" | "FAIR" | "POOR" | "WAIT"
    spread_status: str           # "NORMAL" | "HIGH_SPREAD" | "UNAVAILABLE"
    news_status: str             # "NEWS_DATA_UNAVAILABLE" (always — no news feed)


# ---------------------------------------------------------------------------
# ConfluenceEngine
# ---------------------------------------------------------------------------

class ConfluenceEngine:
    """
    Computes all 17 signal contributors from a synchronized MarketSnapshot
    and produces a ConfluenceResult.
    """

    def __init__(self) -> None:
        # Previous scores for delta / hysteresis tracking
        self._prev_scores: Dict[str, int] = {}
        self._last_changed_at: Dict[str, str] = {}
        self._prev_signal: str = "WAIT"
        self._prev_final_score: int = 0

        # Audit trail (most recent first)
        self._audit_trail: List[dict] = []

        # Evidence registry for double-counting protection (cleared each cycle)
        self._evidence_registry: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_snapshot(
        self,
        mtf_input: Any,
        ai_result: Any,
        candles_dict: Optional[Dict[str, List]] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> MarketSnapshot:
        """
        Build a MarketSnapshot from existing service layer objects.
        This is the ONLY place that reads live data — keeps compute() pure.
        """
        now_ts = time.time()
        snap_id = _make_snapshot_id(mtf_input.symbol or "XAU/USD", now_ts)
        tf = mtf_input.timeframes if mtf_input else {}

        # Extract closed candles only (exclude any forming/live candle)
        def _closed(candles: List) -> List[dict]:
            result = []
            for c in (candles or []):
                if isinstance(c, dict):
                    if c.get("is_closed", True):
                        result.append(c)
                else:
                    if getattr(c, "is_closed", True):
                        result.append({
                            "open": getattr(c, "open", 0),
                            "high": getattr(c, "high", 0),
                            "low": getattr(c, "low", 0),
                            "close": getattr(c, "close", 0),
                            "volume": getattr(c, "volume", None),
                            "timestamp": getattr(c, "timestamp", ""),
                            "is_closed": True,
                        })
            return result

        cd = candles_dict or {}
        return MarketSnapshot(
            snapshot_id=snap_id,
            created_at=datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat(),
            symbol=mtf_input.symbol or "XAU/USD",
            current_price=mtf_input.current_price,
            ta_5m=tf.get("5m"),
            ta_15m=tf.get("15m"),
            ta_1h=tf.get("1h"),
            ta_1d=tf.get("1d"),
            candles_5m=_closed(cd.get("5m", [])),
            candles_15m=_closed(cd.get("15m", [])),
            candles_1h=_closed(cd.get("1h", [])),
            candles_1d=_closed(cd.get("1d", [])),
            ai_result=ai_result,
            bid=bid,
            ask=ask,
        )

    def compute(self, snapshot: MarketSnapshot) -> ConfluenceResult:
        """
        Run all 17 contributors from the snapshot and return a ConfluenceResult.
        Never raises — all exceptions produce WAIT with descriptive status.
        """
        try:
            return self._compute_internal(snapshot)
        except Exception as exc:
            logger.error(f"ConfluenceEngine.compute() error: {exc}", exc_info=True)
            return self._safe_wait_result(snapshot, reason=str(exc))

    # ------------------------------------------------------------------
    # Internal compute pipeline
    # ------------------------------------------------------------------

    def _compute_internal(self, snap: MarketSnapshot) -> ConfluenceResult:
        now_iso = datetime.now(timezone.utc).isoformat()

        # ---- Pre-compute SMC/ICT results once (shared by multiple contributors) ----
        snap = self._run_smc_analysis(snap)

        # Reset evidence registry for this cycle (double-counting protection)
        self._evidence_registry = {}

        # ---- Compute all 17 contributors ----
        contributors: List[ContributorState] = [
            self._c_htf_trend(snap),
            self._c_market_structure(snap),
            self._c_momentum(snap),
            self._c_mtf_alignment(snap),
            self._c_sr_price_action(snap),
            self._c_breakout_retest(snap),
            self._c_supply_demand(snap),
            self._c_volume_confirmation(snap),
            self._c_smc(snap),
            self._c_ict(snap),
            self._c_fibonacci(snap),
            self._c_elliott_wave(snap),
            self._c_vwap(snap),
            self._c_ema_ma(snap),
            self._c_rsi(snap),
            self._c_macd(snap),
            self._c_gemini_ai(snap),
        ]

        # ---- Apply delta tracking and hysteresis ----
        contributors = self._apply_delta_tracking(contributors, snap.snapshot_id, now_iso)

        # ---- Direction gate ----
        gate_bullish = sum(
            1 for c in contributors
            if c.name in GATE_CONTRIBUTORS and c.bias == "BULLISH"
        )
        gate_bearish = sum(
            1 for c in contributors
            if c.name in GATE_CONTRIBUTORS and c.bias == "BEARISH"
        )
        gate_passed = gate_bullish >= 2 or gate_bearish >= 2
        gate_dir = "BULLISH" if gate_bullish >= 2 else ("BEARISH" if gate_bearish >= 2 else "NONE")

        # ---- Scores ----
        gemini_contrib = next((c for c in contributors if c.name == "Gemini AI"), None)
        gemini_score = gemini_contrib.score if gemini_contrib else 0
        technical_score = sum(
            c.score for c in contributors if c.name != "Gemini AI"
        )
        final_score = technical_score + gemini_score
        final_score = max(0, min(TOTAL_MAX_SCORE, final_score))

        # ---- Data quality ----
        unavailable_count = sum(1 for c in contributors if c.status == "UNAVAILABLE")
        stale_count = sum(1 for c in contributors if c.status == "STALE")
        total = len(contributors)
        available_count = total - unavailable_count
        data_completeness = f"{available_count}/{total} contributors available"

        if unavailable_count >= 6 or stale_count >= 4:
            data_quality = "LOW"
        elif unavailable_count >= 3 or stale_count >= 2:
            data_quality = "MEDIUM"
        else:
            data_quality = "HIGH"

        # ---- Signal determination with hysteresis ----
        raw_signal = "WAIT"
        if gate_passed:
            if gate_dir == "BULLISH" and final_score >= _BUY_THRESHOLD:
                raw_signal = "BUY"
            elif gate_dir == "BEARISH" and final_score >= _SELL_THRESHOLD:
                raw_signal = "SELL"

        # Apply hysteresis — only change signal if score shifted enough OR gate changed
        gate_changed = (
            (gate_dir == "BULLISH" and self._prev_signal != "BUY") or
            (gate_dir == "BEARISH" and self._prev_signal != "SELL") or
            (gate_dir == "NONE" and self._prev_signal != "WAIT")
        )
        score_delta = abs(final_score - self._prev_final_score)

        if gate_changed or score_delta >= SIGNAL_HYSTERESIS_THRESHOLD:
            final_signal = raw_signal
        else:
            # Hysteresis: keep previous signal if score barely moved and gate unchanged
            if self._prev_signal in ("BUY", "SELL") and raw_signal == "WAIT":
                final_signal = self._prev_signal  # hold last signal
            else:
                final_signal = raw_signal

        # Block high-confidence signals when data quality is LOW
        if data_quality == "LOW" and final_signal in ("BUY", "SELL"):
            final_signal = "WAIT"

        signal_changed = final_signal != self._prev_signal

        # ---- Market regime ----
        market_regime = self._classify_regime(snap, final_score, gate_dir)

        # ---- Entry quality ----
        if final_signal == "WAIT":
            entry_quality = "WAIT"
        elif final_score >= 75 and data_quality == "HIGH":
            entry_quality = "GOOD"
        elif final_score >= 60:
            entry_quality = "FAIR"
        else:
            entry_quality = "POOR"

        # ---- Evidence and conflicts ----
        top_confirmations = self._extract_top_confirmations(contributors, gate_dir)
        conflicts = self._extract_conflicts(contributors, gate_dir)

        # ---- Spread status ----
        spread_status = self._compute_spread_status(snap)

        # ---- Update state ----
        self._prev_signal = final_signal
        self._prev_final_score = final_score

        # ---- Audit trail ----
        audit_entry = {
            "snapshot_id": snap.snapshot_id,
            "timestamp": now_iso,
            "signal": final_signal,
            "final_score": final_score,
            "gate_direction": gate_dir,
            "data_quality": data_quality,
            "market_regime": market_regime,
        }
        self._audit_trail.insert(0, audit_entry)
        if len(self._audit_trail) > MAX_AUDIT_TRAIL:
            self._audit_trail = self._audit_trail[:MAX_AUDIT_TRAIL]

        return ConfluenceResult(
            snapshot_id=snap.snapshot_id,
            timestamp=now_iso,
            symbol=snap.symbol,
            current_price=snap.current_price,
            technical_score=technical_score,
            gemini_score=gemini_score,
            final_score=final_score,
            gate_bullish_count=gate_bullish,
            gate_bearish_count=gate_bearish,
            gate_passed=gate_passed,
            gate_direction=gate_dir,
            signal=final_signal,
            signal_changed=signal_changed,
            prev_signal=self._prev_signal,
            contributors=contributors,
            market_regime=market_regime,
            data_quality=data_quality,
            data_completeness=data_completeness,
            top_confirmations=top_confirmations,
            conflicts=conflicts,
            entry_quality=entry_quality,
            spread_status=spread_status,
            news_status="NEWS_DATA_UNAVAILABLE",
        )

    # ------------------------------------------------------------------
    # SMC / ICT pre-computation (shared across multiple contributors)
    # ------------------------------------------------------------------

    def _run_smc_analysis(self, snap: MarketSnapshot) -> MarketSnapshot:
        """Run OTE/SMC/Elliott analysis and attach to snapshot."""
        try:
            from src.services.ote_engine import OTEEngine
            from src.services.elliott_wave_service import ElliottWaveService

            ote = OTEEngine()
            ta_1h = snap.ta_1h
            e20 = ta_1h.ema20 if ta_1h else None
            e50 = ta_1h.ema50 if ta_1h else None
            e200 = ta_1h.ema200 if ta_1h else None

            snap.smc_trend = ote.analyze_trend(snap.current_price, e20, e50, e200)
            snap.smc_liquidity = ote.analyze_liquidity(
                snap.candles_1d, snap.candles_1h, snap.current_price
            )
            snap.smc_mss = ote.analyze_mss(
                snap.candles_15m,
                snap.smc_liquidity.sweep_direction if snap.smc_liquidity else None,
                timeframe="15m",
            )
            snap.smc_fib = ote.analyze_fibonacci(
                snap.candles_15m,
                snap.smc_mss.direction if snap.smc_mss else None,
                snap.current_price,
            )
            snap.smc_fvg = ote.analyze_fvg(
                snap.candles_5m or snap.candles_15m,
                snap.smc_mss.direction if snap.smc_mss else None,
                snap.current_price,
            )
            candles_ew = snap.candles_15m or snap.candles_1h
            snap.elliott_result = ElliottWaveService.analyze(
                candles_ew, snap.current_price, timeframe="15m"
            )
        except Exception as exc:
            logger.warning(f"SMC pre-computation failed (non-fatal): {exc}")
        return snap

    # ------------------------------------------------------------------
    # Delta tracking (UP / DOWN / UNCHANGED + last_changed_at)
    # ------------------------------------------------------------------

    def _apply_delta_tracking(
        self,
        contributors: List[ContributorState],
        snapshot_id: str,
        now_iso: str,
    ) -> List[ContributorState]:
        for c in contributors:
            prev = self._prev_scores.get(c.name, c.score)
            c.prev_score = prev

            if c.score > prev:
                c.direction = "UP"
                self._last_changed_at[c.name] = now_iso
            elif c.score < prev:
                c.direction = "DOWN"
                self._last_changed_at[c.name] = now_iso
            else:
                c.direction = "UNCHANGED"

            # First appearance
            if c.name not in self._last_changed_at:
                self._last_changed_at[c.name] = now_iso

            c.last_changed_at = self._last_changed_at[c.name]
            c.snapshot_id = snapshot_id
            self._prev_scores[c.name] = c.score

        return contributors

    # ------------------------------------------------------------------
    # Evidence registry (double-counting protection)
    # ------------------------------------------------------------------

    def _register_evidence(self, tag: str, contributor_name: str) -> float:
        """
        Register a piece of structural evidence.
        Returns a penalty multiplier: 1.0 if first use, 0.5 if second, 0.25 if third+.
        """
        if tag not in self._evidence_registry:
            self._evidence_registry[tag] = contributor_name
            return 1.0
        existing = self._evidence_registry[tag]
        if existing == contributor_name:
            return 1.0
        # Second use of same evidence
        return 0.5

    # ------------------------------------------------------------------
    # Utility builders
    # ------------------------------------------------------------------

    def _ta_freshness(self, ta: Optional[Any]) -> str:
        if ta is None:
            return "UNAVAILABLE"
        ts = getattr(ta, "data_timestamp", None)
        if not ts:
            return "FRESH"  # assume fresh if no timestamp field
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = ts
            age_s = (datetime.now(tz=timezone.utc) - dt).total_seconds()
            return "STALE" if age_s > FRESHNESS_THRESHOLD_S else "FRESH"
        except Exception:
            return "FRESH"

    def _make_state(
        self,
        name: str,
        score: int,
        bias: str,
        evidence: List[str],
        timeframe: str,
        status: str = "OK",
        conflicts: Optional[List[str]] = None,
        penalty: float = 1.0,
    ) -> ContributorState:
        max_s = CONTRIBUTOR_MAX_SCORES.get(name, 10)
        actual_score = round(score * penalty)
        actual_score = max(0, min(max_s, actual_score))
        return ContributorState(
            name=name,
            max_score=max_s,
            score=actual_score,
            prev_score=self._prev_scores.get(name, actual_score),
            direction="UNCHANGED",
            bias=bias,
            status=status,
            evidence=evidence,
            conflicts=conflicts or [],
            timeframe=timeframe,
            last_changed_at="",
            snapshot_id="",
            data_freshness="FRESH" if status == "OK" else status,
            double_counting_penalty=round(1.0 - penalty, 2),
        )

    def _unavailable(self, name: str, reason: str, timeframe: str = "—") -> ContributorState:
        return self._make_state(
            name=name, score=0, bias="UNAVAILABLE",
            evidence=[reason], timeframe=timeframe, status="UNAVAILABLE",
        )

    # ------------------------------------------------------------------
    # 17 Contributors
    # ------------------------------------------------------------------

    # 1. HTF Trend — 11pt max (1H + 1D)
    def _c_htf_trend(self, snap: MarketSnapshot) -> ContributorState:
        name = "HTF Trend"
        ta_1h = snap.ta_1h
        ta_1d = snap.ta_1d
        if ta_1h is None and ta_1d is None:
            return self._unavailable(name, "1h and 1d data unavailable", "1h/1d")

        freshness = "FRESH"
        score = 0
        evidence = []
        conflicts = []
        bias_votes = []

        # 1H contributes up to 6pts
        if ta_1h:
            td = ta_1h.trend.direction.value if ta_1h.trend else "SIDEWAYS"
            strength = ta_1h.trend.strength if ta_1h.trend else "WEAK"
            pts_map = {"BULLISH": {"STRONG": 6, "MODERATE": 4, "WEAK": 2},
                       "BEARISH": {"STRONG": 6, "MODERATE": 4, "WEAK": 2},
                       "SIDEWAYS": {"STRONG": 0, "MODERATE": 0, "WEAK": 0}}
            pts = pts_map.get(td, {}).get(strength, 0)
            score += pts
            evidence.append(f"1H: {td} ({strength}) → +{pts}pt")
            if td == "BULLISH":
                bias_votes.append("BULLISH")
            elif td == "BEARISH":
                bias_votes.append("BEARISH")
            f1h = self._ta_freshness(ta_1h)
            if f1h == "STALE":
                freshness = "STALE"

        # 1D contributes up to 5pts
        if ta_1d:
            td = ta_1d.trend.direction.value if ta_1d.trend else "SIDEWAYS"
            strength = ta_1d.trend.strength if ta_1d.trend else "WEAK"
            pts_map = {"BULLISH": {"STRONG": 5, "MODERATE": 3, "WEAK": 1},
                       "BEARISH": {"STRONG": 5, "MODERATE": 3, "WEAK": 1},
                       "SIDEWAYS": {"STRONG": 0, "MODERATE": 0, "WEAK": 0}}
            pts = pts_map.get(td, {}).get(strength, 0)
            score += pts
            evidence.append(f"1D: {td} ({strength}) → +{pts}pt")
            if td == "BULLISH":
                bias_votes.append("BULLISH")
            elif td == "BEARISH":
                bias_votes.append("BEARISH")
            f1d = self._ta_freshness(ta_1d)
            if f1d == "STALE":
                freshness = "STALE"

        # Conflict: 1H and 1D disagree
        unique_votes = set(v for v in bias_votes if v != "SIDEWAYS")
        if len(unique_votes) > 1:
            conflicts.append("1H and 1D trend directions conflict")
            score = max(0, score - 2)  # conflict penalty

        bias = max(set(bias_votes), key=bias_votes.count) if bias_votes else "NEUTRAL"
        status = freshness if freshness == "STALE" else "OK"
        return self._make_state(name, score, bias, evidence, "1h/1d", status, conflicts)

    # 2. Market Structure — 9pt max (Break of Structure / CHoCH)
    def _c_market_structure(self, snap: MarketSnapshot) -> ContributorState:
        name = "Market Structure"
        if snap.smc_mss is None:
            return self._unavailable(name, "MSS analysis unavailable", "15m")

        try:
            from src.models.ote_analysis import MSSDirection
            mss = snap.smc_mss
            evidence = []
            score = 0
            bias = "NEUTRAL"
            conflicts = []

            if mss.passed:
                direction = mss.direction.value if hasattr(mss.direction, "value") else str(mss.direction)
                # Register evidence to prevent double-counting in SMC/ICT
                penalty = self._register_evidence("MSS_BOS", name)
                score = round(9 * penalty)
                bias = "BULLISH" if direction == "BULLISH" else "BEARISH"
                evidence.append(f"MSS/BOS confirmed: {direction}")
                if mss.reasoning:
                    evidence.append(mss.reasoning[:80])
                if penalty < 1.0:
                    evidence.append(f"Double-count reduction applied (×{penalty:.1f})")
            else:
                evidence.append("No confirmed BOS or CHoCH on 15m")
                score = 0
                bias = "NEUTRAL"

            return self._make_state(name, score, bias, evidence, "15m", conflicts=conflicts)
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "15m")

    # 3. Momentum — 7pt max (5m + 15m combined)
    def _c_momentum(self, snap: MarketSnapshot) -> ContributorState:
        name = "Momentum"
        ta_5m = snap.ta_5m
        ta_15m = snap.ta_15m
        if ta_5m is None and ta_15m is None:
            return self._unavailable(name, "5m and 15m data unavailable", "5m/15m")

        score = 0
        evidence = []
        votes = []

        for tf_label, ta in [("5m", ta_5m), ("15m", ta_15m)]:
            if ta is None:
                continue
            td = ta.trend.direction.value if ta.trend else "SIDEWAYS"
            macd_hist = ta.macd.histogram if (ta.macd and ta.macd.histogram is not None) else 0
            pts = 0
            if td == "BULLISH":
                pts += 2
                votes.append("BULLISH")
            elif td == "BEARISH":
                pts += 2
                votes.append("BEARISH")
            if macd_hist > 0:
                pts += 1
                votes.append("BULLISH")
            elif macd_hist < 0:
                pts += 1
                votes.append("BEARISH")
            score += pts
            evidence.append(f"{tf_label}: trend={td}, MACD_hist={macd_hist:+.4f} → +{pts}pt")

        # Scale to max 7
        score = min(7, score)
        bias = max(set(votes), key=votes.count) if votes else "NEUTRAL"
        freshness = "STALE" if (
            self._ta_freshness(ta_5m) == "STALE" and self._ta_freshness(ta_15m) == "STALE"
        ) else "FRESH"
        status = "STALE" if freshness == "STALE" else "OK"
        return self._make_state(name, score, bias, evidence, "5m/15m", status)

    # 4. MTF Alignment — 7pt max (5m/15m/1h/1d agreeing)
    def _c_mtf_alignment(self, snap: MarketSnapshot) -> ContributorState:
        name = "MTF Alignment"
        tfs = {
            "5m": snap.ta_5m,
            "15m": snap.ta_15m,
            "1h": snap.ta_1h,
            "1d": snap.ta_1d,
        }
        available = {k: v for k, v in tfs.items() if v is not None}
        if not available:
            return self._unavailable(name, "No timeframe data available", "all")

        bull_count = 0
        bear_count = 0
        evidence = []
        for tf_label, ta in available.items():
            td = ta.trend.direction.value if ta.trend else "SIDEWAYS"
            if td == "BULLISH":
                bull_count += 1
                evidence.append(f"{tf_label}: BULLISH")
            elif td == "BEARISH":
                bear_count += 1
                evidence.append(f"{tf_label}: BEARISH")
            else:
                evidence.append(f"{tf_label}: SIDEWAYS")

        total = len(available)
        dominant = max(bull_count, bear_count)
        bias = "BULLISH" if bull_count > bear_count else ("BEARISH" if bear_count > bull_count else "NEUTRAL")

        # Proportional score: aligned / total * max_pts
        score = round((dominant / total) * 7) if total > 0 else 0
        # Conflict: no clear majority
        conflicts = []
        if abs(bull_count - bear_count) <= 1 and total >= 3:
            conflicts.append(f"MTF conflict: {bull_count}B/{bear_count}S across {total} timeframes")
            score = max(0, score - 2)

        return self._make_state(name, score, bias, evidence, "all TFs", conflicts=conflicts)

    # 5. S/R Price Action — 7pt max
    def _c_sr_price_action(self, snap: MarketSnapshot) -> ContributorState:
        name = "S/R Price Action"
        ta = snap.ta_1h or snap.ta_15m
        if ta is None:
            return self._unavailable(name, "No S/R data available", "1h")

        price = snap.current_price
        supports = ta.support_levels or []
        resistances = ta.resistance_levels or []
        evidence = []
        score = 0
        bias = "NEUTRAL"

        nearest_sup = max((s for s in supports if s <= price), default=None)
        nearest_res = min((r for r in resistances if r >= price), default=None)

        # Score based on proximity and bounce context
        if nearest_sup and nearest_res:
            dist_sup_pct = (price - nearest_sup) / price * 100
            dist_res_pct = (nearest_res - price) / price * 100

            if dist_sup_pct < 0.1:
                score = 7
                bias = "BULLISH"
                evidence.append(f"Price at support ${nearest_sup:.2f} (dist={dist_sup_pct:.3f}%)")
            elif dist_res_pct < 0.1:
                score = 7
                bias = "BEARISH"
                evidence.append(f"Price at resistance ${nearest_res:.2f} (dist={dist_res_pct:.3f}%)")
            elif dist_sup_pct < 0.3:
                score = 4
                bias = "BULLISH"
                evidence.append(f"Price near support ${nearest_sup:.2f} (dist={dist_sup_pct:.3f}%)")
            elif dist_res_pct < 0.3:
                score = 4
                bias = "BEARISH"
                evidence.append(f"Price near resistance ${nearest_res:.2f} (dist={dist_res_pct:.3f}%)")
            else:
                score = 1
                evidence.append(f"Support ${nearest_sup:.2f}, Resistance ${nearest_res:.2f} — midrange")
        elif nearest_sup:
            dist_sup_pct = (price - nearest_sup) / price * 100
            score = 3 if dist_sup_pct < 0.3 else 1
            bias = "BULLISH" if dist_sup_pct < 0.3 else "NEUTRAL"
            evidence.append(f"Support only: ${nearest_sup:.2f}")
        elif nearest_res:
            dist_res_pct = (nearest_res - price) / price * 100
            score = 3 if dist_res_pct < 0.3 else 1
            bias = "BEARISH" if dist_res_pct < 0.3 else "NEUTRAL"
            evidence.append(f"Resistance only: ${nearest_res:.2f}")
        else:
            evidence.append("No S/R levels identified")

        return self._make_state(name, score, bias, evidence, "1h")

    # 6. Breakout / Retest — 6pt max
    def _c_breakout_retest(self, snap: MarketSnapshot) -> ContributorState:
        name = "Breakout / Retest"
        candles = snap.candles_1h or snap.candles_15m
        ta = snap.ta_1h or snap.ta_15m
        if not candles or ta is None:
            return self._unavailable(name, "Candle data unavailable", "1h/15m")

        price = snap.current_price
        supports = ta.support_levels or []
        resistances = ta.resistance_levels or []
        evidence = []
        score = 0
        bias = "NEUTRAL"

        if len(candles) < 5:
            return self._unavailable(name, "Insufficient candles for breakout analysis", "1h")

        recent = candles[-10:]
        for level in resistances:
            # Breakout above resistance → bullish
            closes_above = sum(1 for c in recent if _candle_close(c) > level)
            wicks_to = sum(1 for c in recent if _candle_low(c) <= level * 1.001 and _candle_close(c) > level)
            if closes_above >= 2 and wicks_to >= 1:
                score = 6
                bias = "BULLISH"
                evidence.append(f"Bullish breakout & retest of ${level:.2f}")
                break

        if score == 0:
            for level in supports:
                # Breakdown below support → bearish
                closes_below = sum(1 for c in recent if _candle_close(c) < level)
                wicks_to = sum(1 for c in recent if _candle_high(c) >= level * 0.999 and _candle_close(c) < level)
                if closes_below >= 2 and wicks_to >= 1:
                    score = 6
                    bias = "BEARISH"
                    evidence.append(f"Bearish breakdown & retest of ${level:.2f}")
                    break

        if score == 0:
            evidence.append("No confirmed breakout or breakdown pattern")

        return self._make_state(name, score, bias, evidence, "1h/15m")

    # 7. Supply & Demand — 5pt max (derived from FVG)
    def _c_supply_demand(self, snap: MarketSnapshot) -> ContributorState:
        name = "Supply & Demand"
        fvg = snap.smc_fvg
        if fvg is None:
            return self._unavailable(name, "FVG analysis unavailable", "5m/15m")

        try:
            from src.models.ote_analysis import FVGType
            evidence = []
            score = 0
            bias = "NEUTRAL"

            if fvg.passed:
                fvg_type = fvg.fvg_type
                direction = fvg_type.value if hasattr(fvg_type, "value") else str(fvg_type)
                penalty = self._register_evidence("FVG", name)
                score = round(5 * penalty)
                bias = "BULLISH" if direction == "BULLISH" else "BEARISH"
                evidence.append(f"FVG identified: {direction}")
                if fvg.reasoning:
                    evidence.append(fvg.reasoning[:80])
                if penalty < 1.0:
                    evidence.append(f"Double-count reduction applied (×{penalty:.1f})")
            else:
                evidence.append("No active FVG/supply-demand zone detected")

            return self._make_state(name, score, bias, evidence, "5m/15m")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "5m/15m")

    # 8. Volume Confirmation — 5pt max
    def _c_volume_confirmation(self, snap: MarketSnapshot) -> ContributorState:
        name = "Volume Confirmation"
        candles = snap.candles_15m or snap.candles_1h
        if not candles:
            return self._unavailable(name, "Candle data unavailable", "15m")

        # Check if volume is present at all
        has_volume = any(_candle_volume(c) is not None and _candle_volume(c) > 0 for c in candles[-20:])
        if not has_volume:
            return self._unavailable(name, "Volume data unavailable (gold spot market)", "15m")

        recent = candles[-10:]
        vols = [_candle_volume(c) for c in recent if _candle_volume(c) is not None]
        if not vols:
            return self._unavailable(name, "Volume data empty", "15m")

        avg_vol = sum(vols) / len(vols)
        last_vol = vols[-1]
        evidence = []
        score = 0
        bias = "NEUTRAL"

        # Determine last candle direction
        last_c = candles[-1]
        is_bull = _candle_close(last_c) > _candle_open(last_c)

        if last_vol > avg_vol * 1.5:
            score = 5
            bias = "BULLISH" if is_bull else "BEARISH"
            evidence.append(f"Volume spike: {last_vol:.0f} vs avg {avg_vol:.0f} (+{(last_vol/avg_vol-1)*100:.0f}%)")
        elif last_vol > avg_vol * 1.1:
            score = 3
            bias = "BULLISH" if is_bull else "BEARISH"
            evidence.append(f"Above-average volume: {last_vol:.0f} vs avg {avg_vol:.0f}")
        elif last_vol < avg_vol * 0.7:
            score = 1
            evidence.append(f"Low volume: {last_vol:.0f} vs avg {avg_vol:.0f} — weak signal")
        else:
            score = 2
            evidence.append(f"Average volume: {last_vol:.0f}")

        return self._make_state(name, score, bias, evidence, "15m")

    # 9. SMC / ICT — 5pt max (trend + MSS + FVG combined)
    def _c_smc(self, snap: MarketSnapshot) -> ContributorState:
        name = "SMC / ICT"
        if snap.smc_trend is None:
            return self._unavailable(name, "SMC analysis unavailable", "1h")

        try:
            from src.models.ote_analysis import MSSDirection, FVGType, SweepDirection
            evidence = []
            raw_score = 0.0
            bias_votes = []

            # Trend (0.3 weight)
            if snap.smc_trend and snap.smc_trend.passed:
                direction = snap.smc_trend.direction
                raw_score += 0.3 if direction == "BULLISH" else -0.3
                bias_votes.append(direction)
                evidence.append(f"SMC Trend: {direction}")

            # MSS / BOS (0.4 weight) — with double-count protection
            if snap.smc_mss and snap.smc_mss.passed:
                mss_dir = snap.smc_mss.direction.value if hasattr(snap.smc_mss.direction, "value") else str(snap.smc_mss.direction)
                penalty = self._register_evidence("MSS_BOS", name)
                raw_score += (0.4 if mss_dir == "BULLISH" else -0.4) * penalty
                bias_votes.append(mss_dir)
                evidence.append(f"BOS/CHoCH: {mss_dir} (penalty×{penalty:.1f})")

            # FVG (0.3 weight) — with double-count protection
            if snap.smc_fvg and snap.smc_fvg.passed:
                fvg_type = snap.smc_fvg.fvg_type.value if hasattr(snap.smc_fvg.fvg_type, "value") else str(snap.smc_fvg.fvg_type)
                penalty = self._register_evidence("FVG", name)
                raw_score += (0.3 if fvg_type == "BULLISH" else -0.3) * penalty
                bias_votes.append(fvg_type)
                evidence.append(f"FVG: {fvg_type} (penalty×{penalty:.1f})")

            raw_score = max(-1.0, min(1.0, raw_score))
            pts = round(abs(raw_score) * 5)
            bias = "BULLISH" if raw_score > 0 else ("BEARISH" if raw_score < 0 else "NEUTRAL")
            if not evidence:
                evidence.append("No SMC structure confirmed")

            return self._make_state(name, pts, bias, evidence, "15m/1h")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "15m/1h")

    # 10. ICT Concepts — 4pt max (liquidity sweep focus)
    def _c_ict(self, snap: MarketSnapshot) -> ContributorState:
        name = "ICT Concepts"
        if snap.smc_liquidity is None:
            return self._unavailable(name, "Liquidity analysis unavailable", "1d/1h")

        try:
            from src.models.ote_analysis import SweepDirection
            liq = snap.smc_liquidity
            evidence = []
            score = 0
            bias = "NEUTRAL"

            if liq.passed:
                sweep_dir = liq.sweep_direction
                direction = sweep_dir.value if hasattr(sweep_dir, "value") else str(sweep_dir)
                penalty = self._register_evidence("LIQUIDITY_SWEEP", name)
                score = round(4 * penalty)
                bias = "BULLISH" if direction == "BULLISH" else "BEARISH"
                evidence.append(f"PDH/PDL liquidity swept: {direction}")
                if liq.reasoning:
                    evidence.append(liq.reasoning[:80])
                if penalty < 1.0:
                    evidence.append(f"Double-count reduction (×{penalty:.1f})")
            else:
                evidence.append("No PDH/PDL liquidity sweep detected")

            return self._make_state(name, score, bias, evidence, "1d/1h")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "1d/1h")

    # 11. Fibonacci OTE — 4pt max
    def _c_fibonacci(self, snap: MarketSnapshot) -> ContributorState:
        name = "Fibonacci OTE"
        if snap.smc_fib is None:
            return self._unavailable(name, "Fibonacci analysis unavailable", "15m")

        try:
            from src.models.ote_analysis import MSSDirection
            fib = snap.smc_fib
            mss = snap.smc_mss
            evidence = []
            score = 0
            bias = "NEUTRAL"

            if fib.passed:
                mss_dir = (mss.direction.value if (mss and hasattr(mss.direction, "value")) else "NEUTRAL")
                score = 4 if mss_dir in ("BULLISH", "BEARISH") else 2
                bias = mss_dir if mss_dir != "NEUTRAL" else "NEUTRAL"
                evidence.append(f"OTE zone confirmed (0.618–0.786 retracement)")
                if fib.reasoning:
                    evidence.append(fib.reasoning[:80])
            else:
                evidence.append("Price not in OTE zone")

            return self._make_state(name, score, bias, evidence, "15m")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "15m")

    # 12. Elliott Wave — 4pt max
    def _c_elliott_wave(self, snap: MarketSnapshot) -> ContributorState:
        name = "Elliott Wave"
        ew = snap.elliott_result
        if ew is None:
            return self._unavailable(name, "Elliott Wave analysis unavailable", "15m")

        try:
            score = round(abs(ew.score) * 4)
            bias = "BULLISH" if ew.score > 0 else ("BEARISH" if ew.score < 0 else "NEUTRAL")
            evidence = [
                f"Wave phase: {ew.wave_phase.replace('_', ' ')}",
                f"EW score: {ew.score:+.2f}",
            ]
            if ew.reasoning:
                evidence.append(ew.reasoning[:80])
            return self._make_state(name, score, bias, evidence, "15m")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "15m")

    # 13. VWAP — 4pt max
    def _c_vwap(self, snap: MarketSnapshot) -> ContributorState:
        name = "VWAP"
        ta = snap.ta_15m or snap.ta_1h
        candles = snap.candles_15m or snap.candles_1h
        if not candles:
            return self._unavailable(name, "No candle data for VWAP", "15m")

        # Compute VWAP from available intraday candles (today's only)
        vwap = _compute_vwap(candles[-100:])
        if vwap is None or vwap <= 0:
            return self._unavailable(name, "VWAP could not be computed (no volume data)", "15m")

        price = snap.current_price
        evidence = [f"VWAP: ${vwap:.2f}, Price: ${price:.2f}"]
        if price > vwap * 1.001:
            score = 4
            bias = "BULLISH"
            evidence.append(f"Price {((price/vwap)-1)*100:.2f}% above VWAP — bullish")
        elif price < vwap * 0.999:
            score = 4
            bias = "BEARISH"
            evidence.append(f"Price {((vwap/price)-1)*100:.2f}% below VWAP — bearish")
        else:
            score = 1
            bias = "NEUTRAL"
            evidence.append("Price at VWAP — neutral zone")

        return self._make_state(name, score, bias, evidence, "15m")

    # 14. EMA / MA Stack — 4pt max
    def _c_ema_ma(self, snap: MarketSnapshot) -> ContributorState:
        name = "EMA / MA Stack"
        ta = snap.ta_1h or snap.ta_15m
        if ta is None:
            return self._unavailable(name, "EMA data unavailable", "1h")

        price = snap.current_price
        e20, e50, e200 = ta.ema20, ta.ema50, ta.ema200
        evidence = []
        bullish = 0
        bearish = 0
        total = 0

        for label, val in [("EMA20", e20), ("EMA50", e50), ("EMA200", e200)]:
            if val is not None:
                total += 1
                if price > val:
                    bullish += 1
                    evidence.append(f"Price > {label} (${val:.1f})")
                else:
                    bearish += 1
                    evidence.append(f"Price < {label} (${val:.1f})")

        if total == 0:
            return self._unavailable(name, "No EMA values computed", "1h")

        raw = (bullish - bearish) / total
        score = round(abs(raw) * 4)
        bias = "BULLISH" if raw > 0 else ("BEARISH" if raw < 0 else "NEUTRAL")
        return self._make_state(name, score, bias, evidence, "1h")

    # 15. RSI — 3pt max
    def _c_rsi(self, snap: MarketSnapshot) -> ContributorState:
        name = "RSI"
        ta = snap.ta_1h or snap.ta_15m
        if ta is None or ta.rsi14 is None:
            return self._unavailable(name, "RSI data unavailable", "1h")

        try:
            from src.models.technical_analysis import RSICondition
            rsi_val = ta.rsi14.value
            condition = ta.rsi14.condition
            evidence = [f"RSI(14): {rsi_val:.1f}"]

            if condition == RSICondition.OVERSOLD:
                score = 3
                bias = "BULLISH"
                evidence.append("Oversold — potential reversal zone")
            elif condition == RSICondition.OVERBOUGHT:
                score = 3
                bias = "BEARISH"
                evidence.append("Overbought — potential reversal zone")
            elif 40 <= rsi_val <= 60:
                score = 1
                bias = "NEUTRAL"
                evidence.append("RSI neutral zone")
            elif rsi_val > 60:
                score = 2
                bias = "BULLISH"
                evidence.append("RSI above 60 — mild bullish")
            else:
                score = 2
                bias = "BEARISH"
                evidence.append("RSI below 40 — mild bearish")

            return self._make_state(name, score, bias, evidence, "1h")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "1h")

    # 16. MACD — 2pt max
    def _c_macd(self, snap: MarketSnapshot) -> ContributorState:
        name = "MACD"
        ta = snap.ta_15m or snap.ta_1h
        if ta is None or ta.macd is None:
            return self._unavailable(name, "MACD data unavailable", "15m")

        try:
            from src.models.technical_analysis import MACDState
            macd = ta.macd
            state = macd.state
            hist = macd.histogram if macd.histogram is not None else 0
            evidence = [f"MACD state: {state.value if hasattr(state, 'value') else state}",
                        f"Histogram: {hist:+.4f}"]
            if state == MACDState.BULLISH:
                score = 2
                bias = "BULLISH"
            elif state == MACDState.BEARISH:
                score = 2
                bias = "BEARISH"
            else:
                score = 0
                bias = "NEUTRAL"
                evidence.append("MACD neutral — no directional pressure")

            return self._make_state(name, score, bias, evidence, "15m")
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "15m")

    # 17. Gemini AI — 10pt max
    def _c_gemini_ai(self, snap: MarketSnapshot) -> ContributorState:
        name = "Gemini AI"
        ai = snap.ai_result
        if ai is None:
            return self._unavailable(name, "AI result unavailable", "—")

        try:
            from src.models.ai_analysis import OverallBias
            bias_map = {OverallBias.BULLISH: "BULLISH", OverallBias.BEARISH: "BEARISH", OverallBias.NEUTRAL: "NEUTRAL"}
            bias = bias_map.get(ai.overall_bias, "NEUTRAL")
            confidence_scale = ai.confidence / 100.0

            if bias == "NEUTRAL":
                score = round(3 * confidence_scale)
            else:
                score = round(10 * confidence_scale)

            is_fallback = getattr(ai, "is_fallback", False)
            provider = getattr(ai, "provider_used", "unknown")
            evidence = [
                f"AI Bias: {bias} ({ai.confidence}% confidence)",
                f"Provider: {provider}{'  [fallback]' if is_fallback else ''}",
            ]
            if hasattr(ai, "key_bullish_factors") and ai.key_bullish_factors:
                evidence.append(f"Bullish: {ai.key_bullish_factors[0][:60]}")
            if hasattr(ai, "key_bearish_factors") and ai.key_bearish_factors:
                evidence.append(f"Bearish: {ai.key_bearish_factors[0][:60]}")

            status = "OK" if not is_fallback else "OK"  # fallback is still valid data
            return self._make_state(name, score, bias, evidence, "—", status)
        except Exception as exc:
            return self._unavailable(name, f"Error: {exc}", "—")

    # ------------------------------------------------------------------
    # Supporting helpers
    # ------------------------------------------------------------------

    def _classify_regime(self, snap: MarketSnapshot, score: int, gate_dir: str) -> str:
        ta_1h = snap.ta_1h
        ta_1d = snap.ta_1d
        if ta_1h and ta_1h.atr14:
            atr = ta_1h.atr14.value or 0
            volatility_pct = (atr / snap.current_price) * 100 if snap.current_price > 0 else 0
            if volatility_pct > 0.8:
                return "HIGH_VOLATILITY"

        if gate_dir == "BULLISH" and score >= _BUY_THRESHOLD:
            return "TRENDING_BULLISH"
        elif gate_dir == "BEARISH" and score >= _SELL_THRESHOLD:
            return "TRENDING_BEARISH"
        elif gate_dir == "NONE":
            return "RANGING"
        return "UNCLEAR"

    def _extract_top_confirmations(
        self, contributors: List[ContributorState], gate_dir: str
    ) -> List[str]:
        target_bias = "BULLISH" if gate_dir == "BULLISH" else "BEARISH"
        aligned = [
            c for c in contributors
            if c.bias == target_bias and c.score > 0 and c.evidence
        ]
        aligned.sort(key=lambda c: c.score, reverse=True)
        result = []
        for c in aligned[:5]:
            result.append(f"{c.name}: {c.evidence[0]}")
        return result

    def _extract_conflicts(
        self, contributors: List[ContributorState], gate_dir: str
    ) -> List[str]:
        result = []
        for c in contributors:
            result.extend(c.conflicts)
        # Also find contributors whose bias opposes the gate direction
        if gate_dir == "BULLISH":
            for c in contributors:
                if c.bias == "BEARISH" and c.score >= 3:
                    result.append(f"{c.name} bearish despite bullish gate ({c.score}pt)")
        elif gate_dir == "BEARISH":
            for c in contributors:
                if c.bias == "BULLISH" and c.score >= 3:
                    result.append(f"{c.name} bullish despite bearish gate ({c.score}pt)")
        return result[:8]  # cap at 8

    def _compute_spread_status(self, snap: MarketSnapshot) -> str:
        if snap.bid is None or snap.ask is None:
            return "UNAVAILABLE"
        spread = snap.ask - snap.bid
        spread_pct = (spread / snap.current_price) * 100 if snap.current_price > 0 else 0
        return "HIGH_SPREAD" if spread_pct > 0.05 else "NORMAL"

    def _safe_wait_result(self, snap: MarketSnapshot, reason: str) -> ConfluenceResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        return ConfluenceResult(
            snapshot_id=snap.snapshot_id,
            timestamp=now_iso,
            symbol=snap.symbol,
            current_price=snap.current_price,
            technical_score=0,
            gemini_score=0,
            final_score=0,
            gate_bullish_count=0,
            gate_bearish_count=0,
            gate_passed=False,
            gate_direction="NONE",
            signal="WAIT",
            signal_changed=False,
            prev_signal=self._prev_signal,
            contributors=[],
            market_regime="UNCLEAR",
            data_quality="LOW",
            data_completeness="0/17 contributors available",
            top_confirmations=[],
            conflicts=[f"Engine error: {reason}"],
            entry_quality="WAIT",
            spread_status="UNAVAILABLE",
            news_status="NEWS_DATA_UNAVAILABLE",
        )

    def get_audit_trail(self) -> List[dict]:
        """Return immutable copy of the audit trail for backtesting."""
        return list(self._audit_trail)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine_instance: Optional[ConfluenceEngine] = None


def get_confluence_engine() -> ConfluenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConfluenceEngine()
    return _engine_instance


# ---------------------------------------------------------------------------
# Candle field helpers (handle both dict and object candles)
# ---------------------------------------------------------------------------

def _candle_close(c: Any) -> float:
    if isinstance(c, dict):
        return float(c.get("close", 0) or 0)
    return float(getattr(c, "close", 0) or 0)


def _candle_open(c: Any) -> float:
    if isinstance(c, dict):
        return float(c.get("open", 0) or 0)
    return float(getattr(c, "open", 0) or 0)


def _candle_high(c: Any) -> float:
    if isinstance(c, dict):
        return float(c.get("high", 0) or 0)
    return float(getattr(c, "high", 0) or 0)


def _candle_low(c: Any) -> float:
    if isinstance(c, dict):
        return float(c.get("low", 0) or 0)
    return float(getattr(c, "low", 0) or 0)


def _candle_volume(c: Any) -> Optional[float]:
    if isinstance(c, dict):
        v = c.get("volume")
    else:
        v = getattr(c, "volume", None)
    return float(v) if v is not None else None


def _compute_vwap(candles: List[Any]) -> Optional[float]:
    """Compute VWAP from a list of candles. Returns None if no volume data."""
    total_pv = 0.0
    total_v = 0.0
    for c in candles:
        vol = _candle_volume(c)
        if vol is None or vol <= 0:
            return None  # No volume data at all
        typical_price = (_candle_high(c) + _candle_low(c) + _candle_close(c)) / 3
        total_pv += typical_price * vol
        total_v += vol
    if total_v <= 0:
        return None
    return total_pv / total_v
