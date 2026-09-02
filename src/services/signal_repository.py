"""
Immutable Signal Repository for the Empirical Backtesting Layer.

Stores every actionable BUY/SELL advisory signal as an immutable JSON record.
Outcome is the only field appended after creation — all original fields are never overwritten.

Storage: signal_records.json in project root (same pattern as paper_trading.json).
Thread-safety: single threading.Lock around all file I/O.

DISCLAIMER: Records advisory signals only. No real trades.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.models.signal_record import (
    SignalRecord,
    SignalOutcome,
    _score_band,
)
from src.models.trading_decision import TradingDecision, TradingSignal

logger = logging.getLogger(__name__)

_REPO_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "signal_records.json",
)

# Duplicate guard: skip a new signal if another with same direction + score
# was recorded within this many seconds.
_DUPLICATE_GUARD_SECONDS = 60

# Data integrity: price boundaries per asset
_MIN_GOLD_PRICE = 500.0
_MAX_GOLD_PRICE = 10_000.0
_MIN_BTC_PRICE = 1_000.0
_MAX_BTC_PRICE = 1_000_000.0


def _matches_symbol(record_symbol: str, target_symbol: Optional[str]) -> bool:
    if not target_symbol:
        return True
    rs_u = (record_symbol or "").upper()
    ts_u = target_symbol.upper()
    is_target_btc = "BTC" in ts_u
    is_target_xau = "XAU" in ts_u or "GOLD" in ts_u
    if is_target_btc:
        return "BTC" in rs_u
    elif is_target_xau:
        return "XAU" in rs_u or "GOLD" in rs_u
    return rs_u == ts_u


def _is_price_valid_for_symbol(price: float, symbol: str) -> bool:
    if not price or price <= 0:
        return False
    s_u = (symbol or "").upper()
    if "BTC" in s_u:
        return _MIN_BTC_PRICE <= price <= _MAX_BTC_PRICE
    elif "XAU" in s_u or "GOLD" in s_u:
        return _MIN_GOLD_PRICE <= price <= _MAX_GOLD_PRICE
    return price > 0


def _safe_str(val: Any) -> Optional[str]:
    if val is None or hasattr(val, "_mock_name") or type(val).__name__ == "MagicMock":
        return None
    if isinstance(val, str):
        return val
    return str(val)


def _safe_float(val: Any) -> Optional[float]:
    if val is None or hasattr(val, "_mock_name") or type(val).__name__ == "MagicMock":
        return None
    try:
        return float(val)
    except Exception:
        return None


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or hasattr(val, "_mock_name") or type(val).__name__ == "MagicMock":
        return default
    try:
        return int(val)
    except Exception:
        return default


class SignalRepository:
    """
    Thread-safe, append-only store for SignalRecord objects.
    Outcomes are written as updates — original signal fields never change.
    """

    def __init__(self, file_path: str = _REPO_FILE_PATH) -> None:
        self._path = file_path
        self._lock = threading.Lock()
        self._ensure_file()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_signal(self, decision: Any) -> Optional[SignalRecord]:
        """
        Create an immutable SignalRecord from a TradingDecision (BUY or SELL only).
        Returns None if the signal is a duplicate or invalid.
        Never overwrites an existing record.
        """
        decision_raw = getattr(decision, "decision", None)
        decision_val = (
            decision_raw.value
            if hasattr(decision_raw, "value") and isinstance(decision_raw.value, str)
            else str(decision_raw)
        )
        if decision_val not in ("BUY", "SELL"):
            return None

        with self._lock:
            records = self._load()

            # ---- Duplicate guard ----
            now_ts = datetime.now(timezone.utc)
            direction = decision_val
            score = (
                getattr(decision, "final_confluence", None)
                or getattr(decision, "confluence_pct", None)
                or getattr(decision, "signal_strength", None)
                or 0
            )
            score = _safe_int(score, 0)
            symbol_str = str(getattr(decision, "symbol", "UNKNOWN"))

            for r in reversed(records[-50:]):  # check most recent 50
                try:
                    if not _matches_symbol(r.get("symbol", ""), symbol_str):
                        continue
                    prev_ts = datetime.fromisoformat(r["signal_timestamp"].replace("Z", "+00:00"))
                    age_s = (now_ts - prev_ts).total_seconds()
                    if (
                        age_s < _DUPLICATE_GUARD_SECONDS
                        and r.get("direction") == direction
                        and r.get("confluence_score") == score
                    ):
                        logger.debug(
                            f"SignalRepository: duplicate signal suppressed "
                            f"({symbol_str} {direction}, score={score}, age={age_s:.1f}s)"
                        )
                        return None
                except Exception:
                    continue

            # ---- Validate price ----
            price = 0.0
            if hasattr(decision, "entry_zone") and decision.entry_zone:
                price = getattr(decision.entry_zone, "min", 0.0) or 0.0
            if price <= 0:
                price = getattr(decision, "entry_price", 0.0) or 0.0
            price = _safe_float(price) or 0.0
            if not _is_price_valid_for_symbol(price, symbol_str):
                logger.warning(
                    f"SignalRepository: impossible entry price {price} for {symbol_str} — signal rejected"
                )
                return None

            # ---- Extract contributor data ----
            contributor_scores: Dict[str, int] = {}
            contributor_directions: Dict[str, str] = {}
            contributor_biases: Dict[str, str] = {}
            strategy_evidence: List[str] = []

            contributors = getattr(decision, "signal_contributors", None)
            if contributors and not hasattr(contributors, "_mock_name"):
                for c in contributors:
                    if not isinstance(c, dict):
                        continue
                    name = c.get("name", "")
                    if not name:
                        continue
                    contributor_scores[name] = c.get("points", 0)
                    contributor_directions[name] = c.get("direction", "UNCHANGED")
                    contributor_biases[name] = c.get("bias", "NEUTRAL")
                    ev = c.get("evidence", [])
                    if ev:
                        strategy_evidence.append(f"{name}: {ev[0]}")

            # ---- Build record ----
            signal_id = str(uuid.uuid4())
            snap_id = _safe_str(getattr(decision, "snapshot_id", None)) or f"NO_SNAP-{signal_id[:8]}"
            conf_val = _safe_float(getattr(decision, "confidence", None))
            raw_prob = (conf_val / 100.0) if conf_val is not None else None

            inval_list = getattr(decision, "invalidation_conditions", None)
            inval_level = inval_list[0] if (inval_list and not hasattr(inval_list, "_mock_name") and len(inval_list) > 0) else None

            record = SignalRecord(
                signal_id=signal_id,
                symbol=symbol_str,
                signal_timestamp=now_ts.isoformat(),
                snapshot_id=snap_id,
                entry_price=round(price, 2),
                direction=direction,
                stop_loss=_safe_float(getattr(decision, "stop_loss", None)),
                take_profit_1=_safe_float(getattr(decision, "take_profit_1", None)),
                take_profit_2=_safe_float(getattr(decision, "take_profit_2", None)),
                invalidation_level=inval_level,
                confluence_score=score,
                technical_score=_safe_int(getattr(decision, "technical_score", 0), 0),
                gemini_score=_safe_int(getattr(decision, "gemini_score", 0), 0),
                score_band=_score_band(score),
                raw_probability=raw_prob,
                calibrated_probability=_safe_float(getattr(decision, "calibrated_probability", None)),
                signal_strength=_safe_int(getattr(decision, "signal_strength", score), score),
                quality_score=_safe_float(getattr(decision, "quality_score", None)),
                setup_grade=_safe_str(getattr(decision, "setup_grade", None)),
                contributor_scores=contributor_scores,
                contributor_directions=contributor_directions,
                contributor_biases=contributor_biases,
                data_quality=_safe_str(getattr(decision, "data_quality", None)) or "UNKNOWN",
                gate_direction=_safe_str(getattr(decision, "gate_direction", None)) or "NONE",
                gate_passed=bool(getattr(decision, "gate_passed", False)),
                market_regime=_safe_str(getattr(decision, "market_regime", None)) or "UNCLEAR",
                market_session=_safe_str(getattr(decision, "market_session", None)),
                mtf_alignment=_safe_str(getattr(decision, "mtf_alignment_summary", None)),
                timeframe=_safe_str(getattr(decision, "timeframe", None)) or "15m",
                strategy_evidence=strategy_evidence[:20],
                conflicts=list(decision.conflicts or [])[:10] if (getattr(decision, "conflicts", None) and not hasattr(decision.conflicts, "_mock_name")) else [],
                entry_quality=_safe_str(getattr(decision, "entry_quality", None)) or "UNKNOWN",
                outcome=SignalOutcome(
                    outcome="OPEN",
                    transaction_cost_included=False,
                    spread_at_entry=_safe_float(getattr(decision, "_spread_at_entry", None)),
                ),
            )

            # Append to store
            records.append(record.model_dump())
            self._save(records)
            logger.info(
                f"SignalRepository: recorded {symbol_str} {direction} signal "
                f"#{signal_id[:8]} @ {price:.2f} (score={score})"
            )
            return record

    def get_pending_outcome_signals(self, symbol: Optional[str] = None) -> List[SignalRecord]:
        """Return signals with outcome=OPEN that still need labeling (optionally filtered by symbol)."""
        with self._lock:
            records = self._load()
        result = []
        for r in records:
            if symbol and not _matches_symbol(r.get("symbol", ""), symbol):
                continue
            outcome = r.get("outcome") or {}
            if outcome.get("outcome") == "OPEN":
                try:
                    result.append(SignalRecord(**r))
                except Exception as exc:
                    logger.warning(f"SignalRepository: malformed record skipped: {exc}")
        return result

    def update_outcome(self, signal_id: str, outcome: SignalOutcome) -> bool:
        """
        Append outcome to an existing signal.
        The original signal fields are NEVER modified.
        Returns True on success, False if signal not found.
        """
        with self._lock:
            records = self._load()
            for r in records:
                if r.get("signal_id") == signal_id:
                    r["outcome"] = outcome.model_dump()
                    self._save(records)
                    logger.debug(
                        f"SignalRepository: outcome={outcome.outcome} "
                        f"for signal #{signal_id[:8]}"
                    )
                    return True
        logger.warning(f"SignalRepository: signal {signal_id[:8]} not found for outcome update")
        return False

    def update_running_excursions(
        self, signal_id: str, mfe: float, mae: float
    ) -> None:
        """Update running MFE/MAE fields (not the outcome) for an open signal."""
        with self._lock:
            records = self._load()
            for r in records:
                if r.get("signal_id") == signal_id:
                    r["current_mfe"] = round(mfe, 4)
                    r["current_mae"] = round(mae, 4)
                    self._save(records)
                    return

    def get_all_completed(self, symbol: Optional[str] = None) -> List[SignalRecord]:
        """Return all signals with a terminal outcome (optionally filtered by symbol)."""
        with self._lock:
            records = self._load()
        result = []
        terminal = {"WIN", "LOSS", "BREAKEVEN", "EXPIRED", "INVALID"}
        for r in records:
            if symbol and not _matches_symbol(r.get("symbol", ""), symbol):
                continue
            outcome = r.get("outcome") or {}
            if outcome.get("outcome") in terminal:
                try:
                    result.append(SignalRecord(**r))
                except Exception as exc:
                    logger.warning(f"SignalRepository: malformed record skipped: {exc}")
        return result

    def get_all(self, symbol: Optional[str] = None) -> List[SignalRecord]:
        """Return all signal records (optionally filtered by symbol)."""
        with self._lock:
            records = self._load()
        result = []
        for r in records:
            if symbol and not _matches_symbol(r.get("symbol", ""), symbol):
                continue
            try:
                result.append(SignalRecord(**r))
            except Exception as exc:
                logger.warning(f"SignalRepository: malformed record skipped: {exc}")
        return result

    def get_by_id(self, signal_id: str) -> Optional[SignalRecord]:
        """Return a single signal record by ID."""
        with self._lock:
            records = self._load()
        for r in records:
            if r.get("signal_id") == signal_id:
                try:
                    return SignalRecord(**r)
                except Exception:
                    return None
        return None

    def validate_dataset(self) -> Tuple[List[str], int]:
        """
        Validate all records for data integrity.
        Returns (list_of_issue_strings, valid_record_count).
        """
        with self._lock:
            records = self._load()

        issues: List[str] = []
        seen_ids: set = set()
        valid_count = 0

        now_utc = datetime.now(timezone.utc)

        for r in records:
            sid = r.get("signal_id", "UNKNOWN")
            sym = r.get("symbol", "UNKNOWN")

            # Duplicate signal ID
            if sid in seen_ids:
                issues.append(f"DUPLICATE signal_id={sid[:8]}")
                continue
            seen_ids.add(sid)

            # Impossible price
            price = r.get("entry_price", 0.0)
            if not _is_price_valid_for_symbol(price or 0, sym):
                issues.append(
                    f"IMPOSSIBLE_PRICE signal_id={sid[:8]} symbol={sym} entry_price={price}"
                )
                continue

            # Future timestamp
            ts_str = r.get("signal_timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts > now_utc + timedelta(seconds=60):
                    issues.append(
                        f"FUTURE_TIMESTAMP signal_id={sid[:8]} ts={ts_str}"
                    )
                    continue
            except Exception:
                issues.append(f"MALFORMED_TIMESTAMP signal_id={sid[:8]} ts={ts_str}")
                continue

            # Invalid R calculation (if outcome present)
            outcome = r.get("outcome") or {}
            realized_r = outcome.get("realized_r")
            if realized_r is not None and (realized_r < -100 or realized_r > 100):
                issues.append(
                    f"INVALID_R signal_id={sid[:8]} realized_r={realized_r}"
                )
                continue

            # Validate direction
            direction = r.get("direction", "")
            if direction not in ("BUY", "SELL"):
                issues.append(
                    f"INCORRECT_DIRECTION signal_id={sid[:8]} direction={direction}"
                )
                continue

            valid_count += 1

        return issues, valid_count

    def count(self) -> Dict[str, int]:
        """Return a count summary of signal statuses."""
        with self._lock:
            records = self._load()
        counts: Dict[str, int] = {
            "total": len(records),
            "OPEN": 0,
            "WIN": 0,
            "LOSS": 0,
            "BREAKEVEN": 0,
            "EXPIRED": 0,
            "INVALID": 0,
        }
        for r in records:
            outcome = (r.get("outcome") or {}).get("outcome", "OPEN")
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _ensure_file(self) -> None:
        if not os.path.exists(self._path) or os.path.getsize(self._path) == 0:
            logger.info(f"SignalRepository: initializing {self._path}")
            self._save([])

    def _load(self) -> List[Dict[str, Any]]:
        """Load raw records list. Caller must hold _lock."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            logger.error(f"SignalRepository: JSON parse error in {self._path} — returning []")
            return []
        except Exception as exc:
            logger.error(f"SignalRepository: read error: {exc}")
            return []

    def _save(self, records: List[Dict[str, Any]]) -> None:
        """Save raw records list. Caller must hold _lock."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
        except Exception as exc:
            logger.error(f"SignalRepository: write error: {exc}")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_repo_instance: Optional[SignalRepository] = None


def get_signal_repository() -> SignalRepository:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = SignalRepository()
    return _repo_instance
