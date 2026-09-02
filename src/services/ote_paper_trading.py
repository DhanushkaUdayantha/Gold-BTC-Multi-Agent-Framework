"""
OTE Paper Trading Service — Separate from the main PaperTradingService.

Manages paper trade positions opened by the OTE Smart Money strategy.
Persists to ote_trades.json (never touches paper_trading.json).

All trades are simulated. No real orders. No broker connection.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_OTE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ote_trades.json",
)
_STARTING_BALANCE = 10_000.0
_LOT_UNIT = 100.0  # $100 per $1 move per lot for XAU/USD


class OTEPaperTradingService:
    """Manages OTE-strategy paper trade positions and performance metrics."""

    def __init__(self):
        self._ensure_file()

    # ─────────────────────────────────────────────────────────
    # File I/O
    # ─────────────────────────────────────────────────────────

    def _ensure_file(self):
        """Initialize ote_trades.json with demo history if missing."""
        if not os.path.exists(_OTE_FILE) or os.path.getsize(_OTE_FILE) == 0:
            logger.info("Initializing ote_trades.json with demo OTE trade history.")
            demo = self._build_demo_history()
            self._save(demo)

    def _load(self) -> List[Dict[str, Any]]:
        self._ensure_file()
        try:
            with open(_OTE_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read ote_trades.json: {exc}")
            return []

    def _save(self, records: List[Dict[str, Any]]):
        try:
            with open(_OTE_FILE, "w") as f:
                json.dump(records, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to write ote_trades.json: {exc}")

    # ─────────────────────────────────────────────────────────
    # Demo history
    # ─────────────────────────────────────────────────────────

    def _build_demo_history(self) -> List[Dict[str, Any]]:
        """Create a set of realistic closed OTE demo trades."""
        return [
            self._make_trade("BUY",  2683.50, 2668.00, 2706.00, 2728.00, "CLOSED", "WIN",  447.50, "2026-08-24T08:15:00Z", "2026-08-24T12:45:00Z", 2728.00, 0.07, "A+"),
            self._make_trade("SELL", 2701.80, 2716.80, 2679.00, 2658.00, "CLOSED", "WIN",  306.60, "2026-08-25T14:00:00Z", "2026-08-25T17:30:00Z", 2658.00, 0.07, "A"),
            self._make_trade("BUY",  2668.20, 2654.00, 2691.00, 2713.00, "CLOSED", "LOSS",-99.40, "2026-08-26T07:10:00Z", "2026-08-26T09:55:00Z", 2654.00, 0.07, "B"),
            self._make_trade("BUY",  2658.80, 2645.00, 2680.00, 2699.00, "CLOSED", "WIN",  280.00, "2026-08-26T14:20:00Z", "2026-08-27T01:00:00Z", 2680.00, 0.07, "A"),
            self._make_trade("SELL", 2695.40, 2708.40, 2675.00, 2657.00, "CLOSED", "WIN",  267.40, "2026-08-27T08:00:00Z", "2026-08-27T11:30:00Z", 2657.00, 0.07, "A+"),
            self._make_trade("BUY",  2672.10, 2658.50, 2694.00, 2714.00, "CLOSED", "LOSS",-95.20, "2026-08-27T13:45:00Z", "2026-08-27T15:20:00Z", 2658.50, 0.07, "B"),
            self._make_trade("SELL", 2712.60, 2726.00, 2692.00, 2674.00, "CLOSED", "WIN",  185.50, "2026-08-28T07:30:00Z", "2026-08-28T10:00:00Z", 2692.00, 0.07, "A"),
        ]

    @staticmethod
    def _make_trade(
        direction, entry, sl, tp1, tp2, status, result, pnl,
        entry_ts, exit_ts, exit_price, lots, grade
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "symbol": "XAU/USD",
            "strategy": "OTE",
            "direction": direction,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "status": status,
            "result": result,
            "pnl": pnl,
            "entry_timestamp": entry_ts,
            "exit_timestamp": exit_ts,
            "exit_price": exit_price,
            "position_size": lots,
            "setup_grade": grade,
            "trailed_to_breakeven": False,
        }

    # ─────────────────────────────────────────────────────────
    # Trade Management
    # ─────────────────────────────────────────────────────────

    def log_new_signal(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit_1: float,
        take_profit_2: float,
        position_size: float,
        setup_grade: str,
    ):
        """Open a new OTE paper trade if no position is currently open."""
        records = self._load()
        if any(r["status"] == "OPEN" for r in records):
            logger.debug("OTE paper trade skipped — position already open.")
            return

        trade = {
            "id": str(uuid.uuid4()),
            "symbol": "XAU/USD",
            "strategy": "OTE",
            "direction": direction,
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit_1": round(take_profit_1, 2),
            "take_profit_2": round(take_profit_2, 2),
            "status": "OPEN",
            "result": "OPEN",
            "pnl": 0.0,
            "entry_timestamp": datetime.now(timezone.utc).isoformat(),
            "exit_timestamp": None,
            "exit_price": None,
            "position_size": position_size,
            "setup_grade": setup_grade,
            "trailed_to_breakeven": False,
        }
        records.append(trade)
        self._save(records)
        logger.info(f"Opened OTE paper {direction} @ {entry_price:.2f} | SL {stop_loss:.2f} | TP2 {take_profit_2:.2f}")

    def update_and_get_stats(
        self, current_price: float
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Update open OTE positions against current price, then return
        (performance_stats_dict, recent_10_trades_list).
        """
        records = self._load()
        updated = False
        now_str = datetime.now(timezone.utc).isoformat()

        for t in records:
            if t["status"] != "OPEN":
                continue

            direction = t["direction"]
            entry  = t["entry_price"]
            sl     = t["stop_loss"]
            tp1    = t["take_profit_1"]
            tp2    = t["take_profit_2"]
            lots   = t.get("position_size", 0.07)

            if direction == "BUY":
                if current_price <= sl:
                    t.update(status="CLOSED", result="LOSS", exit_price=sl,
                              exit_timestamp=now_str,
                              pnl=round((sl - entry) * _LOT_UNIT * lots, 2))
                    updated = True
                elif current_price >= tp2:
                    t.update(status="CLOSED", result="WIN", exit_price=tp2,
                              exit_timestamp=now_str,
                              pnl=round((tp2 - entry) * _LOT_UNIT * lots, 2))
                    updated = True
                elif current_price >= tp1 and not t.get("trailed_to_breakeven"):
                    t["stop_loss"] = entry
                    t["trailed_to_breakeven"] = True
                    updated = True
            else:  # SELL
                if current_price >= sl:
                    t.update(status="CLOSED", result="LOSS", exit_price=sl,
                              exit_timestamp=now_str,
                              pnl=round((entry - sl) * _LOT_UNIT * lots, 2))
                    updated = True
                elif current_price <= tp2:
                    t.update(status="CLOSED", result="WIN", exit_price=tp2,
                              exit_timestamp=now_str,
                              pnl=round((entry - tp2) * _LOT_UNIT * lots, 2))
                    updated = True
                elif current_price <= tp1 and not t.get("trailed_to_breakeven"):
                    t["stop_loss"] = entry
                    t["trailed_to_breakeven"] = True
                    updated = True

        if updated:
            self._save(records)

        stats = self._compute_stats(records)
        recent = sorted(records, key=lambda x: x["entry_timestamp"], reverse=True)[:10]
        return stats, recent

    # ─────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────

    def _compute_stats(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        closed = [r for r in records if r["status"] == "CLOSED"]
        open_  = [r for r in records if r["status"] == "OPEN"]

        if not closed:
            return {
                "starting_balance": _STARTING_BALANCE,
                "current_balance": _STARTING_BALANCE,
                "net_profit": 0.0,
                "total_trades": 0,
                "open_trades": len(open_),
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
            }

        wins   = [r for r in closed if r["result"] == "WIN"]
        losses = [r for r in closed if r["result"] == "LOSS"]
        net_profit     = sum(r["pnl"] for r in closed)
        gross_profit   = sum(r["pnl"] for r in wins)
        gross_loss_abs = sum(abs(r["pnl"]) for r in losses)

        profit_factor = (
            gross_profit / gross_loss_abs if gross_loss_abs > 0
            else (gross_profit if gross_profit > 0 else 0.0)
        )
        win_rate = len(wins) / len(closed) * 100 if closed else 0.0

        # Max drawdown via equity curve
        balance = _STARTING_BALANCE
        peak = balance
        max_dd = 0.0
        for r in sorted(closed, key=lambda x: x.get("exit_timestamp") or ""):
            balance += r["pnl"]
            peak = max(peak, balance)
            dd = (peak - balance) / peak * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        return {
            "starting_balance": _STARTING_BALANCE,
            "current_balance": round(_STARTING_BALANCE + net_profit, 2),
            "net_profit": round(net_profit, 2),
            "total_trades": len(closed),
            "open_trades": len(open_),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_dd, 2),
        }
