"""
Automated Test Suite for Regime-Aware Sequential Validation Engine.

Validates:
1. Sequential Event Simulation (Chronological order, equity curves, run streaks, drawdown computation)
2. Regime Transitions & Session Dynamics (static regimes, transitions, edge deterioration)
3. Rolling Performance Windows (25, 50, 100, 200 trade windows, stability scores)
4. Probability Calibration Drift (ECE, Brier score, Predicted vs Actual win rate per bin)
5. Strategy Degradation Detector (multi-condition rule engine, warning and degraded states)
6. 10,000-Path Monte Carlo Stress Testing (1st/5th percentile terminal R, max DD distributions)
7. Synchronized Multi-Asset Portfolio Simulation (Combined equity curve, correlation, diversification benefit)
8. Qualification Scoring & Classification Formula (0 to 100, Paper Trading qualification)
9. End-to-End Report Generation (6 JSON & Markdown artifacts)
"""
from __future__ import annotations

import json
import os
import numpy as np
import pytest

from src.services.sequential_regime_validator import (
    SequentialRegimeValidator,
    SequentialTradeStep,
    SequentialSimulationResult,
    RegimeTransitionResult,
    RollingPerformanceWindowSummary,
    CalibrationDriftSummary,
    DegradationDetectorSummary,
    MonteCarloStressSummary,
    PortfolioCombinedSummary,
    CandidateQualificationProfile,
    SequentialValidationMasterReport,
)
from src.services.stable_expectancy_researcher import ResearchObservation


@pytest.fixture
def validator():
    """Instance of SequentialRegimeValidator."""
    return SequentialRegimeValidator()


@pytest.fixture
def sample_sequential_records():
    """Create deterministic chronological signal records with prices."""
    records = []
    regimes = ["LOW_VOLATILITY", "TRENDING", "RANGING", "HIGH_VOLATILITY"]
    sessions = ["LONDON", "NEW_YORK", "ASIA", "OVERLAP"]

    for i in range(150):
        ts = f"2023-01-01T{i:02d}:00:00Z"
        dir_ = "SELL" if i % 2 == 0 else "BUY"
        is_win = (i % 3 != 0) if dir_ == "SELL" else (i % 4 == 0)
        outcome = "WIN" if is_win else "LOSS"
        realized_r = 1.5 if outcome == "WIN" else -1.0

        obs = ResearchObservation(
            signal_id=f"sig_seq_{i:04d}",
            asset="BTC/USD",
            signal_timestamp=ts,
            outcome_timestamp=ts,
            direction=dir_,
            confluence_score=65,
            raw_strength=58,
            calibrated_probability=0.44,
            market_regime=regimes[i % len(regimes)],
            session=sessions[i % len(sessions)],
            htf_aligned=True,
            mom_aligned=True,
            ms_aligned=True,
            sr_aligned=True,
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
            mfe=2.0 if outcome == "WIN" else 0.4,
            mae=0.4 if outcome == "WIN" else 1.1,
            time_to_outcome_minutes=45.0,
        )

        records.append({
            "observation": obs,
            "entry_price": 50000.0 + i * 10,
            "stop_loss": 50500.0 if dir_ == "SELL" else 49500.0,
            "take_profit_1": 49000.0 if dir_ == "SELL" else 51000.0,
            "take_profit_2": 48000.0 if dir_ == "SELL" else 52000.0,
            "exit_price": 49000.0 if outcome == "WIN" else (50500.0 if dir_ == "SELL" else 49500.0),
            "market_regime": obs.market_regime,
            "session": obs.session,
        })

    return records


# ---------------------------------------------------------------------------
# 1. Sequential Event Simulation Tests
# ---------------------------------------------------------------------------

def test_sequential_simulation_execution(validator, sample_sequential_records):
    """Verify sequential chronological trade processing and metrics."""
    res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    assert res.total_trades == 75  # Half of 150 are SELL
    assert res.expectancy_r > 0.0
    assert len(res.trades) == 75
    assert res.max_drawdown_r >= 0.0
    assert res.max_consecutive_wins >= 1
    assert res.max_consecutive_losses >= 1

    # Verify chronological order and cumulative arithmetic
    cum_check = 0.0
    for t in res.trades:
        cum_check += t.realized_r
        assert t.cumulative_r == round(cum_check, 3)
        assert t.drawdown_r >= 0.0


# ---------------------------------------------------------------------------
# 2. Regime Transitions & Session Tests
# ---------------------------------------------------------------------------

def test_regime_and_transitions(validator, sample_sequential_records):
    """Verify static regime breakdown, session summary, and sequential transitions."""
    sim_res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    reg_break, sess_break, trans_res = validator.test_regime_and_transitions(sim_res)

    assert len(reg_break) >= 2
    assert len(sess_break) >= 2
    assert len(trans_res) >= 1
    for t in trans_res:
        assert isinstance(t.is_edge_deteriorated, bool)


