"""
Dataset Builder for Machine Learning Research.
Extracts point-in-time feature records from the historical database.
"""
import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

class DatasetBuilder:
    """Builds clean, point-in-time tabular ML datasets from historical signals."""

    def __init__(self, db_path: str = "data/historical/historical_market_data.db"):
        self.db_path = db_path

    def load_raw_signals(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """Load signals from SQLite ordered chronologically by timestamp."""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT signal_id, run_id, dataset_id, symbol, source_symbol,
                   signal_timestamp, snapshot_id, entry_price, direction,
                   confluence_score, technical_score, gemini_score,
                   contributor_scores_json, contributor_directions_json,
                   data_quality, gate_direction, stop_loss, take_profit_1,
                   take_profit_2, market_regime, session, outcome, realized_r
            FROM historical_signals
        """
        params = []
        if symbol:
            if "BTC" in symbol.upper():
                query += " WHERE symbol LIKE '%BTC%'"
            elif "XAU" in symbol.upper():
                query += " WHERE symbol LIKE '%XAU%'"

        query += " ORDER BY signal_timestamp ASC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def build_dataset(self, symbol: str) -> pd.DataFrame:
        """Constructs a fully parsed point-in-time ML dataframe for a given asset."""
        raw_df = self.load_raw_signals(symbol=symbol)
        if raw_df.empty:
            raise ValueError(f"No historical signals found for symbol pattern: {symbol}")

        records = []
        for _, row in raw_df.iterrows():
            # Parse timestamp & time-derived features
            ts_str = str(row["signal_timestamp"])
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                hour = dt.hour
                day_of_week = dt.weekday()
            except Exception:
                hour = 0
                day_of_week = 0

            # Calculate risk ratios at T0
            entry_p = float(row["entry_price"]) if row["entry_price"] else 1.0
            sl = float(row["stop_loss"]) if row["stop_loss"] else entry_p * 0.99
            tp1 = float(row["take_profit_1"]) if row["take_profit_1"] else entry_p * 1.01

            sl_dist = abs(entry_p - sl)
            sl_dist_pct = (sl_dist / entry_p) if entry_p > 0 else 0.0
            tp_sl_ratio = (abs(tp1 - entry_p) / sl_dist) if sl_dist > 0 else 1.5

            # Parse contributor scores
            contrib_scores = json.loads(row["contributor_scores_json"]) if row["contributor_scores_json"] else {}
            contrib_dirs = json.loads(row["contributor_directions_json"]) if row["contributor_directions_json"] else {}

            # Parse primary target (1 = WIN, 0 = LOSS)
            outcome = str(row["outcome"]).upper()
            target_binary = 1 if outcome == "WIN" else (0 if outcome == "LOSS" else -1)
            realized_r = float(row["realized_r"]) if row["realized_r"] is not None else (1.5 if outcome == "WIN" else (-1.0 if outcome == "LOSS" else 0.0))

            # Build record dict
            rec = {
                # Identifiers (non-feature)
                "signal_id": row["signal_id"],
                "run_id": row["run_id"],
                "signal_timestamp": ts_str,
                "symbol": row["symbol"],
                
                # Base features (T0)
                "direction": row["direction"],
                "entry_price": entry_p,
                "confluence_score": int(row["confluence_score"] or 0),
                "technical_score": int(row["technical_score"] or 0),
                "gemini_score": int(row["gemini_score"] or 0),
                "data_quality": row["data_quality"] or "HIGH",
                "gate_direction": row["gate_direction"] or "NONE",
                "market_regime": row["market_regime"] or "UNCLEAR",
                "session": row["session"] or "UNKNOWN",
                "hour_of_day": hour,
                "day_of_week": day_of_week,
                "sl_dist_pct": sl_dist_pct,
                "tp_sl_ratio": tp_sl_ratio,

                # Contributor individual scores (17 factors)
                "score_HTF_Trend": int(contrib_scores.get("HTF Trend", 0)),
                "score_Market_Structure": int(contrib_scores.get("Market Structure", 0)),
                "score_Momentum": int(contrib_scores.get("Momentum", 0)),
                "score_MTF_Alignment": int(contrib_scores.get("MTF Alignment", 0)),
                "score_SR_Price_Action": int(contrib_scores.get("S/R Price Action", 0)),
                "score_Breakout_Retest": int(contrib_scores.get("Breakout / Retest", 0)),
                "score_Supply_Demand": int(contrib_scores.get("Supply & Demand", 0)),
                "score_Volume_Confirmation": int(contrib_scores.get("Volume Confirmation", 0)),
                "score_SMC_ICT": int(contrib_scores.get("SMC / ICT", 0)),
                "score_ICT_Concepts": int(contrib_scores.get("ICT Concepts", 0)),
                "score_Fibonacci_OTE": int(contrib_scores.get("Fibonacci OTE", 0)),
                "score_Elliott_Wave": int(contrib_scores.get("Elliott Wave", 0)),
                "score_VWAP": int(contrib_scores.get("VWAP", 0)),
                "score_EMA_MA_Stack": int(contrib_scores.get("EMA / MA Stack", 0)),
                "score_RSI": int(contrib_scores.get("RSI", 0)),
                "score_MACD": int(contrib_scores.get("MACD", 0)),
                "score_Gemini_AI": int(contrib_scores.get("Gemini AI", 0)),

                # Contributor directional biases
                "bias_MTF_Alignment": contrib_dirs.get("MTF Alignment", "NEUTRAL"),
                "bias_VWAP": contrib_dirs.get("VWAP", "NEUTRAL"),
                "bias_Momentum": contrib_dirs.get("Momentum", "NEUTRAL"),
                "bias_Volume_Confirmation": contrib_dirs.get("Volume Confirmation", "NEUTRAL"),

                # Targets & Outcome Metrics (strictly isolated from feature vectors)
                "target_binary": target_binary,
                "realized_r": realized_r,
                "outcome": outcome,
            }
            records.append(rec)

        df = pd.DataFrame(records)
        # Filter only resolved outcomes (WIN / LOSS)
        df = df[df["target_binary"].isin([0, 1])].reset_index(drop=True)
        return df
