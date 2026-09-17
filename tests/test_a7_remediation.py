"""
tests/test_a7_remediation.py

Verifies remediation of A7 Runtime API Verification findings:
- F-01: Cross-asset AI fallback leakage during Gemini cooldown (symbol isolation)
- F-02: Non-idempotent GET /api/v1/decision persistent side effect (Hook 1 record_signal)
- H-01: GET decision evaluation triggering persistent ML shadow/candle writes
"""
import numpy as np
import pytest
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.models.trading_decision import TradingDecision, TradingSignal
from tests.test_ai_analysis import make_dummy_technical_response, make_multi_timeframe_input
from src.services.ai.fallback_provider import FallbackAIProvider


# ---------------------------------------------------------------------------
# F-01 Tests: AI Service Symbol Isolation Under Cooldown
# ---------------------------------------------------------------------------

def test_f01_ai_service_symbol_scoped_cache_isolation():
    """
    Verify that AI service stores and retrieves cached/cooldown responses
    strictly per-symbol so BTC responses never leak into XAU queries.
    """
    from src.services.ai_service import AIMarketAnalysisService

    svc = AIMarketAnalysisService()

    # Generate valid schema-compliant responses
    raw_xau = make_multi_timeframe_input(conflict=False)
    xau_resp = FallbackAIProvider().generate_analysis(raw_xau)
    xau_resp.symbol = "XAU-USD-SPOT"

    raw_btc = make_multi_timeframe_input(conflict=False)
    raw_btc.symbol = "BTC-USD-SPOT"
    btc_resp = FallbackAIProvider().generate_analysis(raw_btc)
    btc_resp.symbol = "BTC-USD-SPOT"

    # Use backward-compatible property setter and symbol dictionary
    svc._last_successful_analysis = btc_resp
    assert svc._last_successful_by_symbol.get("BTC-USD-SPOT") is btc_resp

    svc._last_successful_by_symbol["XAU-USD-SPOT"] = xau_resp

    # Verify per-symbol isolation
    assert svc._last_successful_by_symbol.get("BTC-USD-SPOT").symbol == "BTC-USD-SPOT"
    assert svc._last_successful_by_symbol.get("XAU-USD-SPOT").symbol == "XAU-USD-SPOT"

    # Query for an unknown symbol must return None (not leak BTC or XAU)
    assert svc._last_successful_by_symbol.get("ETH-USD") is None


def test_f01_fallback_invariant_defense():
    """
    Verify that even if fallback provider or cache had a mismatched symbol,
    the invariant defense in analyze_market catches it and replaces with symbol-matched fallback.
    """
    from src.services.ai_service import AIMarketAnalysisService

    svc = AIMarketAnalysisService()

    # Precondition: Set last successful analysis as BTC
    raw_btc = make_multi_timeframe_input(conflict=False)
    raw_btc.symbol = "BTC-USD-SPOT"
    btc_resp = FallbackAIProvider().generate_analysis(raw_btc)
    btc_resp.symbol = "BTC-USD-SPOT"
    svc._last_successful_by_symbol["BTC-USD-SPOT"] = btc_resp

    with patch.object(svc.settings, "APP_ENV", "production"), \
         patch.object(svc.request_manager, "is_request_allowed", return_value=(False, "COOLDOWN_ACTIVE")), \
         patch.object(svc, "_resolve_provider", return_value=MagicMock()):
        raw_xau = make_multi_timeframe_input(conflict=False)
        raw_xau.symbol = "XAU-USD-SPOT"

        res = svc.analyze_market(symbol="XAU-USD-SPOT", raw_input=raw_xau)

        # Must NOT be BTC
        assert res.symbol == "XAU-USD-SPOT", f"Expected XAU-USD-SPOT, got {res.symbol}"
        assert res.symbol != "BTC-USD-SPOT"


# ---------------------------------------------------------------------------
# F-02 & H-01 Tests: Decision Pipeline Idempotence (No Disk/DB Side Effects on GET)
# ---------------------------------------------------------------------------

