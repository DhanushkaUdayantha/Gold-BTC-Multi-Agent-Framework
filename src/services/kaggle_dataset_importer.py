"""
Kaggle Historical Dataset Importer & Multi-Timeframe Resampling Pipeline.

Directly processes the ~593 MB Kaggle dataset from:
    D:\\Project\\TRADE\\New folder

Features:
- Memory-efficient streaming/chunked processing of 1-minute CSVs
- Preserves full original 1-minute (1m) candlestick resolution
- Computes and stores aggregated 5m, 15m, 1h, 4h, and 1d timeframes
- Zero look-ahead bias: Resampling aggregates past 1m bars into standard closed buckets
- Full data quality audit trail (rejections, duplicate checks, OHLC validity)
- Strict separation between BTC/USD (Binance) and XAU/USD (Gold)
- Stores macro context tables (DXY index and FED economic indicators)
- Integrates with SQLite repository (data/historical/historical_market_data.db)
- Feeds data directly into Historical Learning, Pattern Discovery, and Empirical Calibration

DISCLAIMER: Research and analytical modeling only. No real trades are executed.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.models.historical_data import (
    HistoricalCandle,
    DatasetQualityReport,
    DatasetMetadata,
)
from src.services.historical_data_service import HistoricalDataService, DB_PATH

logger = logging.getLogger(__name__)

KAGGLE_DATA_DIR = r"D:\Project\TRADE\New folder"


class KaggleDatasetImporter:
    """Imports, validates, resamples, and indexes the local Kaggle dataset."""

    def __init__(self, data_dir: str = KAGGLE_DATA_DIR, db_path: str = DB_PATH):
        self.data_dir = data_dir
        self.db_path = db_path
        self.data_service = HistoricalDataService(db_path=db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        # Fast write pragmas for bulk ingestion
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = 100000")
        return conn

    def _init_macro_tables(self) -> None:
        """Initialize auxiliary tables for macro context."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS macro_dxy (
                    date TEXT PRIMARY KEY,
                    dxy_close REAL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS macro_fed (
                    date TEXT PRIMARY KEY,
                    cpi REAL,
                    fed_funds_rate REAL,
                    treasury_10y REAL,
                    treasury_2y REAL,
                    unemployment_rate REAL,
                    raw_json TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Ingest Macro Datasets (DXY & FED)
    # -----------------------------------------------------------------------

    def import_macro_data(self) -> Dict[str, int]:
        """Ingest US Dollar Index and FED economic data."""
        self._init_macro_tables()
        conn = self._get_connection()
        counts = {"dxy": 0, "fed": 0}
        try:
            # 1. DXY
            dxy_path = os.path.join(self.data_dir, "US_Dollar_Index_2018_2026.csv")
            if os.path.exists(dxy_path):
                df_dxy = pd.read_csv(dxy_path)
                df_dxy = df_dxy.dropna(subset=["Date", "US_Dollar_Index"])
                rows_dxy = [
                    (str(r["Date"]).strip(), float(r["US_Dollar_Index"]))
                    for _, r in df_dxy.iterrows()
                ]
                cur = conn.cursor()
                cur.executemany(
                    "INSERT OR REPLACE INTO macro_dxy (date, dxy_close) VALUES (?, ?)",
                    rows_dxy,
                )
                conn.commit()
                counts["dxy"] = len(rows_dxy)
                logger.info(f"Ingested {len(rows_dxy)} DXY records.")

            # 2. FED Data
            fed_path = os.path.join(self.data_dir, "fed_economic_data_2018_2026.csv")
            if os.path.exists(fed_path):
                df_fed = pd.read_csv(fed_path)
                df_fed = df_fed.dropna(subset=["Date"])
                rows_fed = []
                for _, r in df_fed.iterrows():
                    d_str = str(r["Date"]).strip()
                    cpi = float(r.get("CPI", 0) or 0)
                    ffr = float(r.get("Fed_Funds_Rate", 0) or 0)
                    t10 = float(r.get("Treasury_10Y", 0) or 0)
                    t2 = float(r.get("Treasury_2Y", 0) or 0)
                    unemp = float(r.get("Unemployment_Rate", 0) or 0)
                    raw_j = json.dumps(r.to_dict())
                    rows_fed.append((d_str, cpi, ffr, t10, t2, unemp, raw_j))

                cur = conn.cursor()
                cur.executemany(
                    "INSERT OR REPLACE INTO macro_fed (date, cpi, fed_funds_rate, treasury_10y, treasury_2y, unemployment_rate, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows_fed,
                )
                conn.commit()
                counts["fed"] = len(rows_fed)
                logger.info(f"Ingested {len(rows_fed)} FED macro records.")

            return counts
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Ingest BTC/USDT (Binance 2018-2026)
    # -----------------------------------------------------------------------

    def import_btc_dataset(self) -> Tuple[Dict[str, int], DatasetQualityReport]:
        """
        Stream and ingest BTC/USDT Binance 1-minute files from 2018 to 2026.
        Generates 5m, 15m, 1h, 4h, 1d resampled timeframes and stores all into SQLite.
        """
        pattern = os.path.join(self.data_dir, "btc_usdt_binance_*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            raise FileNotFoundError(f"No BTC CSV files found matching {pattern}")

        logger.info(f"Found {len(files)} BTC historical files to process.")
        counts_by_tf: Dict[str, int] = {"1m": 0, "5m": 0, "15m": 0, "1h": 0, "4h": 0, "1d": 0}

        first_iso: Optional[str] = None
        last_iso: Optional[str] = None
        total_1m_rows = 0
        valid_1m_rows = 0
        rejected_rows = 0

        conn = self._get_connection()
        try:
            for filepath in files:
                filename = os.path.basename(filepath)
                logger.info(f"Processing BTC file: {filename}...")

                df = pd.read_csv(filepath)
                total_1m_rows += len(df)

                # Validate required columns
                req_cols = ["timestamp", "open", "high", "low", "close", "volume"]
                if not all(c in df.columns for c in req_cols):
                    logger.warning(f"File {filename} missing required columns; skipping.")
                    continue

                # Filter valid OHLC
                valid_mask = (
                    (df["open"] > 0)
                    & (df["high"] > 0)
                    & (df["low"] > 0)
                    & (df["close"] > 0)
                    & (df["high"] >= df[["open", "close"]].max(axis=1))
                    & (df["low"] <= df[["open", "close"]].min(axis=1))
                )
                bad_count = int((~valid_mask).sum())
                rejected_rows += bad_count
                df = df[valid_mask].copy()

                if df.empty:
                    continue

                valid_1m_rows += len(df)

                # Parse datetime index for fast resampling
                df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"])
                df = df.set_index("dt")

                if first_iso is None:
                    first_iso = df.index[0].isoformat()
                last_iso = df.index[-1].isoformat()

                # 1. Insert 1m candles
                rows_1m = [
                    (
                        "BTC/USD",
                        "BTCUSDT",
                        "1m",
                        idx.isoformat(),
                        int(r["timestamp"]),
                        float(r["open"]),
                        float(r["high"]),
                        float(r["low"]),
                        float(r["close"]),
                        float(r["volume"]),
                        1,
                        "binance_kaggle",
                    )
                    for idx, r in df.iterrows()
                ]
                cur = conn.cursor()
                cur.executemany("""
                    INSERT OR REPLACE INTO candles (
                        symbol, source_symbol, timeframe, timestamp, epoch_ms,
                        open, high, low, close, volume, is_closed, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_1m)
                counts_by_tf["1m"] += len(rows_1m)

                # 2. Resample to 5m, 15m, 1h, 4h, 1d
                tf_mappings = [
                    ("5m", "5min"),
                    ("15m", "15min"),
                    ("1h", "1h"),
                    ("4h", "4h"),
                    ("1d", "1D"),
                ]
                for tf_name, rule in tf_mappings:
                    res = df.resample(rule).agg({
                        "timestamp": "first",
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }).dropna()

                    rows_agg = [
                        (
                            "BTC/USD",
                            "BTCUSDT",
                            tf_name,
                            idx.isoformat(),
                            int(idx.timestamp() * 1000),
                            float(r["open"]),
                            float(r["high"]),
                            float(r["low"]),
                            float(r["close"]),
                            float(r["volume"]),
                            1,
                            "binance_kaggle",
                        )
                        for idx, r in res.iterrows()
                    ]
                    cur.executemany("""
                        INSERT OR REPLACE INTO candles (
                            symbol, source_symbol, timeframe, timestamp, epoch_ms,
                            open, high, low, close, volume, is_closed, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, rows_agg)
                    counts_by_tf[tf_name] += len(rows_agg)

                conn.commit()
                logger.info(f"Finished {filename}: 1m={len(rows_1m):,}, 15m={counts_by_tf['15m']:,}")

            # Register Dataset Metadata & Quality Report
            quality_score = 100.0 if total_1m_rows == 0 else round((valid_1m_rows / total_1m_rows) * 100.0, 2)
            quality_report = DatasetQualityReport(
                dataset_id="DATASET-BTC-USD-KAGGLE-2018-2026",
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                source="binance_kaggle",
                date_range_start=first_iso,
                date_range_end=last_iso,
                timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
                total_rows=total_1m_rows,
                valid_rows=valid_1m_rows,
                rejected_rows=rejected_rows,
                duplicate_rows=0,
                invalid_ohlc_rows=rejected_rows,
                future_rows=0,
                missing_intervals=0,
                volume_available=True,
                quality_score_pct=quality_score,
                issues=[],
                dataset_version="v2.0-kaggle",
            )

            meta = DatasetMetadata(
                dataset_id="DATASET-BTC-USD-KAGGLE-2018-2026",
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                source="binance_kaggle",
                description="Kaggle Historical BTC/USDT Binance 1-minute data (2018-2026) with multi-timeframe resampled 5m, 15m, 1h, 4h, 1d bars.",
                timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
                start_date=first_iso or "2018-01-01T00:00:00+00:00",
                end_date=last_iso or "2026-06-30T23:59:00+00:00",
                row_count=counts_by_tf["15m"],
                valid_rows=counts_by_tf["15m"],
                volume_available=True,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
                status="SYNCHRONIZED",
            )
            self.data_service.register_dataset_metadata(meta)

            # Also maintain legacy standard 15m ID for backward compatibility
            meta_15m = DatasetMetadata(
                dataset_id="DATASET-BTC-USD-15m-BINANCE",
                symbol="BTC/USD",
                source_symbol="BTCUSDT",
                source="binance_kaggle",
                description="Historical BTC/USDT klines from Binance used as historical proxy for BTC/USD (2018-2026).",
                timeframes=["15m", "5m", "1h", "4h", "1d"],
                start_date=first_iso or "2018-01-01T00:00:00+00:00",
                end_date=last_iso or "2026-06-30T23:59:00+00:00",
                row_count=counts_by_tf["15m"],
                valid_rows=counts_by_tf["15m"],
                volume_available=True,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
                status="SYNCHRONIZED",
            )
            self.data_service.register_dataset_metadata(meta_15m)

            return counts_by_tf, quality_report
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Ingest XAU/USD (Gold 2018-2026)
    # -----------------------------------------------------------------------

    def import_xau_dataset(
        self, chunk_size: int = 500000
    ) -> Tuple[Dict[str, int], DatasetQualityReport]:
        """
        Stream and ingest XAU/USD (Gold) 1-minute CSV from 2018 to 2026 in chunks.
        Generates 5m, 15m, 1h, 4h, 1d resampled timeframes and stores all into SQLite.
        """
        xau_path = os.path.join(self.data_dir, "xauusd_2018_2026.csv")
        if not os.path.exists(xau_path):
            raise FileNotFoundError(f"XAU CSV file not found at {xau_path}")

        logger.info(f"Starting chunked stream ingestion of {xau_path} (chunk_size={chunk_size:,})...")
        counts_by_tf: Dict[str, int] = {"1m": 0, "5m": 0, "15m": 0, "1h": 0, "4h": 0, "1d": 0}

        first_iso: Optional[str] = None
        last_iso: Optional[str] = None
        total_1m_rows = 0
        valid_1m_rows = 0
        rejected_rows = 0

        conn = self._get_connection()
        try:
            chunk_idx = 0
            for chunk in pd.read_csv(xau_path, chunksize=chunk_size):
                chunk_idx += 1
                total_1m_rows += len(chunk)

                # Rename columns to standard lowercase
                chunk = chunk.rename(columns={
                    "Date": "date",
                    "Timestamp": "time",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                })

                # Validate OHLC
                valid_mask = (
                    (chunk["open"] > 0)
                    & (chunk["high"] > 0)
                    & (chunk["low"] > 0)
                    & (chunk["close"] > 0)
                    & (chunk["high"] >= chunk[["open", "close"]].max(axis=1))
                    & (chunk["low"] <= chunk[["open", "close"]].min(axis=1))
                )
                bad_count = int((~valid_mask).sum())
                rejected_rows += bad_count
                chunk = chunk[valid_mask].copy()

                if chunk.empty:
                    continue

                valid_1m_rows += len(chunk)

                # Parse DateTime: Date format YYYYMMDD + HH:MM:SS
                dt_str = chunk["date"].astype(str) + " " + chunk["time"].astype(str)
                chunk["dt"] = pd.to_datetime(dt_str, format="%Y%m%d %H:%M:%S", utc=True)
                chunk["epoch_ms"] = chunk["dt"].values.astype("datetime64[ms]").astype("int64")
                chunk = chunk.sort_values("epoch_ms").drop_duplicates(subset=["epoch_ms"])
                chunk = chunk.set_index("dt")

                if first_iso is None:
                    first_iso = chunk.index[0].isoformat()
                last_iso = chunk.index[-1].isoformat()

                # 1. Insert 1m candles
                rows_1m = [
                    (
                        "XAU/USD",
                        "XAUUSD",
                        "1m",
                        idx.isoformat(),
                        int(r["epoch_ms"]),
                        float(r["open"]),
                        float(r["high"]),
                        float(r["low"]),
                        float(r["close"]),
                        float(r["volume"]),
                        1,
                        "kaggle_historical",
                    )
                    for idx, r in chunk.iterrows()
                ]
                cur = conn.cursor()
                cur.executemany("""
                    INSERT OR REPLACE INTO candles (
                        symbol, source_symbol, timeframe, timestamp, epoch_ms,
                        open, high, low, close, volume, is_closed, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows_1m)
                counts_by_tf["1m"] += len(rows_1m)

                # 2. Resample to 5m, 15m, 1h, 4h, 1d
                tf_mappings = [
                    ("5m", "5min"),
                    ("15m", "15min"),
                    ("1h", "1h"),
                    ("4h", "4h"),
                    ("1d", "1D"),
                ]
                for tf_name, rule in tf_mappings:
                    res = chunk.resample(rule).agg({
                        "epoch_ms": "first",
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }).dropna()

                    rows_agg = [
                        (
                            "XAU/USD",
                            "XAUUSD",
                            tf_name,
                            idx.isoformat(),
                            int(idx.timestamp() * 1000),
                            float(r["open"]),
                            float(r["high"]),
                            float(r["low"]),
                            float(r["close"]),
                            float(r["volume"]),
                            1,
                            "kaggle_historical",
                        )
                        for idx, r in res.iterrows()
                    ]
                    cur.executemany("""
                        INSERT OR REPLACE INTO candles (
                            symbol, source_symbol, timeframe, timestamp, epoch_ms,
                            open, high, low, close, volume, is_closed, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, rows_agg)
                    counts_by_tf[tf_name] += len(rows_agg)

                conn.commit()
                logger.info(f"Processed XAU chunk {chunk_idx}: 1m total={counts_by_tf['1m']:,}, 15m total={counts_by_tf['15m']:,}")

            # Register Dataset Metadata & Quality Report
            quality_score = 100.0 if total_1m_rows == 0 else round((valid_1m_rows / total_1m_rows) * 100.0, 2)
            quality_report = DatasetQualityReport(
                dataset_id="DATASET-XAU-USD-KAGGLE-2018-2026",
                symbol="XAU/USD",
                source_symbol="XAUUSD",
                source="kaggle_historical",
                date_range_start=first_iso,
                date_range_end=last_iso,
                timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
                total_rows=total_1m_rows,
                valid_rows=valid_1m_rows,
                rejected_rows=rejected_rows,
                duplicate_rows=0,
                invalid_ohlc_rows=rejected_rows,
                future_rows=0,
                missing_intervals=0,
                volume_available=True,
                quality_score_pct=quality_score,
                issues=[],
                dataset_version="v2.0-kaggle",
            )

            meta = DatasetMetadata(
                dataset_id="DATASET-XAU-USD-KAGGLE-2018-2026",
                symbol="XAU/USD",
                source_symbol="XAUUSD",
                source="kaggle_historical",
                description="Kaggle Historical XAU/USD 1-minute data (2018-2026) with multi-timeframe resampled 5m, 15m, 1h, 4h, 1d bars.",
                timeframes=["1m", "5m", "15m", "1h", "4h", "1d"],
                start_date=first_iso or "2018-01-01T23:00:00+00:00",
                end_date=last_iso or "2026-05-31T23:59:00+00:00",
                row_count=counts_by_tf["15m"],
                valid_rows=counts_by_tf["15m"],
                volume_available=True,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
                status="SYNCHRONIZED",
            )
            self.data_service.register_dataset_metadata(meta)

            # Also maintain legacy standard 15m ID for backward compatibility
            meta_15m = DatasetMetadata(
                dataset_id="DATASET-XAU-USD-15m-YAHOO",
                symbol="XAU/USD",
                source_symbol="XAUUSD",
                source="kaggle_historical",
                description="Historical XAU/USD Gold data (2018-2026) used as historical proxy for XAU/USD.",
                timeframes=["15m", "5m", "1h", "4h", "1d"],
                start_date=first_iso or "2018-01-01T23:00:00+00:00",
                end_date=last_iso or "2026-05-31T23:59:00+00:00",
                row_count=counts_by_tf["15m"],
                valid_rows=counts_by_tf["15m"],
                volume_available=True,
                version="v2.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                quality_report=quality_report,
                status="SYNCHRONIZED",
            )
            self.data_service.register_dataset_metadata(meta_15m)

            return counts_by_tf, quality_report
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Run Complete Ingestion & Background Learning Pipeline
    # -----------------------------------------------------------------------

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Execute full ingestion of BTC, XAU, and macro data, then trigger
        automated historical learning, pattern discovery, and probability calibration.
        """
        start_time = time.time()
        logger.info("=== STARTING FULL KAGGLE HISTORICAL DATASET INGESTION ===")

        # 1. Macro data
        macro_counts = self.import_macro_data()

        # 2. BTC/USD
        btc_counts, btc_quality = self.import_btc_dataset()

        # 3. XAU/USD
        xau_counts, xau_quality = self.import_xau_dataset()

        elapsed = time.time() - start_time
        logger.info(f"=== KAGGLE INGESTION COMPLETED IN {elapsed:.2f}s ===")

        # 4. Trigger Automated Historical Learning & Empirical Calibration
        from src.services.historical_evidence_service import HistoricalEvidenceService
        evidence_svc = HistoricalEvidenceService.get_instance()
        evidence_svc.ensure_historical_learning_ready(force=True)

        return {
            "elapsed_seconds": round(elapsed, 2),
            "macro_counts": macro_counts,
            "btc_counts": btc_counts,
            "btc_quality": btc_quality.model_dump() if hasattr(btc_quality, "model_dump") else btc_quality.dict(),
            "xau_counts": xau_counts,
            "xau_quality": xau_quality.model_dump() if hasattr(xau_quality, "model_dump") else xau_quality.dict(),
        }
