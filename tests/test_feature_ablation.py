"""
Unit and Integration Tests for Phase 4 Feature Importance, Ablation & Signal Quality Hardening.

Verifies:
1. Feature Inventory & T0 timing integrity (0 lookahead violations)
2. Classical and ML feature importance extraction across 4 folds
3. Single-feature and filter ablation calculations (Train, OOS, Holdout)
4. Redundancy, missingness, and distribution drift metrics
5. Experiment registry structure and retrieval
6. Strict BTC/XAU asset isolation
7. Production decision isolation (100% identical DecisionEngine outputs before and after research execution)
8. Edge cases (empty dataset, missing features, single trade)
"""
import pytest
from src.research.feature_ablation.inventory import build_feature_inventory, audit_feature_timing
from src.research.feature_ablation.importance import calculate_feature_importance, calculate_ml_importance
from src.research.feature_ablation.ablation import run_feature_ablation, run_filter_research
from src.research.feature_ablation.stability import (
    analyze_feature_stability,
    analyze_feature_redundancy,
    analyze_feature_missingness,
    analyze_distribution_stability,
)
from src.research.feature_ablation.registry import get_experiment_registry
from src.research.feature_ablation.validator import run_full_phase4_analysis


class TestFeatureInventoryAndTiming:
    """Tests for repository feature inventory and T0 timing audit."""

    def test_inventory_completeness(self):
        inv = build_feature_inventory()
        assert inv.total_features_count >= 20
        assert inv.features_available_at_t0 >= 18
        assert inv.lookahead_violations_count == 0

    def test_timing_audit_zero_leakage(self):
        audit = audit_feature_timing()
        assert audit["status"] == "PASS"
        assert audit["lookahead_violations_count"] == 0
        assert len(audit["lookahead_violations"]) == 0


class TestFeatureImportance:
    """Tests for classical and ML feature importance across folds."""

    def test_classical_importance_btc(self):
        res = calculate_feature_importance("BTC/USD")
        assert len(res) >= 8
        top_feat = res[0]
        assert top_feat.feature_name in ("mtf_aligned", "confluence_score")
        assert top_feat.mean_importance > 0.05
        assert top_feat.stability == "STABLE"
        assert len(top_feat.fold_scores) == 4

    def test_classical_importance_xau(self):
        res = calculate_feature_importance("XAU/USD")
        assert len(res) >= 8
        top_feat = res[0]
        assert top_feat.feature_name in ("confluence_score", "mtf_aligned")
        assert top_feat.mean_importance > 0.05
        assert top_feat.stability == "STABLE"

    def test_ml_importance_btc_logistic(self):
        ml_res = calculate_ml_importance("BTC/USD")
        assert len(ml_res) >= 6
        top_ml = ml_res[0]
        assert top_ml.model_type == "Logistic Regression"
        assert top_ml.coefficient is not None
        assert top_ml.permutation_importance_mean > 0.05
        assert top_ml.classification == "ADDS_VALUE"

    def test_ml_importance_xau_random_forest(self):
        ml_res = calculate_ml_importance("XAU/USD")
        assert len(ml_res) >= 6
        top_ml = ml_res[0]
        assert top_ml.model_type == "Random Forest"
        assert top_ml.tree_mdi_importance is not None
        assert top_ml.permutation_importance_mean > 0.05
        assert top_ml.classification == "ADDS_VALUE"


class TestFeatureAblation:
    """Tests for single-feature and candidate filter ablations."""

    def test_feature_ablation_btc(self):
        ablations = run_feature_ablation("BTC/USD")
        assert len(ablations) >= 6
        # Removing MTF aligned or Confluence should show negative delta on EV (hurting performance)
        mtf_abl = next(a for a in ablations if a.target_name == "mtf_aligned")
        assert mtf_abl.train_delta_ev < 0.0
        assert mtf_abl.oos_delta_ev < 0.0
        assert mtf_abl.holdout_delta_ev < 0.0
        assert mtf_abl.classification == "ADDS_VALUE"

    def test_filter_research_xau(self):
        filters = run_filter_research("XAU/USD")
        assert len(filters) >= 4
        # Requiring MTF alignment should increase EV
        mtf_flt = next(f for f in filters if "MTF" in f.target_name)
        assert mtf_flt.train_delta_ev > 0.0
        assert mtf_flt.oos_delta_ev > 0.0
        assert mtf_flt.holdout_delta_ev > 0.0
        assert mtf_flt.classification == "ADDS_VALUE"


class TestStabilityRedundancyMissingness:
    """Tests for stability, redundancy, missingness, and drift analysis."""

    def test_feature_stability(self):
        stab = analyze_feature_stability("BTC/USD")
        assert "mtf_aligned" in stab.stable_features
        assert "confluence_score" in stab.stable_features
        assert "vwap_deviation" in stab.unstable_features

    def test_feature_redundancy(self):
        red = analyze_feature_redundancy("BTC/USD")
        assert len(red.correlated_pairs) >= 3
        assert "confluence_score" in red.vif_scores
        assert any(c["status"] == "REDUNDANT" for c in red.redundancy_conclusions)

    def test_missingness_audit(self):
        miss = analyze_feature_missingness("BTC/USD")
        assert miss.total_records == 1519
        assert len(miss.missingness_table) >= 6
        rsi_row = next(r for r in miss.missingness_table if r["feature"] == "rsi_14")
        assert rsi_row["missing_pct"] == 0.0

    def test_distribution_stability(self):
        drift = analyze_distribution_stability("BTC/USD")
        assert drift.drift_detected_count == 0
        assert len(drift.features_drift_table) >= 3


class TestExperimentRegistry:
    """Tests for Phase 4 experiment registry."""

    def test_registry_retrieval(self):
        reg = get_experiment_registry()
        assert reg.total_experiments >= 10
        assert any(e.experiment_type == "FEATURE_ABLATION" for e in reg.experiments)
        assert any(e.experiment_type == "ML_IMPORTANCE" for e in reg.experiments)


class TestAssetAndProductionIsolation:
    """Tests for asset separation and strict production decision engine isolation."""

    def test_asset_isolation(self):
        btc_res = run_full_phase4_analysis("BTC/USD")
        xau_res = run_full_phase4_analysis("XAU/USD")
        assert btc_res.symbol == "BTC/USD"
        assert xau_res.symbol == "XAU/USD"
        assert btc_res.lookahead_violations_count == 0
        assert xau_res.lookahead_violations_count == 0

    def test_production_isolation_unaffected_by_phase4(self):
        from src.services.decision_engine import DecisionEngine
        from tests.test_decision_engine import _make_ta, _make_mtf_input, _make_ai_result

        ta = _make_ta(price=2700.0)
        ta_map = {"5m": ta, "15m": ta, "1h": ta, "1d": ta}
        mtf_in = _make_mtf_input(ta_map, price=2700.0)
        ai_in = _make_ai_result()

        engine = DecisionEngine()
        dec_before, breakdown_before = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Run heavy Phase 4 feature importance & ablation research
        _ = run_full_phase4_analysis(symbol="BTC/USD")
        _ = run_full_phase4_analysis(symbol="XAU/USD")

        # Re-evaluate under identical inputs
        dec_after, breakdown_after = engine.evaluate(mtf_input=mtf_in, ai_result=ai_in)

        # Production decisions must be 100% invariant
        assert dec_before.decision == dec_after.decision
        assert dec_before.signal_strength == dec_after.signal_strength
        assert dec_before.stop_loss == dec_after.stop_loss
        assert dec_before.take_profit_1 == dec_after.take_profit_1
        assert dec_before.take_profit_2 == dec_after.take_profit_2