def test_f02_get_decision_persist_false_skips_signal_recording():
    """
    Verify that DecisionService._build_decision with persist=False (default)
    does NOT invoke record_signal on get_signal_repository() or resolve_pending_observations.
    """
    from src.services.decision_service import DecisionService

    svc = DecisionService.__new__(DecisionService)
    svc._cache = {}
    svc._ttl = 30
    svc._build_lock = threading.Lock()

    with patch("src.services.decision_service.get_signal_repository") as mock_repo_fn, \
         patch("src.services.decision_service.get_outcome_tracker") as mock_tracker_fn, \
         patch("src.research.ml_shadow.shadow_service.get_ml_shadow_service") as mock_ml_fn:

        mock_repo = MagicMock()
        mock_repo_fn.return_value = mock_repo
        mock_tracker = MagicMock()
        mock_tracker_fn.return_value = mock_tracker
        mock_ml = MagicMock()
        mock_ml_fn.return_value = mock_ml

        # Set up stub decision returned by engine
        stub_decision = MagicMock(spec=TradingDecision)
        stub_decision.decision = TradingSignal.BUY
        stub_decision.signal_strength = 75
        stub_decision.confidence = 75
        stub_decision.technical_score = 75
        stub_decision.gemini_score = 70
        stub_decision.stop_loss = 2640.0
        stub_decision.take_profit_1 = 2670.0
        stub_decision.take_profit_2 = 2690.0
        stub_decision.market_regime = "TRENDING"
        stub_decision.data_quality = "HIGH"
        stub_decision.gate_direction = "NONE"
        stub_decision.quality_gate_status = "PASSED"
        stub_decision.signal_contributors = []
        stub_decision.calibrated_probability = 65.0
        stub_decision.composite_score = 0.75
        stub_decision.historical_evidence_status = "AVAILABLE"
        stub_decision.reasons = []
        stub_decision.warnings = []
        stub_decision.top_confirmations = []
        stub_decision.top_conflicts = []

        svc._engine = MagicMock()
        svc._engine.evaluate = MagicMock(return_value=(stub_decision, MagicMock()))

        raw_xau = make_multi_timeframe_input(conflict=False)
        xau_resp = FallbackAIProvider().generate_analysis(raw_xau)
        svc._ai_service = MagicMock()
        svc._ai_service.analyze_market = MagicMock(return_value=xau_resp)

        svc._tech_service = MagicMock()
        svc._tech_service.analyze = MagicMock(
            side_effect=lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
        )
        svc._hourly_strong_signals = {}

        # Test with persist=False
        svc._build_decision(symbol="XAU-USD-SPOT", force_refresh=True, persist=False)

        # record_signal MUST NOT be called
        mock_repo.record_signal.assert_not_called()
        mock_tracker.label_outcomes.assert_not_called()

        # ml_shadow generate_prediction MUST receive persist=False
        mock_ml.generate_prediction.assert_called_once()
        _, kwargs = mock_ml.generate_prediction.call_args
        assert kwargs.get("persist") is False, f"Expected persist=False, got {kwargs.get('persist')}"

        # resolve_pending_observations MUST NOT be called
        mock_ml.resolve_pending_observations.assert_not_called()


