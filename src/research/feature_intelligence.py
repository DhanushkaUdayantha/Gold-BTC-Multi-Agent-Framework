"""
Feature Intelligence, Interaction & Calibration Quality Engine.

Provides deep historical feature evaluation:
  1. Feature Contribution Analysis (single features vs baseline)
  2. Feature Interaction Analysis (pairs, regimes, MTF, probability combinations)
  3. Probability Quality & Reliability Analysis (bucket monotonicity, Brier, ECE)
  4. Strength Quality Analysis (strength bands monotonicity, win rate, expectancy)

Generates:
  data/reports/FEATURE_CONTRIBUTION_REPORT.md / .json
  data/reports/FEATURE_INTERACTION_REPORT.md / .json
  data/reports/PROBABILITY_QUALITY_REPORT.md / .json
  data/reports/STRENGTH_QUALITY_REPORT.md / .json

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from src.research.outcome_engine import OutcomeEngine
from src.research.statistical_validation import compute_wilson_score_interval
from src.research.signal_research_record import SignalResearchRecord, OutcomeLabel

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "reports")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class FeatureContributionResult:
    feature_name: str
    sample_size: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    total_r: float
    oos_expectancy_r: float
    holdout_expectancy_r: float
    winner_retention_pct: float
    loser_reduction_pct: float
    classification: str  # STRONG POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / STRONGLY NEGATIVE / INSUFFICIENT DATA
    detail: str


@dataclass
class FeatureInteractionResult:
    interaction_name: str
    feature_a: str
    feature_b: str
    sample_size: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    oos_expectancy_r: float
    holdout_expectancy_r: float
    classification: str  # ROBUST INTERACTION / PROMISING INTERACTION / UNSTABLE INTERACTION / NO VALUE / HARMFUL
    detail: str


@dataclass
class ProbabilityBucketEvaluation:
    bucket_label: str
    min_prob: float
    max_prob: float
    sample_size: int
    win_count: int
    loss_count: int
    observed_win_rate_pct: float
    expected_win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    calibration_error: float
    ci_lower: float
    ci_upper: float


@dataclass
class ProbabilityQualityReport:
    generated_at: str
    total_trades: int
    brier_score: float
    ece: float
    mce: float
    is_monotonic: bool
    monotonicity_violations: int
    buckets: List[ProbabilityBucketEvaluation]
    summary: str


@dataclass
class StrengthBandEvaluation:
    band_label: str
    min_strength: int
    max_strength: int
    sample_size: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    expectancy_r: float
    profit_factor: float
    total_r: float
    avg_calibrated_prob: float


@dataclass
class StrengthQualityReport:
    generated_at: str
    total_trades: int
    is_monotonic: bool
    strength_predictive_score: float  # Pearson correlation of strength vs realized R
    bands: List[StrengthBandEvaluation]
    summary: str


# ---------------------------------------------------------------------------
# Feature Intelligence Engine
# ---------------------------------------------------------------------------

class FeatureIntelligenceEngine:
    """Computes comprehensive feature contributions, interactions, and calibration quality."""

    @staticmethod
    def _extract_trades(records: List[SignalResearchRecord]) -> List[SignalResearchRecord]:
        return [r for r in records
                if getattr(r, "decision", "WAIT") in ("BUY", "SELL")
                and getattr(r, "outcome", "OPEN") in (OutcomeLabel.WIN, OutcomeLabel.LOSS, OutcomeLabel.EXPIRED, "WIN", "LOSS", "EXPIRED")]

    @classmethod
    def evaluate_feature_contributions(
        cls,
        records: List[SignalResearchRecord],
    ) -> List[FeatureContributionResult]:
        trades = cls._extract_trades(records)
        trades.sort(key=lambda r: getattr(r, "signal_timestamp", ""))
        n_total = len(trades)
        if n_total == 0:
            return []

        base_r = np.array([float(getattr(r, "realized_r", 0.0) or 0.0) for r in trades])
        base_wins = int(np.sum(base_r > 0))
        base_losses = int(np.sum(base_r < 0))
        base_exp = float(np.mean(base_r)) if len(base_r) > 0 else 0.0

        # Features to evaluate
        features = [
            ("HTF_ALIGNMENT", lambda r: bool(getattr(getattr(r, "mtf", None), "htf_aligned", False))),
            ("EMA_ALIGNMENT", lambda r: bool(getattr(getattr(r, "indicators", None), "ema_aligned", False))),
            ("VWAP_ALIGNMENT", lambda r: bool(getattr(getattr(r, "indicators", None), "vwap_aligned", False))),
            ("MOMENTUM_ALIGNMENT", lambda r: bool(getattr(getattr(r, "indicators", None), "momentum_aligned", False))),
            ("SR_ALIGNMENT", lambda r: bool(getattr(getattr(r, "indicators", None), "sr_aligned", False))),
            ("SMC_ALIGNMENT", lambda r: bool(getattr(getattr(r, "indicators", None), "smc_aligned", False))),
            ("HIGH_CONFIDENCE", lambda r: str(getattr(getattr(r, "ai", None), "ai_confidence", "")).upper() == "HIGH" or float(getattr(r, "confidence", 0.0) or 0.0) >= 70.0),
            ("POSITIVE_PROBABILITY (>50%)", lambda r: float(getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0) >= 0.50),
            ("HIGH_CONFLUENCE (>=65)", lambda r: int(getattr(getattr(r, "strategy_scores", None), "confluence_score", 0) or 0) >= 65),
            ("CONFIRMATION_COUNT >= 3", lambda r: int(getattr(getattr(r, "strategy_scores", None), "confirmation_score", 0) or 0) >= 3),
            ("TRENDING_REGIME", lambda r: "TRENDING" in str(getattr(r, "regime", "")).upper()),
            ("LONDON_SESSION", lambda r: "LONDON" in str(getattr(r, "session", "")).upper()),
            ("NEW_YORK_SESSION", lambda r: "NEW_YORK" in str(getattr(r, "session", "")).upper()),
        ]

        results: List[FeatureContributionResult] = []

        for name, pred in features:
            matched_indices = [i for i, t in enumerate(trades) if pred(t)]
            n_match = len(matched_indices)

            if n_match < 30:
                results.append(FeatureContributionResult(
                    feature_name=name,
                    sample_size=n_match,
                    win_count=0,
                    loss_count=0,
                    win_rate_pct=0.0,
                    expectancy_r=0.0,
                    profit_factor=0.0,
                    max_drawdown_r=0.0,
                    total_r=0.0,
                    oos_expectancy_r=0.0,
                    holdout_expectancy_r=0.0,
                    winner_retention_pct=0.0,
                    loser_reduction_pct=0.0,
                    classification="INSUFFICIENT DATA",
                    detail=f"Sample size {n_match} < 30 minimum threshold.",
                ))
                continue

            r_match = base_r[matched_indices]
            wins = int(np.sum(r_match > 0))
            losses = int(np.sum(r_match < 0))
            wr = round(wins / n_match * 100.0, 1)
            exp = round(float(np.mean(r_match)), 4)
            tot_r = round(float(np.sum(r_match)), 2)

            pos_sum = float(np.sum(r_match[r_match > 0])) if wins > 0 else 0.0
            neg_sum = float(np.sum(np.abs(r_match[r_match < 0]))) if losses > 0 else 0.0
            pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0
            dd = round(OutcomeEngine.calculate_max_drawdown(r_match), 2)

            # OOS (last 20% of matched)
            oos_n = int(n_match * 0.80)
            r_oos = r_match[oos_n:]
            oos_exp = round(float(np.mean(r_oos)), 4) if len(r_oos) > 0 else 0.0

            # Holdout (last 15% of matched)
            hold_n = int(n_match * 0.85)
            r_hold = r_match[hold_n:]
            hold_exp = round(float(np.mean(r_hold)), 4) if len(r_hold) > 0 else 0.0

            win_ret = round(wins / max(base_wins, 1) * 100.0, 1)
            loser_red = round((base_losses - losses) / max(base_losses, 1) * 100.0, 1)

            delta_exp = exp - base_exp
            if delta_exp >= 0.08 and oos_exp > 0 and hold_exp > 0:
                classification = "STRONG POSITIVE"
            elif delta_exp >= 0.02 and oos_exp >= 0:
                classification = "POSITIVE"
            elif abs(delta_exp) < 0.02:
                classification = "NEUTRAL"
            elif delta_exp <= -0.06:
                classification = "STRONGLY NEGATIVE"
            else:
                classification = "NEGATIVE"

            detail = (
                f"Expectancy delta: {delta_exp:+.4f}R (Matched: {exp:+.4f}R vs Base: {base_exp:+.4f}R). "
                f"OOS: {oos_exp:+.4f}R, Holdout: {hold_exp:+.4f}R, Winner Ret: {win_ret}%, Loser Red: {loser_red}%."
            )

            results.append(FeatureContributionResult(
                feature_name=name,
                sample_size=n_match,
                win_count=wins,
                loss_count=losses,
                win_rate_pct=wr,
                expectancy_r=exp,
                profit_factor=pf,
                max_drawdown_r=dd,
                total_r=tot_r,
                oos_expectancy_r=oos_exp,
                holdout_expectancy_r=hold_exp,
                winner_retention_pct=win_ret,
                loser_reduction_pct=loser_red,
                classification=classification,
                detail=detail,
            ))

        return results

    @classmethod
    def evaluate_feature_interactions(
        cls,
        records: List[SignalResearchRecord],
    ) -> List[FeatureInteractionResult]:
        trades = cls._extract_trades(records)
        trades.sort(key=lambda r: getattr(r, "signal_timestamp", ""))
        n_total = len(trades)
        if n_total == 0:
            return []

        base_r = np.array([float(getattr(r, "realized_r", 0.0) or 0.0) for r in trades])
        base_exp = float(np.mean(base_r)) if len(base_r) > 0 else 0.0

        interactions = [
            ("PROB_HIGH + TRENDING_REGIME",
             "HIGH_PROBABILITY (>=60%)", "TRENDING_REGIME",
             lambda r: (float(getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0) >= 0.60) and ("TRENDING" in str(getattr(r, "regime", "")).upper())),

            ("PROB_HIGH + HTF_ALIGNED",
             "HIGH_PROBABILITY (>=60%)", "HTF_ALIGNMENT",
             lambda r: (float(getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0) >= 0.60) and bool(getattr(getattr(r, "mtf", None), "htf_aligned", False))),

            ("HTF_ALIGNED + SR_ALIGNED",
             "HTF_ALIGNMENT", "SR_ALIGNMENT",
             lambda r: bool(getattr(getattr(r, "mtf", None), "htf_aligned", False)) and bool(getattr(getattr(r, "indicators", None), "sr_aligned", False))),

            ("VWAP_ALIGNED + EMA_ALIGNED",
             "VWAP_ALIGNMENT", "EMA_ALIGNMENT",
             lambda r: bool(getattr(getattr(r, "indicators", None), "vwap_aligned", False)) and bool(getattr(getattr(r, "indicators", None), "ema_aligned", False))),

            ("TRENDING_REGIME + HTF_ALIGNED",
             "TRENDING_REGIME", "HTF_ALIGNMENT",
             lambda r: ("TRENDING" in str(getattr(r, "regime", "")).upper()) and bool(getattr(getattr(r, "mtf", None), "htf_aligned", False))),

            ("HIGH_CONFLUENCE + MOMENTUM_ALIGNED",
             "HIGH_CONFLUENCE (>=65)", "MOMENTUM_ALIGNMENT",
             lambda r: (int(getattr(getattr(r, "strategy_scores", None), "confluence_score", 0) or 0) >= 65) and bool(getattr(getattr(r, "indicators", None), "momentum_aligned", False))),

            ("LONDON_SESSION + TRENDING_REGIME",
             "LONDON_SESSION", "TRENDING_REGIME",
             lambda r: ("LONDON" in str(getattr(r, "session", "")).upper()) and ("TRENDING" in str(getattr(r, "regime", "")).upper())),

            ("HIGH_CONFIDENCE + HIGH_CONFLUENCE",
             "HIGH_CONFIDENCE", "HIGH_CONFLUENCE (>=65)",
             lambda r: (str(getattr(getattr(r, "ai", None), "ai_confidence", "")).upper() == "HIGH" or float(getattr(r, "confidence", 0.0) or 0.0) >= 70.0) and (int(getattr(getattr(r, "strategy_scores", None), "confluence_score", 0) or 0) >= 65)),
        ]

        results: List[FeatureInteractionResult] = []

        for iname, fa, fb, pred in interactions:
            matched_indices = [i for i, t in enumerate(trades) if pred(t)]
            n_match = len(matched_indices)

            if n_match < 25:
                results.append(FeatureInteractionResult(
                    interaction_name=iname,
                    feature_a=fa,
                    feature_b=fb,
                    sample_size=n_match,
                    win_rate_pct=0.0,
                    expectancy_r=0.0,
                    profit_factor=0.0,
                    max_drawdown_r=0.0,
                    oos_expectancy_r=0.0,
                    holdout_expectancy_r=0.0,
                    classification="NO VALUE",
                    detail=f"Sample size {n_match} < 25 minimum threshold.",
                ))
                continue

            r_match = base_r[matched_indices]
            wins = int(np.sum(r_match > 0))
            losses = int(np.sum(r_match < 0))
            wr = round(wins / n_match * 100.0, 1)
            exp = round(float(np.mean(r_match)), 4)

            pos_sum = float(np.sum(r_match[r_match > 0])) if wins > 0 else 0.0
            neg_sum = float(np.sum(np.abs(r_match[r_match < 0]))) if losses > 0 else 0.0
            pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0
            dd = round(OutcomeEngine.calculate_max_drawdown(r_match), 2)

            oos_n = int(n_match * 0.80)
            r_oos = r_match[oos_n:]
            oos_exp = round(float(np.mean(r_oos)), 4) if len(r_oos) > 0 else 0.0

            hold_n = int(n_match * 0.85)
            r_hold = r_match[hold_n:]
            hold_exp = round(float(np.mean(r_hold)), 4) if len(r_hold) > 0 else 0.0

            delta = exp - base_exp
            if delta >= 0.08 and oos_exp > 0 and hold_exp > 0 and pf >= 1.25:
                classification = "ROBUST INTERACTION"
            elif delta >= 0.03 and oos_exp >= 0:
                classification = "PROMISING INTERACTION"
            elif delta < -0.05:
                classification = "HARMFUL"
            elif abs(delta) < 0.03:
                classification = "NO VALUE"
            else:
                classification = "UNSTABLE INTERACTION"

            detail = (
                f"Combined Exp: {exp:+.4f}R (Delta: {delta:+.4f}R vs Base). "
                f"WR: {wr}%, PF: {pf:.2f}, OOS: {oos_exp:+.4f}R, Holdout: {hold_exp:+.4f}R."
            )

            results.append(FeatureInteractionResult(
                interaction_name=iname,
                feature_a=fa,
                feature_b=fb,
                sample_size=n_match,
                win_rate_pct=wr,
                expectancy_r=exp,
                profit_factor=pf,
                max_drawdown_r=dd,
                oos_expectancy_r=oos_exp,
                holdout_expectancy_r=hold_exp,
                classification=classification,
                detail=detail,
            ))

        return results

    @classmethod
    def evaluate_probability_quality(
        cls,
        records: List[SignalResearchRecord],
    ) -> ProbabilityQualityReport:
        trades = cls._extract_trades(records)
        if not trades:
            return ProbabilityQualityReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_trades=0,
                brier_score=0.25,
                ece=0.0,
                mce=0.0,
                is_monotonic=True,
                monotonicity_violations=0,
                buckets=[],
                summary="No trades available.",
            )

        # 10 buckets: [0-0.10], [0.10-0.20], ..., [0.90-1.00]
        bucket_defs = [(i * 0.10, (i + 1) * 0.10, f"{i*10}–{(i+1)*10}%") for i in range(10)]
        bucket_evals: List[ProbabilityBucketEvaluation] = []

        squared_errors = []
        calibration_errors = []

        for b_min, b_max, label in bucket_defs:
            b_trades = [t for t in trades
                        if (b_min <= float(getattr(getattr(t, "ai", None), "ai_probability", 0.5) or 0.5) < b_max)
                        or (b_max == 1.0 and float(getattr(getattr(t, "ai", None), "ai_probability", 0.5) or 0.5) == 1.0)]
            n_b = len(b_trades)
            if n_b == 0:
                bucket_evals.append(ProbabilityBucketEvaluation(
                    bucket_label=label,
                    min_prob=b_min,
                    max_prob=b_max,
                    sample_size=0,
                    win_count=0,
                    loss_count=0,
                    observed_win_rate_pct=0.0,
                    expected_win_rate_pct=round((b_min + b_max) / 2 * 100, 1),
                    expectancy_r=0.0,
                    profit_factor=0.0,
                    calibration_error=0.0,
                    ci_lower=0.0,
                    ci_upper=0.0,
                ))
                continue

            r_arr = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in b_trades])
            wins = int(np.sum(r_arr > 0))
            losses = int(np.sum(r_arr < 0))
            obs_wr = round(wins / n_b * 100.0, 1)
            exp_wr = round((b_min + b_max) / 2 * 100.0, 1)
            exp_r = round(float(np.mean(r_arr)), 4)

            pos_sum = float(np.sum(r_arr[r_arr > 0])) if wins > 0 else 0.0
            neg_sum = float(np.sum(np.abs(r_arr[r_arr < 0]))) if losses > 0 else 0.0
            pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0

            ci = compute_wilson_score_interval(wins, n_b)
            cal_err = abs(obs_wr - exp_wr) / 100.0

            calibration_errors.append((n_b, cal_err))

            for t in b_trades:
                p = float(getattr(getattr(t, "ai", None), "ai_probability", 0.5) or 0.5)
                y = 1.0 if (getattr(t, "realized_r", 0.0) or 0.0) > 0 else 0.0
                squared_errors.append((p - y) ** 2)

            bucket_evals.append(ProbabilityBucketEvaluation(
                bucket_label=label,
                min_prob=b_min,
                max_prob=b_max,
                sample_size=n_b,
                win_count=wins,
                loss_count=losses,
                observed_win_rate_pct=obs_wr,
                expected_win_rate_pct=exp_wr,
                expectancy_r=exp_r,
                profit_factor=pf,
                calibration_error=round(cal_err, 4),
                ci_lower=round(ci.ci_lower, 1),
                ci_upper=round(ci.ci_upper, 1),
            ))

        # Metrics
        brier = round(float(np.mean(squared_errors)), 4) if squared_errors else 0.25
        total_n = sum(n for n, _ in calibration_errors)
        ece = round(sum(n * err for n, err in calibration_errors) / max(total_n, 1), 4)
        mce = round(max((err for _, err in calibration_errors), default=0.0), 4)

        # Monotonicity check on populated buckets
        populated = [b for b in bucket_evals if b.sample_size >= 15]
        violations = 0
        for i in range(len(populated) - 1):
            if populated[i].observed_win_rate_pct > populated[i + 1].observed_win_rate_pct:
                violations += 1

        is_monotonic = violations == 0

        summary = (
            f"Probability Calibration Quality: Brier={brier:.4f}, ECE={ece:.4f} (Max={mce:.4f}). "
            f"Monotonic across populated buckets: {is_monotonic} ({violations} inversion(s))."
        )

        return ProbabilityQualityReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_trades=len(trades),
            brier_score=brier,
            ece=ece,
            mce=mce,
            is_monotonic=is_monotonic,
            monotonicity_violations=violations,
            buckets=bucket_evals,
            summary=summary,
        )

    @classmethod
    def evaluate_strength_quality(
        cls,
        records: List[SignalResearchRecord],
    ) -> StrengthQualityReport:
        trades = cls._extract_trades(records)
        if not trades:
            return StrengthQualityReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_trades=0,
                is_monotonic=True,
                strength_predictive_score=0.0,
                bands=[],
                summary="No trades available.",
            )

        bands_def = [
            ("50–54", 50, 54),
            ("55–59", 55, 59),
            ("60–64", 60, 64),
            ("65–69", 65, 69),
            ("70–74", 70, 74),
            ("75+", 75, 100),
        ]

        band_evals: List[StrengthBandEvaluation] = []
        strengths = []
        realized_rs = []

        for label, s_min, s_max in bands_def:
            b_trades = [t for t in trades
                        if s_min <= int(getattr(getattr(t, "strategy_scores", None), "confluence_score", 50) or 50) <= s_max]
            n_b = len(b_trades)
            if n_b == 0:
                band_evals.append(StrengthBandEvaluation(
                    band_label=label,
                    min_strength=s_min,
                    max_strength=s_max,
                    sample_size=0,
                    win_count=0,
                    loss_count=0,
                    win_rate_pct=0.0,
                    expectancy_r=0.0,
                    profit_factor=0.0,
                    total_r=0.0,
                    avg_calibrated_prob=0.0,
                ))
                continue

            r_arr = np.array([float(getattr(t, "realized_r", 0.0) or 0.0) for t in b_trades])
            wins = int(np.sum(r_arr > 0))
            losses = int(np.sum(r_arr < 0))
            wr = round(wins / n_b * 100.0, 1)
            exp_r = round(float(np.mean(r_arr)), 4)
            tot_r = round(float(np.sum(r_arr)), 2)

            pos_sum = float(np.sum(r_arr[r_arr > 0])) if wins > 0 else 0.0
            neg_sum = float(np.sum(np.abs(r_arr[r_arr < 0]))) if losses > 0 else 0.0
            pf = round(pos_sum / neg_sum, 2) if neg_sum > 0 else 99.0

            probs = [float(getattr(getattr(t, "ai", None), "ai_probability", 0.5) or 0.5) for t in b_trades]
            avg_prob = round(float(np.mean(probs)), 3)

            for t in b_trades:
                strengths.append(int(getattr(getattr(t, "strategy_scores", None), "confluence_score", 50) or 50))
                realized_rs.append(float(getattr(t, "realized_r", 0.0) or 0.0))

            band_evals.append(StrengthBandEvaluation(
                band_label=label,
                min_strength=s_min,
                max_strength=s_max,
                sample_size=n_b,
                win_count=wins,
                loss_count=losses,
                win_rate_pct=wr,
                expectancy_r=exp_r,
                profit_factor=pf,
                total_r=tot_r,
                avg_calibrated_prob=avg_prob,
            ))

        # Monotonicity check
        populated = [b for b in band_evals if b.sample_size >= 20]
        violations = 0
        for i in range(len(populated) - 1):
            if populated[i].expectancy_r > populated[i + 1].expectancy_r:
                violations += 1

        is_monotonic = violations <= 1  # Allow at most 1 minor noise inversion

        corr = float(np.corrcoef(strengths, realized_rs)[0, 1]) if len(strengths) > 10 and np.std(strengths) > 0 else 0.0

        summary = (
            f"Strength Quality: Correlation with Realized R = {corr:+.4f}. "
            f"Bands expectancy monotonic: {is_monotonic} ({violations} inversion(s))."
        )

        return StrengthQualityReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_trades=len(trades),
            is_monotonic=is_monotonic,
            strength_predictive_score=round(corr, 4),
            bands=band_evals,
            summary=summary,
        )

    @classmethod
    def evaluate_feature_contributions_by_asset(
        cls,
        records: List[SignalResearchRecord],
    ) -> Dict[str, List[FeatureContributionResult]]:
        """Evaluate single feature contributions separately for BTC and XAU."""
        btc_records = [r for r in records if "BTC" in str(getattr(r, "asset", "")).upper()]
        xau_records = [r for r in records if "XAU" in str(getattr(r, "asset", "")).upper() or "GOLD" in str(getattr(r, "asset", "")).upper()]
        return {
            "BTC": cls.evaluate_feature_contributions(btc_records),
            "XAU": cls.evaluate_feature_contributions(xau_records),
            "ALL": cls.evaluate_feature_contributions(records),
        }

    @classmethod
    def evaluate_feature_interactions_by_asset(
        cls,
        records: List[SignalResearchRecord],
    ) -> Dict[str, List[FeatureInteractionResult]]:
        """Evaluate feature pair interactions separately for BTC and XAU."""
        btc_records = [r for r in records if "BTC" in str(getattr(r, "asset", "")).upper()]
        xau_records = [r for r in records if "XAU" in str(getattr(r, "asset", "")).upper() or "GOLD" in str(getattr(r, "asset", "")).upper()]
        return {
            "BTC": cls.evaluate_feature_interactions(btc_records),
            "XAU": cls.evaluate_feature_interactions(xau_records),
            "ALL": cls.evaluate_feature_interactions(records),
        }

    # ---------------------------------------------------------------------------
    # Master Report Generation
    # ---------------------------------------------------------------------------

    @classmethod
    def generate_all_reports(
        cls,
        records: List[SignalResearchRecord],
    ) -> Dict[str, Tuple[str, str]]:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        paths: Dict[str, Tuple[str, str]] = {}

        # 1. Feature Contribution Report
        fc_results = cls.evaluate_feature_contributions(records)
        fc_json = os.path.join(REPORTS_DIR, "FEATURE_CONTRIBUTION_REPORT.json")
        fc_md   = os.path.join(REPORTS_DIR, "FEATURE_CONTRIBUTION_REPORT.md")
        fva_json = os.path.join(REPORTS_DIR, "FEATURE_VALUE_ANALYSIS.json")
        fva_md   = os.path.join(REPORTS_DIR, "FEATURE_VALUE_ANALYSIS.md")
        with open(fc_json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in fc_results], f, indent=2, default=str)
        with open(fva_json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in fc_results], f, indent=2, default=str)

        lines = [
            "# Feature Contribution Analysis Report — Phase 4",
            f"\n**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Total Features Evaluated:** {len(fc_results)}",
            "\n## Feature Contribution Table",
            "| Feature | Sample N | Win Rate | Expectancy | PF | Max DD | OOS Exp | Holdout Exp | Win Ret | Loser Red | Classification |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for r in fc_results:
            lines.append(
                f"| `{r.feature_name}` | {r.sample_size} | {r.win_rate_pct}% | {r.expectancy_r:+.4f}R | "
                f"{r.profit_factor:.2f} | {r.max_drawdown_r:.1f}R | {r.oos_expectancy_r:+.4f}R | "
                f"{r.holdout_expectancy_r:+.4f}R | {r.winner_retention_pct}% | {r.loser_reduction_pct}% | `{r.classification}` |"
            )
        lines += ["\n## Detailed Feature Insights"]
        for r in fc_results:
            lines += [
                f"\n### `{r.feature_name}` [{r.classification}]",
                f"- {r.detail}",
            ]
        fc_md_content = "\n".join(lines)
        with open(fc_md, "w", encoding="utf-8") as f:
            f.write(fc_md_content)
        with open(fva_md, "w", encoding="utf-8") as f:
            f.write(fc_md_content)
        paths["feature_contribution"] = (fc_json, fc_md)
        paths["feature_value_analysis"] = (fva_json, fva_md)

        # 2. Feature Interaction Report
        fi_results = cls.evaluate_feature_interactions(records)
        fi_json = os.path.join(REPORTS_DIR, "FEATURE_INTERACTION_REPORT.json")
        fi_md   = os.path.join(REPORTS_DIR, "FEATURE_INTERACTION_REPORT.md")
        fia_json = os.path.join(REPORTS_DIR, "FEATURE_INTERACTION_ANALYSIS.json")
        fia_md   = os.path.join(REPORTS_DIR, "FEATURE_INTERACTION_ANALYSIS.md")
        with open(fi_json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in fi_results], f, indent=2, default=str)
        with open(fia_json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in fi_results], f, indent=2, default=str)

        lines = [
            "# Feature Interaction Analysis Report — Phase 4",
            f"\n**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Total Interactions Evaluated:** {len(fi_results)}",
            "\n## Feature Interaction Matrix",
            "| Interaction | Sample N | Win Rate | Expectancy | PF | Max DD | OOS Exp | Holdout Exp | Classification |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for r in fi_results:
            lines.append(
                f"| `{r.interaction_name}` | {r.sample_size} | {r.win_rate_pct}% | {r.expectancy_r:+.4f}R | "
                f"{r.profit_factor:.2f} | {r.max_drawdown_r:.1f}R | {r.oos_expectancy_r:+.4f}R | "
                f"{r.holdout_expectancy_r:+.4f}R | `{r.classification}` |"
            )
        lines += ["\n## Detailed Interaction Insights"]
        for r in fi_results:
            lines += [
                f"\n### `{r.interaction_name}` [{r.classification}]",
                f"- {r.detail}",
            ]
        fi_content = "\n".join(lines)
        with open(fi_md, "w", encoding="utf-8") as f:
            f.write(fi_content)
        with open(fia_md, "w", encoding="utf-8") as f:
            f.write(fi_content)
        paths["feature_interaction"] = (fi_json, fi_md)
        paths["feature_interaction_analysis"] = (fia_json, fia_md)

        # 3. Probability Quality Report
        pq_report = cls.evaluate_probability_quality(records)
        pq_json = os.path.join(REPORTS_DIR, "PROBABILITY_QUALITY_REPORT.json")
        pq_md   = os.path.join(REPORTS_DIR, "PROBABILITY_QUALITY_REPORT.md")
        with open(pq_json, "w", encoding="utf-8") as f:
            json.dump(asdict(pq_report), f, indent=2, default=str)

        lines = [
            "# Probability Quality & Reliability Report — Phase 4",
            f"\n**Generated:** {pq_report.generated_at}",
            f"\n## Summary",
            pq_report.summary,
            "\n## Probability Reliability Buckets",
            "| Bucket | Min–Max | Sample N | Wins | Losses | Obs WR | Exp WR | Expectancy | PF | Error | 95% CI |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for b in pq_report.buckets:
            lines.append(
                f"| {b.bucket_label} | {b.min_prob:.2f}–{b.max_prob:.2f} | {b.sample_size} | {b.win_count} | "
                f"{b.loss_count} | {b.observed_win_rate_pct}% | {b.expected_win_rate_pct}% | {b.expectancy_r:+.4f}R | "
                f"{b.profit_factor:.2f} | {b.calibration_error:.4f} | [{b.ci_lower}%–{b.ci_upper}%] |"
            )
        with open(pq_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        paths["probability_quality"] = (pq_json, pq_md)

        # 4. Strength Quality Report
        sq_report = cls.evaluate_strength_quality(records)
        sq_json = os.path.join(REPORTS_DIR, "STRENGTH_QUALITY_REPORT.json")
        sq_md   = os.path.join(REPORTS_DIR, "STRENGTH_QUALITY_REPORT.md")
        with open(sq_json, "w", encoding="utf-8") as f:
            json.dump(asdict(sq_report), f, indent=2, default=str)

        lines = [
            "# Strength Quality & Monotonicity Report — Phase 4",
            f"\n**Generated:** {sq_report.generated_at}",
            f"\n## Summary",
            sq_report.summary,
            "\n## Strength Bands Evaluation",
            "| Strength Band | Score Range | Sample N | Wins | Losses | Win Rate | Expectancy | PF | Total R | Avg Calib Prob |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for b in sq_report.bands:
            lines.append(
                f"| {b.band_label} | {b.min_strength}–{b.max_strength} | {b.sample_size} | {b.win_count} | "
                f"{b.loss_count} | {b.win_rate_pct}% | {b.expectancy_r:+.4f}R | {b.profit_factor:.2f} | "
                f"{b.total_r:+.2f}R | {b.avg_calibrated_prob:.3f} |"
            )
        with open(sq_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        paths["strength_quality"] = (sq_json, sq_md)

        return paths
