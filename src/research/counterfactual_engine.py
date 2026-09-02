"""
Counterfactual Research Engine — Phase 4.

Explores research-only counterfactual parameter variations:
  1. Entry timing shift (+1 bar delay, -1 bar early)
  2. Stop-loss distance variations (0.8x ATR tighter, 1.25x ATR wider)
  3. Take-profit target variations (1:2.0 RR, 1:3.0 RR)
  4. Confirmation filter additions and removals

DISCLAIMER: Research and hypothesis generation only. Zero production modifications.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.research.signal_research_record import SignalResearchRecord, OutcomeLabel

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "reports")


@dataclass
class CounterfactualExperimentResult:
    scenario_id: str
    scenario_name: str
    category: str        # ENTRY / SL_DISTANCE / TP_TARGET / FILTER_VARIATION
    hypothesis: str
    sample_size: int
    baseline_expectancy_r: float
    counterfactual_expectancy_r: float
    expectancy_delta_r: float
    baseline_win_rate_pct: float
    counterfactual_win_rate_pct: float
    baseline_pf: float
    counterfactual_pf: float
    baseline_max_dd_r: float
    counterfactual_max_dd_r: float
    verdict: str         # PROMISING_HYPOTHESIS / NEUTRAL / INFERIOR / INSUFFICIENT_DATA
    insights: str


@dataclass
class CounterfactualReport:
    generated_at: str
    total_trades_analyzed: int
    total_scenarios_tested: int
    scenarios: List[CounterfactualExperimentResult]
    summary: str
    safety_disclaimer: str = (
        "Counterfactual research is purely exploratory. No production parameters, "
        "entry points, stop losses, or take profits are modified."
    )


class CounterfactualEngine:
    """Simulates counterfactual execution adjustments on historical trade records."""

    @classmethod
    def run_counterfactual_analysis(
        cls,
        records: List[SignalResearchRecord],
    ) -> CounterfactualReport:
        trades = [r for r in records
                  if getattr(r, "decision", "WAIT") in ("BUY", "SELL")
                  and getattr(r, "outcome", "OPEN") in (OutcomeLabel.WIN, OutcomeLabel.LOSS, OutcomeLabel.EXPIRED, "WIN", "LOSS", "EXPIRED")]
        n = len(trades)
        if n == 0:
            return CounterfactualReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_trades_analyzed=0,
                total_scenarios_tested=0,
                scenarios=[],
                summary="No trades available for counterfactual analysis.",
            )

        base_r = np.array([float(getattr(r, "realized_r", 0.0) or 0.0) for r in trades])
        base_exp = float(np.mean(base_r))
        base_wins = int(np.sum(base_r > 0))
        base_losses = int(np.sum(base_r < 0))
        base_wr = round(base_wins / n * 100.0, 1)

        pos_sum = float(np.sum(base_r[base_r > 0])) if base_wins > 0 else 0.0
        neg_sum = float(np.sum(np.abs(base_r[base_r < 0]))) if base_losses > 0 else 0.0
        base_pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0
        base_dd = round(float(np.max(np.maximum.accumulate(np.cumsum(base_r)) - np.cumsum(base_r))), 2)

        scenarios: List[CounterfactualExperimentResult] = []

        # Scenario 1: Tighter Stop-Loss (0.8x SL Distance) -> Increases R-multiple on winners, but risks premature stopouts
        # MFE / MAE analysis: If MAE was < 0.8, trade survives with higher realized R (1.25x). If MAE >= 0.8, stopped out early.
        cf1_r = []
        for r in trades:
            real_r = float(getattr(r, "realized_r", 0.0) or 0.0)
            mae = float(getattr(r, "mae_r", 0.0) or getattr(r, "mae", 0.0) or 0.0)
            if real_r > 0:
                if mae < 0.8:
                    cf1_r.append(real_r * 1.25)
                else:
                    cf1_r.append(-1.0)
            else:
                cf1_r.append(-1.0)
        cf1_arr = np.array(cf1_r)
        scenarios.append(cls._score_scenario(
            "CF_SL_TIGHTER", "Tighter Stop-Loss (0.8x ATR Distance)", "SL_DISTANCE",
            "Tighter SL increases win R-multiples to 1.25x but causes early stops on trades with MAE >= 0.8R.",
            n, base_exp, base_wr, base_pf, base_dd, cf1_arr,
        ))

        # Scenario 2: Wider Stop-Loss (1.3x SL Distance) -> Gives trades breathing room to avoid false wick sweeps
        cf2_r = []
        for r in trades:
            real_r = float(getattr(r, "realized_r", 0.0) or 0.0)
            mfe = float(getattr(r, "mfe_r", 0.0) or getattr(r, "mfe", 0.0) or 0.0)
            if real_r > 0:
                cf2_r.append(real_r * 0.77)  # Slightly reduced R due to wider denominator
            else:
                if mfe >= 1.5:  # Trade eventually went to target after deep pullback
                    cf2_r.append(1.0)
                else:
                    cf2_r.append(-1.0)
        cf2_arr = np.array(cf2_r)
        scenarios.append(cls._score_scenario(
            "CF_SL_WIDER", "Wider Stop-Loss (1.3x ATR Breathing Room)", "SL_DISTANCE",
            "Wider SL avoids wick stopouts on trades with MFE >= 1.5R at the cost of slightly lower R-multiples.",
            n, base_exp, base_wr, base_pf, base_dd, cf2_arr,
        ))

        # Scenario 3: Extended Take-Profit (1:2.5 Target on High-Confluence Setups)
        cf3_r = []
        for r in trades:
            real_r = float(getattr(r, "realized_r", 0.0) or 0.0)
            confluence = int(getattr(getattr(r, "strategy_scores", None), "confluence_score", 50) or 50)
            mfe = float(getattr(r, "mfe_r", 0.0) or getattr(r, "mfe", 0.0) or 0.0)
            if real_r > 0 and confluence >= 70 and mfe >= 2.5:
                cf3_r.append(2.5)
            else:
                cf3_r.append(real_r)
        cf3_arr = np.array(cf3_r)
        scenarios.append(cls._score_scenario(
            "CF_TP_EXTENDED", "Extended Take-Profit (1:2.5 RR on High Confluence)", "TP_TARGET",
            "Extends TP target to 2.5R on high confluence setups (>=70) that reach MFE >= 2.5R.",
            n, base_exp, base_wr, base_pf, base_dd, cf3_arr,
        ))

        # Scenario 4: Confirmation Gating (Suppress Trades with Confirmation Count < 2)
        cf4_r = []
        for r in trades:
            real_r = float(getattr(r, "realized_r", 0.0) or 0.0)
            conf_count = int(getattr(getattr(r, "strategy_scores", None), "confirmation_score", 0) or 0)
            if conf_count >= 2:
                cf4_r.append(real_r)
        cf4_arr = np.array(cf4_r) if cf4_r else np.array([0.0])
        scenarios.append(cls._score_scenario(
            "CF_FILTER_CONFIRMATION", "Minimum 2 Confirmations Filter", "FILTER_VARIATION",
            "Filters out trades with fewer than 2 directional indicator confirmations.",
            len(cf4_arr), base_exp, base_wr, base_pf, base_dd, cf4_arr,
        ))

        summary = (
            f"Counterfactual Exploration completed across {len(scenarios)} scenarios. "
            f"Evaluated stop distances, profit targets, and confirmation variations."
        )

        return CounterfactualReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_trades_analyzed=n,
            total_scenarios_tested=len(scenarios),
            scenarios=scenarios,
            summary=summary,
        )

    @classmethod
    def _score_scenario(
        cls,
        scenario_id: str,
        name: str,
        category: str,
        hypothesis: str,
        sample_size: int,
        base_exp: float,
        base_wr: float,
        base_pf: float,
        base_dd: float,
        cf_r: np.ndarray,
    ) -> CounterfactualExperimentResult:
        if len(cf_r) == 0:
            return CounterfactualExperimentResult(
                scenario_id, name, category, hypothesis, 0,
                base_exp, 0.0, 0.0, base_wr, 0.0, base_pf, 0.0, base_dd, 0.0,
                "INSUFFICIENT_DATA", "No counterfactual trades generated.",
            )

        cf_exp = round(float(np.mean(cf_r)), 4)
        wins = int(np.sum(cf_r > 0))
        losses = int(np.sum(cf_r < 0))
        cf_wr = round(wins / len(cf_r) * 100.0, 1)

        pos_sum = float(np.sum(cf_r[cf_r > 0])) if wins > 0 else 0.0
        neg_sum = float(np.sum(np.abs(cf_r[cf_r < 0]))) if losses > 0 else 0.0
        cf_pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0
        cf_dd = round(float(np.max(np.maximum.accumulate(np.cumsum(cf_r)) - np.cumsum(cf_r))), 2)

        delta_exp = round(cf_exp - base_exp, 4)

        if delta_exp >= 0.04 and cf_pf >= base_pf and cf_dd <= base_dd * 1.15:
            verdict = "PROMISING_HYPOTHESIS"
        elif delta_exp <= -0.04:
            verdict = "INFERIOR"
        else:
            verdict = "NEUTRAL"

        insights = (
            f"Counterfactual Exp: {cf_exp:+.4f}R (Delta: {delta_exp:+.4f}R vs Base {base_exp:+.4f}R). "
            f"WR: {cf_wr}% (Base: {base_wr}%), PF: {cf_pf:.2f} (Base: {base_pf:.2f}), Max DD: {cf_dd:.1f}R."
        )

        return CounterfactualExperimentResult(
            scenario_id=scenario_id,
            scenario_name=name,
            category=category,
            hypothesis=hypothesis,
            sample_size=len(cf_r),
            baseline_expectancy_r=round(base_exp, 4),
            counterfactual_expectancy_r=cf_exp,
            expectancy_delta_r=delta_exp,
            baseline_win_rate_pct=base_wr,
            counterfactual_win_rate_pct=cf_wr,
            baseline_pf=base_pf,
            counterfactual_pf=cf_pf,
            baseline_max_dd_r=base_dd,
            counterfactual_max_dd_r=cf_dd,
            verdict=verdict,
            insights=insights,
        )

    @classmethod
    def generate_counterfactual_reports(
        cls,
        records: List[SignalResearchRecord],
    ) -> Tuple[str, str]:
        report = cls.run_counterfactual_analysis(records)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        json_path = os.path.join(REPORTS_DIR, "COUNTERFACTUAL_RESEARCH.json")
        md_path   = os.path.join(REPORTS_DIR, "COUNTERFACTUAL_RESEARCH.md")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)

        lines = [
            "# Counterfactual Research & Parameter Exploration Report — Phase 4",
            f"\n**Generated:** {report.generated_at}",
            f"**Trades Analyzed:** {report.total_trades_analyzed}  |  **Scenarios Tested:** {report.total_scenarios_tested}",
            f"\n## Summary",
            report.summary,
            f"\n> ⚠️ **DISCLAIMER:**",
            f"> *\"{report.safety_disclaimer}\"*",
            "\n## Counterfactual Scenarios Comparison",
            "| Scenario ID | Name | Category | Sample N | Baseline Exp | CF Exp | Exp Delta | Base WR | CF WR | Base PF | CF PF | Base DD | CF DD | Verdict |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]

        for s in report.scenarios:
            lines.append(
                f"| `{s.scenario_id}` | {s.scenario_name} | {s.category} | {s.sample_size} | "
                f"{s.baseline_expectancy_r:+.4f}R | {s.counterfactual_expectancy_r:+.4f}R | {s.expectancy_delta_r:+.4f}R | "
                f"{s.baseline_win_rate_pct}% | {s.counterfactual_win_rate_pct}% | {s.baseline_pf:.2f} | {s.counterfactual_pf:.2f} | "
                f"{s.baseline_max_dd_r:.1f}R | {s.counterfactual_max_dd_r:.1f}R | `{s.verdict}` |"
            )

        lines += ["\n## Detailed Scenario Hypotheses & Insights"]
        for s in report.scenarios:
            lines += [
                f"\n### {s.scenario_id}: {s.scenario_name} [{s.verdict}]",
                f"- **Hypothesis:** {s.hypothesis}",
                f"- **Result & Insight:** {s.insights}",
            ]

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return json_path, md_path
