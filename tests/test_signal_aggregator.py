"""
Unit tests for SignalAggregator — Phase 5c-g Evidence Fusion Engine.

Verifies:
1. Base weights match exact approved values (25/27/26/22 BTC, 27/26/24/23 XAU).
2. Traceability invariant: sum(component_contributions.values()) == net_score.
3. Conflict invariance: opposing directional forces produce WAIT with percentage=None.
4. Dynamic proportional re-weighting when optional components are missing.
5. Insufficient active component coverage (< 50%) aborts safely to WAIT.
6. Semantic separation: calibrated_probability is distinct from confluence percentage.
7. No circular aggregation: static AST import scan ensures upstream never imports aggregator.
"""
import ast
import os
import pytest

from src.models.trading_decision import (
    NowMarketSignal,
    HistoricalMarketSignal,
    ValidatedStrategyEvaluation,
)
from src.services.signal_aggregator import (
    SignalAggregator,
    BASE_WEIGHTS_BTC,
    BASE_WEIGHTS_XAU,
)


# ─── Test 1: Exact Base Weights ──────────────────────────────────────────────

def test_exact_base_weights_match_methodology():
    """Verify base weights match exact formula-derived percentages."""
    btc_w = SignalAggregator.get_base_weights("BTC/USD")
    assert btc_w["NOW_MARKET_TECHNICAL"] == 0.25
    assert btc_w["HISTORICAL_EVIDENCE"] == 0.27
    assert btc_w["ML_SHADOW_MODEL"] == 0.26
    assert btc_w["VALIDATED_STRATEGY"] == 0.22
    assert pytest.approx(sum(btc_w.values()), 0.0001) == 1.0

    xau_w = SignalAggregator.get_base_weights("XAU/USD")
    assert xau_w["NOW_MARKET_TECHNICAL"] == 0.27
    assert xau_w["HISTORICAL_EVIDENCE"] == 0.26
    assert xau_w["ML_SHADOW_MODEL"] == 0.24
    assert xau_w["VALIDATED_STRATEGY"] == 0.23
    assert pytest.approx(sum(xau_w.values()), 0.0001) == 1.0


# ─── Test 2: Contributor Traceability Invariant ───────────────────────────────

def test_contributor_traceability_sum_equals_score():
    """Every point in net score must trace back to the sum of effective contributions."""
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=80,
        strength="VERY STRONG",
        technical_score=75,
        gemini_score=8,
    )
    hist_sig = HistoricalMarketSignal(
        signal="BUY",
        percentage=65,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=120,
        calibrated_probability=0.62,
    )
    strat = ValidatedStrategyEvaluation(
        strategy_id="XAU-BUY-P42-VWAP_ALIGNED",
        strategy_name="XAU BUY VWAP",
        qualified=True,
        direction="BUY",
        validation_score=84,
        degradation_status="NORMAL",
    )

    sig = SignalAggregator.aggregate(
        symbol="XAU/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.68,
        ml_predicted_class=1,
        validated_strategy=strat,
    )

    assert sig.signal == "BUY"
    assert sig.conflict_detected is False
    assert sig.component_contributions is not None

    # Traceability check: sum of points equals net score
    expected_sum = sum(sig.component_contributions.values())
    assert sig.overall_evidence_score == round(abs(expected_sum))
    assert sig.percentage == round(abs(expected_sum))

    # Traceability ledger check: each contributor item has expected keys
    assert len(sig.contributors) == 4
    for c in sig.contributors:
        assert "component_id" in c
        assert "effective_points" in c
        assert "effective_weight" in c
        assert "directional_bias" in c
        assert c["status"] == "ACTIVE"


# ─── Test 3: Conflict Invariance (No 51% Override) ───────────────────────────

def test_directional_conflict_enforces_wait_with_none_percentage():
    """Opposing directional forces (>= 0.25 weight each) must yield WAIT and percentage=None."""
    # Bullish Now Market
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=85,
        strength="VERY STRONG",
    )
    # Bearish Historical Evidence
    hist_sig = HistoricalMarketSignal(
        signal="SELL",
        percentage=75,
        strength="STRONG",
        status="AVAILABLE",
        sample_size=150,
        calibrated_probability=0.72,
    )

    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
    )

    assert sig.signal == "WAIT"
    assert sig.percentage is None
    assert sig.strength == "CONFLICT"
    assert sig.conflict_detected is True
    assert sig.overall_evidence_score is None
    assert any("Directional conflict" in r for r in sig.reasons)


