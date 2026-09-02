"""
Isolated Shadow Trading Ledger Service for BTC/USD Shadow Mode.

Completely separated from user-facing manual demo paper trading (paper_trading.json).
- Persisted in an independent SQLite table/database (data/shadow_trades.db).
- Immune to user-facing demo account resets (trade/reset).
- Does not surface in user manual demo balance or open position views.
- Zero broker connections, zero external order routing.

DISCLAIMER: Advisory shadow analytics only. No real broker orders are executed.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/shadow_trades.db"


@dataclass
class ShadowTradeRecord:
    """Individual shadow paper trade record."""
    trade_id: str
    asset: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    calibrated_probability: float
    mtf_confluence_state: str
    session: str
    strategy_version: str
    t0_snapshot_hash: str
    status: str  # "OPEN", "CLOSED_WIN", "CLOSED_LOSS", "CLOSED_EXPIRED"
    open_timestamp_utc: str
    close_timestamp_utc: Optional[str] = None
    exit_price: Optional[float] = None
    realized_r: Optional[float] = None
    mfe_r: Optional[float] = None
    mae_r: Optional[float] = None
    outcome_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShadowTradingStore:
    """
    Isolated persistent storage ledger for BTC shadow paper trades.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create shadow_trades table if not present."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shadow_trades (
                        trade_id TEXT PRIMARY KEY,
                        asset TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        stop_loss REAL NOT NULL,
                        take_profit_1 REAL NOT NULL,
                        take_profit_2 REAL NOT NULL,
                        calibrated_probability REAL NOT NULL,
                        mtf_confluence_state TEXT NOT NULL,
                        session TEXT NOT NULL,
                        strategy_version TEXT NOT NULL,
                        t0_snapshot_hash TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'OPEN',
                        open_timestamp_utc TEXT NOT NULL,
                        close_timestamp_utc TEXT,
                        exit_price REAL,
                        realized_r REAL,
                        mfe_r REAL,
                        mae_r REAL,
                        outcome_notes TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_asset_status ON shadow_trades(asset, status)")
        except Exception as exc:
            logger.error(f"Error initializing shadow_trades SQLite database: {exc}")

    def open_shadow_trade(
        self,
        trade_id: str,
        asset: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit_1: float,
        take_profit_2: float,
        calibrated_probability: float,
        mtf_confluence_state: str,
        session: str,
        strategy_version: str,
        t0_snapshot_hash: str,
        open_timestamp_utc: Optional[str] = None,
    ) -> Optional[ShadowTradeRecord]:
        """Record a new open shadow paper trade idempotently."""
        ts = open_timestamp_utc or datetime.now(timezone.utc).isoformat()
        record = ShadowTradeRecord(
            trade_id=trade_id,
            asset=asset,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            calibrated_probability=calibrated_probability,
            mtf_confluence_state=mtf_confluence_state,
            session=session,
            strategy_version=strategy_version,
            t0_snapshot_hash=t0_snapshot_hash,
            status="OPEN",
            open_timestamp_utc=ts,
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO shadow_trades (
                        trade_id, asset, direction, entry_price, stop_loss,
                        take_profit_1, take_profit_2, calibrated_probability,
                        mtf_confluence_state, session, strategy_version,
                        t0_snapshot_hash, status, open_timestamp_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (
                    record.trade_id, record.asset, record.direction,
                    record.entry_price, record.stop_loss, record.take_profit_1,
                    record.take_profit_2, record.calibrated_probability,
                    record.mtf_confluence_state, record.session,
                    record.strategy_version, record.t0_snapshot_hash,
                    record.open_timestamp_utc
                ))
            return record
        except Exception as exc:
            logger.error(f"Failed to record shadow trade {trade_id}: {exc}")
            return None

    def close_shadow_trade(
        self,
        trade_id: str,
        exit_price: float,
        realized_r: float,
        outcome_status: str,
        mfe_r: Optional[float] = None,
        mae_r: Optional[float] = None,
        outcome_notes: Optional[str] = None,
        close_timestamp_utc: Optional[str] = None,
    ) -> bool:
        """Close an existing open shadow trade with final outcome and realized R."""
        ts = close_timestamp_utc or datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    UPDATE shadow_trades
                    SET status = ?,
                        close_timestamp_utc = ?,
                        exit_price = ?,
                        realized_r = ?,
                        mfe_r = ?,
                        mae_r = ?,
                        outcome_notes = ?
                    WHERE trade_id = ? AND status = 'OPEN'
                """, (outcome_status, ts, exit_price, realized_r, mfe_r, mae_r, outcome_notes, trade_id))
                return cur.rowcount > 0
        except Exception as exc:
            logger.error(f"Failed to close shadow trade {trade_id}: {exc}")
            return False

    def get_all_trades(self, asset: Optional[str] = None) -> List[ShadowTradeRecord]:
        """Fetch all shadow trade records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if asset:
                    rows = conn.execute("SELECT * FROM shadow_trades WHERE asset = ? ORDER BY open_timestamp_utc ASC", (asset,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM shadow_trades ORDER BY open_timestamp_utc ASC").fetchall()

                return [
                    ShadowTradeRecord(
                        trade_id=r["trade_id"],
                        asset=r["asset"],
                        direction=r["direction"],
                        entry_price=r["entry_price"],
                        stop_loss=r["stop_loss"],
                        take_profit_1=r["take_profit_1"],
                        take_profit_2=r["take_profit_2"],
                        calibrated_probability=r["calibrated_probability"],
                        mtf_confluence_state=r["mtf_confluence_state"],
                        session=r["session"],
                        strategy_version=r["strategy_version"],
                        t0_snapshot_hash=r["t0_snapshot_hash"],
                        status=r["status"],
                        open_timestamp_utc=r["open_timestamp_utc"],
                        close_timestamp_utc=r["close_timestamp_utc"],
                        exit_price=r["exit_price"],
                        realized_r=r["realized_r"],
                        mfe_r=r["mfe_r"],
                        mae_r=r["mae_r"],
                        outcome_notes=r["outcome_notes"],
                    )
                    for r in rows
                ]
        except Exception as exc:
            logger.error(f"Failed to load shadow trades: {exc}")
            return []

    def get_summary_metrics(self, asset: str = "BTC/USD") -> Dict[str, Any]:
        """Calculate live summary statistics from resolved shadow trades."""
        trades = self.get_all_trades(asset=asset)
        open_trades = [t for t in trades if t.status == "OPEN"]
        resolved = [t for t in trades if t.status.startswith("CLOSED_")]

        resolved_count = len(resolved)
        if resolved_count == 0:
            return {
                "asset": asset,
                "total_trades": len(trades),
                "open_trades_count": len(open_trades),
                "resolved_trades_count": 0,
                "wins_count": 0,
                "losses_count": 0,
                "win_rate_pct": 0.0,
                "ev_r": 0.0,
                "profit_factor": 0.0,
                "total_realized_r": 0.0,
                "max_drawdown_r": 0.0,
                "first_trade_ts": None,
                "last_trade_ts": None,
                "days_active": 0.0,
            }

        wins = [t for t in resolved if t.status == "CLOSED_WIN"]
        losses = [t for t in resolved if t.status == "CLOSED_LOSS"]
        total_r = sum(t.realized_r or 0.0 for t in resolved)
        ev_r = total_r / resolved_count
        win_rate = (len(wins) / resolved_count) * 100.0

        gross_profit = sum(t.realized_r for t in wins if t.realized_r and t.realized_r > 0)
        gross_loss = abs(sum(t.realized_r for t in losses if t.realized_r and t.realized_r < 0))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        # Calculate Max Drawdown in R
        cum_r = 0.0
        peak_r = 0.0
        max_dd = 0.0
        for t in resolved:
            cum_r += (t.realized_r or 0.0)
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd:
                max_dd = dd

        first_ts = resolved[0].open_timestamp_utc
        last_ts = resolved[-1].close_timestamp_utc or resolved[-1].open_timestamp_utc
        days_active = 0.0
        try:
            dt1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            dt2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            days_active = max(0.0, (dt2 - dt1).total_seconds() / 86400.0)
        except Exception:
            pass

        return {
            "asset": asset,
            "total_trades": len(trades),
            "open_trades_count": len(open_trades),
            "resolved_trades_count": resolved_count,
            "wins_count": len(wins),
            "losses_count": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "ev_r": round(ev_r, 4),
            "profit_factor": round(pf, 2),
            "total_realized_r": round(total_r, 2),
            "max_drawdown_r": round(max_dd, 2),
            "first_trade_ts": first_ts,
            "last_trade_ts": last_ts,
            "days_active": round(days_active, 1),
        }


_shadow_store_instance: Optional[ShadowTradingStore] = None


def get_shadow_trading_store(db_path: str = _DEFAULT_DB_PATH) -> ShadowTradingStore:
    global _shadow_store_instance
    if _shadow_store_instance is None:
        _shadow_store_instance = ShadowTradingStore(db_path=db_path)
    return _shadow_store_instance
