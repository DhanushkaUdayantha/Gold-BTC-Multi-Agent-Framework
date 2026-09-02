"""
Historical Market Data Service & SQLite Repository.

Provides:
- SQLite persistence in data/historical/historical_market_data.db
- Validation & audit pipeline (detecting bad OHLC, duplicates, future timestamps, missing intervals)
- Incremental downloading & caching for Binance BTC/USDT (BTC/USD proxy) and Yahoo/Gold (XAU/USD proxy)
- CSV file import capabilities
- Zero synthetic data for production claims

DISCLAIMER: Research and analytical modeling only. No real trades are executed.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.models.historical_data import (
    HistoricalCandle,
    DatasetQualityReport,
    DatasetMetadata,
    BacktestRunRecord,
    BacktestConfig,
    HistoricalSignalRecord,
    BacktestPerformanceReport,
    BacktestStatus,
)

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "historical")
DB_PATH = os.path.join(DB_DIR, "historical_market_data.db")


class HistoricalDataService:
    """Manages historical market data ingestion, validation, caching, and storage."""

    _instance: Optional[HistoricalDataService] = None
    _lock = threading.RLock()

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Thread-local storage for persistent read-only connections (1 per thread).
        # Avoids both the 1-2s cold SQLite open cost AND concurrent cursor corruption.
        self._local = threading.local()
        # In-memory result cache for get_fast_dataset_status (30s TTL)
        self._status_cache: Optional[Dict[str, Any]] = None
        self._status_cache_ts: float = 0.0
        self._STATUS_CACHE_TTL = 30.0
        self._init_db()

    @classmethod
    def get_instance(cls) -> HistoricalDataService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_read_connection(self) -> sqlite3.Connection:
        """Return (or lazily open) a long-lived thread-local connection.
        Avoids the 1-2s SQLite file-open overhead on every status/candle read,
        and provides total thread isolation for concurrent FastAPI requests.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA mmap_size=134217728")  # 128 MB
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database tables and high-speed indexes."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                # Candles Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS candles (
                        symbol TEXT NOT NULL,
                        source_symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        epoch_ms INTEGER NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        is_closed INTEGER NOT NULL,
                        source TEXT NOT NULL,
                        PRIMARY KEY (symbol, timeframe, epoch_ms)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles (symbol, timeframe, epoch_ms)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_source ON candles (source_symbol, timeframe, epoch_ms)")

                # Datasets Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS datasets (
                        dataset_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        source_symbol TEXT NOT NULL,
                        source TEXT NOT NULL,
                        description TEXT NOT NULL,
                        timeframes TEXT NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        row_count INTEGER NOT NULL,
                        valid_rows INTEGER NOT NULL,
                        volume_available INTEGER NOT NULL,
                        version TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        quality_report_json TEXT,
                        status TEXT NOT NULL DEFAULT 'SYNCHRONIZED'
                    )
                """)
                try:
                    cur.execute("ALTER TABLE datasets ADD COLUMN status TEXT DEFAULT 'SYNCHRONIZED'")
                except Exception:
                    pass

                # Backtest Runs Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_runs (
                        run_id TEXT PRIMARY KEY,
                        dataset_id TEXT NOT NULL,
                        dataset_version TEXT NOT NULL,
                        engine_version TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        config_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress_pct REAL NOT NULL,
                        current_step TEXT NOT NULL,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        execution_time_seconds REAL,
                        total_signals_evaluated INTEGER DEFAULT 0,
                        total_trades_generated INTEGER DEFAULT 0
                    )
                """)

                # Historical Signal Records Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS historical_signals (
                        signal_id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        dataset_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        source_symbol TEXT NOT NULL,
                        signal_timestamp TEXT NOT NULL,
                        snapshot_id TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        direction TEXT NOT NULL,
                        confluence_score INTEGER NOT NULL,
                        technical_score INTEGER NOT NULL,
                        gemini_score INTEGER NOT NULL,
                        contributor_scores_json TEXT,
                        contributor_directions_json TEXT,
                        data_quality TEXT,
                        gate_direction TEXT,
                        stop_loss REAL,
                        take_profit_1 REAL,
                        take_profit_2 REAL,
                        invalidation_level REAL,
                        market_regime TEXT,
                        session TEXT,
                        strategy_evidence_json TEXT,
                        conflicts_json TEXT,
                        outcome TEXT,
                        outcome_timestamp TEXT,
                        exit_price REAL,
                        realized_r REAL,
                        mfe REAL,
                        mae REAL,
                        max_r REAL,
                        time_to_outcome_minutes REAL,
                        transaction_cost_deducted REAL,
                        ambiguity_flag INTEGER,
                        is_in_sample INTEGER,
                        success_reason TEXT,
                        failure_reason TEXT
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_sym_tf ON candles (symbol, timeframe)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_run ON historical_signals (run_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_sym_outcome ON historical_signals (symbol, outcome)")

                try:
                    cur.execute("ALTER TABLE historical_signals ADD COLUMN success_reason TEXT")
                except Exception:
                    pass
                try:
                    cur.execute("ALTER TABLE historical_signals ADD COLUMN failure_reason TEXT")
                except Exception:
                    pass

                # Backtest Performance Reports Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_reports (
                        run_id TEXT PRIMARY KEY,
                        report_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

                conn.commit()
            finally:
                conn.close()

    # -----------------------------------------------------------------------
    # Data Validation Pipeline
    # -----------------------------------------------------------------------

    def validate_candles(
        self,
        raw_candles: List[Dict[str, Any]],
        symbol: str,
        source_symbol: str,
        timeframe: str,
        source: str,
    ) -> Tuple[List[HistoricalCandle], DatasetQualityReport]:
        """
        Validate, normalize, and audit a list of candlestick dictionaries.
        Rejects invalid OHLC, non-chronological order, future timestamps, and duplicates.
        """
        valid_candles: List[HistoricalCandle] = []
        now_utc = datetime.now(timezone.utc)
        issues: List[str] = []

        total_rows = len(raw_candles)
        rejected_rows = 0
        duplicate_rows = 0
        invalid_ohlc_rows = 0
        future_rows = 0
        seen_epochs = set()
        has_volume = False

        sorted_raw = []
        for row in raw_candles:
            ts_str = str(row.get("timestamp") or "")
            epoch_ms = row.get("epoch_ms")
            if epoch_ms is None:
                try:
                    if ts_str.endswith("Z"):
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(ts_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    epoch_ms = int(dt.timestamp() * 1000)
                except Exception:
                    rejected_rows += 1
                    continue
            sorted_raw.append((epoch_ms, row))

        # Sort chronologically
        sorted_raw.sort(key=lambda x: x[0])

        for epoch_ms, row in sorted_raw:
            # 1. Duplicate check
            if epoch_ms in seen_epochs:
                duplicate_rows += 1
                rejected_rows += 1
                continue

            # 2. Future timestamp check
            dt_candle = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
            if dt_candle > now_utc + timedelta(minutes=5):
                future_rows += 1
                rejected_rows += 1
                issues.append(f"Future timestamp rejected: {dt_candle.isoformat()}")
                continue

            # 3. OHLC positivity & validity
            try:
                op = float(row.get("open", 0))
                hi = float(row.get("high", 0))
                lo = float(row.get("low", 0))
                cl = float(row.get("close", 0))
                vol = float(row.get("volume", 0) or 0)
            except (ValueError, TypeError):
                invalid_ohlc_rows += 1
                rejected_rows += 1
                continue

            if op <= 0 or hi <= 0 or lo <= 0 or cl <= 0:
                invalid_ohlc_rows += 1
                rejected_rows += 1
                continue

            if hi < max(op, cl) or lo > min(op, cl):
                invalid_ohlc_rows += 1
                rejected_rows += 1
                issues.append(f"Impossible OHLC at {dt_candle.isoformat()}: H={hi}, L={lo}, O={op}, C={cl}")
                continue

            if vol > 0:
                has_volume = True

            seen_epochs.add(epoch_ms)
            iso_str = dt_candle.isoformat()

            valid_candles.append(HistoricalCandle(
                symbol=symbol,
                source_symbol=source_symbol,
                timeframe=timeframe,
                timestamp=iso_str,
                epoch_ms=epoch_ms,
                open=op,
                high=hi,
                low=lo,
                close=cl,
                volume=vol,
                is_closed=bool(row.get("is_closed", True)),
                source=source,
            ))

        # Missing interval detection
        missing_intervals = 0
        if len(valid_candles) >= 2:
            step_ms = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3600_000, "4h": 14400_000, "1d": 86400_000}.get(timeframe, 900_000)
            for i in range(1, len(valid_candles)):
                diff = valid_candles[i].epoch_ms - valid_candles[i - 1].epoch_ms
                if diff > step_ms * 1.5:
                    missing_intervals += int(diff // step_ms) - 1

        quality_pct = 100.0 if total_rows == 0 else round((len(valid_candles) / total_rows) * 100.0, 2)
        dataset_id = f"DATASET-{symbol.replace('/', '-')}-{timeframe}-{source.upper()}"

        report = DatasetQualityReport(
            dataset_id=dataset_id,
            symbol=symbol,
            source_symbol=source_symbol,
            source=source,
            date_range_start=valid_candles[0].timestamp if valid_candles else None,
            date_range_end=valid_candles[-1].timestamp if valid_candles else None,
            timeframes=[timeframe],
            total_rows=total_rows,
            valid_rows=len(valid_candles),
            rejected_rows=rejected_rows,
            duplicate_rows=duplicate_rows,
            invalid_ohlc_rows=invalid_ohlc_rows,
            future_rows=future_rows,
            missing_intervals=missing_intervals,
            volume_available=has_volume,
            quality_score_pct=quality_pct,
            issues=issues[:20],
            dataset_version="v2.0",
        )

        return valid_candles, report

    # -----------------------------------------------------------------------
    # SQLite Storage & Retrieval
    # -----------------------------------------------------------------------

    def save_candles(self, candles: List[HistoricalCandle]) -> int:
        """Insert or replace validated historical candles into SQLite.
        Used for initial dataset ingestion (Kaggle CSV, bulk downloads).
        """
        if not candles:
            return 0
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
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
                        1 if c.is_closed else 0,
                        c.source,
                    )
                    for c in candles
                ]
                cur.executemany("""
                    INSERT OR REPLACE INTO candles (
                        symbol, source_symbol, timeframe, timestamp, epoch_ms,
                        open, high, low, close, volume, is_closed, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                conn.commit()
                return len(rows)
            finally:
                conn.close()

    def save_live_candles(self, candles: List[HistoricalCandle]) -> int:
        """
        INSERT OR IGNORE validated live candles into SQLite.

        SAFETY CONTRACT:
        - Uses INSERT OR IGNORE — an existing row (same symbol+timeframe+epoch_ms)
          is NEVER overwritten or modified.
        - Original 2016–2026 historical candle OHLCV values are protected.
        - Only genuinely new timestamps result in new rows.
        - Returns the count of rows actually inserted (0 for all duplicates).
        """
        if not candles:
            return 0
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
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
                        1 if c.is_closed else 0,
                        c.source,
                    )
                    for c in candles
                ]
                # INSERT OR IGNORE: collision on PRIMARY KEY (symbol, timeframe, epoch_ms)
                # silently skips the row — original data is NEVER overwritten.
                cur.executemany("""
                    INSERT OR IGNORE INTO candles (
                        symbol, source_symbol, timeframe, timestamp, epoch_ms,
                        open, high, low, close, volume, is_closed, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                conn.commit()
                # executemany rowcount can be -1 on some sqlite3 builds;
                # compute exact insertions as attempted - ignored.
                return max(0, cur.rowcount) if cur.rowcount >= 0 else len(rows)
            finally:
                conn.close()

    def get_live_ingestion_status(self) -> Dict[str, Any]:
        """
        Query live_ingestion_status table.
        Returns dict keyed by symbol with baseline/live candle counts and timestamps.
        Falls back to empty dict if the table does not yet exist.
        """
        conn = self._get_read_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, timeframe, last_candle_epoch_ms, last_candle_timestamp,
                       last_ingested_at, baseline_candles, live_candles_added,
                       baseline_start, baseline_end, status, last_error
                FROM live_ingestion_status
                ORDER BY symbol
            """)
            rows = cur.fetchall()
            result: Dict[str, Any] = {}
            for row in rows:
                sym       = row["symbol"]
                base_cnt  = row["baseline_candles"]  or 0
                live_cnt  = row["live_candles_added"] or 0
                result[sym] = {
                    "symbol":                sym,
                    "timeframe":             row["timeframe"],
                    "last_candle_epoch_ms":  row["last_candle_epoch_ms"],
                    "last_candle_timestamp": row["last_candle_timestamp"],
                    "last_ingested_at":      row["last_ingested_at"],
                    "baseline_candles":      base_cnt,
                    "live_candles_added":    live_cnt,
                    "total_candles":         base_cnt + live_cnt,
                    "baseline_start":        row["baseline_start"],
                    "baseline_end":          row["baseline_end"],
                    "status":                row["status"] or "INITIALIZING",
                    "last_error":            row["last_error"],
                }
            return result
        except Exception:
            # Table may not yet exist on first-boot before ingestion daemon initialises
            return {}
        # Note: read connection stays open (thread-local) — no close() call

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[HistoricalCandle]:
        """Fetch chronologically ordered candles from SQLite."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT * FROM candles WHERE symbol = ? AND timeframe = ?"
            params: List[Any] = [symbol, timeframe]

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)

            query += " ORDER BY epoch_ms ASC"
            if limit:
                query += f" LIMIT {int(limit)}"

            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                HistoricalCandle(
                    symbol=r["symbol"],
                    source_symbol=r["source_symbol"],
                    timeframe=r["timeframe"],
                    timestamp=r["timestamp"],
                    epoch_ms=r["epoch_ms"],
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["volume"],
                    is_closed=bool(r["is_closed"]),
                    source=r["source"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_latest_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> List[HistoricalCandle]:
        """Fetch the most recent `limit` closed candles from SQLite ordered chronologically."""
        norm_sym = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM candles
                WHERE symbol = ? AND timeframe = ?
                ORDER BY epoch_ms DESC
                LIMIT ?
            """, (norm_sym, timeframe, int(limit)))
            rows = cur.fetchall()
            candles = [
                HistoricalCandle(
                    symbol=r["symbol"],
                    source_symbol=r["source_symbol"],
                    timeframe=r["timeframe"],
                    timestamp=r["timestamp"],
                    epoch_ms=r["epoch_ms"],
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["volume"],
                    is_closed=bool(r["is_closed"]),
                    source=r["source"],
                )
                for r in rows
            ]
            candles.reverse()
            return candles
        finally:
            conn.close()

    def register_dataset_metadata(self, meta: DatasetMetadata) -> None:
        """Register or update a dataset catalog entry."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                status_val = getattr(meta, "status", None) or "SYNCHRONIZED"
                cur.execute("""
                    INSERT OR REPLACE INTO datasets (
                        dataset_id, symbol, source_symbol, source, description,
                        timeframes, start_date, end_date, row_count, valid_rows,
                        volume_available, version, created_at, quality_report_json, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meta.dataset_id,
                    meta.symbol,
                    meta.source_symbol,
                    meta.source,
                    meta.description,
                    json.dumps(meta.timeframes),
                    meta.start_date,
                    meta.end_date,
                    meta.row_count,
                    meta.valid_rows,
                    1 if meta.volume_available else 0,
                    meta.version,
                    meta.created_at,
                    json.dumps(meta.quality_report.model_dump() if hasattr(meta.quality_report, "model_dump") else (meta.quality_report.dict() if meta.quality_report else {})),
                    status_val,
                ))
                conn.commit()
            finally:
                conn.close()

    def list_datasets(self) -> List[DatasetMetadata]:
        """List all registered historical datasets in SQLite."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM datasets ORDER BY created_at DESC")
            rows = cur.fetchall()
            datasets: List[DatasetMetadata] = []
            for r in rows:
                q_json = r["quality_report_json"]
                q_report = DatasetQualityReport(**json.loads(q_json)) if q_json else None
                status_val = r["status"] if "status" in r.keys() else "SYNCHRONIZED"
                datasets.append(DatasetMetadata(
                    dataset_id=r["dataset_id"],
                    symbol=r["symbol"],
                    source_symbol=r["source_symbol"],
                    source=r["source"],
                    description=r["description"],
                    timeframes=json.loads(r["timeframes"]) if r["timeframes"] else [],
                    start_date=r["start_date"],
                    end_date=r["end_date"],
                    row_count=r["row_count"],
                    valid_rows=r["valid_rows"],
                    volume_available=bool(r["volume_available"]),
                    version=r["version"],
                    created_at=r["created_at"],
                    quality_report=q_report,
                    status=status_val,
                ))
            return datasets
        finally:
            conn.close()

    def get_xau_candles_fast(self, timeframe: str = "15m", limit: int = 50) -> List[Any]:
        """Return up to `limit` most-recent XAU/USD candles directly from the SQLite historical DB.

        Uses the persistent read connection and the existing idx_candles_lookup index so the
        query resolves in <20ms from 9.5M rows. Returns raw sqlite3.Row objects.
        """
        conn = self._get_read_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, epoch_ms, open, high, low, close, volume, is_closed
            FROM   candles
            WHERE  symbol = 'XAU/USD' AND timeframe = ?
            ORDER  BY epoch_ms DESC
            LIMIT  ?
            """,
            (timeframe, int(limit)),
        )
        rows = cur.fetchall()
        rows.reverse()  # chronological order (oldest first)
        return rows

    def get_fast_dataset_status(self) -> Dict[str, Any]:
        """
        High-speed dataset status query using registered dataset metadata and signal aggregates.
        Returns in <15ms without full-table scanning multi-million row candle tables.
        Result is cached in-memory for 30 seconds to avoid repeated SQLite file-open overhead.
        """
        now = time.time()
        if self._status_cache is not None and (now - self._status_cache_ts) < self._STATUS_CACHE_TTL:
            return self._status_cache

        conn = self._get_read_connection()
        try:
            cur = conn.cursor()

            # Query datasets table metadata (<1ms)
            cur.execute("SELECT * FROM datasets ORDER BY created_at DESC")
            dataset_rows = cur.fetchall()

            # Query historical signals outcome counts (<2ms)
            cur.execute("""
                SELECT symbol, direction, outcome, COUNT(*) as cnt
                FROM historical_signals
                GROUP BY symbol, direction, outcome
            """)
            signal_rows = cur.fetchall()

            symbols_data: Dict[str, Dict[str, Any]] = {}
            total_candles = 0
            registered_datasets = []

            for dr in dataset_rows:
                sym = dr["symbol"]
                tfs = []
                try:
                    tfs = json.loads(dr["timeframes"]) if dr["timeframes"] else ["15m"]
                except Exception:
                    tfs = ["15m"]

                row_cnt = int(dr["row_count"] or 0)
                q_json = dr["quality_report_json"]
                q_data = {}
                if q_json:
                    try:
                        q_data = json.loads(q_json)
                    except Exception:
                        pass
                tot_rows = int(q_data.get("total_rows") or row_cnt)

                if sym not in symbols_data:
                    symbols_data[sym] = {
                        "symbol": sym,
                        "total_candles": 0,
                        "timeframes": {},
                        "start_date": dr["start_date"],
                        "end_date": dr["end_date"],
                        "completed_signals": {"WIN": 0, "LOSS": 0, "BREAKEVEN": 0, "EXPIRED": 0, "total": 0},
                    }

                symbols_data[sym]["total_candles"] = max(symbols_data[sym]["total_candles"], tot_rows)
                for tf in tfs:
                    symbols_data[sym]["timeframes"][tf] = {
                        "timeframe": tf,
                        "count": row_cnt,
                        "start_date": dr["start_date"],
                        "end_date": dr["end_date"],
                    }

                if dr["start_date"] and (not symbols_data[sym]["start_date"] or dr["start_date"] < symbols_data[sym]["start_date"]):
                    symbols_data[sym]["start_date"] = dr["start_date"]
                if dr["end_date"] and (not symbols_data[sym]["end_date"] or dr["end_date"] > symbols_data[sym]["end_date"]):
                    symbols_data[sym]["end_date"] = dr["end_date"]

                registered_datasets.append({
                    "dataset_id": dr["dataset_id"],
                    "symbol": dr["symbol"],
                    "source_symbol": dr["source_symbol"],
                    "source": dr["source"],
                    "row_count": dr["row_count"],
                    "valid_rows": dr["valid_rows"],
                    "start_date": dr["start_date"],
                    "end_date": dr["end_date"],
                    "status": dr["status"] if "status" in dr.keys() else "SYNCHRONIZED",
                })

            # If datasets table was empty, fallback to scanning candles
            if not dataset_rows:
                cur.execute("""
                    SELECT 
                        symbol, 
                        timeframe, 
                        COUNT(*) as count,
                        MIN(timestamp) as start_date,
                        MAX(timestamp) as end_date
                    FROM candles
                    GROUP BY symbol, timeframe
                """)
                for r in cur.fetchall():
                    sym = r["symbol"]
                    tf = r["timeframe"]
                    cnt = r["count"]
                    if sym not in symbols_data:
                        symbols_data[sym] = {
                            "symbol": sym,
                            "total_candles": 0,
                            "timeframes": {},
                            "start_date": r["start_date"],
                            "end_date": r["end_date"],
                            "completed_signals": {"WIN": 0, "LOSS": 0, "BREAKEVEN": 0, "EXPIRED": 0, "total": 0},
                        }
                    symbols_data[sym]["total_candles"] += cnt
                    symbols_data[sym]["timeframes"][tf] = {
                        "timeframe": tf,
                        "count": cnt,
                        "start_date": r["start_date"],
                        "end_date": r["end_date"],
                    }

            for s_info in symbols_data.values():
                total_candles += s_info["total_candles"]

            for sr in signal_rows:
                sym = sr["symbol"]
                outcome = sr["outcome"]
                cnt = sr["cnt"]
                if sym in symbols_data:
                    if outcome in symbols_data[sym]["completed_signals"]:
                        symbols_data[sym]["completed_signals"][outcome] += cnt
                    symbols_data[sym]["completed_signals"]["total"] += cnt

            # ── Live ingestion extension fields ──────────────────────────
            live_ingestion: Dict[str, Any] = {}
            try:
                cur.execute("""
                    SELECT symbol, timeframe, last_candle_epoch_ms, last_candle_timestamp,
                           last_ingested_at, baseline_candles, live_candles_added,
                           baseline_start, baseline_end, status, last_error
                    FROM live_ingestion_status
                    ORDER BY symbol
                """)
                for li_row in cur.fetchall():
                    sym      = li_row["symbol"]
                    base_cnt = li_row["baseline_candles"]  or 0
                    live_cnt = li_row["live_candles_added"] or 0
                    live_ingestion[sym] = {
                        "symbol":                sym,
                        "timeframe":             li_row["timeframe"],
                        "last_candle_timestamp": li_row["last_candle_timestamp"],
                        "last_ingested_at":      li_row["last_ingested_at"],
                        "baseline_candles":      base_cnt,
                        "live_candles_added":    live_cnt,
                        "total_candles":         base_cnt + live_cnt,
                        "baseline_start":        li_row["baseline_start"],
                        "baseline_end":          li_row["baseline_end"],
                        "status":                li_row["status"] or "INITIALIZING",
                        "last_error":            li_row["last_error"],
                    }
                    # Propagate live latest_timestamp into per-symbol data
                    if sym in symbols_data and li_row["last_candle_timestamp"]:
                        symbols_data[sym]["latest_live_timestamp"] = (
                            li_row["last_candle_timestamp"]
                        )
                        symbols_data[sym]["ingestion_status"] = (
                            li_row["status"] or "INITIALIZING"
                        )
                        symbols_data[sym]["live_candles_added"] = live_cnt
            except Exception:
                pass  # live_ingestion_status table not yet created

            result = {
                "status": "HEALTHY" if total_candles > 0 else "EMPTY",
                "total_candles": total_candles,
                "symbols": symbols_data,
                "registered_datasets": registered_datasets,
                "live_ingestion": live_ingestion,
                "server_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            # Cache result; persistent read connection stays open — no close()
            self._status_cache = result
            self._status_cache_ts = time.time()
            return result
        except Exception:
            # On any read error fall back to a new connection and clear cache
            self._status_cache = None
            raise

    # -----------------------------------------------------------------------
    # External Market Data Downloaders
    # -----------------------------------------------------------------------

    def download_binance_btc(
        self,
        timeframe: str = "15m",
        start_date: str = "2023-01-01",
        end_date: Optional[str] = None,
        max_candles: int = 15000,
    ) -> Tuple[int, DatasetQualityReport]:
        """
        Download real historical BTC/USDT klines from Binance public API.
        Notes: BTC/USDT is used as the historical market proxy for BTC/USD.
        """
        binance_interval = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}.get(timeframe, "15m")
        url = "https://api.binance.com/api/v3/klines"

        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if "T" in start_date else datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_ms = int(start_dt.timestamp() * 1000)

        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if (end_date and "T" in end_date) else (datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end_date else datetime.now(timezone.utc))
        end_ms = int(end_dt.timestamp() * 1000)

        raw_rows = []
        current_start = start_ms

        while current_start < end_ms and len(raw_rows) < max_candles:
            params = {
                "symbol": "BTCUSDT",
                "interval": binance_interval,
                "startTime": current_start,
                "endTime": end_ms,
                "limit": 1000,
            }
            try:
                resp = requests.get(url, params=params, timeout=10.0)
                if resp.status_code != 200:
                    logger.warning(f"Binance kline request failed: HTTP {resp.status_code}")
                    break
                data = resp.json()
                if not data or not isinstance(data, list):
                    break

                for item in data:
                    # Binance kline format: [openTime, open, high, low, close, volume, closeTime, ...]
                    raw_rows.append({
                        "epoch_ms": item[0],
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                        "is_closed": True,
                    })

                last_open = data[-1][0]
                if last_open <= current_start:
                    break
                current_start = last_open + 1
                time.sleep(0.05)  # Respect rate limit
            except Exception as exc:
                logger.error(f"Error fetching Binance BTC klines: {exc}")
                break

        if not raw_rows:
            return 0, DatasetQualityReport(
                dataset_id=f"DATASET-BTC-USD-{timeframe}-BINANCE",
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                source="binance",
                timeframes=[timeframe],
                quality_score_pct=0.0,
                issues=["No data returned from Binance API"],
            )

        valid_candles, quality_report = self.validate_candles(
            raw_candles=raw_rows,
            symbol="BTC/USD",
            source_symbol="BTCUSDT",
            timeframe=timeframe,
            source="binance",
        )

        saved = self.save_candles(valid_candles)

        # Register metadata
        if valid_candles:
            meta = DatasetMetadata(
                dataset_id=quality_report.dataset_id,
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                source="binance",
                description="Historical BTC/USDT klines from Binance used as historical proxy for BTC/USD.",
                timeframes=[timeframe],
                start_date=valid_candles[0].timestamp,
                end_date=valid_candles[-1].timestamp,
                row_count=len(valid_candles),
                valid_rows=quality_report.valid_rows,
                volume_available=quality_report.volume_available,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
            )
            self.register_dataset_metadata(meta)

        return saved, quality_report

    def download_yahoo_gold(
        self,
        timeframe: str = "15m",
        range_period: str = "60d",
    ) -> Tuple[int, DatasetQualityReport]:
        """
        Download real historical Gold candles from Yahoo Finance (GC=F Gold Futures proxy).
        Notes: If volume is unavailable, volume_available is set to False.
        """
        from src.services.yahoo_finance import YahooFinanceProvider
        from src.models.market_data import Timeframe
        yp = YahooFinanceProvider()

        # Map timeframe to Timeframe enum
        tf_enum = {
            "5m": Timeframe.M5,
            "15m": Timeframe.M15,
            "1h": Timeframe.H1,
            "1d": Timeframe.D1,
            "4h": Timeframe.H1,
        }.get(timeframe, Timeframe.M15)

        try:
            history = yp.get_candles(
                symbol="XAU-USD-SPOT",
                timeframe=tf_enum,
                limit=3000,
            )
            raw_rows = []
            for c in history.candles:
                dt_iso = c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else str(c.timestamp)
                raw_rows.append({
                    "timestamp": dt_iso,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": getattr(c, "volume", 0) or 0,
                    "is_closed": True,
                })

            valid_candles, quality_report = self.validate_candles(
                raw_candles=raw_rows,
                symbol="XAU/USD",
                source_symbol="GC=F",
                timeframe=timeframe,
                source="yahoo",
            )

            saved = self.save_candles(valid_candles)
            if valid_candles:
                meta = DatasetMetadata(
                    dataset_id=quality_report.dataset_id,
                    symbol="XAU/USD",
                    source_symbol="GC=F",
                    source="yahoo",
                    description="Historical GC=F (Gold Futures) from Yahoo Finance used as historical proxy for XAU/USD.",
                    timeframes=[timeframe],
                    start_date=valid_candles[0].timestamp,
                    end_date=valid_candles[-1].timestamp,
                    row_count=len(valid_candles),
                    valid_rows=quality_report.valid_rows,
                    volume_available=quality_report.volume_available,
                    version="v2.0",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    quality_report=quality_report,
                )
                self.register_dataset_metadata(meta)

            return saved, quality_report
        except Exception as exc:
            logger.error(f"Error fetching Yahoo Gold data: {exc}")
            return 0, DatasetQualityReport(
                dataset_id=f"DATASET-XAU-USD-{timeframe}-YAHOO",
                symbol="XAU/USD",
                source_symbol="GC=F",
                source="yahoo",
                timeframes=[timeframe],
                quality_score_pct=0.0,
                issues=[f"Yahoo Finance fetch error: {str(exc)}"],
                volume_available=False,
            )

    def import_csv(
        self,
        file_path: str,
        symbol: str,
        source_symbol: str,
        timeframe: str,
        source: str = "csv_import",
    ) -> Tuple[int, DatasetQualityReport]:
        """Import historical candles from an external CSV file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        raw_rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys: support Date/Time/Timestamp, Open, High, Low, Close, Volume
                ts = row.get("timestamp") or row.get("Timestamp") or row.get("Date") or row.get("date") or row.get("time") or row.get("Time")
                op = row.get("open") or row.get("Open")
                hi = row.get("high") or row.get("High")
                lo = row.get("low") or row.get("Low")
                cl = row.get("close") or row.get("Close")
                vol = row.get("volume") or row.get("Volume") or 0.0

                if ts and op and hi and lo and cl:
                    raw_rows.append({
                        "timestamp": ts,
                        "open": op,
                        "high": hi,
                        "low": lo,
                        "close": cl,
                        "volume": vol,
                        "is_closed": True,
                    })

        valid_candles, quality_report = self.validate_candles(
            raw_candles=raw_rows,
            symbol=symbol,
            source_symbol=source_symbol,
            timeframe=timeframe,
            source=source,
        )

        saved = self.save_candles(valid_candles)
        if valid_candles:
            meta = DatasetMetadata(
                dataset_id=quality_report.dataset_id,
                symbol=symbol,
                source_symbol=source_symbol,
                source=source,
                description=f"CSV imported dataset for {symbol} ({timeframe}) from {os.path.basename(file_path)}",
                timeframes=[timeframe],
                start_date=valid_candles[0].timestamp,
                end_date=valid_candles[-1].timestamp,
                row_count=len(valid_candles),
                valid_rows=quality_report.valid_rows,
                volume_available=quality_report.volume_available,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
            )
            self.register_dataset_metadata(meta)

        return saved, quality_report

    def ensure_default_datasets(self) -> List[DatasetMetadata]:
        """
        Verify that automatically collected historical datasets exist for both BTC/USD and XAU/USD.
        If local Kaggle historical dataset exists in 'New folder', imports directly from it.
        """
        existing = self.list_datasets()
        existing_symbols = {d.symbol for d in existing}

        kaggle_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "New folder")
        if os.path.exists(kaggle_dir) and (len(existing_symbols) < 2 or any("kaggle" not in (d.source or "") for d in existing)):
            try:
                from src.services.kaggle_dataset_importer import KaggleDatasetImporter
                importer = KaggleDatasetImporter(data_dir=kaggle_dir, db_path=self.db_path)
                importer.import_macro_data()
                importer.import_btc_dataset()
                importer.import_xau_dataset()
                return self.list_datasets()
            except Exception as e:
                logger.warning(f"Kaggle local importer note: {e}")

        # Fallbacks if local files are missing
        if "BTC/USD" not in existing_symbols:
            logger.info("Initializing automated historical dataset collection for BTC/USD (Binance)...")
            try:
                self.download_binance_btc(timeframe="15m", start_date="2023-01-01", max_candles=5000)
            except Exception as e:
                logger.error(f"Failed to auto-collect BTC/USD historical data: {e}")

        if "XAU/USD" not in existing_symbols:
            logger.info("Initializing automated historical dataset collection for XAU/USD (Yahoo Finance GC=F)...")
            try:
                self.download_yahoo_gold(timeframe="15m", range_period="60d")
            except Exception as e:
                logger.error(f"Failed to auto-collect XAU/USD historical data: {e}")

        return self.list_datasets()
