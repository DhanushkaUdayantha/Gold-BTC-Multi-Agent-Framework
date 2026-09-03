"""
Storage and Persistence for ML Shadow Observations.
Maintains strict immutable T0 snapshots and isolated forward outcome updates.
"""
import sqlite3
import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from src.research.ml_shadow.models import MLShadowPrediction
from src.research.ml_shadow.symbol_utils import normalize_ml_symbol

logger = logging.getLogger("ml_shadow_store")

class MLShadowStore:
    """Isolated SQLite repository for shadow mode observations."""

    def __init__(self, db_path: str = "data/historical/historical_market_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes the dedicated ml_shadow_observations table."""
        try:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_shadow_observations (
                        observation_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        timestamp_t0 TEXT NOT NULL,
                        production_decision TEXT NOT NULL,
                        confluence_score INTEGER NOT NULL,
                        technical_score INTEGER NOT NULL,
                        quality_gate_passed INTEGER NOT NULL,
                        ml_model_name TEXT NOT NULL,
                        ml_model_version TEXT NOT NULL,
                        ml_probability REAL NOT NULL,
                        ml_predicted_class INTEGER NOT NULL,
                        entry_price REAL NOT NULL,
                        stop_loss REAL,
                        take_profit_1 REAL,
                        take_profit_2 REAL,
                        session TEXT,
                        market_regime TEXT,
                        features_snapshot_json TEXT,
                        outcome TEXT DEFAULT 'PENDING',
                        exit_price REAL,
                        realized_r REAL,
                        outcome_timestamp TEXT,
                        time_to_outcome_minutes REAL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_shadow_sym_ts ON ml_shadow_observations(symbol, timestamp_t0)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_shadow_outcome ON ml_shadow_observations(outcome)")
            conn.close()
        except Exception as e:
            logger.error(f"[ML SHADOW] Failed to initialize storage table: {e}")

    def save_observation(self, pred: MLShadowPrediction) -> bool:
        """
        Saves an immutable point-in-time T0 prediction snapshot.
        If an observation with the same observation_id exists, it is ignored (never overwritten).
        """
        try:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT OR IGNORE INTO ml_shadow_observations (
                        observation_id, symbol, timestamp_t0, production_decision,
                        confluence_score, technical_score, quality_gate_passed,
                        ml_model_name, ml_model_version, ml_probability,
                        ml_predicted_class, entry_price, stop_loss,
                        take_profit_1, take_profit_2, session, market_regime,
                        features_snapshot_json, outcome, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """, (
                    pred.observation_id, pred.symbol, pred.timestamp_t0,
                    pred.production_decision, pred.confluence_score,
                    pred.technical_score, 1 if pred.quality_gate_passed else 0,
                    pred.ml_model_name, pred.ml_model_version,
                    pred.ml_probability, pred.ml_predicted_class,
                    pred.entry_price, pred.stop_loss, pred.take_profit_1,
                    pred.take_profit_2, pred.session, pred.market_regime,
                    json.dumps(pred.features_snapshot), pred.created_at
                ))
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ML SHADOW] Failed to save observation {pred.observation_id}: {e}")
            return False

    def resolve_observation_outcome(
        self,
        observation_id: str,
        outcome: str,
        exit_price: float,
        realized_r: float,
        outcome_timestamp: str,
        duration_minutes: float
    ) -> bool:
        """
        Resolves the forward outcome of a pending observation.
        STRICT RULE: Only updates outcome columns. Never alters T0 snapshot columns.
        """
        try:
            conn = self._get_connection()
            now_iso = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute("""
                    UPDATE ml_shadow_observations
                    SET outcome = ?,
                        exit_price = ?,
                        realized_r = ?,
                        outcome_timestamp = ?,
                        time_to_outcome_minutes = ?,
                        updated_at = ?
                    WHERE observation_id = ? AND outcome = 'PENDING'
                """, (
                    outcome, exit_price, realized_r,
                    outcome_timestamp, duration_minutes,
                    now_iso, observation_id
                ))
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ML SHADOW] Failed to resolve outcome for {observation_id}: {e}")
            return False

    def get_observation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM ml_shadow_observations WHERE observation_id = ?", (observation_id,))
            row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[ML SHADOW] Error fetching observation: {e}")
            return None

    def get_pending_observations(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            if symbol:
                canonical = normalize_ml_symbol(symbol)
                cur.execute(
                    "SELECT * FROM ml_shadow_observations WHERE outcome = 'PENDING' AND symbol = ? ORDER BY timestamp_t0 ASC",
                    (canonical,),
                )
            else:
                cur.execute("SELECT * FROM ml_shadow_observations WHERE outcome = 'PENDING' ORDER BY timestamp_t0 ASC")
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[ML SHADOW] Error fetching pending observations: {e}")
            return []

    def get_all_observations(self, symbol: str, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns all observations for a specific asset symbol and optional model version.

        Parameters
        ----------
        symbol:
            Required. Must be a recognizable BTC or XAU variant.
            Normalized internally via normalize_ml_symbol().
        model_version:
            Optional. Specific ML model version to filter by (e.g. 'v1.0.0-research').

        Raises
        ------
        ValueError
            If symbol is None, empty, or unrecognizable.
        """
        if not symbol:
            raise ValueError(
                "MLShadowStore.get_all_observations: symbol is required. "
                "Pass 'BTC/USD' or 'XAU/USD' — never omit the symbol."
            )
        canonical = normalize_ml_symbol(symbol)
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            if model_version:
                cur.execute(
                    "SELECT * FROM ml_shadow_observations WHERE symbol = ? AND ml_model_version = ? ORDER BY timestamp_t0 ASC",
                    (canonical, model_version),
                )
            else:
                cur.execute(
                    "SELECT * FROM ml_shadow_observations WHERE symbol = ? ORDER BY timestamp_t0 ASC",
                    (canonical,),
                )
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[ML SHADOW] Error fetching all observations: {e}")
            return []