# ─── Test 4: Dynamic Proportional Re-weighting ───────────────────────────────

def test_dynamic_reweighting_when_components_missing():
    """When optional components are missing, active weights re-normalize to 1.0."""
    now_sig = NowMarketSignal(
        signal="SELL",
        percentage=70,
        strength="STRONG",
    )

    # Historical signal has insufficient sample size (< 25)
    hist_sig = HistoricalMarketSignal(
        signal="SELL",
        percentage=60,
        strength="MODERATE",
        status="INSUFFICIENT_SAMPLE",
        sample_size=12,
        calibrated_probability=0.55,
    )

    # Only Now Market (nominal 0.25) and ML Model (nominal 0.26) active on BTC
    # Total active nominal = 0.51 >= 0.50 (passes minimum coverage)
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.35,  # Bearish (class 0)
        ml_predicted_class=0,
    )

    assert sig.signal == "SELL"
    assert sig.conflict_detected is False

    # Effective weights must sum to 1.0 across active components
    active_weights_sum = sum(sig.component_weights.values())
    assert pytest.approx(active_weights_sum, 0.001) == 1.0

    # Inactive components must have effective_weight == 0.0
    assert sig.component_weights["HISTORICAL_EVIDENCE"] == 0.0
    assert sig.component_weights["VALIDATED_STRATEGY"] == 0.0

    # Active components proportionally scaled: 0.25 / 0.51 and 0.26 / 0.51
    assert pytest.approx(sig.component_weights["NOW_MARKET_TECHNICAL"], 0.001) == round(0.25 / 0.51, 4)
    assert pytest.approx(sig.component_weights["ML_SHADOW_MODEL"], 0.001) == round(0.26 / 0.51, 4)


# ─── Test 5: Insufficient Active System Coverage ─────────────────────────────

def test_insufficient_active_coverage_aborts_to_wait():
    """If available components cover less than minimum required nominal weight, abort to WAIT."""
    # Zero active components available
    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=None,
        historical_signal=None,
        ml_probability=None,
        validated_strategy=None,
    )

    assert sig.signal == "WAIT"
    assert sig.percentage is None
    assert any("insufficient active analytical components" in r for r in sig.reasons)


# ─── Test 6: Semantic Separation ─────────────────────────────────────────────

def test_semantic_separation_of_probability_and_score():
    """Calibrated probability must be distinct from heuristic confluence percentage."""
    now_sig = NowMarketSignal(
        signal="BUY",
        percentage=82,
        strength="VERY STRONG",
    )
    hist_sig = HistoricalMarketSignal(
        signal="BUY",
        percentage=68,
        status="AVAILABLE",
        sample_size=100,
        calibrated_probability=0.64,
    )

    sig = SignalAggregator.aggregate(
        symbol="BTC/USD",
        now_signal=now_sig,
        historical_signal=hist_sig,
        ml_probability=0.68,
        ml_predicted_class=1,
    )

    # Percentage is an integer confluence score [20, 100]
    assert isinstance(sig.percentage, int)
    assert 20 <= sig.percentage <= 100

    # Calibrated probability is a float in [0.0, 1.0] synthesized via Bayesian log-odds
    assert isinstance(sig.calibrated_probability, float)
    assert 0.0 < sig.calibrated_probability < 1.0


# ─── Test 7: No Circular Aggregation (AST Import Scan) ────────────────────────

def test_no_circular_aggregation_upstream_never_imports_aggregator():
    """Static AST scan ensuring upstream modules never import signal_aggregator."""
    upstream_dirs = [
        "src/services/technical_service.py",
        "src/services/ai_service.py",
        "src/services/decision_engine.py",
        "src/services/signal_repository.py",
        "src/services/validated_strategy_layer.py",
        "src/research/ml_shadow/shadow_service.py",
        "src/research/ml_shadow/shadow_store.py",
    ]

    for rel_path in upstream_dirs:
        abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), rel_path)
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=abs_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        assert "signal_aggregator" not in n.name, f"Circular import in {rel_path}: {n.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert "signal_aggregator" not in node.module, f"Circular import in {rel_path}: {node.module}"
