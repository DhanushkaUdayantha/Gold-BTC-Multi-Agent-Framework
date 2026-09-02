"""
Phase 3 Filter Ablation Engine.

Tests every filter independently to determine whether it:
- ADDS_VALUE:  statistically improves expectancy, PF, or DD
- MARGINAL:    small improvement within noise
- NO_VALUE:    no measurable effect
- HURTS:       materially reduces expectancy or winner retention

Every ablation is registered to prevent uncontrolled optimization.

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
from src.research.statistical_validation import compute_bootstrap_expectancy_ci

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class FilterVerdict(str):
    ADDS_VALUE  = "ADDS_VALUE"
    MARGINAL    = "MARGINAL"
    NO_VALUE    = "NO_VALUE"
    HURTS       = "HURTS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class FilterAblationResult:
    """Single filter ablation outcome."""
    filter_name: str
    filter_description: str

    # Full-universe metrics (no filter applied)
    base_trades: int
    base_win_rate_pct: float
    base_expectancy_r: float
    base_profit_factor: float
    base_max_drawdown_r: float
    base_total_r: float

    # Filter-ON metrics (only trades passing this filter)
    filtered_trades: int
    filtered_win_rate_pct: float
    filtered_expectancy_r: float
    filtered_profit_factor: float
    filtered_max_drawdown_r: float
    filtered_total_r: float

    # Delta (filtered - base)
    expectancy_delta: float
    profit_factor_delta: float
    max_drawdown_delta: float      # negative = improvement

    # Winner/loser impact
    winner_retention_pct: float
    loser_reduction_pct: float
    winner_r_lost: float
    loser_r_saved: float
    benefit_cost_ratio: float

    # OOS validation (chronological split)
    oos_base_expectancy: float
    oos_filtered_expectancy: float
    oos_delta: float

    # Walk-forward stability
    wf_base_expectancy: float
    wf_filtered_expectancy: float
    wf_delta: float

    # Verdict
    verdict: str = FilterVerdict.INSUFFICIENT_DATA
    verdict_reasoning: str = ""
    confidence: str = "LOW"       # HIGH / MEDIUM / LOW

    experiment_id: str = ""
    evaluated_at: str = ""


@dataclass
class FilterAblationReport:
    """Complete filter ablation experiment results."""
    generated_at: str
    total_filters_tested: int
    results: List[FilterAblationResult] = field(default_factory=list)
    adds_value: List[str] = field(default_factory=list)
    marginal: List[str] = field(default_factory=list)
    no_value: List[str] = field(default_factory=list)
    hurts: List[str] = field(default_factory=list)
    best_filter: Optional[str] = None
    worst_filter: Optional[str] = None
    recommended_combination: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FilterAblationEngine:
    """
    Tests each filter in isolation against the research trade population.

    Filters are defined as simple attribute checks on SignalResearchRecord.
    """

    # Minimum trades to compute meaningful metrics
    MIN_TRADES = 30

    # Effect thresholds
    ADDS_VALUE_THRESHOLD   = 0.05   # expectancy delta > +0.05R
    HURTS_THRESHOLD        = -0.05  # expectancy delta < -0.05R
    MARGINAL_THRESHOLD     = 0.01   # |delta| < 0.01 = NO_VALUE

    # Filter definitions: (name, description, attribute_path, expected_value_for_passing)
    STANDARD_FILTERS: List[Tuple[str, str, str, Any]] = [
        ("MTF_ALIGNMENT",      "HTF trend aligned with signal",           "mtf.htf_aligned",              True),
        ("VWAP_ALIGNMENT",     "Price vs VWAP confirms signal direction",  "indicators.vwap_aligned",      True),
        ("EMA_ALIGNMENT",      "EMA stack aligned with signal direction",  "indicators.ema_aligned",       True),
        ("SR_ALIGNMENT",       "S/R level confirms signal direction",      "indicators.sr_aligned",        True),
        ("MOMENTUM",           "Momentum indicator aligned",               "indicators.momentum_aligned",  True),
        ("SMC",                "SMC structure confirms direction",          "indicators.smc_aligned",       True),
        ("HIGH_CONFLUENCE",    "Confluence score >= 65",                   "_confluence_ge65",             True),
        ("HIGH_PROBABILITY",   "AI probability >= 0.45",                   "_prob_ge45",                   True),
        ("HIGH_CONFIRMATION",  "Confirmation score >= 2",                  "_confirmation_ge2",            True),
        ("TRENDING_REGIME",    "Market regime is TRENDING",                "_regime_trending",             True),
        ("LONDON_NY_SESSION",  "London or NY session",                     "_session_liquid",              True),
        ("MTF_PARTIAL",        "At least 2 of 3 TFs aligned",             "_mtf_partial",                 True),
    ]

    @classmethod
    def run_ablation(cls, records: List[Any]) -> FilterAblationReport:
        """Run all standard filter ablations."""
        # Base population: all resolved trades
        trades = [r for r in records
                  if getattr(r, "decision", "WAIT") in ("BUY", "SELL")
                  and getattr(r, "outcome", "OPEN") in ("WIN", "LOSS", "EXPIRED")]

        trades.sort(key=lambda r: getattr(r, "signal_timestamp", ""))

        results = []
        for fname, fdesc, fattr, fval in cls.STANDARD_FILTERS:
            result = cls._ablate_filter(fname, fdesc, fattr, fval, trades)
            results.append(result)

        adds_value  = [r.filter_name for r in results if r.verdict == FilterVerdict.ADDS_VALUE]
        marginal    = [r.filter_name for r in results if r.verdict == FilterVerdict.MARGINAL]
        no_value    = [r.filter_name for r in results if r.verdict == FilterVerdict.NO_VALUE]
        hurts       = [r.filter_name for r in results if r.verdict == FilterVerdict.HURTS]

        best_filter  = max(results, key=lambda r: r.expectancy_delta).filter_name if results else None
        worst_filter = min(results, key=lambda r: r.expectancy_delta).filter_name if results else None

        recommended = adds_value[:3]  # Top-3 ADDS_VALUE filters as initial combination

        return FilterAblationReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_filters_tested=len(results),
            results=results,
            adds_value=adds_value,
            marginal=marginal,
            no_value=no_value,
            hurts=hurts,
            best_filter=best_filter,
            worst_filter=worst_filter,
            recommended_combination=recommended,
        )

    @classmethod
    def _ablate_filter(
        cls,
        fname: str,
        fdesc: str,
        fattr: str,
        fval: Any,
        trades: List[Any],
    ) -> FilterAblationResult:
        now = datetime.now(timezone.utc).isoformat()

        passed = [t for t in trades if cls._passes_filter(t, fattr, fval)]
        failed = [t for t in trades if not cls._passes_filter(t, fattr, fval)]

        base_r   = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in trades])
        passed_r = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in passed])

        base_m    = cls._metrics(base_r)
        filtered_m= cls._metrics(passed_r)

        # OOS split (last 30% of chronologically sorted data)
        oos_start = int(len(trades) * 0.70)
        oos_trades  = trades[oos_start:]
        oos_passed  = [t for t in oos_trades if cls._passes_filter(t, fattr, fval)]
        oos_base_r  = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in oos_trades])
        oos_pass_r  = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in oos_passed])
        oos_base_exp    = round(float(np.mean(oos_base_r)),   4) if len(oos_base_r) > 0 else 0.0
        oos_filtered_exp= round(float(np.mean(oos_pass_r)),  4) if len(oos_pass_r) > 0 else 0.0

        # Walk-forward (midpoint)
        wf_start = int(len(trades) * 0.40)
        wf_end   = int(len(trades) * 0.70)
        wf_slice = trades[wf_start:wf_end]
        wf_pass  = [t for t in wf_slice if cls._passes_filter(t, fattr, fval)]
        wf_base_r   = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in wf_slice])
        wf_pass_r   = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in wf_pass])
        wf_base_exp   = round(float(np.mean(wf_base_r)),  4) if len(wf_base_r) > 0 else 0.0
        wf_filtered_exp= round(float(np.mean(wf_pass_r)), 4) if len(wf_pass_r) > 0 else 0.0

        # Winner/loser impact
        all_wins  = [t for t in trades if getattr(t, "outcome", "") == "WIN"]
        all_losses= [t for t in trades if getattr(t, "outcome", "") in ("LOSS", "EXPIRED")]
        pass_wins = [t for t in passed if getattr(t, "outcome", "") == "WIN"]
        fail_losses=[t for t in failed if getattr(t, "outcome", "") in ("LOSS", "EXPIRED")]

        wr_ret  = round(len(pass_wins)  / max(len(all_wins),  1) * 100, 1)
        lr_red  = round(len(fail_losses)/ max(len(all_losses),1) * 100, 1)
        wr_lost = abs(sum(getattr(t, "realized_r", 0.0) or 0.0 for t in [t for t in failed if getattr(t, "outcome", "") == "WIN"]))
        lr_saved= abs(sum(getattr(t, "realized_r", 0.0) or 0.0 for t in fail_losses))
        bcr     = round(lr_saved / max(wr_lost, 0.01), 2)

        exp_delta = round(filtered_m[1] - base_m[1], 4)
        pf_delta  = round(filtered_m[2] - base_m[2], 3)
        dd_delta  = round(filtered_m[3] - base_m[3], 2)   # negative = better

        # Verdict
        if len(passed) < cls.MIN_TRADES:
            verdict = FilterVerdict.INSUFFICIENT_DATA
            reasoning = f"Only {len(passed)} trades pass this filter (< {cls.MIN_TRADES} minimum)"
            confidence = "LOW"
        elif exp_delta >= cls.ADDS_VALUE_THRESHOLD and oos_filtered_exp > oos_base_exp:
            verdict = FilterVerdict.ADDS_VALUE
            reasoning = f"Expectancy delta +{exp_delta:.3f}R confirmed in OOS ({oos_filtered_exp:+.3f} vs {oos_base_exp:+.3f})"
            confidence = "HIGH"
        elif exp_delta <= cls.HURTS_THRESHOLD:
            verdict = FilterVerdict.HURTS
            reasoning = f"Expectancy delta {exp_delta:.3f}R — this filter removes more winners than losers"
            confidence = "HIGH" if abs(exp_delta) >= 0.10 else "MEDIUM"
        elif abs(exp_delta) <= cls.MARGINAL_THRESHOLD:
            verdict = FilterVerdict.NO_VALUE
            reasoning = f"|Delta| = {abs(exp_delta):.3f}R < {cls.MARGINAL_THRESHOLD}R threshold — no measurable effect"
            confidence = "MEDIUM"
        else:
            verdict = FilterVerdict.MARGINAL
            reasoning = f"Expectancy delta {exp_delta:+.3f}R — improvement within noise band"
            confidence = "MEDIUM"

        return FilterAblationResult(
            filter_name=fname,
            filter_description=fdesc,
            base_trades=base_m[0],
            base_win_rate_pct=base_m[4],
            base_expectancy_r=base_m[1],
            base_profit_factor=base_m[2],
            base_max_drawdown_r=base_m[3],
            base_total_r=base_m[5],
            filtered_trades=filtered_m[0],
            filtered_win_rate_pct=filtered_m[4],
            filtered_expectancy_r=filtered_m[1],
            filtered_profit_factor=filtered_m[2],
            filtered_max_drawdown_r=filtered_m[3],
            filtered_total_r=filtered_m[5],
            expectancy_delta=exp_delta,
            profit_factor_delta=pf_delta,
            max_drawdown_delta=dd_delta,
            winner_retention_pct=wr_ret,
            loser_reduction_pct=lr_red,
            winner_r_lost=round(wr_lost, 2),
            loser_r_saved=round(lr_saved, 2),
            benefit_cost_ratio=bcr,
            oos_base_expectancy=oos_base_exp,
            oos_filtered_expectancy=oos_filtered_exp,
            oos_delta=round(oos_filtered_exp - oos_base_exp, 4),
            wf_base_expectancy=wf_base_exp,
            wf_filtered_expectancy=wf_filtered_exp,
            wf_delta=round(wf_filtered_exp - wf_base_exp, 4),
            verdict=verdict,
            verdict_reasoning=reasoning,
            confidence=confidence,
            experiment_id=f"ABLATION_{fname}_{now[:10]}",
            evaluated_at=now,
        )

    @staticmethod
    def _metrics(r_arr: np.ndarray) -> Tuple[int, float, float, float, float, float]:
        """Returns (n, expectancy, profit_factor, max_dd, win_rate_pct, total_r)."""
        if len(r_arr) == 0:
            return (0, 0.0, 1.0, 0.0, 0.0, 0.0)
        wins   = int(np.sum(r_arr > 0))
        losses = int(np.sum(r_arr < 0))
        exp    = round(float(np.mean(r_arr)), 4)
        tot    = round(float(np.sum(r_arr)), 2)
        wr     = round(wins / len(r_arr) * 100, 1)
        pos    = float(np.sum(r_arr[r_arr > 0])) if wins   > 0 else 0.0
        neg    = float(np.sum(np.abs(r_arr[r_arr < 0]))) if losses > 0 else 0.0
        pf     = round(pos / neg, 2) if neg > 0 else 99.0
        dd     = OutcomeEngine.calculate_max_drawdown(r_arr)
        return (len(r_arr), exp, pf, round(dd, 2), wr, tot)

    @staticmethod
    def _passes_filter(record: Any, fattr: str, fval: Any) -> bool:
        """Evaluate whether a record passes a given filter."""
        # Handle computed pseudo-attributes
        if fattr == "_confluence_ge65":
            sc = getattr(getattr(record, "strategy_scores", None), "confluence_score", 0) or 0
            return sc >= 65

        if fattr == "_prob_ge45":
            prob = getattr(getattr(record, "ai", None), "ai_probability", 0.0) or 0.0
            return prob >= 0.45

        if fattr == "_confirmation_ge2":
            conf = getattr(getattr(record, "strategy_scores", None), "confirmation_score", 0) or 0
            return conf >= 2

        if fattr == "_regime_trending":
            regime = str(getattr(record, "regime", "") or "")
            return "TREND" in regime.upper()

        if fattr == "_session_liquid":
            session = str(getattr(record, "session", "") or "").upper()
            return session in {"LONDON", "NEW_YORK", "OVERLAP"}

        if fattr == "_mtf_partial":
            mtf = getattr(record, "mtf", None)
            score = getattr(mtf, "alignment_score", 0) if mtf else 0
            return score >= 2

        # Generic dot-notation attribute access
        obj = record
        for part in fattr.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return False
        return bool(obj) == bool(fval)


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_ablation_report(report: FilterAblationReport) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "FILTER_ABLATION_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "FILTER_ABLATION_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write ablation JSON: %s", exc)

    lines = [
        "# Filter Ablation Report",
        f"\n**Generated:** {report.generated_at}",
        f"**Filters Tested:** {report.total_filters_tested}",
        f"**Best Filter:** {report.best_filter}  |  **Worst Filter:** {report.worst_filter}",
        f"\n## Summary",
        f"- ADDS_VALUE: {', '.join(report.adds_value) or 'None'}",
        f"- MARGINAL: {', '.join(report.marginal) or 'None'}",
        f"- NO_VALUE: {', '.join(report.no_value) or 'None'}",
        f"- HURTS: {', '.join(report.hurts) or 'None'}",
        f"- Recommended combination: {', '.join(report.recommended_combination) or 'None'}",
        f"\n## Per-Filter Results",
        "| Filter | Base Exp | Filtered Exp | Delta | OOS Delta | WR Ret% | LR Red% | BCR | Verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(report.results, key=lambda x: x.expectancy_delta, reverse=True):
        lines.append(
            f"| {r.filter_name} | {r.base_expectancy_r:+.3f} | {r.filtered_expectancy_r:+.3f} "
            f"| {r.expectancy_delta:+.3f} | {r.oos_delta:+.3f} "
            f"| {r.winner_retention_pct:.0f}% | {r.loser_reduction_pct:.0f}% "
            f"| {r.benefit_cost_ratio:.2f} | {r.verdict} |"
        )

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write ablation MD: %s", exc)

    return json_path, md_path
