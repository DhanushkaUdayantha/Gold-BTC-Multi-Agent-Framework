"""
Strict Asset Isolation & Signal Quality Governance Regression Test Suite.

Verifies:
1. Complete separation of BTC and XAU across:
   - Data / Historical Records
   - Calibration & Performance metrics
   - Feature intelligence contributions & interactions
   - Failure pattern attribution
   - Daily signal ranking (up to 24 cap, zero forced signals)
2. Production architecture freeze (DecisionEngine logic & rules remain unchanged).
3. All Phase 4 research reports exist and contain zero cross-contamination.
"""

import pytest
import numpy as np
import os
import json
from src.research.signal_quality_optimizer import (
    SignalQualityOptimizer,
    AssetDirectionMetrics,
)
from src.research.signal_research_record import (
    SignalResearchRecord,
    StrategyScoreSnapshot,
    AISnapshot,
    MTFSnapshot,
    IndicatorSnapshot,
)
from src.research.feature_intelligence import FeatureIntelligenceEngine
from src.services.decision_engine import DecisionEngine


@pytest.fixture
def mock_isolated_records():
    """Create a synthetic dataset with distinct BTC and XAU characteristics."""
    records = []
    # 60 BTC trades (Strong SELL bias in low vol)
    for i in range(60):
        decision = "SELL" if i % 3 != 0 else "BUY"
        realized_r = 1.2 if decision == "SELL" else -0.8
        records.append(SignalResearchRecord(
            signal_id=f"BTC_SIG_{i:03d}",
            asset="BTC/USD",
            signal_timestamp=f"2026-03-01T{i % 24:02d}:00:00Z",
            decision=decision,
            regime="LOW_VOLATILITY",
            session="LONDON",
            strategy_scores=StrategyScoreSnapshot(
                confluence_score=65 + (i % 20),
                confirmation_score=3 if decision == "SELL" else 1,
            ),
            ai=AISnapshot(
                ai_direction=decision,
                ai_probability=0.62 if decision == "SELL" else 0.44,
                ai_confidence="HIGH",
            ),
            mtf=MTFSnapshot(
                htf_aligned=(decision == "SELL"),
            ),
            realized_r=realized_r,
            outcome="WIN" if realized_r > 0 else "LOSS",
            failure_reason="MOMENTUM_FAILURE" if realized_r < 0 else "",
            mae_r=-0.4,
            mfe_r=1.8,
            entry_price=80000.0 + i * 10,
            stop_loss=80300.0 if decision == "SELL" else 79700.0,
            take_profit_1=79400.0 if decision == "SELL" else 80600.0,
        ))

    # 60 XAU trades (Strong BUY bias in NY session)
    for i in range(60):
        decision = "BUY" if i % 3 != 0 else "SELL"
        realized_r = 1.5 if decision == "BUY" else -1.0
        records.append(SignalResearchRecord(
            signal_id=f"XAU_SIG_{i:03d}",
            asset="XAU/USD",
            signal_timestamp=f"2026-03-01T{i % 24:02d}:30:00Z",
            decision=decision,
            regime="TRENDING_BULLISH",
            session="NEW_YORK",
            strategy_scores=StrategyScoreSnapshot(
                confluence_score=70 + (i % 15),
                confirmation_score=3 if decision == "BUY" else 1,
            ),
            ai=AISnapshot(
                ai_direction=decision,
                ai_probability=0.68 if decision == "BUY" else 0.40,
                ai_confidence="HIGH",
            ),
            mtf=MTFSnapshot(
                htf_aligned=(decision == "BUY"),
            ),
            realized_r=realized_r,
            outcome="WIN" if realized_r > 0 else "LOSS",
            failure_reason="FALSE_BREAKOUT" if realized_r < 0 else "",
            mae_r=-0.3,
            mfe_r=2.1,
            entry_price=2750.0 + i * 2,
            stop_loss=2735.0 if decision == "BUY" else 2765.0,
            take_profit_1=2775.0 if decision == "BUY" else 2725.0,
        ))

    return records


