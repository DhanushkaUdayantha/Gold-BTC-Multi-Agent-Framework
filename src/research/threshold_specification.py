"""
Master Research Threshold Specification & Calculation Engine.

Mathematical definitions, metadata, unrounded boundary checks, and machine-auditable
traceability for every research and governance threshold.

Version: 1.0 (Frozen)
DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

RESEARCH_POLICY_VERSION = "1.0"
THRESHOLD_SPEC_VERSION = "1.0"
EPSILON = 1e-9

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ThresholdDefinition:
    """Explicit mathematical and governance definition of a research threshold."""
    threshold_name: str
    threshold_value: float
    preferred_value: Optional[float]
    unit: str
    input_variables: List[str]
    calculation_method: str
    denominator: str
    measurement_window: str
    minimum_sample: int
    boundary_operator: str   # ">=", "<=", ">", "<", "=="
    pass_condition: str
    fail_condition: str
    insufficient_data_behavior: str
    policy_version: str = RESEARCH_POLICY_VERSION
    spec_version: str = THRESHOLD_SPEC_VERSION


@dataclass
class ThresholdEvaluationResult:
    """Machine-auditable record of a single threshold comparison."""
    threshold_name: str
    observed_value: Optional[float]
    threshold_value: float
    boundary_operator: str
    passed: bool
    status: str          # PASS / FAIL / INSUFFICIENT_DATA / NOT_EVALUATED
    sample_size: int
    minimum_sample_required: int
    policy_version: str
    calculation_method: str
    detail: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Authoritative Threshold Registry Catalog
# ---------------------------------------------------------------------------

DEFINED_THRESHOLDS: Dict[str, ThresholdDefinition] = {
    "MINIMUM_RESEARCH_SAMPLE": ThresholdDefinition(
        threshold_name="MINIMUM_RESEARCH_SAMPLE",
        threshold_value=500.0,
        preferred_value=750.0,
        unit="trades",
        input_variables=["valid_resolved_trades"],
        calculation_method="count(BUY/SELL trades with valid entry, SL, TP and resolved outcome)",
        denominator="All valid resolved trades (WAIT/INVALID excluded)",
        measurement_window="Full evaluation cohort",
        minimum_sample=500,
        boundary_operator=">=",
        pass_condition="N >= 500",
        fail_condition="N < 500",
        insufficient_data_behavior="Automatic INSUFFICIENT_SAMPLE status",
    ),
    "EXPECTANCY_MINIMUM": ThresholdDefinition(
        threshold_name="EXPECTANCY_MINIMUM",
        threshold_value=0.15,
        preferred_value=0.20,
        unit="R",
        input_variables=["realized_r_series"],
        calculation_method="sum(realized_R) / N",
        denominator="N = valid resolved trades",
        measurement_window="Full evaluation cohort",
        minimum_sample=500,
        boundary_operator=">=",
        pass_condition="Expectancy >= +0.15R and 95% Bootstrap CI evaluated",
        fail_condition="Expectancy < +0.15R",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "PROFIT_FACTOR_MINIMUM": ThresholdDefinition(
        threshold_name="PROFIT_FACTOR_MINIMUM",
        threshold_value=1.20,
        preferred_value=1.30,
        unit="ratio",
        input_variables=["positive_realized_r", "negative_realized_r"],
        calculation_method="sum(realized_R > 0) / abs(sum(realized_R < 0))",
        denominator="Total gross loss R (if 0, marked NO-LOSS-SAMPLE)",
        measurement_window="Full evaluation cohort",
        minimum_sample=500,
        boundary_operator=">=",
        pass_condition="PF >= 1.20",
        fail_condition="PF < 1.20",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "TOTAL_R_MINIMUM": ThresholdDefinition(
        threshold_name="TOTAL_R_MINIMUM",
        threshold_value=0.0,
        preferred_value=50.0,
        unit="R",
        input_variables=["cumulative_realized_r"],
        calculation_method="sum(realized_R_1 ... realized_R_t)",
        denominator="Full trade sequence",
        measurement_window="Full evaluation cohort",
        minimum_sample=100,
        boundary_operator=">",
        pass_condition="Total R > 0",
        fail_condition="Total R <= 0",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "MAX_DRAWDOWN_BENCHMARK_RATIO": ThresholdDefinition(
        threshold_name="MAX_DRAWDOWN_BENCHMARK_RATIO",
        threshold_value=1.25,
        preferred_value=1.00,
        unit="multiplier",
        input_variables=["observed_max_dd_r", "benchmark_max_dd_r"],
        calculation_method="observed_max_dd_r / benchmark_max_dd_r",
        denominator="Validated historical benchmark drawdown",
        measurement_window="Full chronological equity curve",
        minimum_sample=500,
        boundary_operator="<=",
        pass_condition="ObservedDD <= 1.25 * BenchmarkDD",
        fail_condition="ObservedDD > 1.25 * BenchmarkDD",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "DRAWDOWN_CONCENTRATION_THRESHOLD": ThresholdDefinition(
        threshold_name="DRAWDOWN_CONCENTRATION_THRESHOLD",
        threshold_value=0.50,
        preferred_value=0.35,
        unit="ratio",
        input_variables=["category_drawdown_r", "total_max_drawdown_r"],
        calculation_method="category_drawdown_r / total_max_drawdown_r",
        denominator="Total portfolio maximum drawdown in R",
        measurement_window="Drawdown episodes",
        minimum_sample=30,
        boundary_operator="<",
        pass_condition="Category contribution < 50%",
        fail_condition="Category contribution >= 50% (triggers concentration warning)",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "ROLLING_NEGATIVE_RATIO_MAX": ThresholdDefinition(
        threshold_name="ROLLING_NEGATIVE_RATIO_MAX",
        threshold_value=0.10,
        preferred_value=0.05,
        unit="ratio",
        input_variables=["rolling_50_expectancies"],
        calculation_method="count(rolling_50_exp < 0) / count(valid_50_windows)",
        denominator="All valid 50-trade sliding windows",
        measurement_window="50-trade rolling windows",
        minimum_sample=200,
        boundary_operator="<=",
        pass_condition="NegativeWindowRatio <= 10%",
        fail_condition="NegativeWindowRatio > 10%",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "WALK_FORWARD_POSITIVE_RATIO": ThresholdDefinition(
        threshold_name="WALK_FORWARD_POSITIVE_RATIO",
        threshold_value=0.75,
        preferred_value=0.80,
        unit="ratio",
        input_variables=["oos_fold_expectancies"],
        calculation_method="count(oos_fold_exp > 0) / count(total_oos_folds)",
        denominator="Total chronological OOS folds",
        measurement_window="Chronological walk-forward folds",
        minimum_sample=4,
        boundary_operator=">=",
        pass_condition="WFPositiveRatio >= 75%",
        fail_condition="WFPositiveRatio < 75%",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "OOS_EXPECTANCY_MINIMUM": ThresholdDefinition(
        threshold_name="OOS_EXPECTANCY_MINIMUM",
        threshold_value=0.0,
        preferred_value=0.10,
        unit="R",
        input_variables=["oos_realized_r_series"],
        calculation_method="sum(oos_realized_r) / N_oos",
        denominator="Out-of-sample trade count",
        measurement_window="20% chronological out-of-sample window",
        minimum_sample=100,
        boundary_operator=">",
        pass_condition="OOS Expectancy > 0.0R",
        fail_condition="OOS Expectancy <= 0.0R",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "HOLDOUT_EXPECTANCY_MINIMUM": ThresholdDefinition(
        threshold_name="HOLDOUT_EXPECTANCY_MINIMUM",
        threshold_value=0.0,
        preferred_value=0.05,
        unit="R",
        input_variables=["holdout_realized_r_series"],
        calculation_method="sum(holdout_realized_r) / N_holdout",
        denominator="Untouched holdout trade count",
        measurement_window="15-20% untouched final chronological holdout",
        minimum_sample=50,
        boundary_operator=">",
        pass_condition="Holdout Expectancy > 0.0R",
        fail_condition="Holdout Expectancy <= 0.0R",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "HOLDOUT_PF_MINIMUM": ThresholdDefinition(
        threshold_name="HOLDOUT_PF_MINIMUM",
        threshold_value=1.10,
        preferred_value=1.20,
        unit="ratio",
        input_variables=["holdout_gross_profit_r", "holdout_gross_loss_r"],
        calculation_method="holdout_gross_profit_r / holdout_gross_loss_r",
        denominator="Holdout gross loss R",
        measurement_window="Untouched final holdout",
        minimum_sample=50,
        boundary_operator=">=",
        pass_condition="Holdout PF >= 1.10",
        fail_condition="Holdout PF < 1.10",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "WINNER_RETENTION_MINIMUM": ThresholdDefinition(
        threshold_name="WINNER_RETENTION_MINIMUM",
        threshold_value=0.40,
        preferred_value=0.60,
        unit="ratio",
        input_variables=["retained_winning_trades", "all_base_winning_trades"],
        calculation_method="retained_winning_trades / all_base_winning_trades",
        denominator="Total base winning trades",
        measurement_window="Evaluation cohort",
        minimum_sample=100,
        boundary_operator=">=",
        pass_condition="Winner retention >= 40%",
        fail_condition="Winner retention < 40%",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "LOSER_REDUCTION_MINIMUM": ThresholdDefinition(
        threshold_name="LOSER_REDUCTION_MINIMUM",
        threshold_value=0.50,
        preferred_value=0.65,
        unit="ratio",
        input_variables=["removed_losing_trades", "all_base_losing_trades"],
        calculation_method="removed_losing_trades / all_base_losing_trades",
        denominator="Total base losing trades",
        measurement_window="Evaluation cohort",
        minimum_sample=100,
        boundary_operator=">=",
        pass_condition="Loser reduction >= 50%",
        fail_condition="Loser reduction < 50%",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "CALIBRATION_ECE_MAX": ThresholdDefinition(
        threshold_name="CALIBRATION_ECE_MAX",
        threshold_value=0.10,
        preferred_value=0.05,
        unit="error_rate",
        input_variables=["bucket_probabilities", "bucket_empirical_rates", "bucket_counts"],
        calculation_method="sum(N_bucket / N_total * abs(pred_prob - emp_rate))",
        denominator="Total resolved probabilistic signals",
        measurement_window="Calibration evaluation sample",
        minimum_sample=100,
        boundary_operator="<=",
        pass_condition="ECE <= 0.10 (Preferred <= 0.05)",
        fail_condition="ECE > 0.10",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "CALIBRATION_BRIER_MAX": ThresholdDefinition(
        threshold_name="CALIBRATION_BRIER_MAX",
        threshold_value=0.25,
        preferred_value=0.20,
        unit="score",
        input_variables=["predicted_probabilities", "binary_outcomes"],
        calculation_method="mean((pred_prob - actual_outcome)^2)",
        denominator="Total resolved probabilistic signals",
        measurement_window="Evaluation sample",
        minimum_sample=100,
        boundary_operator="<=",
        pass_condition="Brier <= 0.25 (Below no-skill benchmark)",
        fail_condition="Brier > 0.25 (Worse than random coin flip)",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
    "REGIME_SAMPLE_MINIMUM": ThresholdDefinition(
        threshold_name="REGIME_SAMPLE_MINIMUM",
        threshold_value=100.0,
        preferred_value=200.0,
        unit="trades",
        input_variables=["regime_trade_count"],
        calculation_method="count(trades within market regime)",
        denominator="Trades within specific regime",
        measurement_window="Regime partition",
        minimum_sample=100,
        boundary_operator=">=",
        pass_condition="N_regime >= 100",
        fail_condition="N_regime < 100 -> INSUFFICIENT_SAMPLE",
        insufficient_data_behavior="INSUFFICIENT_SAMPLE",
    ),
    "SESSION_SAMPLE_MINIMUM": ThresholdDefinition(
        threshold_name="SESSION_SAMPLE_MINIMUM",
        threshold_value=100.0,
        preferred_value=200.0,
        unit="trades",
        input_variables=["session_trade_count"],
        calculation_method="count(trades within session)",
        denominator="Trades within specific session",
        measurement_window="Session partition",
        minimum_sample=100,
        boundary_operator=">=",
        pass_condition="N_session >= 100",
        fail_condition="N_session < 100 -> INSUFFICIENT_SAMPLE",
        insufficient_data_behavior="INSUFFICIENT_SAMPLE",
    ),
    "DATA_QUALITY_LOOKAHEAD_VIOLATIONS": ThresholdDefinition(
        threshold_name="DATA_QUALITY_LOOKAHEAD_VIOLATIONS",
        threshold_value=0.0,
        preferred_value=0.0,
        unit="violations",
        input_variables=["lookahead_violations_count"],
        calculation_method="count(temporal sequence, future feature, calibration overlap violations)",
        denominator="All records audited",
        measurement_window="Full historical dataset",
        minimum_sample=1,
        boundary_operator="==",
        pass_condition="Lookahead violations == 0",
        fail_condition="Lookahead violations > 0 (Immediate experiment invalidation)",
        insufficient_data_behavior="FAIL",
    ),
    "STATISTICAL_ALPHA": ThresholdDefinition(
        threshold_name="STATISTICAL_ALPHA",
        threshold_value=0.05,
        preferred_value=0.01,
        unit="significance_level",
        input_variables=["raw_p_value", "bonferroni_corrected_alpha"],
        calculation_method="alpha / N_comparisons for family-wide error control",
        denominator="Number of simultaneously tested hypotheses",
        measurement_window="Experiment hypothesis family",
        minimum_sample=30,
        boundary_operator="<",
        pass_condition="p < corrected_alpha",
        fail_condition="p >= corrected_alpha",
        insufficient_data_behavior="INSUFFICIENT_DATA",
    ),
}


# ---------------------------------------------------------------------------
# Evaluator Engine
# ---------------------------------------------------------------------------

class ThresholdEvaluator:
    """
    Evaluates research metrics mechanically against exact mathematical definitions
    using unrounded comparisons and floating-point tolerance.
    """

    @classmethod
    def evaluate(
        cls,
        threshold_name: str,
        observed_value: Optional[float],
        sample_size: int,
        custom_threshold: Optional[float] = None,
    ) -> ThresholdEvaluationResult:
        defn = DEFINED_THRESHOLDS.get(threshold_name)
        if defn is None:
            return ThresholdEvaluationResult(
                threshold_name=threshold_name,
                observed_value=observed_value,
                threshold_value=custom_threshold or 0.0,
                boundary_operator="unknown",
                passed=False,
                status="NOT_EVALUATED",
                sample_size=sample_size,
                minimum_sample_required=0,
                policy_version=RESEARCH_POLICY_VERSION,
                calculation_method="unknown",
                detail=f"Threshold '{threshold_name}' is not registered in specification.",
            )

        threshold_val = custom_threshold if custom_threshold is not None else defn.threshold_value

        # Check sample size
        if sample_size < defn.minimum_sample:
            return ThresholdEvaluationResult(
                threshold_name=defn.threshold_name,
                observed_value=observed_value,
                threshold_value=threshold_val,
                boundary_operator=defn.boundary_operator,
                passed=False,
                status="INSUFFICIENT_DATA",
                sample_size=sample_size,
                minimum_sample_required=defn.minimum_sample,
                policy_version=defn.policy_version,
                calculation_method=defn.calculation_method,
                detail=f"Sample size {sample_size} < minimum {defn.minimum_sample} required.",
            )

        if observed_value is None:
            return ThresholdEvaluationResult(
                threshold_name=defn.threshold_name,
                observed_value=None,
                threshold_value=threshold_val,
                boundary_operator=defn.boundary_operator,
                passed=False,
                status="INSUFFICIENT_DATA",
                sample_size=sample_size,
                minimum_sample_required=defn.minimum_sample,
                policy_version=defn.policy_version,
                calculation_method=defn.calculation_method,
                detail="Observed value is None.",
            )

        # Unrounded comparison with epsilon
        op = defn.boundary_operator
        passed = False
        if op == ">=":
            passed = observed_value >= (threshold_val - EPSILON)
        elif op == "<=":
            passed = observed_value <= (threshold_val + EPSILON)
        elif op == ">":
            passed = observed_value > (threshold_val + EPSILON)
        elif op == "<":
            passed = observed_value < (threshold_val - EPSILON)
        elif op == "==":
            passed = abs(observed_value - threshold_val) < EPSILON

        status = "PASS" if passed else "FAIL"
        detail = (
            f"Observed {observed_value:.6f} {op} threshold {threshold_val:.6f} {defn.unit} "
            f"(N={sample_size}, method='{defn.calculation_method}')"
        )

        return ThresholdEvaluationResult(
            threshold_name=defn.threshold_name,
            observed_value=observed_value,
            threshold_value=threshold_val,
            boundary_operator=op,
            passed=passed,
            status=status,
            sample_size=sample_size,
            minimum_sample_required=defn.minimum_sample,
            policy_version=defn.policy_version,
            calculation_method=defn.calculation_method,
            detail=detail,
        )

    @classmethod
    def generate_threshold_register_report(cls) -> Tuple[str, str]:
        """
        Generates THRESHOLD_REGISTER.md and THRESHOLD_REGISTER.json
        documenting every registered research threshold.
        """
        os.makedirs(REPORTS_DIR, exist_ok=True)
        json_path = os.path.join(REPORTS_DIR, "THRESHOLD_REGISTER.json")
        md_path   = os.path.join(REPORTS_DIR, "THRESHOLD_REGISTER.md")

        data = {
            "research_policy_version": RESEARCH_POLICY_VERSION,
            "threshold_spec_version": THRESHOLD_SPEC_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_thresholds_defined": len(DEFINED_THRESHOLDS),
            "thresholds": {k: asdict(v) for k, v in DEFINED_THRESHOLDS.items()},
        }

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Could not write threshold register JSON: %s", exc)

        lines = [
            "# Master Research Threshold Register",
            f"\n**Research Policy Version:** `{RESEARCH_POLICY_VERSION}`  |  "
            f"**Threshold Spec Version:** `{THRESHOLD_SPEC_VERSION}`",
            f"**Generated:** {data['generated_at']}",
            f"**Total Thresholds Defined:** {len(DEFINED_THRESHOLDS)}",
            "\n> **NON-NEGOTIABLE RULE:** Every research threshold has an explicit mathematical formula, "
            "input variables, minimum sample size, and unrounded boundary operator. Magic numbers are strictly prohibited.",
            "\n## Threshold Catalog",
            "| Threshold Name | Value | Preferred | Operator | Min N | Unit | Calculation Method |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]

        for k, t in sorted(DEFINED_THRESHOLDS.items()):
            pref_str = f"{t.preferred_value}" if t.preferred_value is not None else "—"
            lines.append(
                f"| `{t.threshold_name}` | {t.threshold_value} | {pref_str} | "
                f"`{t.boundary_operator}` | {t.minimum_sample} | {t.unit} | {t.calculation_method} |"
            )

        lines += ["\n## Detailed Mathematical Definitions"]
        for k, t in sorted(DEFINED_THRESHOLDS.items()):
            lines += [
                f"\n### `{t.threshold_name}`",
                f"- **Threshold Value:** `{t.threshold_value} {t.unit}` (Preferred: `{t.preferred_value}`)",
                f"- **Boundary Operator:** `{t.boundary_operator}` (Pass: `{t.pass_condition}` | Fail: `{t.fail_condition}`)",
                f"- **Calculation Method:** `{t.calculation_method}`",
                f"- **Denominator:** {t.denominator}",
                f"- **Input Variables:** `{', '.join(t.input_variables)}`",
                f"- **Minimum Sample Size:** `{t.minimum_sample}` ({t.insufficient_data_behavior})",
                f"- **Measurement Window:** {t.measurement_window}",
            ]

        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as exc:
            logger.warning("Could not write threshold register MD: %s", exc)

        return json_path, md_path
