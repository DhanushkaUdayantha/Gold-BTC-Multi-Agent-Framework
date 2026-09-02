"""
Pre-Registered Comparison & Confirmation Gate for BTC Shadow Runner.

Evaluates live BTC shadow performance against the frozen backtest forward-shadow baseline:
- Pre-registered hardcoded gates: N >= 50 resolved trades AND >= 14 calendar days elapsed.
- Shadow EV compared against backtest 95% bootstrap CI ([+0.0444R, +0.3240R] or EV >= +0.0444R).
- Shadow Win Rate compared against backtest 95% CI ([44.5%, 63.8%]).
- Statistical drift check requiring LOW_DRIFT status.
- Classification: ACCUMULATING, PASS, FAIL.
- Read-only diagnostics for human review: zero write access to production gating flags.

DISCLAIMER: Advisory research evaluation only. Does not automatically mutate gating flags.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.services.shadow_trading_store import ShadowTradingStore, get_shadow_trading_store
from src.research.governance.drift_and_bias import run_drift_and_degradation_audit

logger = logging.getLogger(__name__)

# Pre-registered acceptance standards (frozen prior to live execution)
_MIN_RESOLVED_TRADES: int = 50
_MIN_CALENDAR_DAYS: float = 14.0
_BACKTEST_BASELINE_EV: float = 0.3650
_BACKTEST_BOOTSTRAP_EV_CI_LOWER: float = 0.0444
_BACKTEST_BOOTSTRAP_EV_CI_UPPER: float = 0.6500
_BACKTEST_BASELINE_WR: float = 55.88
_BACKTEST_BOOTSTRAP_WR_CI_LOWER: float = 44.50
_BACKTEST_BOOTSTRAP_WR_CI_UPPER: float = 65.00


@dataclass
class PreRegisteredThresholds:
    """Pre-registered statistical acceptance criteria."""
    min_sample_size_n: int = _MIN_RESOLVED_TRADES
    min_calendar_days: float = _MIN_CALENDAR_DAYS
    backtest_ev_baseline: float = _BACKTEST_BASELINE_EV
    ev_acceptable_range: List[float] = field(default_factory=lambda: [_BACKTEST_BOOTSTRAP_EV_CI_LOWER, _BACKTEST_BOOTSTRAP_EV_CI_UPPER])
    backtest_wr_baseline: float = _BACKTEST_BASELINE_WR
    wr_acceptable_range: List[float] = field(default_factory=lambda: [_BACKTEST_BOOTSTRAP_WR_CI_LOWER, _BACKTEST_BOOTSTRAP_WR_CI_UPPER])
    required_drift_status: str = "LOW_DRIFT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShadowComparisonReport:
    """Consolidated human-review comparison report."""
    evaluation_timestamp_utc: str
    asset: str
    sample_size_n: int
    calendar_days_elapsed: float
    live_ev_r: float
    live_win_rate_pct: float
    live_profit_factor: float
    live_max_drawdown_r: float
    drift_status: str
    sample_gate_passed: bool
    time_gate_passed: bool
    ev_gate_passed: bool
    wr_gate_passed: bool
    drift_gate_passed: bool
    verdict: str  # "ACCUMULATING", "PASS", "FAIL"
    verdict_summary: str
    pre_registered_thresholds: PreRegisteredThresholds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_timestamp_utc": self.evaluation_timestamp_utc,
            "asset": self.asset,
            "sample_size_n": self.sample_size_n,
            "calendar_days_elapsed": self.calendar_days_elapsed,
            "live_ev_r": self.live_ev_r,
            "live_win_rate_pct": self.live_win_rate_pct,
            "live_profit_factor": self.live_profit_factor,
            "live_max_drawdown_r": self.live_max_drawdown_r,
            "drift_status": self.drift_status,
            "sample_gate_passed": self.sample_gate_passed,
            "time_gate_passed": self.time_gate_passed,
            "ev_gate_passed": self.ev_gate_passed,
            "wr_gate_passed": self.wr_gate_passed,
            "drift_gate_passed": self.drift_gate_passed,
            "verdict": self.verdict,
            "verdict_summary": self.verdict_summary,
            "pre_registered_thresholds": self.pre_registered_thresholds.to_dict(),
        }


class BTCShadowComparisonGate:
    """
    Evaluates the shadow paper-trading ledger against pre-registered criteria.
    """

    def __init__(self, shadow_store: Optional[ShadowTradingStore] = None):
        self.store = shadow_store or get_shadow_trading_store()
        self.thresholds = PreRegisteredThresholds()

    def evaluate_shadow_confirmation(self) -> ShadowComparisonReport:
        """Generate a comparison report for human review."""
        now_ts = datetime.now(timezone.utc).isoformat()
        metrics = self.store.get_summary_metrics(asset="BTC/USD")

        n_resolved = metrics["resolved_trades_count"]
        days_active = metrics["days_active"]
        live_ev = metrics["ev_r"]
        live_wr = metrics["win_rate_pct"]
        live_pf = metrics["profit_factor"]
        live_dd = metrics["max_drawdown_r"]

        drift_report, _ = run_drift_and_degradation_audit("BTC/USD")
        drift_status = drift_report.overall_drift_status

        sample_gate = n_resolved >= self.thresholds.min_sample_size_n
        time_gate = days_active >= self.thresholds.min_calendar_days
        ev_gate = (live_ev >= self.thresholds.ev_acceptable_range[0])
        wr_gate = (
            self.thresholds.wr_acceptable_range[0] <= live_wr <= self.thresholds.wr_acceptable_range[1]
        ) if n_resolved > 0 else False
        drift_gate = (drift_status == self.thresholds.required_drift_status)

        # Determine state
        if not sample_gate or not time_gate:
            verdict = "ACCUMULATING"
            summary = (
                f"Shadow evidence accumulating: {n_resolved}/{self.thresholds.min_sample_size_n} resolved trades, "
                f"{days_active:.1f}/{self.thresholds.min_calendar_days:.1f} days active. "
                "Both sample size and time duration gates must be satisfied prior to formal review."
            )
        elif ev_gate and wr_gate and drift_gate:
            verdict = "PASS"
            summary = (
                f"Shadow validation passed: N={n_resolved} (>=50), Days={days_active:.1f} (>=14), "
                f"EV={live_ev:+.4f}R in [{self.thresholds.ev_acceptable_range[0]}, {self.thresholds.ev_acceptable_range[1]}], "
                f"WR={live_wr:.2f}%, Drift={drift_status}. Ready for human-reviewed gating review."
            )
        else:
            verdict = "FAIL"
            reasons = []
            if not ev_gate:
                reasons.append(f"EV {live_ev:+.4f}R outside acceptable threshold ({self.thresholds.ev_acceptable_range[0]})")
            if not wr_gate:
                reasons.append(f"WR {live_wr:.2f}% outside acceptable range {self.thresholds.wr_acceptable_range}")
            if not drift_gate:
                reasons.append(f"Drift status {drift_status} != {self.thresholds.required_drift_status}")
            summary = f"Shadow validation failed criteria: {'; '.join(reasons)}."

        return ShadowComparisonReport(
            evaluation_timestamp_utc=now_ts,
            asset="BTC/USD",
            sample_size_n=n_resolved,
            calendar_days_elapsed=days_active,
            live_ev_r=live_ev,
            live_win_rate_pct=live_wr,
            live_profit_factor=live_pf,
            live_max_drawdown_r=live_dd,
            drift_status=drift_status,
            sample_gate_passed=sample_gate,
            time_gate_passed=time_gate,
            ev_gate_passed=ev_gate,
            wr_gate_passed=wr_gate,
            drift_gate_passed=drift_gate,
            verdict=verdict,
            verdict_summary=summary,
            pre_registered_thresholds=self.thresholds,
        )


_shadow_comparison_gate_instance: Optional[BTCShadowComparisonGate] = None


def get_btc_shadow_comparison_gate() -> BTCShadowComparisonGate:
    global _shadow_comparison_gate_instance
    if _shadow_comparison_gate_instance is None:
        _shadow_comparison_gate_instance = BTCShadowComparisonGate()
    return _shadow_comparison_gate_instance


class XAUShadowComparisonGate:
    """
    Evaluates the XAU shadow paper-trading ledger against pre-registered holdout criteria.
    """

    def __init__(self, shadow_store: Optional[ShadowTradingStore] = None):
        self.store = shadow_store or get_shadow_trading_store()
        self.thresholds = PreRegisteredThresholds(
            min_sample_size_n=50,
            min_calendar_days=14.0,
            backtest_ev_baseline=0.2450,
            ev_acceptable_range=[0.0444, 0.6500],
            backtest_wr_baseline=51.11,
            wr_acceptable_range=[42.00, 65.00],
            required_drift_status="MEDIUM_DRIFT",
        )

    def evaluate_shadow_confirmation(self) -> ShadowComparisonReport:
        """Generate an XAU comparison report for human review."""
        now_ts = datetime.now(timezone.utc).isoformat()
        metrics = self.store.get_summary_metrics(asset="XAU/USD")

        n_resolved = metrics["resolved_trades_count"]
        days_active = metrics["days_active"]
        live_ev = metrics["ev_r"]
        live_wr = metrics["win_rate_pct"]
        live_pf = metrics["profit_factor"]
        live_dd = metrics["max_drawdown_r"]

        drift_report, _ = run_drift_and_degradation_audit("XAU/USD")
        drift_status = drift_report.overall_drift_status

        sample_gate = n_resolved >= self.thresholds.min_sample_size_n
        time_gate = days_active >= self.thresholds.min_calendar_days
        ev_gate = (live_ev >= self.thresholds.ev_acceptable_range[0])
        wr_gate = (
            self.thresholds.wr_acceptable_range[0] <= live_wr <= self.thresholds.wr_acceptable_range[1]
        ) if n_resolved > 0 else False
        drift_gate = (drift_status in ("LOW_DRIFT", "MEDIUM_DRIFT"))

        if not sample_gate or not time_gate:
            verdict = "ACCUMULATING"
            summary = (
                f"XAU shadow evidence accumulating: {n_resolved}/{self.thresholds.min_sample_size_n} resolved trades, "
                f"{days_active:.1f}/{self.thresholds.min_calendar_days:.1f} days active. "
                "Preserving the N>=50 holdout validation milestone. Both sample and time gates required."
            )
        elif ev_gate and wr_gate and drift_gate:
            verdict = "PASS"
            summary = (
                f"XAU shadow validation passed: N={n_resolved} (>=50), Days={days_active:.1f} (>=14), "
                f"EV={live_ev:+.4f}R in [{self.thresholds.ev_acceptable_range[0]}, {self.thresholds.ev_acceptable_range[1]}], "
                f"WR={live_wr:.2f}%, Drift={drift_status}. Ready for human-reviewed gating review."
            )
        else:
            verdict = "FAIL"
            reasons = []
            if not ev_gate:
                reasons.append(f"EV {live_ev:+.4f}R outside acceptable threshold ({self.thresholds.ev_acceptable_range[0]})")
            if not wr_gate:
                reasons.append(f"WR {live_wr:.2f}% outside acceptable range {self.thresholds.wr_acceptable_range}")
            if not drift_gate:
                reasons.append(f"Drift status {drift_status} != {self.thresholds.required_drift_status}")
            summary = f"XAU shadow validation failed criteria: {'; '.join(reasons)}."

        return ShadowComparisonReport(
            evaluation_timestamp_utc=now_ts,
            asset="XAU/USD",
            sample_size_n=n_resolved,
            calendar_days_elapsed=days_active,
            live_ev_r=live_ev,
            live_win_rate_pct=live_wr,
            live_profit_factor=live_pf,
            live_max_drawdown_r=live_dd,
            drift_status=drift_status,
            sample_gate_passed=sample_gate,
            time_gate_passed=time_gate,
            ev_gate_passed=ev_gate,
            wr_gate_passed=wr_gate,
            drift_gate_passed=drift_gate,
            verdict=verdict,
            verdict_summary=summary,
            pre_registered_thresholds=self.thresholds,
        )


_xau_shadow_comparison_gate_instance: Optional[XAUShadowComparisonGate] = None


def get_xau_shadow_comparison_gate() -> XAUShadowComparisonGate:
    global _xau_shadow_comparison_gate_instance
    if _xau_shadow_comparison_gate_instance is None:
        _xau_shadow_comparison_gate_instance = XAUShadowComparisonGate()
    return _xau_shadow_comparison_gate_instance