# ---------------------------------------------------------------------------
# 3. Rolling Performance Windows Tests
# ---------------------------------------------------------------------------

def test_rolling_performance_windows(validator, sample_sequential_records):
    """Verify rolling performance calculations across 25, 50, 100 trade windows."""
    sim_res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    roll_res = validator.calculate_rolling_windows(sim_res)
    assert len(roll_res) == 4
    w25 = next(r for r in roll_res if r.window_size == 25)
    assert w25.total_windows_evaluated == 75 - 25 + 1
    assert 0.0 <= w25.rolling_stability_score <= 100.0


# ---------------------------------------------------------------------------
# 4. Calibration Drift & ECE Tests
# ---------------------------------------------------------------------------

def test_calibration_drift(validator, sample_sequential_records):
    """Verify Expected Calibration Error (ECE) and Brier scores between eras."""
    sim_res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    calib = validator.test_calibration_drift(sim_res)
    assert calib.train_ece >= 0.0
    assert calib.holdout_ece >= 0.0
    assert calib.calibration_stability_verdict in ("STABLE", "MODERATE DRIFT", "SEVERE DRIFT")
    assert len(calib.bins) == 5


# ---------------------------------------------------------------------------
# 5. Strategy Degradation Detector Tests
# ---------------------------------------------------------------------------

def test_strategy_degradation_detector(validator, sample_sequential_records):
    """Verify multi-condition degradation trigger evaluation."""
    sim_res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    degrad = validator.detect_strategy_degradation(sim_res)
    assert degrad.total_trades_monitored == 75 - 50
    assert degrad.degraded_time_pct >= 0.0
    assert "RESILIENCE" in degrad.degradation_resilience_verdict


# ---------------------------------------------------------------------------
# 6. Monte Carlo Simulation Tests
# ---------------------------------------------------------------------------

def test_monte_carlo_simulation_stress(validator, sample_sequential_records):
    """Verify 10,000 Monte Carlo bootstrap random-walk metrics."""
    sim_res = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test simulation",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    mc = validator.run_monte_carlo_simulations(sim_res)
    assert mc.simulations_count == 10000
    assert mc.percentile_1st_r <= mc.percentile_5th_r <= mc.median_final_r
    assert mc.median_max_drawdown_r <= mc.percentile_95th_max_drawdown_r <= mc.percentile_99th_max_drawdown_r
    assert 0.0 <= mc.prob_negative_final_r_pct <= 100.0


# ---------------------------------------------------------------------------
# 7. Combined Portfolio Simulation Tests
# ---------------------------------------------------------------------------

def test_combined_portfolio_simulation(validator, sample_sequential_records):
    """Verify multi-asset chronological merging, correlation, and diversification benefit."""
    sim_btc = validator.simulate_sequential_trades(
        strategy_id="TEST-BTC-SELL",
        asset="BTC/USD",
        direction="SELL",
        min_prob=0.40,
        condition_name="ALL",
        description="Test BTC",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )
    sim_xau = validator.simulate_sequential_trades(
        strategy_id="TEST-XAU-BUY",
        asset="XAU/USD",
        direction="BUY",
        min_prob=0.40,
        condition_name="ALL",
        description="Test XAU",
        condition_fn=lambda o: True,
        records=sample_sequential_records,
    )

    port = validator.simulate_combined_portfolio(
        portfolio_id="TEST_PORTFOLIO",
        btc_sim=sim_btc,
        xau_sim=sim_xau,
    )

    assert port.total_trades_count == sim_btc.total_trades + sim_xau.total_trades
    assert port.combined_total_r == round(sim_btc.total_cumulative_r + sim_xau.total_cumulative_r, 2)
    assert port.sum_standalone_dd_r == round(sim_btc.max_drawdown_r + sim_xau.max_drawdown_r, 2)
    assert port.concentration_risk_grade in ("LOW (True Diversification)", "MODERATE", "HIGH CONCENTRATION RISK")


# ---------------------------------------------------------------------------
# 8. Full Validation Suite Integration & Report Export Tests
# ---------------------------------------------------------------------------

def test_full_validation_suite_and_report_export(validator):
    """Verify execution of full validation suite and generation of all 6 reports."""
    paths = validator.export_all_reports()

    for k, p in paths.items():
        assert os.path.exists(p), f"Missing report {k} at {p}"

    # Verify JSON structure
    with open(paths["main_json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "candidate_profiles" in data
    assert "primary_portfolio" in data
    assert "research_questions_answers" in data

    # Verify Markdown contents
    with open(paths["main_md"], "r", encoding="utf-8") as f:
        md = f.read()
    assert "# Regime-Aware Sequential Validation Research Report" in md
    assert "## 1. Master Qualification Summary" in md
    assert "## 4. Multi-Asset Combined Portfolio Simulation" in md
    assert "## 5. Answers to the 10 Mandatory Validation Questions" in md
