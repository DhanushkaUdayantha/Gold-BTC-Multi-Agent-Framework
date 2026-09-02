"""
Historical Strategy Analytics Service.

Provides validated point-in-time strategy qualification, multi-dimensional filtering,
dynamic performance summary KPI calculation, rolling expectancy curves, and research
benchmark comparison for the upgraded History section.

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.services.point_in_time_validator import DB_PATH
from src.services.stable_expectancy_researcher import StableExpectancyResearcher, ResearchObservation

logger = logging.getLogger(__name__)


@dataclass
class ValidatedSignalRecord:
    """Historical signal record augmented with point-in-time validated strategy analytics."""
    signal_id: str
    symbol: str
    signal_timestamp: str
    direction: str  # BUY / SELL
    confluence_score: int
    entry_price: float
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    exit_price: Optional[float]
    outcome: str  # WIN / LOSS / BREAKEVEN / EXPIRED
    realized_r: float
    mfe: float
    mae: float
    market_regime: str  # LOW_VOLATILITY, TRENDING, RANGING, HIGH_VOLATILITY
    session: str  # LONDON, NEW_YORK, ASIA, OVERLAP
    calibrated_probability: float  # 0.0 to 1.0 (from 60% Train Logistic Calibration)
    # Alignment features
    htf_aligned: bool
    sr_aligned: bool
    vwap_aligned: bool
    ema_aligned: bool
    mom_aligned: bool
    # Strategy Qualification
    qualification_status: str  # QUALIFIED, NOT QUALIFIED, INSUFFICIENT DATA
    qualification_tag: str  # e.g. "BTC SELL LOW-VOL QUALIFIED", "XAU BUY VWAP QUALIFIED", "NOT QUALIFIED"
    qualification_reason: str


@dataclass
class PerformanceSummaryKPIs:
    """Dynamically calculated performance metrics for currently filtered trade set."""
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    total_realized_r: float
    max_drawdown_r: float
    avg_win_r: float
    avg_loss_r: float


@dataclass
class EquityCurvePoint:
    """Point along cumulative R and drawdown equity trajectory."""
    trade_index: int
    timestamp: str
    signal_id: str
    symbol: str
    direction: str
    outcome: str
    realized_r: float
    cumulative_r: float
    drawdown_r: float
    rolling_expectancy_25: float


@dataclass
class StrategyBenchmarkCard:
    """Research-validated benchmark for comparison."""
    strategy_id: str
    display_name: str
    asset: str
    direction: str
    primary_condition: str
    expectancy_r: float
    win_rate_pct: float
    profit_factor: float
    validation_score: int
    status: str
    description: str


class HistoricalStrategyAnalyticsService:
    """
    Singleton service managing historical signals and validated strategy qualifications.
    """
    _instance: Optional[HistoricalStrategyAnalyticsService] = None

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.researcher = StableExpectancyResearcher(db_path=self.db_path)
        self._cached_signals: Optional[List[ValidatedSignalRecord]] = None
        self._cache_timestamp: Optional[str] = None

    @classmethod
    def get_instance(cls, db_path: str = DB_PATH) -> HistoricalStrategyAnalyticsService:
        if cls._instance is None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    def _load_and_qualify_all_signals(self) -> List[ValidatedSignalRecord]:
        """Load and qualify all historical signals strictly with point-in-time calibration."""
        btc_obs = self.researcher.build_research_dataset("BTC-USD")
        xau_obs = self.researcher.build_research_dataset("XAU-USD")

        all_obs = btc_obs + xau_obs

        # Query price and trade parameters
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                """
                SELECT signal_id, entry_price, stop_loss, take_profit_1, take_profit_2,
                       exit_price, market_regime, session
                FROM historical_signals
                """
            )
            price_map = {r["signal_id"]: dict(r) for r in cur.fetchall()}
        finally:
            conn.close()

        records: List[ValidatedSignalRecord] = []

        for o in all_obs:
            pm = price_map.get(o.signal_id, {})
            norm_sym = "BTC/USD" if "BTC" in o.asset else "XAU/USD"
            reg = pm.get("market_regime", o.market_regime) or "UNKNOWN"
            sess = pm.get("session", o.session) or "UNKNOWN"

            # Strategy Qualification Logic (strictly aligned with research findings)
            qual_status = "NOT QUALIFIED"
            qual_tag = "NOT QUALIFIED"
            qual_reason = "Signal does not satisfy validated strategy criteria"

            if norm_sym == "BTC/USD":
                if o.direction == "SELL" and o.calibrated_probability >= 0.40 and reg == "LOW_VOLATILITY":
                    qual_status = "QUALIFIED"
                    qual_tag = "BTC SELL LOW-VOL QUALIFIED"
                    qual_reason = "Meets primary validated BTC research criteria (Prob >= 40% + LOW_VOLATILITY)"
                elif o.direction == "SELL" and o.calibrated_probability >= 0.40 and (o.htf_aligned and o.sr_aligned):
                    qual_status = "QUALIFIED"
                    qual_tag = "BTC SELL HTF+SR QUALIFIED"
                    qual_reason = "Meets secondary validated BTC criteria (Prob >= 40% + HTF Trend & S/R aligned)"
                elif o.direction == "BUY":
                    qual_status = "NOT QUALIFIED"
                    qual_tag = "NOT QUALIFIED (NEGATIVE BTC BUY DRIFT)"
                    qual_reason = "BTC BUY signals exhibit empirical negative expectancy across historical data"
            elif norm_sym == "XAU/USD":
                if o.direction == "BUY" and o.calibrated_probability >= 0.42 and o.vwap_aligned:
                    qual_status = "QUALIFIED"
                    qual_tag = "XAU BUY VWAP QUALIFIED"
                    qual_reason = "Meets primary validated XAU research criteria (Prob >= 42% + VWAP aligned)"
                elif o.direction == "BUY" and o.calibrated_probability >= 0.42 and o.ema_aligned:
                    qual_status = "QUALIFIED"
                    qual_tag = "XAU BUY EMA QUALIFIED"
                    qual_reason = "Meets secondary validated XAU criteria (Prob >= 42% + EMA Stack aligned)"

            rec = ValidatedSignalRecord(
                signal_id=o.signal_id,
                symbol=norm_sym,
                signal_timestamp=o.signal_timestamp,
                direction=o.direction,
                confluence_score=o.confluence_score,
                entry_price=float(pm.get("entry_price") or 0.0),
                stop_loss=float(pm.get("stop_loss")) if pm.get("stop_loss") is not None else None,
                take_profit_1=float(pm.get("take_profit_1")) if pm.get("take_profit_1") is not None else None,
                take_profit_2=float(pm.get("take_profit_2")) if pm.get("take_profit_2") is not None else None,
                exit_price=float(pm.get("exit_price")) if pm.get("exit_price") is not None else None,
                outcome=o.actual_outcome,
                realized_r=round(o.realized_r, 3),
                mfe=round(o.mfe, 2),
                mae=round(o.mae, 2),
                market_regime=reg,
                session=sess,
                calibrated_probability=round(o.calibrated_probability, 3),
                htf_aligned=o.htf_aligned,
                sr_aligned=o.sr_aligned,
                vwap_aligned=o.vwap_aligned,
                ema_aligned=o.ema_aligned,
                mom_aligned=o.mom_aligned,
                qualification_status=qual_status,
                qualification_tag=qual_tag,
                qualification_reason=qual_reason,
            )
            records.append(rec)

        # Sort strictly chronologically
        records.sort(key=lambda x: x.signal_timestamp)
        return records

    def get_all_signals(self, force_refresh: bool = False) -> List[ValidatedSignalRecord]:
        """Get cached signals or reload."""
        if self._cached_signals is None or force_refresh:
            self._cached_signals = self._load_and_qualify_all_signals()
            self._cache_timestamp = datetime.now(timezone.utc).isoformat()
        return self._cached_signals

    def query_history_analytics(
        self,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        outcome: Optional[str] = None,
        min_prob: Optional[float] = None,
        max_prob: Optional[float] = None,
        market_regime: Optional[str] = None,
        qualification_status: Optional[str] = None,
        qualification: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute multi-factor dynamic filter query, compute KPIs, and build equity curves.
        """
        all_signals = self.get_all_signals()
        filtered: List[ValidatedSignalRecord] = []
        target_qual = qualification or qualification_status

        for s in all_signals:
            # 1. Symbol Filter
            if symbol and symbol.upper() != "ALL":
                if "BTC" in symbol.upper() and s.symbol != "BTC/USD":
                    continue
                if ("XAU" in symbol.upper() or "GOLD" in symbol.upper()) and s.symbol != "XAU/USD":
                    continue

            # 2. Direction Filter
            if direction and direction.upper() != "ALL" and s.direction != direction.upper():
                continue

            # 3. Outcome Filter
            if outcome and outcome.upper() != "ALL" and s.outcome != outcome.upper():
                continue

            # 4. Probability Filter
            if min_prob is not None and s.calibrated_probability < min_prob:
                continue
            if max_prob is not None and s.calibrated_probability > max_prob:
                continue

            # 5. Market Regime Filter
            if market_regime and market_regime.upper() != "ALL" and s.market_regime != market_regime.upper():
                continue

            # 6. Strategy Qualification Filter
            if target_qual and target_qual.upper() != "ALL":
                if target_qual.upper() in ("QUALIFIED", "QUALIFIED_ONLY") and s.qualification_status != "QUALIFIED":
                    continue
                if target_qual.upper() == "NOT_QUALIFIED" and s.qualification_status == "QUALIFIED":
                    continue

            # 7. Date Range Filter
            if start_date and s.signal_timestamp[:10] < start_date:
                continue
            if end_date and s.signal_timestamp[:10] > end_date:
                continue

            filtered.append(s)

        total_count = len(filtered)

        # Calculate Performance KPIs over the filtered subset
        wins = sum(1 for s in filtered if s.outcome == "WIN")
        losses = sum(1 for s in filtered if s.outcome == "LOSS")
        breakevens = sum(1 for s in filtered if s.outcome == "BREAKEVEN")
        completed = wins + losses

        wr_pct = round(wins / completed * 100.0, 1) if completed > 0 else 0.0
        r_vals = [s.realized_r for s in filtered if s.outcome in ("WIN", "LOSS")]
        exp_r = round(float(np.mean(r_vals)), 3) if r_vals else 0.0
        tot_r = round(float(sum(r_vals)), 2) if r_vals else 0.0

        pos_rs = [r for r in r_vals if r > 0]
        neg_rs = [abs(r) for r in r_vals if r < 0]
        avg_win = round(float(np.mean(pos_rs)), 2) if pos_rs else 0.0
        avg_loss = round(float(np.mean(neg_rs)), 2) if neg_rs else 0.0
        pf = round(sum(pos_rs) / sum(neg_rs), 2) if neg_rs and pos_rs else (1.0 if not r_vals else 0.0)

        # Equity Curve and Max Drawdown Calculation
        equity_points: List[EquityCurvePoint] = []
        cum_r = 0.0
        peak_r = 0.0
        max_dd = 0.0
        window_25_rs: List[float] = []
        trade_idx = 0

        for s in filtered:
            if s.outcome not in ("WIN", "LOSS"):
                continue
            trade_idx += 1
            r = s.realized_r
            cum_r += r
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd:
                max_dd = dd

            window_25_rs.append(r)
            if len(window_25_rs) > 25:
                window_25_rs.pop(0)
            roll_exp_25 = round(float(np.mean(window_25_rs)), 3) if window_25_rs else 0.0

            equity_points.append(
                EquityCurvePoint(
                    trade_index=trade_idx,
                    timestamp=s.signal_timestamp,
                    signal_id=s.signal_id,
                    symbol=s.symbol,
                    direction=s.direction,
                    outcome=s.outcome,
                    realized_r=r,
                    cumulative_r=round(cum_r, 3),
                    drawdown_r=round(dd, 3),
                    rolling_expectancy_25=roll_exp_25,
                )
            )

        kpi_summary = PerformanceSummaryKPIs(
            total_trades=total_count,
            wins=wins,
            losses=losses,
            breakevens=breakevens,
            win_rate_pct=wr_pct,
            expectancy_r=exp_r,
            profit_factor=pf,
            total_realized_r=tot_r,
            max_drawdown_r=round(max_dd, 2),
            avg_win_r=avg_win,
            avg_loss_r=avg_loss,
        )

        # Slice paginated results
        paginated_signals = filtered[offset : offset + limit]

        # Strategy benchmark definitions
        benchmarks = [
            StrategyBenchmarkCard(
                strategy_id="BTC-SELL-P40-REGIME_LOW_VOL",
                display_name="BTC SELL LOW-VOL",
                asset="BTC/USD",
                direction="SELL",
                primary_condition="Probability >= 40% + LOW_VOLATILITY",
                expectancy_r=0.47,
                win_rate_pct=58.9,
                profit_factor=2.15,
                validation_score=95,
                status="QUALIFIED FOR PAPER TRADING",
                description="Highest overall expectancy; 100% positive rolling windows, 4/4 walk-forward folds.",
            ),
            StrategyBenchmarkCard(
                strategy_id="XAU-BUY-P42-VWAP_ALIGNED",
                display_name="XAU BUY VWAP",
                asset="XAU/USD",
                direction="BUY",
                primary_condition="Probability >= 42% + VWAP Aligned",
                expectancy_r=0.20,
                win_rate_pct=48.2,
                profit_factor=1.39,
                validation_score=84,
                status="QUALIFIED FOR PAPER TRADING",
                description="High sample volume (N=517); stable across all historical eras and 4/4 walk-forward folds.",
            ),
        ]

        return {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "kpi_summary": asdict(kpi_summary),
            "strategy_benchmarks": [asdict(b) for b in benchmarks],
            "equity_curve": [asdict(p) for p in equity_points],
            "signals": [asdict(s) for s in paginated_signals],
        }
