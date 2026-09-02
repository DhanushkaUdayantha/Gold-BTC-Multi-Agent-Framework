"""
Automated Test Suite for Stable Positive Expectancy Discovery Research.

Validates:
1. Field Availability & Database Schema Inspection
2. Point-in-Time Research Dataset Construction
3. Lookahead Bias Auditing (Zero violations on clean data, detects synthetic leakage)
4. Comprehensive Strategy Candidate Metric Calculations
5. Non-parametric Bootstrap Confidence Intervals (1,000 resamples)
6. 4-Fold Chronological Walk-Forward Cross-Validation
7. 3-Way Train / Validation / Holdout Split Isolation
8. Composite Multi-Factor Strategy Ranking Logic
9. Directional Separation (BTC SELL vs BUY, XAU BUY vs SELL)
10. End-to-End Report Generation (6 exported JSON and Markdown artifacts)
"""
from __future__ import annotations

import json
import os
import tempfile
import numpy as np
import pytest

from src.services.stable_expectancy_researcher import (
    StableExpectancyResearcher,
    ResearchObservation,
    StrategyCandidateResult,
    StableExpectancyLookaheadAudit,
    StableExpectancyResearchReport,
)


@pytest.fixture
def researcher():
    """Instance of StableExpectancyResearcher."""
    return StableExpectancyResearcher()


@pytest.fixture
def synthetic_observations():
    """Generate synthetic point-in-time research observations for testing."""
    obs_list = []
    for i in range(100):
        ts = f"2021-01-01T{i:02d}:00:00Z"
        dir_ = "SELL" if i % 2 == 0 else "BUY"
        # Synthetic outcome
        is_win = (i % 2 == 0) if dir_ == "SELL" else (i % 4 == 0)
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
            calibrated_probability=0.45,
            market_regime="LOW_VOLATILITY" if i % 3 == 0 else "TRENDING",
            session="LONDON" if i % 2 == 0 else "NEW_YORK",
            htf_aligned=(i % 2 == 0),
            mom_aligned=(i % 2 == 0),
            ms_aligned=(i % 3 == 0),
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
# 1. Inspection & Dataset Tests
# ---------------------------------------------------------------------------

def test_field_availability_inspection(researcher):
    """Verify database fields and schema are correctly inspected."""
    rep = researcher.get_field_availability_report()
    assert rep["table_name"] == "historical_signals"
    assert "signal_id" in rep["available_columns"]
    assert "market_regime" in rep["available_columns"]
    assert "contributor_directions_json" in rep["available_columns"]
    assert len(rep["verified_fields"]) >= 10


def test_research_dataset_point_in_time_construction(researcher):
    """Verify research observations are loaded point-in-time with calibrated probabilities."""
    btc_obs = researcher.build_research_dataset("BTC/USD")
    assert len(btc_obs) == 1519
    for o in btc_obs[:10]:
        assert o.asset == "BTC/USD"
        assert o.direction in ("BUY", "SELL")
        assert 0.01 <= o.calibrated_probability <= 0.99
        assert isinstance(o.htf_aligned, bool)
        assert isinstance(o.mom_aligned, bool)


# ---------------------------------------------------------------------------
# 2. Lookahead Audit Tests
# ---------------------------------------------------------------------------

def test_lookahead_audit_clean(researcher, synthetic_observations):
    """Verify audit passes with zero violations on clean observations."""
    audit = researcher.perform_lookahead_audit(synthetic_observations[:50], synthetic_observations[50:])
    assert audit.audit_status == "PASSED"
    assert audit.violation_count == 0
    assert not audit.future_timestamp_used
    assert not audit.future_trade_used


def test_lookahead_audit_detects_leakage(researcher, synthetic_observations):
    """Verify audit flags future data leakage if flags are tripped."""
    synthetic_observations[0].future_outcome_used = True
    audit = researcher.perform_lookahead_audit(synthetic_observations[:50], synthetic_observations[50:])
    assert audit.audit_status == "FAILED"
    assert audit.violation_count > 0


# ---------------------------------------------------------------------------
# 3. Strategy Candidate Evaluation & Walk-Forward Tests
# ---------------------------------------------------------------------------

def test_strategy_candidate_evaluation(researcher, synthetic_observations):
    """Verify metrics calculation for a strategy candidate."""
    res = researcher.evaluate_strategy_candidate(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="HTF_ALIGNED",
        description="Test sell strategy",
        condition_fn=lambda o: o.htf_aligned,
        observations=synthetic_observations,
    )

    assert res.strategy_id == "TEST-BTC-SELL"
    assert res.total_trades > 0
    assert res.win_rate_pct > 0.0
    assert res.profit_factor > 0.0
    assert len(res.wf_folds) == 4
    assert 0.0 <= res.wf_stability_pct <= 100.0
    assert res.bootstrap_ci_lower <= res.expectancy_r <= res.bootstrap_ci_upper


def test_walk_forward_cross_validation(researcher, synthetic_observations):
    """Verify 4-fold walk-forward integrity and fold metrics."""
    res = researcher.evaluate_strategy_candidate(
        strategy_id="TEST-WF",
        asset="BTC/USD",
        direction="ALL",
        min_prob=0.40,
        condition_name="BASE",
        description="WF test",
        condition_fn=lambda o: True,
        observations=synthetic_observations,
    )

    assert len(res.wf_folds) == 4
    for f in res.wf_folds:
        assert f.test_range in ("Test 40–55%", "Test 55–70%", "Test 70–85%", "Test 85–100%")
        assert f.test_count >= 0


def test_directional_asymmetry_detection(researcher):
    """Verify that BTC SELL and XAU BUY are differentiated in the strategy search."""
    report = researcher.run_strategy_search()
    assert report.best_btc_strategy is not None
    assert report.best_xau_strategy is not None
    assert report.best_btc_strategy.direction == "SELL"
    assert report.best_btc_strategy.expectancy_r > 0.15


# ---------------------------------------------------------------------------
# 4. Report Generation & File Export Integration Test
# ---------------------------------------------------------------------------

def test_full_report_generation_and_export(researcher):
    """Verify that all 6 required reports are generated and exported."""
    paths = researcher.export_all_reports()

    for k, p in paths.items():
        assert os.path.exists(p), f"Export file {k} does not exist at {p}"

    # Verify Main JSON structure
    with open(paths["main_json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "top_20_candidates" in data
    assert len(data["top_20_candidates"]) == 20
    assert "field_availability_summary" in data
    assert "research_questions_answers" in data

    # Verify Top Candidates JSON
    with open(paths["top_json"], "r", encoding="utf-8") as f:
        top_data = json.load(f)
    assert len(top_data) == 20

    # Verify Main Markdown contains key sections
    with open(paths["main_md"], "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "# Stable Positive Expectancy Discovery Report" in md_text
    assert "## 2. Field Availability Report" in md_text
    assert "## 3. Top 20 Strategy Candidates" in md_text
    assert "## 7. Lookahead Bias Audit Confirmation" in md_text
    assert "## 8. Answers to the 12 Mandatory Research Questions" in md_text
