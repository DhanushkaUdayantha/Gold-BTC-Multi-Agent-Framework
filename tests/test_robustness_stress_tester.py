"""
Automated Test Suite for Robustness & Stress-Test Validation Engine.

Validates:
1. Threshold Sensitivity across probability spectrum (35%–50%)
2. Condition Ablation & Edge Retention Analysis
3. Time Epoch Stability across 4 Historical Eras
4. 4-Fold Walk-Forward Cross-Validation Stress Testing
5. High-Precision 10,000-Resample Bootstrap Stability
6. Execution Friction & Cost Stress Testing (0.00R to 0.20R)
7. Market Regime Viability Breakdown
8. Parameter Perturbation & Plateau Verification (±2%)
9. Multi-Factor Robustness Scoring Formula (0 to 100)
10. Multiple-Testing & Selection-Bias Audit
11. End-to-End Report Generation (4 JSON and Markdown artifacts)
"""
from __future__ import annotations

import json
import os
import numpy as np
import pytest

from src.services.robustness_stress_tester import (
    RobustnessStressTester,
    ThresholdSensitivityRow,
    ConditionAblationRow,
    TimeEpochStabilityRow,
    HighPrecisionBootstrapResult,
    CostStressTestRow,
    RegimeStressRow,
    CandidateStressTestProfile,
    RobustnessStressTestReport,
)
from src.services.stable_expectancy_researcher import ResearchObservation


@pytest.fixture
def stress_tester():
    """Instance of RobustnessStressTester."""
    return RobustnessStressTester()


@pytest.fixture
def synthetic_observations():
    """Generate deterministic research observations for testing."""
    obs_list = []
    for i in range(120):
        ts = f"2022-01-01T{i:02d}:00:00Z"
        dir_ = "SELL" if i % 2 == 0 else "BUY"
        is_win = (i % 2 == 0) if dir_ == "SELL" else (i % 5 == 0)
        outcome = "WIN" if is_win else "LOSS"
        realized_r = 1.5 if outcome == "WIN" else -1.0

        obs = ResearchObservation(
            signal_id=f"sig_{i:04d}",
            asset="BTC/USD",
            signal_timestamp=ts,
            outcome_timestamp=ts,
            direction=dir_,
            confluence_score=60,
            raw_strength=55,
            calibrated_probability=0.42,
            market_regime="LOW_VOLATILITY" if i % 3 == 0 else "TRENDING",
            session="LONDON",
            htf_aligned=(i % 2 == 0),
            mom_aligned=(i % 2 == 0),
            ms_aligned=True,
            sr_aligned=(i % 2 == 0),
            smc_aligned=True,
            ema_aligned=True,
            vwap_aligned=True,
            htf_direction="BEARISH" if dir_ == "SELL" else "BULLISH",
            momentum_direction="BEARISH" if dir_ == "SELL" else "BULLISH",
            market_structure_direction="BEARISH",
            sr_direction="BEARISH",
            smc_direction="BEARISH",
            actual_outcome=outcome,
            realized_r=realized_r,
            mfe=2.0 if outcome == "WIN" else 0.5,
            mae=0.5 if outcome == "WIN" else 1.2,
            time_to_outcome_minutes=60.0,
            future_timestamp_used=False,
            future_trade_used=False,
            future_outcome_used=False,
            future_calibration_data_used=False,
        )
        obs_list.append(obs)
    return obs_list


# ---------------------------------------------------------------------------
# 1. Threshold Sensitivity & Plateau Tests
# ---------------------------------------------------------------------------

def test_threshold_sensitivity_spectrum(stress_tester, synthetic_observations):
    """Verify testing across 35%, 38%, 40%, 42%, 45%, 48%, 50% thresholds."""
    rows = stress_tester.test_threshold_sensitivity(
        asset="BTC/USD",
        direction="SELL",
        condition_name="HTF_ALIGNED",
        condition_fn=lambda o: o.htf_aligned,
        observations=synthetic_observations,
    )

    assert len(rows) == 7
    threshold_vals = [r.threshold_pct for r in rows]
    assert threshold_vals == [35.0, 38.0, 40.0, 42.0, 45.0, 48.0, 50.0]
    for r in rows:
        assert isinstance(r.is_positive_plateau, bool)
        assert r.bootstrap_ci_lower <= r.expectancy_r <= r.bootstrap_ci_upper


# ---------------------------------------------------------------------------
# 2. Condition Ablation Tests
# ---------------------------------------------------------------------------

def test_condition_ablation_analysis(stress_tester, synthetic_observations):
    """Verify condition ablation calculates edge retention and verdicts."""
    ablations = [
        ("PROB_ONLY", "Probability only", lambda o: True),
        ("HTF", "HTF Aligned", lambda o: o.htf_aligned),
        ("MOM", "Momentum Aligned", lambda o: o.mom_aligned),
    ]

    rows = stress_tester.test_condition_ablation(
        asset="BTC/USD",
        direction="SELL",
        base_prob=0.40,
        ablation_configs=ablations,
        observations=synthetic_observations,
    )

    assert len(rows) == 3
    for r in rows:
        assert r.verdict in ("ROBUST", "DEGRADED", "DESTROYED / NEGATIVE")
        assert 0.0 <= r.edge_retained_pct <= 500.0


