"""
Phase 3 Drawdown Root-Cause Analyzer.

Decomposes the research portfolio's maximum drawdown into its constituent
causes: asset, direction, regime, session, day-of-week, hour, AI probability
bucket, and MTF alignment state.

Also detects whether losses are independent or clustered (autocorrelation,
consecutive loss analysis, rolling loss concentration).

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.research.outcome_engine import OutcomeEngine

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DrawdownEpisode:
    """A contiguous period of cumulative drawdown."""
    episode_id: int
    start_index: int
    end_index: int
    start_timestamp: str
    end_timestamp: str
    peak_r: float
    trough_r: float
    drawdown_r: float
    duration_bars: int
    assets_involved: List[str] = field(default_factory=list)
    regimes_involved: List[str] = field(default_factory=list)
    sessions_involved: List[str] = field(default_factory=list)
    directions_involved: List[str] = field(default_factory=list)
    loss_count: int = 0
    win_count: int = 0


@dataclass
class DimensionBreakdown:
    """Performance stats for a single dimension slice."""
    dimension_name: str    # e.g. "asset", "regime"
    slice_value: str       # e.g. "BTC/USD", "TRENDING"
    trade_count: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    total_r: float
    max_drawdown_r: float
    dd_contribution_pct: float = 0.0   # % share of total portfolio DD


@dataclass
class ClusteringAnalysis:
    """Statistical analysis of loss clustering."""
    autocorrelation_lag1: float        # Lag-1 autocorrelation of signed R series
    is_autocorrelated: bool            # |lag1| > 0.15
    max_consecutive_losses: int
    avg_consecutive_losses: float
    rolling_50_negative_pct: float     # % of rolling-50 windows with negative expectancy
    loss_concentration_score: float    # 0-1 (1 = highly clustered)
    interpretation: str


@dataclass
class DrawdownRootCauseReport:
    """Complete drawdown decomposition report."""
    generated_at: str
    total_trades: int
    total_r: float
    overall_max_drawdown_r: float
    overall_expectancy_r: float

    # Top drawdown episode
    largest_episode: Optional[DrawdownEpisode]

    # Dimensional breakdowns
    by_asset: List[DimensionBreakdown]
    by_direction: List[DimensionBreakdown]
    by_regime: List[DimensionBreakdown]
    by_session: List[DimensionBreakdown]
    by_day_of_week: List[DimensionBreakdown]
    by_hour_bucket: List[DimensionBreakdown]
    by_probability_bucket: List[DimensionBreakdown]
    by_mtf_alignment: List[DimensionBreakdown]

    # All episodes
    all_episodes: List[DrawdownEpisode]

    # Clustering
    clustering: ClusteringAnalysis

    # Top findings
    primary_dd_source: str
    secondary_dd_source: str
    findings: List[str]
    recommendations: List[str]


# ---------------------------------------------------------------------------
# Decomposer
# ---------------------------------------------------------------------------

class DrawdownDecomposer:
    """Decomposes portfolio drawdown into root-cause dimensions."""

    @classmethod
    def decompose(cls, records: List[Any]) -> DrawdownRootCauseReport:
        """
        Full drawdown root-cause analysis.

        ``records`` — list of SignalResearchRecord (or duck-typed objects) that
        are actual trades (is_trade=True and outcome is WIN/LOSS/EXPIRED).
        """
        trades = [r for r in records
                  if (getattr(r, "is_trade", False) or getattr(r, "decision", "") in ("BUY", "SELL"))
                  and getattr(r, "outcome", "OPEN") in ("WIN", "LOSS", "EXPIRED")]

        if not trades:
            return cls._empty_report()

        # Sort chronologically
        trades.sort(key=lambda r: getattr(r, "signal_timestamp", ""))

        r_vals = [float(getattr(r, "realized_r", 0.0) or 0.0) for r in trades]
        r_arr  = np.array(r_vals)

        total_r       = round(float(np.sum(r_arr)), 2)
        overall_exp   = round(float(np.mean(r_arr)), 4)
        overall_dd    = OutcomeEngine.calculate_max_drawdown(r_arr)
        episodes      = cls._find_episodes(trades, r_arr)
        largest_ep    = max(episodes, key=lambda e: e.drawdown_r) if episodes else None

        # Dimensional breakdowns
        by_asset   = cls._breakdown_by("asset",    trades, r_arr, overall_dd)
        by_dir     = cls._breakdown_by("decision", trades, r_arr, overall_dd)
        by_regime  = cls._breakdown_by("regime",   trades, r_arr, overall_dd)
        by_session = cls._breakdown_by("session",  trades, r_arr, overall_dd)
        by_dow     = cls._breakdown_by("day_of_week", trades, r_arr, overall_dd)
        by_hour    = cls._breakdown_by_hour(trades, r_arr, overall_dd)
        by_prob    = cls._breakdown_by_probability(trades, r_arr, overall_dd)
        by_mtf     = cls._breakdown_by_mtf(trades, r_arr, overall_dd)

        clustering = cls._cluster_analysis(r_arr)

        # Top findings
        findings, recommendations = cls._generate_findings(
            by_asset, by_dir, by_regime, by_session, clustering, largest_ep, overall_dd
        )

        primary = max(by_asset + by_regime, key=lambda b: b.max_drawdown_r).slice_value if (by_asset or by_regime) else "UNKNOWN"
        secondary = max(by_session + by_dir, key=lambda b: b.max_drawdown_r).slice_value if (by_session or by_dir) else "UNKNOWN"

        return DrawdownRootCauseReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_trades=len(trades),
            total_r=total_r,
            overall_max_drawdown_r=overall_dd,
            overall_expectancy_r=overall_exp,
            largest_episode=largest_ep,
            by_asset=by_asset,
            by_direction=by_dir,
            by_regime=by_regime,
            by_session=by_session,
            by_day_of_week=by_dow,
            by_hour_bucket=by_hour,
            by_probability_bucket=by_prob,
            by_mtf_alignment=by_mtf,
            all_episodes=episodes,
            clustering=clustering,
            primary_dd_source=primary,
            secondary_dd_source=secondary,
            findings=findings,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _slice_metrics(
        r_slice: np.ndarray,
        name: str,
        value: str,
        overall_dd: float,
    ) -> DimensionBreakdown:
        if len(r_slice) == 0:
            return DimensionBreakdown(name, value, 0, 0, 0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

        wins  = int(np.sum(r_slice > 0))
        losses= int(np.sum(r_slice < 0))
        wr    = round(wins / len(r_slice) * 100, 1)
        exp_r = round(float(np.mean(r_slice)), 4)
        tot_r = round(float(np.sum(r_slice)), 2)

        pos_sum = float(np.sum(r_slice[r_slice > 0])) if wins > 0 else 0.0
        neg_sum = float(np.sum(np.abs(r_slice[r_slice < 0]))) if losses > 0 else 0.0
        pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else (99.0 if pos_sum > 0 else 1.0)

        dd = OutcomeEngine.calculate_max_drawdown(r_slice)
        dd_contrib = round(dd / max(overall_dd, 0.01) * 100, 1)

        return DimensionBreakdown(
            dimension_name=name,
            slice_value=value,
            trade_count=len(r_slice),
            win_count=wins,
            loss_count=losses,
            win_rate_pct=wr,
            expectancy_r=exp_r,
            profit_factor=pf,
            total_r=tot_r,
            max_drawdown_r=round(dd, 2),
            dd_contribution_pct=dd_contrib,
        )

    @classmethod
    def _breakdown_by(
        cls,
        attr: str,
        trades: List[Any],
        r_arr: np.ndarray,
        overall_dd: float,
    ) -> List[DimensionBreakdown]:
        groups: Dict[str, List[int]] = defaultdict(list)
        for i, t in enumerate(trades):
            key = str(getattr(t, attr, "UNKNOWN") or "UNKNOWN")
            groups[key].append(i)

        results = []
        for val, indices in sorted(groups.items()):
            r_sl = r_arr[indices]
            results.append(cls._slice_metrics(r_sl, attr, val, overall_dd))
        return results

    @classmethod
    def _breakdown_by_hour(cls, trades: List[Any], r_arr: np.ndarray, overall_dd: float) -> List[DimensionBreakdown]:
        groups: Dict[str, List[int]] = defaultdict(list)
        for i, t in enumerate(trades):
            hour = getattr(t, "hour_utc", 0) or 0
            bucket = f"{(hour // 4) * 4:02d}-{(hour // 4) * 4 + 4:02d}"
            groups[bucket].append(i)
        results = []
        for val, indices in sorted(groups.items()):
            results.append(cls._slice_metrics(r_arr[indices], "hour_bucket", val, overall_dd))
        return results

    @classmethod
    def _breakdown_by_probability(cls, trades: List[Any], r_arr: np.ndarray, overall_dd: float) -> List[DimensionBreakdown]:
        groups: Dict[str, List[int]] = defaultdict(list)
        for i, t in enumerate(trades):
            ai = getattr(t, "ai", None)
            prob = float(getattr(ai, "ai_probability", 0.0) or 0.0)
            bucket_floor = int(prob * 10) * 10
            bucket = f"{bucket_floor}-{bucket_floor + 10}%"
            groups[bucket].append(i)
        results = []
        for val, indices in sorted(groups.items()):
            results.append(cls._slice_metrics(r_arr[indices], "probability_bucket", val, overall_dd))
        return results

    @classmethod
    def _breakdown_by_mtf(cls, trades: List[Any], r_arr: np.ndarray, overall_dd: float) -> List[DimensionBreakdown]:
        groups: Dict[str, List[int]] = defaultdict(list)
        for i, t in enumerate(trades):
            mtf = getattr(t, "mtf", None)
            score = getattr(mtf, "alignment_score", 0) if mtf else 0
            if score == 0:
                key = "CONFLICTING"
            elif score == 1:
                key = "WEAK_ALIGNMENT"
            elif score == 2:
                key = "PARTIAL_ALIGNMENT"
            else:
                key = "FULLY_ALIGNED"
            groups[key].append(i)
        results = []
        for val, indices in sorted(groups.items()):
            results.append(cls._slice_metrics(r_arr[indices], "mtf_alignment", val, overall_dd))
        return results

    @staticmethod
    def _find_episodes(trades: List[Any], r_arr: np.ndarray) -> List[DrawdownEpisode]:
        """Identify all drawdown episodes (peak-to-trough sequences)."""
        episodes: List[DrawdownEpisode] = []
        if len(r_arr) == 0:
            return episodes

        cum = np.cumsum(r_arr)
        peak = 0.0
        peak_idx = 0
        in_dd = False
        ep_start = 0
        ep_id = 0

        for i, val in enumerate(cum):
            if val > peak:
                if in_dd:
                    # Episode ended
                    ts_start = str(getattr(trades[ep_start], "signal_timestamp", ""))
                    ts_end   = str(getattr(trades[i - 1], "signal_timestamp", ""))
                    dd_r     = round(peak - min(cum[ep_start:i]), 2)
                    involved_trades = trades[ep_start:i]

                    episodes.append(DrawdownEpisode(
                        episode_id=ep_id,
                        start_index=ep_start,
                        end_index=i - 1,
                        start_timestamp=ts_start,
                        end_timestamp=ts_end,
                        peak_r=round(peak, 2),
                        trough_r=round(float(min(cum[ep_start:i])), 2),
                        drawdown_r=dd_r,
                        duration_bars=i - ep_start,
                        assets_involved=list(set(str(getattr(t, "asset", "?")) for t in involved_trades)),
                        regimes_involved=list(set(str(getattr(t, "regime", "?")) for t in involved_trades)),
                        sessions_involved=list(set(str(getattr(t, "session", "?")) for t in involved_trades)),
                        directions_involved=list(set(str(getattr(t, "decision", "?")) for t in involved_trades)),
                        loss_count=int(np.sum(r_arr[ep_start:i] < 0)),
                        win_count=int(np.sum(r_arr[ep_start:i] > 0)),
                    ))
                    ep_id += 1
                    in_dd = False
                peak = float(val)
                peak_idx = i
            else:
                if not in_dd:
                    in_dd = True
                    ep_start = i

        if in_dd and len(r_arr) > ep_start:
            ts_start = str(getattr(trades[ep_start], "signal_timestamp", ""))
            ts_end   = str(getattr(trades[-1], "signal_timestamp", ""))
            dd_r     = round(peak - min(cum[ep_start:]), 2)
            involved_trades = trades[ep_start:]

            episodes.append(DrawdownEpisode(
                episode_id=ep_id,
                start_index=ep_start,
                end_index=len(r_arr) - 1,
                start_timestamp=ts_start,
                end_timestamp=ts_end,
                peak_r=round(peak, 2),
                trough_r=round(float(min(cum[ep_start:])), 2),
                drawdown_r=dd_r,
                duration_bars=len(r_arr) - ep_start,
                assets_involved=list(set(str(getattr(t, "asset", "?")) for t in involved_trades)),
                regimes_involved=list(set(str(getattr(t, "regime", "?")) for t in involved_trades)),
                sessions_involved=list(set(str(getattr(t, "session", "?")) for t in involved_trades)),
                directions_involved=list(set(str(getattr(t, "decision", "?")) for t in involved_trades)),
                loss_count=int(np.sum(r_arr[ep_start:] < 0)),
                win_count=int(np.sum(r_arr[ep_start:] > 0)),
            ))

        return episodes

    @staticmethod
    def _cluster_analysis(r_arr: np.ndarray) -> ClusteringAnalysis:
        if len(r_arr) < 10:
            return ClusteringAnalysis(0.0, False, 0, 0.0, 0.0, 0.0, "INSUFFICIENT_DATA")

        # Lag-1 autocorrelation
        if np.std(r_arr) > 0:
            lag1 = float(np.corrcoef(r_arr[:-1], r_arr[1:])[0, 1])
        else:
            lag1 = 0.0

        is_auto = abs(lag1) > 0.15

        # Max consecutive losses
        losses_binary = (r_arr < 0).astype(int)
        max_consec = 0
        curr = 0
        consec_runs = []
        for v in losses_binary:
            if v:
                curr += 1
                max_consec = max(max_consec, curr)
            else:
                if curr > 0:
                    consec_runs.append(curr)
                curr = 0
        if curr > 0:
            consec_runs.append(curr)
        avg_consec = float(np.mean(consec_runs)) if consec_runs else 0.0

        # Rolling-50 negative windows
        window = min(50, len(r_arr))
        negative_windows = 0
        total_windows = max(len(r_arr) - window + 1, 1)
        for i in range(total_windows):
            if np.mean(r_arr[i:i + window]) < 0:
                negative_windows += 1
        rolling_neg_pct = round(negative_windows / total_windows * 100, 1)

        # Concentration score
        conc = min(1.0, abs(lag1) * 2 + (max_consec / max(len(r_arr), 1)))
        conc = round(conc, 3)

        if is_auto:
            interp = f"Losses appear CLUSTERED (lag1={lag1:.3f}). Not random. May indicate regime-driven streaks."
        else:
            interp = f"Losses appear INDEPENDENT (lag1={lag1:.3f}). Consistent with random sampling from a distribution."

        return ClusteringAnalysis(
            autocorrelation_lag1=round(lag1, 3),
            is_autocorrelated=is_auto,
            max_consecutive_losses=max_consec,
            avg_consecutive_losses=round(avg_consec, 1),
            rolling_50_negative_pct=rolling_neg_pct,
            loss_concentration_score=conc,
            interpretation=interp,
        )

    @staticmethod
    def _generate_findings(
        by_asset: List[DimensionBreakdown],
        by_dir: List[DimensionBreakdown],
        by_regime: List[DimensionBreakdown],
        by_session: List[DimensionBreakdown],
        clustering: ClusteringAnalysis,
        largest_ep: Optional[DrawdownEpisode],
        overall_dd: float,
    ) -> Tuple[List[str], List[str]]:
        findings = []
        recommendations = []

        # Asset contribution
        if by_asset:
            worst_asset = max(by_asset, key=lambda b: b.max_drawdown_r)
            findings.append(
                f"Largest per-asset DD: {worst_asset.slice_value} "
                f"({worst_asset.max_drawdown_r:.1f}R, {worst_asset.dd_contribution_pct:.0f}% of total)"
            )

        # Regime contribution
        if by_regime:
            worst_regime = max(by_regime, key=lambda b: b.max_drawdown_r)
            findings.append(
                f"Worst regime for DD: {worst_regime.slice_value} "
                f"({worst_regime.max_drawdown_r:.1f}R DD, {worst_regime.win_rate_pct:.1f}% WR)"
            )
            if worst_regime.win_rate_pct < 35:
                recommendations.append(
                    f"Consider filtering signals in {worst_regime.slice_value} regime "
                    f"(WR={worst_regime.win_rate_pct:.1f}% is materially below base)"
                )

        # Session
        if by_session:
            worst_session = max(by_session, key=lambda b: b.max_drawdown_r)
            findings.append(
                f"Worst session for DD: {worst_session.slice_value} "
                f"({worst_session.max_drawdown_r:.1f}R DD)"
            )

        # Direction
        if by_dir:
            worst_dir = max(by_dir, key=lambda b: b.max_drawdown_r)
            findings.append(
                f"Worst direction for DD: {worst_dir.slice_value} "
                f"({worst_dir.max_drawdown_r:.1f}R DD)"
            )

        # Clustering
        if clustering.is_autocorrelated:
            findings.append(
                f"Losses are CLUSTERED (lag1={clustering.autocorrelation_lag1:.3f}). "
                f"Max consecutive losses: {clustering.max_consecutive_losses}."
            )
            recommendations.append(
                "Clustered losses may benefit from a cooling-off rule after N consecutive losses."
            )
        else:
            findings.append(
                f"Losses appear INDEPENDENT (lag1={clustering.autocorrelation_lag1:.3f}). "
                f"DD is likely inherent to the strategy's win rate distribution."
            )

        # Largest episode
        if largest_ep:
            findings.append(
                f"Largest single DD episode: {largest_ep.drawdown_r:.1f}R "
                f"({largest_ep.duration_bars} bars, {largest_ep.start_timestamp[:10]} → "
                f"{largest_ep.end_timestamp[:10]})"
            )

        return findings, recommendations

    @staticmethod
    def _empty_report() -> DrawdownRootCauseReport:
        return DrawdownRootCauseReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_trades=0,
            total_r=0.0,
            overall_max_drawdown_r=0.0,
            overall_expectancy_r=0.0,
            largest_episode=None,
            by_asset=[], by_direction=[], by_regime=[], by_session=[],
            by_day_of_week=[], by_hour_bucket=[], by_probability_bucket=[],
            by_mtf_alignment=[], all_episodes=[],
            clustering=ClusteringAnalysis(0.0, False, 0, 0.0, 0.0, 0.0, "NO_DATA"),
            primary_dd_source="UNKNOWN",
            secondary_dd_source="UNKNOWN",
            findings=["No resolved trades available for analysis"],
            recommendations=[],
        )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_drawdown_report(report: DrawdownRootCauseReport) -> Tuple[str, str]:
    """Write JSON + Markdown reports. Returns (json_path, md_path)."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "DRAWDOWN_ROOT_CAUSE_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "DRAWDOWN_ROOT_CAUSE_REPORT.md")

    # JSON
    def to_serialisable(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: to_serialisable(v) for k, v in asdict(obj).items()} if False else asdict(obj)
        return obj

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write drawdown JSON: %s", exc)

    # Markdown
    lines = [
        "# Drawdown Root-Cause Report",
        f"\n**Generated:** {report.generated_at}",
        f"\n**Total Trades:** {report.total_trades}  |  "
        f"**Total R:** {report.total_r:+.2f}  |  "
        f"**Max DD:** {report.overall_max_drawdown_r:.2f}R  |  "
        f"**Expectancy:** {report.overall_expectancy_r:+.4f}R",
        "\n## Key Findings",
    ]
    for f_str in report.findings:
        lines.append(f"- {f_str}")

    if report.largest_episode:
        ep = report.largest_episode
        lines += [
            "\n## Largest DD Episode",
            f"- **Size:** {ep.drawdown_r:.2f}R",
            f"- **Period:** {ep.start_timestamp[:10]} → {ep.end_timestamp[:10]}",
            f"- **Duration:** {ep.duration_bars} bars",
            f"- **Assets:** {', '.join(ep.assets_involved)}",
            f"- **Regimes:** {', '.join(ep.regimes_involved)}",
        ]

    def dim_table(title: str, rows: List[DimensionBreakdown]) -> List[str]:
        out = [f"\n## {title}", "| Slice | Trades | WR% | Exp R | PF | Max DD | DD% |",
               "|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda x: x.max_drawdown_r, reverse=True):
            out.append(
                f"| {r.slice_value} | {r.trade_count} | {r.win_rate_pct:.1f}% "
                f"| {r.expectancy_r:+.3f} | {r.profit_factor:.2f} "
                f"| {r.max_drawdown_r:.2f}R | {r.dd_contribution_pct:.0f}% |"
            )
        return out

    lines += dim_table("By Asset", report.by_asset)
    lines += dim_table("By Direction", report.by_direction)
    lines += dim_table("By Regime", report.by_regime)
    lines += dim_table("By Session", report.by_session)

    lines += [
        "\n## Loss Clustering",
        f"- **Lag-1 Autocorrelation:** {report.clustering.autocorrelation_lag1:.3f}",
        f"- **Clustered:** {report.clustering.is_autocorrelated}",
        f"- **Max Consecutive Losses:** {report.clustering.max_consecutive_losses}",
        f"- **Interpretation:** {report.clustering.interpretation}",
        "\n## Recommendations",
    ]
    for r_str in report.recommendations:
        lines.append(f"- {r_str}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write drawdown MD: %s", exc)

    return json_path, md_path
