"""
Forward Shadow Resolver Background Worker Service.

Periodically evaluates eligible PENDING forward shadow observations against
completed market candles using the existing ForwardShadowEngine.resolve_forward_signal() logic.

Design Invariants:
1. Reuses existing ForwardShadowEngine.resolve_forward_signal() — zero duplicated logic.
2. Temporal Causality Firewall — outcome_timestamp MUST be strictly > signal_timestamp.
3. Completed Candles Only — uses only closed 5m bars from the candles table.
4. Idempotent & Deterministic — resolved signals are never overwritten or re-counted.
5. Strict Asset Isolation — BTC and XAU are processed independently.
6. Non-Blocking / Resilient — exceptions are safely logged without crashing the server.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.services.historical_data_service import DB_PATH
from src.research.governance.forward_shadow import (
    ForwardShadowEngine,
    get_forward_shadow_engine,
)

logger = logging.getLogger(__name__)

# Default resolver cycle: 60 seconds
DEFAULT_RESOLVER_INTERVAL_SECONDS: int = 60
MAX_SIGNALS_PER_CYCLE: int = 50
MAX_OBSERVATION_EXPIRY_HOURS: float = 48.0


class ForwardShadowResolverWorker:
    """
    Singleton background worker that polls eligible pending forward shadow signals
    and invokes ForwardShadowEngine.resolve_forward_signal() when valid post-T0
    completed candle data exists.
    """

    _instance: Optional["ForwardShadowResolverWorker"] = None
    _class_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: str = DB_PATH) -> "ForwardShadowResolverWorker":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path)
            return cls._instance

    def __init__(
        self,
        db_path: str = DB_PATH,
        interval_seconds: int = DEFAULT_RESOLVER_INTERVAL_SECONDS,
    ) -> None:
        self.db_path = db_path
        self.interval_seconds = interval_seconds
        self.forward_engine = ForwardShadowEngine(db_path=db_path)

        self._worker: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._inst_lock: threading.Lock = threading.Lock()
        self._started: bool = False

        # Observability state
        self._last_run_utc: Optional[str] = None
        self._last_success_utc: Optional[str] = None
        self._last_duration_ms: float = 0.0
        self._last_resolved_count: int = 0
        self._total_evaluated: int = 0
        self._total_resolved: int = 0
        self._failed_count: int = 0
        self._pending_count: int = 0
        self._eligible_count: int = 0
        self._oldest_pending_ts: Optional[str] = None
        self._health_state: str = "INITIALIZED"
        self._last_status_message: str = "INITIALIZED — Not yet started"

    def start(self) -> None:
        """Start the background worker thread (idempotent)."""
        with self._inst_lock:
            if self._started and self._worker and self._worker.is_alive():
                logger.debug("ForwardShadowResolverWorker already running.")
                return
            self._stop_event.clear()
            self._started = True
            self._health_state = "ACTIVE"
            self._worker = threading.Thread(
                target=self._run_loop,
                name="ForwardShadowResolverWorker",
                daemon=True,
            )
            self._worker.start()
            self._last_status_message = "ACTIVE — Resolver worker running"
            logger.info("ForwardShadowResolverWorker started successfully.")

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Signal the worker thread to stop and wait for clean termination."""
        with self._inst_lock:
            if not self._started:
                return
            self._stop_event.set()
            if self._worker and self._worker.is_alive():
                self._worker.join(timeout=timeout_seconds)
            self._started = False
            self._health_state = "IDLE"
            self._last_status_message = "STOPPED — Worker terminated"
            logger.info("ForwardShadowResolverWorker stopped cleanly.")

    def get_status(self) -> Dict[str, Any]:
        """Return operational observability status."""
        next_run: Optional[str] = None
        if self._started and self._last_run_utc:
            try:
                last_dt = datetime.fromisoformat(self._last_run_utc)
                next_run = (last_dt.timestamp() + self.interval_seconds)
                next_run = datetime.fromtimestamp(next_run, tz=timezone.utc).isoformat()
            except Exception:
                next_run = None

        is_running = bool(self._started and self._worker and self._worker.is_alive())
        effective_health = self._health_state if is_running else "OFF"
        if is_running and self._pending_count == 0:
            effective_health = "IDLE"

        return {
            "status": effective_health,
            "is_active": is_running,
            "interval_seconds": self.interval_seconds,
            "last_run": self._last_run_utc,
            "last_success": self._last_success_utc,
            "next_scheduled_run": next_run,
            "processing_duration_ms": round(self._last_duration_ms, 2),
            "pending_count": self._pending_count,
            "eligible_count": self._eligible_count,
            "resolved_count": self._total_resolved,
            "failed_count": self._failed_count,
            "oldest_pending_timestamp": self._oldest_pending_ts,
            "status_message": self._last_status_message,
        }

    def _run_loop(self) -> None:
        """Periodic background evaluation loop."""
        logger.info("ForwardShadowResolverWorker loop active.")
        while not self._stop_event.is_set():
            t_start = time.perf_counter()
            try:
                resolved_count, evaluated_count = self.run_cycle()
                self._last_duration_ms = (time.perf_counter() - t_start) * 1000.0
                self._last_resolved_count = resolved_count
                self._total_resolved += resolved_count
                self._total_evaluated += evaluated_count
                self._last_run_utc = datetime.now(timezone.utc).isoformat()
                self._last_success_utc = self._last_run_utc

                if evaluated_count == 0:
                    self._health_state = "IDLE"
                    self._last_status_message = "IDLE — No pending signals"
                elif resolved_count == 0:
                    self._health_state = "ACTIVE"
                    self._last_status_message = f"ACTIVE — Evaluated {evaluated_count} pending, 0 eligible for resolution yet"
                else:
                    self._health_state = "ACTIVE"
                    self._last_status_message = f"ACTIVE — Successfully resolved {resolved_count} / {evaluated_count} signals"

            except Exception as exc:
                self._last_duration_ms = (time.perf_counter() - t_start) * 1000.0
                self._failed_count += 1
                self._health_state = "DEGRADED"
                logger.error(f"Error in ForwardShadowResolverWorker cycle: {exc}", exc_info=False)
                self._last_status_message = f"DEGRADED — Minor cycle warning: {type(exc).__name__}"

            # Wait for next interval or stop event
            self._stop_event.wait(timeout=self.interval_seconds)

    def run_cycle(self) -> Tuple[int, int]:
        """
        Execute one deterministic evaluation pass across pending signals using the
        two-stage entry-fill state machine (PENDING_ENTRY -> ACTIVE_POSITION -> RESOLVED).
        Returns: (resolved_count, evaluated_count)
        """
        evaluated_count = 0
        resolved_count = 0

        # 1. Fetch pending and active signals
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(forward_shadow_signals)")
                cols = {c[1] for c in cur.fetchall()}
                has_entry_fill = "entry_filled_at" in cols

                stats_row = conn.execute(
                    "SELECT count(*), min(signal_timestamp) FROM forward_shadow_signals WHERE status IN ('PENDING', 'PENDING_ENTRY', 'ACTIVE_POSITION')"
                ).fetchone()
                self._pending_count = stats_row[0] if stats_row else 0
                self._oldest_pending_ts = stats_row[1] if stats_row else None

                fill_col = "entry_filled_at" if has_entry_fill else "NULL as entry_filled_at"
                query = f"""
                    SELECT signal_id, asset, signal_timestamp, direction,
                           entry_price, stop_loss, take_profit_1, take_profit_2,
                           status, {fill_col}
                    FROM forward_shadow_signals
                    WHERE status IN ('PENDING', 'PENDING_ENTRY', 'ACTIVE_POSITION')
                    ORDER BY signal_timestamp ASC
                    LIMIT ?
                """
                pending_rows = conn.execute(query, (MAX_SIGNALS_PER_CYCLE,)).fetchall()
                self._eligible_count = len(pending_rows)
        except Exception as exc:
            logger.error(f"Failed to query pending forward signals: {exc}")
            return 0, 0

        # 2. Process each governance forward signal through the two-stage state machine
        if pending_rows:
            evaluated_count += len(pending_rows)
            for row in pending_rows:
                sig_id = row["signal_id"]
                asset = row["asset"]
                sig_ts_str = row["signal_timestamp"]
                direction = (row["direction"] or "BUY").upper()
                entry = row["entry_price"]
                sl = row["stop_loss"]
                tp1 = row["take_profit_1"]
                curr_status = row["status"]
                entry_filled_at = row["entry_filled_at"]

                if not sl or not entry:
                    continue

                try:
                    sig_dt = datetime.fromisoformat(sig_ts_str.replace("Z", "+00:00"))
                    sig_epoch_ms = int(sig_dt.timestamp() * 1000)
                except Exception:
                    continue

                # Query completed candles strictly after signal timestamp (T0)
                candles = self._get_completed_candles_after(asset=asset, after_iso=sig_ts_str)
                if not candles:
                    continue

                outcome_res = self._evaluate_two_stage_signal(
                    sig_id=sig_id,
                    direction=direction,
                    entry=entry,
                    sl=sl,
                    tp1=tp1,
                    sig_epoch_ms=sig_epoch_ms,
                    status=curr_status,
                    entry_filled_at=entry_filled_at,
                    candles=candles,
                )

                if outcome_res is not None:
                    res_status, exit_price, realized_r, outcome_ts_str, duration_m = outcome_res
                    success = self.forward_engine.resolve_forward_signal(
                        signal_id=sig_id,
                        resolution_status=res_status,
                        outcome_timestamp_utc=outcome_ts_str,
                        exit_price=exit_price,
                        realized_r=realized_r,
                        duration_minutes=duration_m,
                    )
                    if success:
                        resolved_count += 1
                        logger.info(
                            f"[Forward Resolver] Resolved {sig_id} ({asset}) -> {res_status} "
                            f"(R: {realized_r:+.2f}, Exit: {exit_price}) at {outcome_ts_str}"
                        )

        # 3. Additive ML Shadow Observation Resolution Pass (BTC/USD and XAU/USD)
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_shadow_observations'")
                has_ml_table = cur.fetchone() is not None

            if has_ml_table:
                from src.research.ml_shadow.shadow_service import MLShadowService
                shadow_svc = MLShadowService(db_path=self.db_path)
                for target_symbol in ("BTC/USD", "XAU/USD"):
                    try:
                        pending_obs = shadow_svc.store.get_pending_observations(symbol=target_symbol)
                        if pending_obs:
                            earliest_t0 = min(o["timestamp_t0"] for o in pending_obs if o.get("timestamp_t0"))
                            forward_candles = self._get_completed_candles_after(asset=target_symbol, after_iso=earliest_t0)
                            if forward_candles:
                                num_res = shadow_svc.resolve_pending_observations(
                                    symbol=target_symbol,
                                    forward_candles=forward_candles,
                                    max_horizon_candles=200
                                )
                                if num_res > 0:
                                    logger.info(f"[Forward Resolver] Resolved {num_res} pending ML shadow observations for {target_symbol}")
                    except Exception as _ml_sym_exc:
                        logger.debug(f"[Forward Resolver] ML shadow resolution skipped for {target_symbol}: {_ml_sym_exc}")
        except Exception as _ml_exc:
            logger.debug(f"[Forward Resolver] ML shadow resolution pass skipped: {_ml_exc}")

        return resolved_count, evaluated_count

    def _get_completed_candles_after(
        self, asset: str, after_iso: str
    ) -> List[Dict[str, Any]]:
        """Fetch completed 5m market candles chronologically after after_iso."""
        symbol_key = "BTC/USD" if "BTC" in asset.upper() else "XAU/USD"
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT epoch_ms, timestamp, open, high, low, close
                    FROM candles
                    WHERE symbol = ? AND timeframe = '5m' AND timestamp > ?
                    ORDER BY epoch_ms ASC
                    LIMIT 1000
                    """,
                    (symbol_key, after_iso),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as exc:
            logger.debug(f"Could not read candles for {asset}: {exc}")
            return []

    def _evaluate_two_stage_signal(
        self,
        sig_id: str,
        direction: str,
        entry: float,
        sl: float,
        tp1: Optional[float],
        sig_epoch_ms: int,
        status: str,
        entry_filled_at: Optional[str],
        candles: List[Dict[str, Any]],
    ) -> Optional[Tuple[str, float, float, str, float]]:
        """
        Two-stage entry-fill state machine evaluation:
        Stage 1: PENDING / PENDING_ENTRY -> verify limit order touches entry price.
                 If 48h elapse without touching entry -> resolve as NOT_TRIGGERED.
                 Once touched -> transition to ACTIVE_POSITION with entry_filled_at timestamp.
        Stage 2: ACTIVE_POSITION -> monitor TP and SL levels.
                 If both hit on same bar -> resolve as AMBIGUOUS.
                 If TP hit -> resolve as RESOLVED_WIN.
                 If SL hit -> resolve as RESOLVED_LOSS.
                 If 48h elapse after fill -> resolve as RESOLVED_EXPIRED.
        """
        risk = abs(entry - sl)
        if risk <= 0:
            return None

        current_stage = status
        fill_ts = entry_filled_at
        fill_epoch_ms = sig_epoch_ms

        if fill_ts:
            try:
                fill_dt = datetime.fromisoformat(fill_ts.replace("Z", "+00:00"))
                fill_epoch_ms = int(fill_dt.timestamp() * 1000)
            except Exception:
                fill_epoch_ms = sig_epoch_ms

        for c in candles:
            high = c["high"]
            low = c["low"]
            c_ts = c["timestamp"]
            c_epoch_ms = c["epoch_ms"]
            total_duration_minutes = round((c_epoch_ms - sig_epoch_ms) / 60000.0, 1)

            # Stage 1: Check Entry Fill if not yet active
            if current_stage in ("PENDING", "PENDING_ENTRY"):
                # Check 48-hour expiration for unfilled limit order
                if total_duration_minutes > (MAX_OBSERVATION_EXPIRY_HOURS * 60):
                    return ("NOT_TRIGGERED", entry, 0.0, c_ts, total_duration_minutes)

                # Check if market reaches entry price
                is_filled = False
                if direction == "BUY":
                    is_filled = low <= entry
                elif direction == "SELL":
                    is_filled = high >= entry

                if not is_filled:
                    # Still waiting for fill; do NOT check TP or SL
                    continue

                # Entry confirmed filled at candle c
                current_stage = "ACTIVE_POSITION"
                fill_ts = c_ts
                fill_epoch_ms = c_epoch_ms
                self.forward_engine.mark_entry_filled(signal_id=sig_id, entry_filled_at_utc=c_ts)
                logger.info(f"[Forward Resolver] Entry filled for {sig_id} at {c_ts} (Entry={entry})")

            # Stage 2: Evaluate TP/SL on active position
            if current_stage == "ACTIVE_POSITION":
                duration_from_fill_minutes = round((c_epoch_ms - fill_epoch_ms) / 60000.0, 1)

                # Check 48-hour expiration for active trade
                if duration_from_fill_minutes > (MAX_OBSERVATION_EXPIRY_HOURS * 60):
                    return ("RESOLVED_EXPIRED", c["close"], 0.0, c_ts, total_duration_minutes)

                if direction == "BUY":
                    hit_sl = low <= sl
                    hit_tp = (tp1 is not None) and (high >= tp1)

                    if hit_sl and hit_tp:
                        return ("AMBIGUOUS", entry, 0.0, c_ts, total_duration_minutes)
                    elif hit_sl:
                        return ("RESOLVED_LOSS", sl, -1.0, c_ts, total_duration_minutes)
                    elif hit_tp and tp1 is not None:
                        realized_r = round((tp1 - entry) / risk, 2)
                        return ("RESOLVED_WIN", tp1, realized_r, c_ts, total_duration_minutes)

                elif direction == "SELL":
                    hit_sl = high >= sl
                    hit_tp = (tp1 is not None) and (low <= tp1)

                    if hit_sl and hit_tp:
                        return ("AMBIGUOUS", entry, 0.0, c_ts, total_duration_minutes)
                    elif hit_sl:
                        return ("RESOLVED_LOSS", sl, -1.0, c_ts, total_duration_minutes)
                    elif hit_tp and tp1 is not None:
                        realized_r = round((entry - tp1) / risk, 2)
                        return ("RESOLVED_WIN", tp1, realized_r, c_ts, total_duration_minutes)

        return None