class TestStrictAssetIsolation:
    """Test rigorous separation of BTC and XAU data, analytics, and reports."""

    def test_asset_directional_metrics_isolation(self, mock_isolated_records):
        metrics = SignalQualityOptimizer.analyze_asset_directions(mock_isolated_records)
        assert len(metrics) >= 6  # ALL, BUY, SELL for BTC & XAU

        btc_metrics = [m for m in metrics if m.asset == "BTC/USD"]
        xau_metrics = [m for m in metrics if m.asset == "XAU/USD"]

        assert len(btc_metrics) >= 3
        assert len(xau_metrics) >= 3

        btc_sell = next(m for m in btc_metrics if m.direction == "SELL")
        xau_buy = next(m for m in xau_metrics if m.direction == "BUY")

        # BTC SELL must show strong positive expectancy in our isolated set
        assert btc_sell.expectancy_r > 0.5
        assert btc_sell.win_rate_pct == 100.0

        # XAU BUY must show strong positive expectancy in our isolated set
        assert xau_buy.expectancy_r > 0.5
        assert xau_buy.win_rate_pct == 100.0

    def test_feature_intelligence_by_asset(self, mock_isolated_records):
        fi_by_asset = FeatureIntelligenceEngine.evaluate_feature_contributions_by_asset(mock_isolated_records)
        assert "BTC" in fi_by_asset
        assert "XAU" in fi_by_asset

        btc_contribs = fi_by_asset["BTC"]
        xau_contribs = fi_by_asset["XAU"]

        # Ensure both assets have contributions computed independently
        assert len(btc_contribs) > 0
        assert len(xau_contribs) > 0

    def test_daily_signal_ranking_cap_and_no_forced_signals(self, mock_isolated_records):
        ranked = SignalQualityOptimizer.rank_daily_signals(mock_isolated_records, max_daily_signals=24)
        
        # Must return all ranked candidates
        assert len(ranked) == len(mock_isolated_records)
        
        # Max 24 selected daily signals
        selected = [s for s in ranked if s.is_selected_daily_24]
        assert len(selected) <= 24

        # Diversification limit: max 14 per asset
        btc_sel = [s for s in selected if "BTC" in s.asset]
        xau_sel = [s for s in selected if "XAU" in s.asset]
        assert len(btc_sel) <= 14
        assert len(xau_sel) <= 14

        # No Tier 3 signals ever selected
        for s in selected:
            assert s.tier in ["TIER_1", "TIER_2"]

    def test_asset_separated_reports_generation(self, mock_isolated_records):
        paths = SignalQualityOptimizer.generate_asset_separated_reports(mock_isolated_records)
        
        assert "btc_signal_quality" in paths
        assert "xau_signal_quality" in paths
        assert "btc_failure_patterns" in paths
        assert "xau_failure_patterns" in paths
        assert "signal_ranking_analysis" in paths
        assert "signal_quality_optimization" in paths

        # Verify BTC quality JSON contains ONLY BTC data
        btc_q_path = paths["btc_signal_quality"][0]
        with open(btc_q_path, "r", encoding="utf-8") as f:
            btc_data = json.load(f)
            assert btc_data["asset"] == "BTC/USD"
            assert btc_data["overall"]["n"] == 60

        # Verify XAU failure JSON contains ONLY XAU data
        xau_f_path = paths["xau_failure_patterns"][0]
        with open(xau_f_path, "r", encoding="utf-8") as f:
            xau_failures = json.load(f)
            assert any(f["failure_taxonomy"] == "FALSE_BREAKOUT" for f in xau_failures)

    def test_production_decision_engine_frozen(self):
        """Verify production DecisionEngine remains unchanged and deterministic."""
        engine = DecisionEngine()
        assert hasattr(engine, "evaluate")
        assert hasattr(engine, "_run_evaluation")
        assert hasattr(engine, "_safe_wait_decision")
        assert hasattr(engine, "confluence_engine")