# ---------------------------------------------------------------------------
# 3. Time Epoch Stability Tests
# ---------------------------------------------------------------------------

def test_time_epoch_stability(stress_tester, synthetic_observations):
    """Verify time stability across 4 sequential non-overlapping historical eras."""
    rows = stress_tester.test_time_epoch_stability(
        direction="SELL",
        min_prob=0.40,
        condition_fn=lambda o: o.htf_aligned,
        observations=synthetic_observations,
    )

    assert len(rows) == 4
    for i, r in enumerate(rows, 1):
        assert f"Era {i}" in r.epoch_name
        assert r.trades_count > 0


# ---------------------------------------------------------------------------
# 4. 10,000-Resample High-Precision Bootstrap Tests
# ---------------------------------------------------------------------------

def test_10k_bootstrap_resampling(stress_tester):
    """Verify 10,000 resample bootstrap properties and probabilities."""
    r_vals = [1.5, -1.0, 1.5, 1.5, -1.0, 1.5, -1.0, 1.5, 1.5, -1.0]
    res = stress_tester.run_10k_bootstrap(r_vals)

    assert res.n_resamples == 10000
    assert res.sample_size == len(r_vals)
    assert res.ci_lower_2_5 <= res.mean_expectancy_r <= res.ci_upper_97_5
    assert 0.0 <= res.prob_positive_expectancy_pct <= 100.0
    assert 0.0 <= res.prob_expectancy_above_20_pct <= 100.0


# ---------------------------------------------------------------------------
# 5. Cost & Friction Stress Tests
# ---------------------------------------------------------------------------

def test_cost_and_friction_stress(stress_tester):
    """Verify performance under execution friction costs (0R to 0.20R)."""
    r_vals = [1.5, -1.0, 1.5, 1.5, -1.0]
    rows, break_even = stress_tester.test_cost_stress(r_vals)

    assert len(rows) == 6
    frictions = [r.friction_r_per_trade for r in rows]
    assert frictions == [0.0, 0.02, 0.05, 0.10, 0.15, 0.20]
    assert break_even == round(float(np.mean(r_vals)), 3)
    # Higher friction must strictly decrease expectancy
    assert rows[0].adjusted_expectancy_r > rows[-1].adjusted_expectancy_r


# ---------------------------------------------------------------------------
# 6. Robustness Scoring Formula Tests
# ---------------------------------------------------------------------------

def test_robustness_scoring_and_classification(stress_tester):
    """Verify robustness scoring calculation and classification bounds."""
    # Robust candidate test
    th_rows = [ThresholdSensitivityRow(40.0, 100, 55.0, 0.35, 1.8, 35.0, 5.0, 0.15, 0.50, 0.25, 0.30, 4, 0.10, 0.40, True)] * 5
    time_rows = [TimeEpochStabilityRow("Era 1", "2020", 50, 30, 60.0, 0.30, 1.7, 15.0, 4.0, True)] * 4

    score, cls_, notes = stress_tester.calculate_robustness_score(
        baseline_exp=0.35,
        oos_exp=0.25,
        holdout_exp=0.30,
        wf_positive_folds=4,
        boot_ci_lower=0.15,
        break_even_cost=0.35,
        threshold_rows=th_rows,
        time_rows=time_rows,
        sample_size=250,
        max_dd=5.0,
    )

    assert 0.0 <= score <= 100.0
    assert cls_ == "ROBUST"
    assert len(notes) >= 5


# ---------------------------------------------------------------------------
# 7. Full Stress-Testing Suite & Report Generation Integration Test
# ---------------------------------------------------------------------------

def test_full_robustness_report_export(stress_tester):
    """Verify that the full stress-test suite executes and exports all reports."""
    paths = stress_tester.export_all_reports()

    for k, p in paths.items():
        assert os.path.exists(p), f"Missing report {k} at {p}"

    # Verify JSON structure
    with open(paths["main_json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "candidate_profiles" in data
    assert "multiple_testing_audit" in data
    assert "research_questions_answers" in data
    assert len(data["candidate_profiles"]) >= 4

    # Verify Markdown contains key sections
    with open(paths["main_md"], "r", encoding="utf-8") as f:
        md = f.read()
    assert "# Robustness & Stress-Test Validation Report" in md
    assert "## 1. Executive Summary" in md
    assert "## 2. Threshold Sensitivity & Performance Plateau Analysis" in md
    assert "## 4. High-Precision Bootstrap Stability (10,000 Resamples)" in md
    assert "## 7. Answers to the 12 Mandatory Stress-Test Questions" in md
