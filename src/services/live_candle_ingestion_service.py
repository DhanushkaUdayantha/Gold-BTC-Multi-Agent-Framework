"""
Live 5-Minute Candle Ingestion Service.

Continuously extends the existing 2016–2026 historical SQLite repository with
newly completed 5-minute market candles from live providers.

Design Principles:
──────────────────
1. IMMUTABILITY  — Original dataset OHLCV values are never modified.
                   Live candles use INSERT OR IGNORE so any collision with an
                   existing row is silently discarded (not overwritten).
2. COMPLETENESS  — Only CLOSED (completed) 5m candles are stored.
                   The currently-forming candle is always excluded.
3. SINGLETON     — One worker thread per process.  Calling start() a second
                   time is a safe no-op.
4. RECOVERY      — On startup the worker immediately fetches all candles
                   between the last stored epoch and the latest completed
                   5m boundary, in provider-safe batches.
5. ISOLATION     — BTC failure never blocks XAU ingestion and vice-versa.
6. RATE-SAFETY   — Fetches only the missing range; respects Binance 1 200 rq/min
                   and Yahoo Finance informal limits.
7. UTC           — epoch_ms is the canonical timestamp; local clock is never
                   used to decide candle completeness.

DISCLAIMER: Research and analytical modelling only.  No real trades executed.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.services.historical_data_service import HistoricalDataService, DB_PATH

logger = logging.getLogger(__name__)

# ── Ingestion schedule ──────────────────────────────────────────────────────
INGESTION_INTERVAL_SECONDS: int = 300          # 5 minutes
CANDLE_INTERVAL_MS:         int = 300_000      # 5-minute candle width in ms

# ── Binance constants ───────────────────────────────────────────────────────
BINANCE_KLINES_URL: str = "https://api.binance.com/api/v3/klines"
BINANCE_MAX_LIMIT:  int = 1_000                # max candles per request
BINANCE_SLEEP_S:    float = 0.08              # ~12 rq/s ≪ 1 200 rq/min limit

# ── Yahoo Finance constants ─────────────────────────────────────────────────
YAHOO_CHART_URL:    str = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_SLEEP_S:      float = 0.5

# ── Retry policy ────────────────────────────────────────────────────────────
MAX_RETRIES:        int = 3
RETRY_BASE_S:       float = 10.0
RETRY_MAX_S:        float = 120.0


# ── Helper: latest completed 5m boundary ────────────────────────────────────

def _latest_completed_5m_epoch_ms() -> int:
    """Return the epoch_ms of the LAST fully-closed 5-minute candle."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # Floor to the most recent 5-minute mark, then subtract one interval
    # so the currently-forming candle is excluded.
    last_closed_ms = (now_ms // CANDLE_INTERVAL_MS) * CANDLE_INTERVAL_MS - CANDLE_INTERVAL_MS
    return last_closed_ms


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LiveCandleIngestionService:
    """
    Singleton background service that continuously appends live 5m candles
    to the existing historical SQLite repository.
    """

    _instance: Optional["LiveCandleIngestionService"] = None
    _class_lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path     = db_path
        self.data_service = HistoricalDataService.get_instance()
        self._worker:     Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._started:    bool = False
        self._inst_lock:  threading.Lock = threading.Lock()
        self._init_status_table()

    # ── Singleton factory ────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "LiveCandleIngestionService":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the ingestion daemon thread (safe to call multiple times)."""
        with self._inst_lock:
            if self._started and self._worker and self._worker.is_alive():
                logger.debug("LiveCandleIngestion: already running — start() is a no-op.")
                return
            self._stop_event.clear()
            self._started = True
            self._worker  = threading.Thread(
                target=self._run_loop,
                name="LiveCandleIngestionWorker",
                daemon=True,
            )
            self._worker.start()
            logger.info("LiveCandleIngestion: daemon thread started.")

    def stop(self) -> None:
        """Signal the worker to terminate gracefully."""
        self._stop_event.set()
        logger.info("LiveCandleIngestion: stop requested.")

    # ── Status table init ────────────────────────────────────────────────────

    def _init_status_table(self) -> None:
        """Create live_ingestion_status table if it doesn't exist."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS live_ingestion_status (
                    symbol                   TEXT PRIMARY KEY,
                    timeframe                TEXT NOT NULL DEFAULT '5m',
                    last_candle_epoch_ms     INTEGER,
                    last_candle_timestamp    TEXT,
                    last_ingested_at         TEXT,
                    baseline_candles         INTEGER DEFAULT 0,
                    live_candles_added       INTEGER DEFAULT 0,
                    baseline_start           TEXT,
                    baseline_end             TEXT,
                    status                   TEXT DEFAULT 'INITIALIZING',
                    last_error               TEXT
                )
            """)
            # Migrate: add missing columns if the table already exists without them
            for col, typedef in [
                ("baseline_candles",   "INTEGER DEFAULT 0"),
                ("live_candles_added", "INTEGER DEFAULT 0"),
                ("baseline_start",     "TEXT"),
                ("baseline_end",       "TEXT"),
            ]:
                try:
                    conn.execute(
                        f"ALTER TABLE live_ingestion_status ADD COLUMN {col} {typedef}"
                    )
                except sqlite3.OperationalError:
                    pass   # column already exists
            conn.commit()
        finally:
            conn.close()

    # ── Main worker loop ─────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Worker thread: catch-up on startup, then poll every 5 minutes."""
        logger.info("LiveCandleIngestion: worker thread entered.")
        try:
            # Immediate catch-up pass on startup
            self._ingest_all_symbols(is_startup=True)

            while not self._stop_event.is_set():
                # Sleep in small chunks so stop() is responsive
                for _ in range(INGESTION_INTERVAL_SECONDS * 2):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.5)

                if self._stop_event.is_set():
                    break

                self._ingest_all_symbols(is_startup=False)
        except Exception as exc:
            logger.error(f"LiveCandleIngestion: worker loop crashed: {exc}", exc_info=True)
        finally:
            logger.info("LiveCandleIngestion: worker thread exiting.")

    def _ingest_all_symbols(self, is_startup: bool = False) -> None:
        """
        Run one full ingestion cycle for BTC/USD then XAU/USD.
        Each symbol is independent — failure in one does not prevent the other.
        """
        label = "startup catch-up" if is_startup else "scheduled cycle"
        logger.info(f"LiveCandleIngestion: beginning {label}.")

        # ── BTC/USD ──────────────────────────────────────────────────────────
        try:
            self._ingest_btc()
        except Exception as exc:
            logger.error(f"LiveCandleIngestion: BTC/USD cycle error: {exc}", exc_info=True)
            self._update_status("BTC/USD", status="ERROR", last_error=str(exc))

        if self._stop_event.is_set():
            return

        # ── XAU/USD ──────────────────────────────────────────────────────────
        try:
            self._ingest_xau()
        except Exception as exc:
            logger.error(f"LiveCandleIngestion: XAU/USD cycle error: {exc}", exc_info=True)
            self._update_status("XAU/USD", status="ERROR", last_error=str(exc))

    # ── BTC ingestion ─────────────────────────────────────────────────────────

    def _ingest_btc(self) -> None:
        """
        Fetch missing BTC/USD 5m candles from Binance BTCUSDT API.
        Only closed (completed) candles are inserted; open/forming candle excluded.
        Uses INSERT OR IGNORE — original dataset candles can never be overwritten.
        """
        self._update_status("BTC/USD", status="SYNCING")

        latest_stored_ms = self._get_latest_epoch("BTC/USD", "5m")
        target_end_ms    = _latest_completed_5m_epoch_ms()

        if latest_stored_ms is None:
            logger.warning("LiveCandleIngestion: BTC/USD has no stored 5m candles — skipping.")
            self._update_status("BTC/USD", status="ERROR",
                                last_error="No baseline data found; cannot determine catch-up start.")
            return

        # Nothing to fetch
        if latest_stored_ms >= target_end_ms:
            logger.info("LiveCandleIngestion: BTC/USD 5m is already current.")
            self._update_status("BTC/USD", status="LIVE", last_error=None)
            return

        logger.info(
            f"LiveCandleIngestion: BTC/USD catch-up "
            f"{self._fmt_ms(latest_stored_ms + 1)} → {self._fmt_ms(target_end_ms)}"
        )

        total_added = 0
        fetch_start_ms = latest_stored_ms + 1

        while fetch_start_ms <= target_end_ms and not self._stop_event.is_set():
            candles_raw = self._fetch_binance_klines(
                start_ms=fetch_start_ms,
                end_ms=target_end_ms,
                limit=BINANCE_MAX_LIMIT,
            )
            if not candles_raw:
                break

            # Filter out the currently-forming candle (close_time >= now)
            now_ms     = int(datetime.now(timezone.utc).timestamp() * 1000)
            closed_raw = [c for c in candles_raw if c["close_time_ms"] < now_ms]

            if closed_raw:
                saved = self._save_live("BTC/USD", "BTCUSDT", "5m", "binance_live", closed_raw)
                total_added += saved

            last_open_ms = candles_raw[-1]["epoch_ms"]
            if last_open_ms <= fetch_start_ms:
                break
            fetch_start_ms = last_open_ms + CANDLE_INTERVAL_MS
            time.sleep(BINANCE_SLEEP_S)

        self._update_status(
            "BTC/USD",
            status="LIVE",
            live_added_delta=total_added,
            last_error=None,
        )
        logger.info(f"LiveCandleIngestion: BTC/USD added {total_added} new candles.")

    def _fetch_binance_klines(
        self,
        start_ms: int,
        end_ms: int,
        limit: int = BINANCE_MAX_LIMIT,
    ) -> List[Dict[str, Any]]:
        """
        Call Binance /api/v3/klines for BTCUSDT 5m.
        Returns a list of dicts with epoch_ms, close_time_ms, open/high/low/close/volume.
        Retries with exponential back-off on transient errors.
        """
        params = {
            "symbol":    "BTCUSDT",
            "interval":  "5m",
            "startTime": start_ms,
            "endTime":   end_ms,
            "limit":     limit,
        }
        backoff = RETRY_BASE_S
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=12.0)
                if resp.status_code == 429:
                    logger.warning(f"LiveCandleIngestion: Binance 429 — sleeping {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, RETRY_MAX_S)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list) or not data:
                    return []
                return [
                    {
                        "epoch_ms":      int(item[0]),     # open time
                        "close_time_ms": int(item[6]),     # close time
                        "open":   float(item[1]),
                        "high":   float(item[2]),
                        "low":    float(item[3]),
                        "close":  float(item[4]),
                        "volume": float(item[5]),
                    }
                    for item in data
                ]
            except requests.RequestException as exc:
                logger.warning(
                    f"LiveCandleIngestion: Binance fetch attempt {attempt}/{MAX_RETRIES}: {exc}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, RETRY_MAX_S)
        return []

    # ── XAU ingestion ─────────────────────────────────────────────────────────

    def _ingest_xau(self) -> None:
        """
        Fetch missing XAU/USD 5m candles from Yahoo Finance GC=F.
        Note: Yahoo's free tier provides at most ~60 days of 5m history.
        Any gap before that window is left as-is; no synthetic candles are generated.
        Only completed candles are inserted with INSERT OR IGNORE.
        """
        self._update_status("XAU/USD", status="SYNCING")

        latest_stored_ms = self._get_latest_epoch("XAU/USD", "5m")
        target_end_ms    = _latest_completed_5m_epoch_ms()

        if latest_stored_ms is None:
            logger.warning("LiveCandleIngestion: XAU/USD has no stored 5m candles — skipping.")
            self._update_status("XAU/USD", status="ERROR",
                                last_error="No baseline data found; cannot determine catch-up start.")
            return

        if latest_stored_ms >= target_end_ms:
            logger.info("LiveCandleIngestion: XAU/USD 5m is already current.")
            self._update_status("XAU/USD", status="LIVE", last_error=None)
            return

        # Yahoo Finance 5m lookback limit ≈ 60 days
        yahoo_lookback_ms  = 60 * 24 * 60 * CANDLE_INTERVAL_MS   # 60 days in ms
        oldest_fetchable_ms = target_end_ms - yahoo_lookback_ms

        fetch_start_ms = max(latest_stored_ms + 1, oldest_fetchable_ms)
        gap_ms = max(0, oldest_fetchable_ms - (latest_stored_ms + 1))

        if gap_ms > 0:
            gap_days = gap_ms / (24 * 3600 * 1000)
            logger.warning(
                f"LiveCandleIngestion: XAU/USD historical gap of ~{gap_days:.1f} days "
                f"cannot be recovered (Yahoo Finance 5m lookback limited to 60 days). "
                f"Gap is left intact — no synthetic candles generated."
            )
            self._update_status(
                "XAU/USD",
                status="SYNCING",
                last_error=(
                    f"Unrecoverable historical gap ~{gap_days:.0f}d "
                    f"({self._fmt_ms(latest_stored_ms + 1)} → "
                    f"{self._fmt_ms(oldest_fetchable_ms)}). "
                    "Provider lookback window exceeded. Going forward, all new candles captured."
                ),
            )

        logger.info(
            f"LiveCandleIngestion: XAU/USD catch-up "
            f"{self._fmt_ms(fetch_start_ms)} → {self._fmt_ms(target_end_ms)}"
        )

        candles_raw = self._fetch_yahoo_5m(
            start_ms=fetch_start_ms,
            end_ms=target_end_ms,
        )

        total_added = 0
        if candles_raw:
            saved = self._save_live("XAU/USD", "GC=F", "5m", "yahoo_live", candles_raw)
            total_added += saved

        # Determine accurate status based on latest candle freshness
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        latest_after_ms = self._get_latest_epoch("XAU/USD", "5m") or latest_stored_ms
        is_fresh = (now_ms - (latest_after_ms or 0)) < (24 * 3600 * 1000)  # within 24 hours

        if is_fresh and (total_added > 0 or latest_after_ms >= target_end_ms):
            status = "LIVE"
            note = None
        else:
            status = "DATA GAP"
            note = (
                "Historical gap (2026-05-31 to present). "
                "Analysis running on all valid available historical data."
            )

        self._update_status(
            "XAU/USD",
            status=status,
            live_added_delta=total_added,
            last_error=note,
        )
        logger.info(f"LiveCandleIngestion: XAU/USD status={status}, added {total_added} new candles.")

    def _fetch_yahoo_5m(
        self,
        start_ms: int,
        end_ms: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch GC=F (Gold Futures) 5m candles from Yahoo Finance chart API.
        Returns closed candles only.
        Retries with exponential back-off on transient errors.
        """
        ticker = "GC=F"
        url    = YAHOO_CHART_URL.format(ticker=ticker)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        # Clamp to provider lookback
        start_s = start_ms // 1000
        # Yahoo Finance 5m intraday allows at most 5-7 days range
        params = {
            "interval": "5m",
            "range": "5d",
            "includePrePost": "false",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }

        backoff = RETRY_BASE_S
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=15.0)
                if resp.status_code == 429:
                    logger.warning(f"LiveCandleIngestion: Yahoo 429 — sleeping {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, RETRY_MAX_S)
                    continue
                resp.raise_for_status()
                data = resp.json()

                results = data.get("chart", {}).get("result", [])
                if not results:
                    logger.info("LiveCandleIngestion: Yahoo Finance returned no GC=F data.")
                    return []

                result  = results[0]
                ts_list = result.get("timestamp", [])
                quotes  = result.get("indicators", {}).get("quote", [{}])[0]
                opens   = quotes.get("open",   [])
                highs   = quotes.get("high",   [])
                lows    = quotes.get("low",    [])
                closes  = quotes.get("close",  [])
                volumes = quotes.get("volume", [])

                if not ts_list:
                    return []

                candles: List[Dict[str, Any]] = []
                for i, ts in enumerate(ts_list):
                    if ts is None:
                        continue
                    epoch_ms_c  = int(ts) * 1000
                    close_ms    = epoch_ms_c + CANDLE_INTERVAL_MS - 1

                    # Skip the forming candle
                    if close_ms >= now_ms:
                        continue

                    try:
                        o = float(opens[i])   if opens[i]  is not None else None
                        h = float(highs[i])   if highs[i]  is not None else None
                        lo= float(lows[i])    if lows[i]   is not None else None
                        c = float(closes[i])  if closes[i] is not None else None
                        v = float(volumes[i]) if (i < len(volumes) and volumes[i] is not None) else 0.0
                    except (TypeError, ValueError, IndexError):
                        continue

                    if any(x is None or x <= 0 for x in [o, h, lo, c]):
                        continue

                    candles.append({
                        "epoch_ms":      epoch_ms_c,
                        "close_time_ms": close_ms,
                        "open":   o,
                        "high":   h,
                        "low":    lo,
                        "close":  c,
                        "volume": v,
                    })

                time.sleep(YAHOO_SLEEP_S)
                return candles

            except requests.RequestException as exc:
                logger.warning(
                    f"LiveCandleIngestion: Yahoo fetch attempt {attempt}/{MAX_RETRIES}: {exc}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, RETRY_MAX_S)
        return []

    # ── Save live candles (INSERT OR IGNORE) ──────────────────────────────────

    def _save_live(
        self,
        symbol:        str,
        source_symbol: str,
        timeframe:     str,
        source:        str,
        raw_candles:   List[Dict[str, Any]],
    ) -> int:
        """
        Validate raw candles and persist using INSERT OR IGNORE.
        The original historical dataset can never be overwritten.
        Returns the number of newly inserted candles.
        """
        if not raw_candles:
            return 0

        # Normalise to the format expected by validate_candles()
        for_validation = [
            {
                "epoch_ms": c["epoch_ms"],
                "open":     c["open"],
                "high":     c["high"],
                "low":      c["low"],
                "close":    c["close"],
                "volume":   c.get("volume", 0.0),
                "is_closed": True,
            }
            for c in raw_candles
        ]

        valid_candles, _ = self.data_service.validate_candles(
            raw_candles=for_validation,
            symbol=symbol,
            source_symbol=source_symbol,
            timeframe=timeframe,
            source=source,
        )
        if not valid_candles:
            return 0

        # Build tuples
        rows = [
            (
                c.symbol,
                c.source_symbol,
                c.timeframe,
                c.timestamp,
                c.epoch_ms,
                c.open,
                c.high,
                c.low,
                c.close,
                c.volume,
                1,          # is_closed = True
                c.source,
            )
            for c in valid_candles
        ]

        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO candles (
                    symbol, source_symbol, timeframe, timestamp, epoch_ms,
                    open, high, low, close, volume, is_closed, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            inserted = cur.rowcount if cur.rowcount >= 0 else 0
            # rowcount from executemany reflects total affected rows
            # Use a count diff for accuracy when rowcount == -1 (some drivers)
            if cur.rowcount < 0:
                inserted = len(rows)  # conservative; duplicates silently discarded
            return inserted
        finally:
            conn.close()

    # ── Status helpers ────────────────────────────────────────────────────────

    def _get_latest_epoch(self, symbol: str, timeframe: str) -> Optional[int]:
        """Return MAX(epoch_ms) for a given symbol/timeframe, or None if empty."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT MAX(epoch_ms) FROM candles WHERE symbol=? AND timeframe=?",
                (symbol, timeframe),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else None
        finally:
            conn.close()

    def _update_status(
        self,
        symbol: str,
        status: str = "LIVE",
        live_added_delta: int = 0,
        last_error: Optional[str] = None,
    ) -> None:
        """
        Upsert a row in live_ingestion_status.
        Computes baseline_candles / baseline_end from the earliest 'kaggle'/'csv*' source rows.
        """
        conn = self._get_conn()
        try:
            # Last stored 5m candle (overall, including new live ones)
            cur = conn.execute(
                """
                SELECT MAX(epoch_ms), MAX(timestamp)
                FROM candles
                WHERE symbol=? AND timeframe='5m'
                """,
                (symbol,),
            )
            row = cur.fetchone()
            last_ep_ms = row[0] if row and row[0] is not None else None
            last_ts    = row[1] if row and row[1] is not None else None

            # Baseline stats (source in ('kaggle','csv_import','yahoo','binance') = original data)
            live_sources = ("'binance_live'", "'yahoo_live'")
            live_src_str = ", ".join(live_sources)

            cur2 = conn.execute(
                f"""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM candles
                WHERE symbol=? AND timeframe='5m'
                  AND source NOT IN ({live_src_str})
                """,
                (symbol,),
            )
            base_row   = cur2.fetchone()
            base_cnt   = base_row[0] or 0
            base_start = base_row[1]
            base_end   = base_row[2]

            # Live candles added
            cur3 = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM candles
                WHERE symbol=? AND timeframe='5m'
                  AND source IN ({live_src_str})
                """,
                (symbol,),
            )
            live_cnt = (cur3.fetchone()[0] or 0)

            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO live_ingestion_status (
                    symbol, timeframe, last_candle_epoch_ms, last_candle_timestamp,
                    last_ingested_at, baseline_candles, live_candles_added,
                    baseline_start, baseline_end, status, last_error
                ) VALUES (?, '5m', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    last_candle_epoch_ms  = excluded.last_candle_epoch_ms,
                    last_candle_timestamp = excluded.last_candle_timestamp,
                    last_ingested_at      = excluded.last_ingested_at,
                    baseline_candles      = excluded.baseline_candles,
                    live_candles_added    = excluded.live_candles_added,
                    baseline_start        = excluded.baseline_start,
                    baseline_end          = excluded.baseline_end,
                    status                = excluded.status,
                    last_error            = excluded.last_error
                """,
                (
                    symbol,
                    last_ep_ms,
                    last_ts,
                    now_iso,
                    base_cnt,
                    live_cnt,
                    base_start,
                    base_end,
                    status,
                    last_error,
                ),
            )
            conn.commit()

            # Invalidate dataset status cache so the frontend sees fresh data
            self.data_service._status_cache    = None
            self.data_service._status_cache_ts = 0.0
        finally:
            conn.close()

    def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Return live ingestion status for all symbols from live_ingestion_status table.
        Also includes total_candles (baseline + live) for each symbol.
        """
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM live_ingestion_status ORDER BY symbol")
            rows = cur.fetchall()
            result: Dict[str, Any] = {}
            for row in rows:
                sym = row[0]
                base_cnt   = row[5] or 0
                live_cnt   = row[6] or 0
                result[sym] = {
                    "symbol":                  sym,
                    "timeframe":               row[1],
                    "last_candle_epoch_ms":    row[2],
                    "last_candle_timestamp":   row[3],
                    "last_ingested_at":        row[4],
                    "baseline_candles":        base_cnt,
                    "live_candles_added":      live_cnt,
                    "total_candles":           base_cnt + live_cnt,
                    "baseline_start":          row[7],
                    "baseline_end":            row[8],
                    "status":                  row[9] or "INITIALIZING",
                    "last_error":              row[10],
                }
            return result
        finally:
            conn.close()

    # ── Utility ───────────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def _fmt_ms(epoch_ms: int) -> str:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
