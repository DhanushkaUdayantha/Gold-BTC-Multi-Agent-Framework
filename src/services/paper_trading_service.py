"""
Paper Trading Performance Tracker and Statistics Service for XAU/USD.

Logs advisory signals, tracks active mock positions against live prices,
and computes win rates, profit factors, drawdowns, and trading logs.

All trades are simulated paper-trading only. No broker orders are executed.
"""
import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# File path inside project root
_PT_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "paper_trading.json")
_STARTING_BALANCE = 10000.0


class PaperTradingService:
    """Simulates paper trading, handles trade logging, and calculates statistics."""

    def __init__(self):
        self._initialize_file_if_missing()

    def _initialize_file_if_missing(self):
        """Create the paper trading log file if empty/missing."""
        if not os.path.exists(_PT_FILE_PATH) or os.path.getsize(_PT_FILE_PATH) == 0:
            logger.info("Initializing empty paper_trading.json")
            self._save_to_file([])


    def _load_from_file(self) -> List[Dict[str, Any]]:
        """Load trade records list from JSON file safely."""
        self._initialize_file_if_missing()
        try:
            with open(_PT_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read paper_trading.json: {exc}")
            return []

    def _save_to_file(self, records: List[Dict[str, Any]]):
        """Save trade records list to JSON file safely."""
        try:
            with open(_PT_FILE_PATH, "w") as f:
                json.dump(records, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to write paper_trading.json: {exc}")

    # ------------------------------------------------------------------
    # Position Sizing
    # ------------------------------------------------------------------

    def calculate_position_size(self, entry: float, stop_loss: float, risk_pct: float = 1.0) -> float:
        """
        Calculate suggested position size in standard lots.
        Formula: (Balance * Risk%) / (SL_Distance_in_USD * 100 ounces_per_lot)
        """
        risk_amount = _STARTING_BALANCE * (risk_pct / 100.0)
        sl_distance = abs(entry - stop_loss)
        if sl_distance <= 0.01:
            return 0.01
        
        # 1 lot of XAU/USD is 100 ounces, meaning a $1 move represents $100 value change
        lots = risk_amount / (sl_distance * 100.0)
        # Round to 2 decimal places, cap between 0.01 and 10.0 lots for safety
        return max(0.01, min(10.0, round(lots, 2)))

    # ------------------------------------------------------------------
    # Duration Calculation Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_duration(entry_ts: str, exit_dt: datetime) -> str:
        """Calculate human-readable duration between entry and exit timestamp."""
        try:
            entry_dt = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
            diff_secs = max(0, int((exit_dt - entry_dt).total_seconds()))
            if diff_secs < 60:
                return f"{diff_secs}s"
            elif diff_secs < 3600:
                return f"{diff_secs // 60}m {diff_secs % 60}s"
            else:
                return f"{diff_secs // 3600}h {(diff_secs % 3600) // 60}m"
        except Exception:
            return "1m"

    # ------------------------------------------------------------------
    # Trade Management Pipeline
    # ------------------------------------------------------------------

    def update_and_get_stats(self, current_price: float) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Main pipeline call:
          1. Continuously calculate live unrealized P/L for open demo positions against current price.
          2. Positions remain strictly OPEN while price moves (SL/TP are reference risk/target levels).
          3. Only manual CLOSE TRADE closes an open position.
          4. Compute performance metrics for closed and open trades.
        Returns (stats_dict, recent_trades_list).
        """
        records = self._load_from_file()

        # Calculate live unrealized P/L on-the-fly for open trades if price is valid (> 500.0)
        if current_price and current_price >= 500.0:
            for t in records:
                if t["status"] == "OPEN":
                    direction = t["direction"]
                    entry = t["entry_price"]
                    lots = t.get("position_size", 0.1)
                    if direction == "BUY":
                        t["pnl"] = round((current_price - entry) * 100.0 * lots, 2)
                    else:
                        t["pnl"] = round((entry - current_price) * 100.0 * lots, 2)

        stats = self._calculate_performance_metrics(records)

        # return all trades sorted by entry date
        recent = sorted(records, key=lambda x: x["entry_timestamp"], reverse=True)

        return stats, recent

    def log_new_signal(self, *args, **kwargs):
        """No-op: Automatic signal logging is disabled in favor of manual dashboard trading."""
        pass

    def open_manual_trade(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float = 0.0,
        take_profit_1: float = 0.0,
        take_profit_2: float = 0.0,
        position_size: float = 0.0,
        setup_grade: str = "MANUAL",
    ) -> Dict[str, Any]:
        """
        Open a new demo trade with:
          - SL = $100 loss from real entry price (or validated custom SL)
          - TP = $300 profit from real entry price (or validated custom TP)
        """
        records = self._load_from_file()
        direction = direction.upper()

        # Validate or default position size in lots
        lots = position_size if position_size > 0 else 0.10
        lots = max(0.01, min(10.0, round(lots, 2)))

        # In XAU/USD (1 standard lot = 100 oz):
        # $100 loss -> price delta = $100 / (100 * lots) = 1.0 / lots
        # $300 profit -> price delta = $300 / (100 * lots) = 3.0 / lots
        price_sl_delta = round(1.0 / lots, 2)
        price_tp_delta = round(3.0 / lots, 2)

        if direction == "BUY":
            default_sl = round(entry_price - price_sl_delta, 2)
            default_tp = round(entry_price + price_tp_delta, 2)
            # Use custom SL/TP if provided and structurally valid (sl < entry < tp)
            sl = round(stop_loss, 2) if (stop_loss and stop_loss > 0 and stop_loss < entry_price) else default_sl
            tp = round(take_profit_1, 2) if (take_profit_1 and take_profit_1 > 0 and take_profit_1 > entry_price) else default_tp
        else:  # SELL
            default_sl = round(entry_price + price_sl_delta, 2)
            default_tp = round(entry_price - price_tp_delta, 2)
            # Use custom SL/TP if provided and structurally valid (tp < entry < sl)
            sl = round(stop_loss, 2) if (stop_loss and stop_loss > 0 and stop_loss > entry_price) else default_sl
            tp = round(take_profit_1, 2) if (take_profit_1 and take_profit_1 > 0 and take_profit_1 < entry_price) else default_tp

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        new_trade = {
            "id": str(uuid.uuid4()),
            "symbol": "XAU/USD",
            "direction": direction,
            "entry_price": round(entry_price, 2),
            "stop_loss": sl,
            "take_profit_1": tp,
            "take_profit_2": tp,
            "status": "OPEN",
            "result": "OPEN",
            "pnl": 0.0,
            "entry_timestamp": now_iso,
            "exit_timestamp": None,
            "exit_price": None,
            "duration": "0m",
            "position_size": lots,
            "setup_grade": setup_grade or "MANUAL",
        }
        records.append(new_trade)
        self._save_to_file(records)
        logger.info(
            f"Opened manual demo position: {direction} @ {entry_price:.2f} "
            f"(lots: {lots}, SL: {sl}, TP: {tp})"
        )
        return new_trade

    def update_trade(
        self,
        trade_id: str,
        stop_loss: Optional[float] = None,
        take_profit_1: Optional[float] = None,
        take_profit_2: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Manually adjust Stop Loss and/or Take Profit for an active open demo trade.
        Validates that SL and TP remain on the correct side of the entry price.
        """
        records = self._load_from_file()
        target = None
        for t in records:
            if t["id"] == trade_id and t["status"] == "OPEN":
                target = t
                break

        if not target:
            return None

        direction = target["direction"]
        entry = target["entry_price"]

        if stop_loss is not None and stop_loss > 0:
            if direction == "BUY" and stop_loss < entry:
                target["stop_loss"] = round(stop_loss, 2)
            elif direction == "SELL" and stop_loss > entry:
                target["stop_loss"] = round(stop_loss, 2)

        tp_val = take_profit_1 if (take_profit_1 is not None and take_profit_1 > 0) else take_profit_2
        if tp_val is not None and tp_val > 0:
            if direction == "BUY" and tp_val > entry:
                target["take_profit_1"] = round(tp_val, 2)
                target["take_profit_2"] = round(tp_val, 2)
            elif direction == "SELL" and tp_val < entry:
                target["take_profit_1"] = round(tp_val, 2)
                target["take_profit_2"] = round(tp_val, 2)

        self._save_to_file(records)
        logger.info(f"Updated demo trade {trade_id}: SL={target['stop_loss']}, TP={target['take_profit_1']}")
        return target

    def close_manual_trade(self, trade_id: str, current_price: float = 0.0) -> Optional[Dict[str, Any]]:
        """Close an open trade manually from the UI."""
        records = self._load_from_file()
        target = None
        for t in records:
            if t["id"] == trade_id and t["status"] == "OPEN":
                target = t
                break
        
        if not target:
            return None
            
        direction = target["direction"]
        entry = target["entry_price"]
        lots = target.get("position_size", 0.10)
        if current_price <= 0:
            current_price = entry  # Fallback

        now = datetime.now(timezone.utc)
        target["status"] = "CLOSED"
        target["exit_price"] = round(current_price, 2)
        target["exit_timestamp"] = now.isoformat()
        duration_str = self._calculate_duration(target.get("entry_timestamp", now.isoformat()), now)
        target["duration"] = duration_str

        # Calculate P&L
        if direction == "BUY":
            pnl = (current_price - entry) * 100.0 * lots
        else:
            pnl = (entry - current_price) * 100.0 * lots
            
        target["pnl"] = round(pnl, 2)
        target["result"] = "WIN" if pnl >= 0 else "LOSS"
        
        self._save_to_file(records)
        logger.info(f"Closed manual demo position {trade_id} @ {current_price:.2f} (P&L: ${pnl:.2f}, Duration: {duration_str})")
        return target

    def reset_account(self):
        """Reset the paper trading balance and trade history to defaults."""
        if os.path.exists(_PT_FILE_PATH):
            try:
                os.remove(_PT_FILE_PATH)
            except Exception as e:
                logger.error(f"Failed to remove paper_trading.json: {e}")
        self._initialize_file_if_missing()


    # ------------------------------------------------------------------
    # Metrics calculations
    # ------------------------------------------------------------------

    def _calculate_performance_metrics(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute win rate, profit factor, drawdown, net profit, equity, open trades and totals."""
        closed_trades = [t for t in records if t["status"] == "CLOSED"]
        open_trades = [t for t in records if t["status"] == "OPEN"]
        total_closed = len(closed_trades)

        net_profit = sum(t["pnl"] for t in closed_trades)
        current_balance = _STARTING_BALANCE + net_profit

        # Calculate unrealized P/L for equity
        unrealized_pnl = sum(t.get("pnl", 0.0) for t in open_trades)
        equity = current_balance + unrealized_pnl

        if total_closed == 0:
            return {
                "starting_balance": _STARTING_BALANCE,
                "current_balance": _STARTING_BALANCE,
                "net_profit": 0.0,
                "total_trades": 0,
                "open_trades": len(open_trades),
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "equity": round(equity, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
            }

        wins_list = [t for t in closed_trades if t["result"] == "WIN"]
        losses_list = [t for t in closed_trades if t["result"] == "LOSS"]

        wins_count = len(wins_list)
        losses_count = len(losses_list)

        win_rate = (wins_count / total_closed) * 100.0 if total_closed > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in wins_list)
        gross_loss = sum(abs(t["pnl"]) for t in losses_list)

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        # Calculate Maximum Drawdown based on historical balance curve
        balance = _STARTING_BALANCE
        peaks = [_STARTING_BALANCE]
        drawdowns = [0.0]

        # Re-sort trades chronologically to compute drawdown correctly
        chrono_trades = sorted(closed_trades, key=lambda x: x["exit_timestamp"])
        for t in chrono_trades:
            balance += t["pnl"]
            peaks.append(max(peaks[-1], balance))
            current_peak = peaks[-1]
            dd = (current_peak - balance) / current_peak * 100.0
            drawdowns.append(dd)

        max_drawdown = max(drawdowns)

        return {
            "starting_balance": _STARTING_BALANCE,
            "current_balance": round(current_balance, 2),
            "net_profit": round(net_profit, 2),
            "total_trades": total_closed,
            "open_trades": len(open_trades),
            "wins": wins_count,
            "losses": losses_count,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
        }