def test_f02_get_decision_persist_true_enables_recording():
    """
    Verify that when persist=True is explicitly passed, record_signal IS called for actionable signals.
    """
    from src.services.decision_service import DecisionService

    svc = DecisionService.__new__(DecisionService)
    svc._cache = {}
    svc._ttl = 30
    svc._build_lock = threading.Lock()

    with patch("src.services.decision_service.get_signal_repository") as mock_repo_fn, \
         patch("src.services.decision_service.get_outcome_tracker") as mock_tracker_fn, \
         patch("src.research.ml_shadow.shadow_service.get_ml_shadow_service") as mock_ml_fn:

        mock_repo = MagicMock()
        mock_repo_fn.return_value = mock_repo
        mock_tracker = MagicMock()
        mock_tracker_fn.return_value = mock_tracker
        mock_ml = MagicMock()
        mock_ml_fn.return_value = mock_ml

        stub_decision = MagicMock(spec=TradingDecision)
        stub_decision.decision = TradingSignal.BUY
        stub_decision.signal_strength = 75
        stub_decision.confidence = 75
        stub_decision.technical_score = 75
        stub_decision.gemini_score = 70
        stub_decision.stop_loss = 2640.0
        stub_decision.take_profit_1 = 2670.0
        stub_decision.take_profit_2 = 2690.0
        stub_decision.market_regime = "TRENDING"
        stub_decision.data_quality = "HIGH"
        stub_decision.gate_direction = "NONE"
        stub_decision.quality_gate_status = "PASSED"
        stub_decision.signal_contributors = []
        stub_decision.calibrated_probability = 65.0
        stub_decision.composite_score = 0.75
        stub_decision.historical_evidence_status = "AVAILABLE"
        stub_decision.reasons = []
        stub_decision.warnings = []
        stub_decision.top_confirmations = []
        stub_decision.top_conflicts = []
        stub_decision.mtf_alignment_summary = "Full Bullish Alignment"

        svc._engine = MagicMock()
        svc._engine.evaluate = MagicMock(return_value=(stub_decision, MagicMock()))

        raw_xau = make_multi_timeframe_input(conflict=False)
        xau_resp = FallbackAIProvider().generate_analysis(raw_xau)
        svc._ai_service = MagicMock()
        svc._ai_service.analyze_market = MagicMock(return_value=xau_resp)

        svc._tech_service = MagicMock()
        svc._tech_service.analyze = MagicMock(
            side_effect=lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
        )
        mock_c = MagicMock()
        mock_c.timestamp = "2026-09-15T12:00:00Z"
        mock_c.is_closed = True
        mock_c.high = 2655.0
        mock_c.low = 2645.0
        mock_c.close = 2650.0
        svc._tech_service.market_service.get_candles.return_value = MagicMock(candles=[mock_c])
        svc._hourly_strong_signals = {}

        # Test with persist=True
        svc._build_decision(symbol="XAU-USD-SPOT", force_refresh=True, persist=True)

        # record_signal MUST be called
        mock_repo.record_signal.assert_called_once_with(stub_decision)
        mock_tracker.label_outcomes.assert_called_once()

        # ml_shadow generate_prediction MUST receive persist=True
        mock_ml.generate_prediction.assert_called_once()
        _, kwargs = mock_ml.generate_prediction.call_args
        assert kwargs.get("persist") is True, f"Expected persist=True, got {kwargs.get('persist')}"


def test_h01_shadow_service_generate_prediction_persist_flag():
    """
    Verify that MLShadowService.generate_prediction with persist=False
    computes the prediction object in memory but does NOT call store.save_observation().
    """
    from src.research.ml_shadow.shadow_service import MLShadowService

    svc = MLShadowService.__new__(MLShadowService)
    svc._models = {"BTC": MagicMock(), "XAU": MagicMock()}
    svc._preprocessors = {"BTC": MagicMock(), "XAU": MagicMock()}
    svc._model_names = {"BTC": "BTC_Classifier", "XAU": "XAU_Classifier"}
    svc.store = MagicMock()

    # Mock model and preprocessor behavior using numpy arrays
    mock_model = svc._models["BTC"]
    mock_model.predict_proba.return_value = np.array([[0.35, 0.65]])
    mock_prep = svc._preprocessors["BTC"]
    mock_prep.transform.return_value = np.zeros((1, 22))

    # Call with persist=False
    pred = svc.generate_prediction(
        symbol="BTC-USD-SPOT",
        timestamp_t0=datetime.now(timezone.utc).isoformat(),
        production_decision="BUY",
        confluence_score=70,
        technical_score=68,
        gemini_score=65,
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit_1=97000.0,
        take_profit_2=99000.0,
        session="NY",
        market_regime="TRENDING",
        contributor_scores={},
        contributor_biases={},
        persist=False
    )

    assert pred is not None
    assert pred.ml_probability == 0.65
    assert pred.ml_predicted_class == 1
    # MUST NOT call save_observation
    svc.store.save_observation.assert_not_called()

    # Now call with persist=True
    pred_persisted = svc.generate_prediction(
        symbol="BTC-USD-SPOT",
        timestamp_t0=datetime.now(timezone.utc).isoformat(),
        production_decision="BUY",
        confluence_score=70,
        technical_score=68,
        gemini_score=65,
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit_1=97000.0,
        take_profit_2=99000.0,
        session="NY",
        market_regime="TRENDING",
        contributor_scores={},
        contributor_biases={},
        persist=True
    )
    assert pred_persisted is not None
    svc.store.save_observation.assert_called_once_with(pred_persisted)
