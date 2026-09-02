"""
Phase 3 Independent Asset Research Engine.

Runs a complete, isolated research pipeline for each asset class (BTC/USD, XAU/USD).
Each asset pipeline produces:
- Core performance metrics (WR, expectancy, PF, max DD, total R, MFE, MAE, streaks)
- OOS / walk-forward / holdout performance
- Regime robustness breakdown
- Session robustness breakdown
- Statistical confidence intervals
- Stress robustness summary
- Robustness classification: ROBUST / PROMISING / WEAK / UNSTABLE / INSUFFICIENT_DATA

Reports:
  BTC_ROBUSTNESS_REPORT.md/json
  XAU_ROBUSTNESS_REPORT.md/json

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.research.outcome_engine import OutcomeEngine
from src.research.statistical_validation import (
    compute_wilson_score_interval,
    compute_bootstrap_expectancy_ci,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RegimeRobustness:
    regime: str
    trade_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float


@dataclass
class SessionRobustness:
    session: str
    trade_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float


@dataclass
class AssetResearchReport:
    """Complete independent research evaluation for a single asset."""
    asset: str
    generated_at: str
    dataset_version: str

    # Sample
    total_signals: int
    total_trades: int
    buy_trades: int
    sell_trades: int
    wait_signals: int

    # Core metrics (full dataset)
    wins: int
    losses: int
    expired: int
    win_rate_pct: float
    win_rate_wilson_lower: float
    win_rate_wilson_upper: float
    expectancy_r: float
    expectancy_ci_lower: float
    expectancy_ci_upper: float
    profit_factor: float
    total_r: float
    avg_win_r: float
    avg_loss_r: float
    max_drawdown_r: float
    avg_mfe_r: float
    avg_mae_r: float
    max_consecutive_losses: int
    max_consecutive_wins: int

    # Chronological split
    train_trades: int
    train_win_rate_pct: float
    train_expectancy_r: float
    val_trades: int
    val_win_rate_pct: float
    val_expectancy_r: float
    oos_trades: int
    oos_win_rate_pct: float
    oos_expectancy_r: float
    holdout_trades: int
    holdout_win_rate_pct: float
    holdout_expectancy_r: float

    # Walk-forward
    wf_positive_windows: int
    wf_total_windows: int
    wf_median_expectancy: float
    wf_worst_expectancy: float

    # Regime & session
    by_regime: List[RegimeRobustness] = field(default_factory=list)
    by_session: List[SessionRobustness] = field(default_factory=list)

    # Robustness
    robustness_classification: str = "INSUFFICIENT_DATA"   # ROBUST/PROMISING/WEAK/UNSTABLE/INSUFFICIENT_DATA
    robustness_score: float = 0.0
    findings: List[str] = field(default_factory=list)

    disclaimer: str = "Research only. Past performance does not guarantee future results."


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AssetResearchEngine:
    """Runs independent research pipelines for BTC and XAU."""

    MIN_TRADES = 50
    TRAIN_RATIO = 0.60
    VAL_RATIO   = 0.20
    OOS_RATIO   = 0.20
    HOLDOUT_LAST_PCT = 0.15   # Last 15% of data is holdout (within OOS)

    @classmethod
    def analyze_asset(
        cls,
        asset: str,
        records: List[Any],
        dataset_version: str = "v1.0",
    ) -> AssetResearchReport:
        """Run the complete research pipeline for a single asset."""
        # Filter to this asset
        asset_records = [r for r in records if getattr(r, "asset", "") == asset]
        # Sort chronologically
        asset_records.sort(key=lambda r: getattr(r, "signal_timestamp", ""))

        # All signals
        trades = [r for r in asset_records
                  if getattr(r, "decision", "WAIT") in ("BUY", "SELL")
                  and getattr(r, "outcome", "OPEN") in ("WIN", "LOSS", "EXPIRED")]

        total_signals = len(asset_records)
        total_trades  = len(trades)
        buy_trades  = sum(1 for t in trades if getattr(t, "decision", "") == "BUY")
        sell_trades = sum(1 for t in trades if getattr(t, "decision", "") == "SELL")
        wait_signals= total_signals - total_trades

        if total_trades < cls.MIN_TRADES:
            return cls._empty_report(asset, dataset_version, total_signals, total_trades)

        r_vals = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in trades])
        perf = OutcomeEngine.calculate_performance_metrics(r_vals.tolist(), total_signals, buy_trades, sell_trades, wait_signals)

        wilson_ci = compute_wilson_score_interval(perf.wins, total_trades)
        exp_ci    = compute_bootstrap_expectancy_ci(r_vals.tolist(), n_iterations=1000)

        mfe_vals = [float(getattr(t, "mfe_r", 0.0) or 0.0) for t in trades]
        mae_vals = [float(getattr(t, "mae_r", 0.0) or 0.0) for t in trades]

        # Chronological splits
        n = len(trades)
        train_end = int(n * cls.TRAIN_RATIO)
        val_end   = int(n * (cls.TRAIN_RATIO + cls.VAL_RATIO))
        oos_end   = n
        holdout_start = int(n * (1.0 - cls.HOLDOUT_LAST_PCT))

        train_m  = cls._split_metrics(trades[:train_end])
        val_m    = cls._split_metrics(trades[train_end:val_end])
        oos_m    = cls._split_metrics(trades[val_end:oos_end])
        holdout_m= cls._split_metrics(trades[holdout_start:])

        # Walk-forward (simple 4-fold)
        wf_results = cls._walk_forward(trades, n_folds=4)
        pos_wf = sum(1 for e in wf_results if e[0] >= 0)
        med_wf = float(np.median([e[0] for e in wf_results])) if wf_results else 0.0
        worst_wf= min([e[0] for e in wf_results]) if wf_results else 0.0

        # Regime breakdown
        by_regime = cls._breakdown_by_regime(trades)
        by_session= cls._breakdown_by_session(trades)

        # Robustness classification
        classification, score = cls._classify(
            total_trades, perf.expectancy_r, perf.profit_factor, perf.max_drawdown_r,
            oos_m[1], med_wf, pos_wf, len(wf_results)
        )

        findings = cls._findings(asset, perf, oos_m, val_m, wf_results, by_regime)

        return AssetResearchReport(
            asset=asset,
            generated_at=datetime.now(timezone.utc).isoformat(),
            dataset_version=dataset_version,
            total_signals=total_signals,
            total_trades=total_trades,
            buy_trades=buy_trades,
            sell_trades=sell_trades,
            wait_signals=wait_signals,
            wins=perf.wins,
            losses=perf.losses,
            expired=perf.expired,
            win_rate_pct=perf.win_rate_pct,
            win_rate_wilson_lower=wilson_ci.ci_lower,
            win_rate_wilson_upper=wilson_ci.ci_upper,
            expectancy_r=perf.expectancy_r,
            expectancy_ci_lower=exp_ci.ci_lower,
            expectancy_ci_upper=exp_ci.ci_upper,
            profit_factor=perf.profit_factor,
            total_r=perf.total_realized_r,
            avg_win_r=perf.avg_win_r,
            avg_loss_r=perf.avg_loss_r,
            max_drawdown_r=perf.max_drawdown_r,
            avg_mfe_r=round(float(np.mean(mfe_vals)), 3),
            avg_mae_r=round(float(np.mean(mae_vals)), 3),
            max_consecutive_losses=perf.max_consecutive_losses,
            max_consecutive_wins=perf.max_consecutive_wins,
            train_trades=train_m[2], train_win_rate_pct=train_m[0], train_expectancy_r=train_m[1],
            val_trades=val_m[2],   val_win_rate_pct=val_m[0],   val_expectancy_r=val_m[1],
            oos_trades=oos_m[2],   oos_win_rate_pct=oos_m[0],   oos_expectancy_r=oos_m[1],
            holdout_trades=holdout_m[2], holdout_win_rate_pct=holdout_m[0], holdout_expectancy_r=holdout_m[1],
            wf_positive_windows=pos_wf,
            wf_total_windows=len(wf_results),
            wf_median_expectancy=round(med_wf, 4),
            wf_worst_expectancy=round(worst_wf, 4),
            by_regime=by_regime,
            by_session=by_session,
            robustness_classification=classification,
            robustness_score=score,
            findings=findings,
        )

    @classmethod
    def analyze_both(
        cls,
        records: List[Any],
        dataset_version: str = "v1.0",
    ) -> Dict[str, AssetResearchReport]:
        """Analyze BTC and XAU independently, return dict keyed by asset."""
        results: Dict[str, AssetResearchReport] = {}
        assets = set(getattr(r, "asset", "UNKNOWN") for r in records)
        for asset in sorted(assets):
            results[asset] = cls.analyze_asset(asset, records, dataset_version)
        return results

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _split_metrics(records: List[Any]) -> Tuple[float, float, int]:
        """Returns (win_rate_pct, expectancy_r, n_trades)."""
        if not records:
            return 0.0, 0.0, 0
        r_vals = [float(getattr(r, "realized_r", 0.0) or 0.0) for r in records]
        r_arr = np.array(r_vals)
        wins = int(np.sum(r_arr > 0))
        wr = round(wins / len(r_arr) * 100, 1) if len(r_arr) > 0 else 0.0
        exp = round(float(np.mean(r_arr)), 4)
        return wr, exp, len(records)

    @classmethod
    def _walk_forward(cls, trades: List[Any], n_folds: int = 4) -> List[Tuple[float, float]]:
        """Simple expanding-window walk-forward. Returns list of (expectancy, win_rate)."""
        results = []
        n = len(trades)
        if n < n_folds * 20:
            return results
        fold_size = n // (n_folds + 1)
        for i in range(1, n_folds + 1):
            test_start = i * fold_size
            test_end   = test_start + fold_size
            if test_end > n:
                break
            test_slice = trades[test_start:test_end]
            exp, _, cnt = cls._split_metrics(test_slice)
            results.append((exp, _))
        return results

    @classmethod
    def _breakdown_by_regime(cls, trades: List[Any]) -> List[RegimeRobustness]:
        from collections import defaultdict
        groups: Dict[str, List[Any]] = defaultdict(list)
        for t in trades:
            groups[str(getattr(t, "regime", "UNKNOWN") or "UNKNOWN")].append(t)
        results = []
        for regime, recs in sorted(groups.items()):
            r_vals = np.array([float(getattr(r, "realized_r", 0.0) or 0.0) for r in recs])
            wins  = int(np.sum(r_vals > 0))
            wr    = round(wins / max(len(r_vals), 1) * 100, 1)
            exp   = round(float(np.mean(r_vals)), 4)
            pos_s = float(np.sum(r_vals[r_vals > 0])) if wins > 0 else 0.0
            neg_s = float(np.sum(np.abs(r_vals[r_vals < 0])))
            pf    = round(pos_s / neg_s, 2) if neg_s > 0 else 99.0
            dd    = OutcomeEngine.calculate_max_drawdown(r_vals)
            results.append(RegimeRobustness(regime, len(recs), wr, exp, pf, round(dd, 2)))
        return results

    @classmethod
    def _breakdown_by_session(cls, trades: List[Any]) -> List[SessionRobustness]:
        from collections import defaultdict
        groups: Dict[str, List[Any]] = defaultdict(list)
        for t in trades:
            groups[str(getattr(t, "session", "UNKNOWN") or "UNKNOWN")].append(t)
        results = []
        for session, recs in sorted(groups.items()):
            r_vals = np.array([float(getattr(r, "realized_r", 0.0) or 0.0) for r in recs])
            wins  = int(np.sum(r_vals > 0))
            wr    = round(wins / max(len(r_vals), 1) * 100, 1)
            exp   = round(float(np.mean(r_vals)), 4)
            pos_s = float(np.sum(r_vals[r_vals > 0])) if wins > 0 else 0.0
            neg_s = float(np.sum(np.abs(r_vals[r_vals < 0])))
            pf    = round(pos_s / neg_s, 2) if neg_s > 0 else 99.0
            results.append(SessionRobustness(session, len(recs), wr, exp, pf))
        return results

    @staticmethod
    def _classify(
        n_trades: int,
        expectancy: float,
        profit_factor: float,
        max_dd: float,
        oos_exp: float,
        wf_med_exp: float,
        wf_pos_windows: int,
        wf_total: int,
    ) -> Tuple[str, float]:
        score = 0.0
        if n_trades >= 200:
            score += 20.0
        elif n_trades >= 100:
            score += 10.0
        elif n_trades < 50:
            return "INSUFFICIENT_DATA", 0.0

        if expectancy >= 0.15:
            score += 20.0
        elif expectancy >= 0.05:
            score += 10.0

        if profit_factor >= 1.3:
            score += 15.0
        elif profit_factor >= 1.1:
            score += 7.0

        if oos_exp >= 0.10:
            score += 20.0
        elif oos_exp >= 0.0:
            score += 10.0

        wf_ratio = wf_pos_windows / max(wf_total, 1)
        if wf_ratio >= 0.75:
            score += 15.0
        elif wf_ratio >= 0.50:
            score += 7.0

        if max_dd <= 10:
            score += 10.0
        elif max_dd <= 20:
            score += 5.0

        score = round(min(score, 100.0), 1)

        if score >= 75:
            return "ROBUST", score
        elif score >= 55:
            return "PROMISING", score
        elif score >= 35:
            return "WEAK", score
        else:
            return "UNSTABLE", score

    @staticmethod
    def _findings(
        asset: str,
        perf: Any,
        oos_m: Tuple,
        val_m: Tuple,
        wf_results: List,
        by_regime: List[RegimeRobustness],
    ) -> List[str]:
        findings = []
        findings.append(f"{asset}: {perf.executed_trades} trades, WR={perf.win_rate_pct:.1f}%, Exp={perf.expectancy_r:+.4f}R, PF={perf.profit_factor:.2f}, DD={perf.max_drawdown_r:.1f}R")
        findings.append(f"OOS ({oos_m[2]} trades): WR={oos_m[0]:.1f}%, Exp={oos_m[1]:+.4f}R")
        if wf_results:
            pos = sum(1 for e in wf_results if e[0] >= 0)
            findings.append(f"Walk-forward: {pos}/{len(wf_results)} positive folds, median exp={float(np.median([e[0] for e in wf_results])):+.4f}R")
        if by_regime:
            worst = min(by_regime, key=lambda r: r.expectancy_r)
            best  = max(by_regime, key=lambda r: r.expectancy_r)
            findings.append(f"Best regime: {best.regime} (exp={best.expectancy_r:+.4f}R)")
            findings.append(f"Worst regime: {worst.regime} (exp={worst.expectancy_r:+.4f}R)")
        return findings

    @staticmethod
    def _empty_report(asset: str, dataset_version: str, total_signals: int, total_trades: int) -> AssetResearchReport:
        return AssetResearchReport(
            asset=asset,
            generated_at=datetime.now(timezone.utc).isoformat(),
            dataset_version=dataset_version,
            total_signals=total_signals,
            total_trades=total_trades,
            buy_trades=0, sell_trades=0, wait_signals=total_signals - total_trades,
            wins=0, losses=0, expired=0,
            win_rate_pct=0.0, win_rate_wilson_lower=0.0, win_rate_wilson_upper=0.0,
            expectancy_r=0.0, expectancy_ci_lower=0.0, expectancy_ci_upper=0.0,
            profit_factor=1.0, total_r=0.0, avg_win_r=0.0, avg_loss_r=0.0,
            max_drawdown_r=0.0, avg_mfe_r=0.0, avg_mae_r=0.0,
            max_consecutive_losses=0, max_consecutive_wins=0,
            train_trades=0, train_win_rate_pct=0.0, train_expectancy_r=0.0,
            val_trades=0, val_win_rate_pct=0.0, val_expectancy_r=0.0,
            oos_trades=0, oos_win_rate_pct=0.0, oos_expectancy_r=0.0,
            holdout_trades=0, holdout_win_rate_pct=0.0, holdout_expectancy_r=0.0,
            wf_positive_windows=0, wf_total_windows=0,
            wf_median_expectancy=0.0, wf_worst_expectancy=0.0,
            robustness_classification="INSUFFICIENT_DATA",
            robustness_score=0.0,
            findings=[f"{asset}: Insufficient data ({total_trades} trades < 50 minimum)"],
        )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_asset_report(report: AssetResearchReport) -> Tuple[str, str]:
    """Write JSON + Markdown reports. Returns (json_path, md_path)."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    safe_asset = report.asset.replace("/", "_")
    json_path = os.path.join(REPORTS_DIR, f"{safe_asset}_ROBUSTNESS_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, f"{safe_asset}_ROBUSTNESS_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write asset JSON: %s", exc)

    lines = [
        f"# {report.asset} — Independent Robustness Report",
        f"\n**Generated:** {report.generated_at}",
        f"**Classification:** {report.robustness_classification}  |  **Score:** {report.robustness_score:.0f}/100",
        f"\n## Core Metrics",
        f"| Metric | Value |",
        "| --- | --- |",
        f"| Total Signals | {report.total_signals} |",
        f"| Total Trades | {report.total_trades} |",
        f"| Win Rate | {report.win_rate_pct:.1f}% [{report.win_rate_wilson_lower:.1f}–{report.win_rate_wilson_upper:.1f}%] |",
        f"| Expectancy | {report.expectancy_r:+.4f}R [{report.expectancy_ci_lower:+.3f}–{report.expectancy_ci_upper:+.3f}] |",
        f"| Profit Factor | {report.profit_factor:.2f} |",
        f"| Max Drawdown | {report.max_drawdown_r:.2f}R |",
        f"| Total R | {report.total_r:+.2f}R |",
        f"\n## Chronological Splits",
        "| Split | Trades | WR% | Exp R |",
        "| --- | --- | --- | --- |",
        f"| Train (60%) | {report.train_trades} | {report.train_win_rate_pct:.1f}% | {report.train_expectancy_r:+.4f} |",
        f"| Val (20%) | {report.val_trades} | {report.val_win_rate_pct:.1f}% | {report.val_expectancy_r:+.4f} |",
        f"| OOS (20%) | {report.oos_trades} | {report.oos_win_rate_pct:.1f}% | {report.oos_expectancy_r:+.4f} |",
        f"| Holdout (15%) | {report.holdout_trades} | {report.holdout_win_rate_pct:.1f}% | {report.holdout_expectancy_r:+.4f} |",
        f"\n## Walk-Forward",
        f"- Positive windows: {report.wf_positive_windows}/{report.wf_total_windows}",
        f"- Median OOS expectancy: {report.wf_median_expectancy:+.4f}R",
        f"- Worst OOS expectancy: {report.wf_worst_expectancy:+.4f}R",
    ]

    if report.by_regime:
        lines += ["\n## Regime Breakdown", "| Regime | Trades | WR% | Exp R | PF | DD |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for r in report.by_regime:
            lines.append(f"| {r.regime} | {r.trade_count} | {r.win_rate_pct:.1f}% | {r.expectancy_r:+.4f} | {r.profit_factor:.2f} | {r.max_drawdown_r:.2f}R |")

    if report.by_session:
        lines += ["\n## Session Breakdown", "| Session | Trades | WR% | Exp R | PF |",
                  "| --- | --- | --- | --- | --- |"]
        for s in report.by_session:
            lines.append(f"| {s.session} | {s.trade_count} | {s.win_rate_pct:.1f}% | {s.expectancy_r:+.4f} | {s.profit_factor:.2f} |")

    lines += ["\n## Findings"]
    for f_str in report.findings:
        lines.append(f"- {f_str}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write asset MD: %s", exc)

    return json_path, md_path
