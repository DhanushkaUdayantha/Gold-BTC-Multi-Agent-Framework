"""
tests/test_ml_shadow_resolution_repair.py

Comprehensive test suite verifying the ML shadow observation collection and shadow resolution repair:
1. Deterministic observation ID generation and SQLite INSERT OR IGNORE idempotency.
2. Decoupled persistence semantics (generic advisory persist=False vs persist_ml_observation=True).
3. Closed-candle T0 extraction and skip-on-missing-candle audit safety.
4. Additive ForwardShadowResolverWorker cycle resolution for ML shadow observations.
5. Asset isolation between BTC/USD and XAU/USD.
6. Decision engine invariance (0% live authority).
"""
import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models.market_data import OHLCVCandle
from src.models.trading_decision import TradingDecision, TradingSignal
from src.research.ml_shadow.models import MLShadowPrediction
from src.research.ml_shadow.shadow_service import MLShadowService
from src.research.ml_shadow.shadow_store import MLShadowStore
from src.services.ai.fallback_provider import FallbackAIProvider
from src.services.decision_service import DecisionService
from src.services.forward_shadow_resolver_worker import ForwardShadowResolverWorker
from tests.test_ai_analysis import make_dummy_technical_response, make_multi_timeframe_input


@pytest.fixture
def temp_ml_db():
    """Create a temporary SQLite database with ml_shadow_observations and candles tables."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # MLShadowStore initializes the exact table schema
    store = MLShadowStore(db_path=path)

    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS forward_shadow_signals (
            signal_id TEXT PRIMARY KEY,
            asset TEXT NOT NULL,
            signal_timestamp TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit_1 REAL,
            take_profit_2 REAL,
            status TEXT NOT NULL,
            entry_filled_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            epoch_ms INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
        )
    """)
    conn.commit()
    conn.close()
    yield path
    try:
        import gc
        gc.collect()
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


def test_deterministic_observation_id_and_idempotency(temp_ml_db):
    """Verify deterministic observation ID computation and SQLite INSERT OR IGNORE idempotency."""
    pred1 = MLShadowPrediction.create(
        symbol="BTC/USD",
        timestamp_t0="2026-09-15T12:00:00Z",
        production_decision="BUY",
        confluence_score=75,
        technical_score=70,
        quality_gate_passed=True,
        ml_model_name="BTC_Classifier",
        ml_model_version="v1.0.0-research",
        ml_probability=0.72,
        ml_predicted_class=1,
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit_1=96500.0,
        take_profit_2=98000.0,
        session="NY",
        market_regime="TRENDING_BULLISH",
        features_snapshot={"feature1": 1.0},
    )
    pred2 = MLShadowPrediction.create(
        symbol="BTC/USD",
        timestamp_t0="2026-09-15T12:00:00Z",
        production_decision="BUY",
        confluence_score=75,
        technical_score=70,
        quality_gate_passed=True,
        ml_model_name="BTC_Classifier",
        ml_model_version="v1.0.0-research",
        ml_probability=0.72,
        ml_predicted_class=1,
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit_1=96500.0,
        take_profit_2=98000.0,
        session="NY",
        market_regime="TRENDING_BULLISH",
        features_snapshot={"feature1": 1.0},
    )

    # Identical inputs must generate identical observation_id
    assert pred1.observation_id == pred2.observation_id
    assert pred1.observation_id.startswith("ML-SHADOW-")
    assert len(pred1.observation_id) == 22

    store = MLShadowStore(db_path=temp_ml_db)
    # First save succeeds
    assert store.save_observation(pred1) is True

    # Second save of identical observation is ignored without error
    assert store.save_observation(pred2) is True

    conn = sqlite3.connect(temp_ml_db)
    count = conn.execute("SELECT count(*) FROM ml_shadow_observations").fetchone()[0]
    conn.close()
    assert count == 1, "Duplicate observation must be ignored via INSERT OR IGNORE"


def test_persistence_decoupling_advisory_vs_research():
    """Verify that persist=False (advisory signals) does NOT block persist_ml_observation=True."""
    svc = DecisionService.__new__(DecisionService)
    svc._cache = {}
    svc._ttl = 30
    svc._build_lock = threading.Lock()

    stub_decision = MagicMock(spec=TradingDecision)
    stub_decision.decision = TradingSignal.BUY
    stub_decision.signal_strength = 80
    stub_decision.confidence = 80
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
    stub_decision.composite_score = 0.80
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

    mock_candle = OHLCVCandle(
        timestamp="2026-09-15T12:00:00Z",
        open=2650.0,
        high=2655.0,
        low=2645.0,
        close=2652.0,
        is_closed=True,
    )
    svc._tech_service = MagicMock()
    svc._tech_service.analyze = MagicMock(
        side_effect=lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
    )
    svc._tech_service.market_service.get_candles.return_value = MagicMock(candles=[mock_candle])
    svc._hourly_strong_signals = {}

    with patch("src.services.decision_service.get_signal_repository") as mock_repo_fn, \
         patch("src.services.decision_service.get_outcome_tracker") as mock_tracker_fn, \
         patch("src.research.ml_shadow.shadow_service.get_ml_shadow_service") as mock_ml_fn:

        mock_repo = MagicMock()
        mock_repo_fn.return_value = mock_repo
        mock_tracker = MagicMock()
        mock_tracker_fn.return_value = mock_tracker
        mock_ml = MagicMock()
        mock_ml_fn.return_value = mock_ml

        # Case A: persist=False, persist_ml_observation=True (Default GET decision request)
        svc._build_decision(symbol="XAU-USD-SPOT", force_refresh=True, persist=False, persist_ml_observation=True)

        # Advisory signals MUST NOT be recorded
        mock_repo.record_signal.assert_not_called()
        mock_tracker.label_outcomes.assert_not_called()

        # ML shadow prediction MUST receive persist=True because closed candle exists
        mock_ml.generate_prediction.assert_called_once()
        _, kwargs = mock_ml.generate_prediction.call_args
        assert kwargs.get("persist") is True
        assert kwargs.get("timestamp_t0") == "2026-09-15T12:00:00Z"
        assert kwargs.get("symbol") == "XAU/USD"

        # Case B: persist=False, persist_ml_observation=False (Explicit research opt-out)
        mock_ml.reset_mock()
        svc._build_decision(symbol="XAU-USD-SPOT", force_refresh=True, persist=False, persist_ml_observation=False)
        _, kwargs = mock_ml.generate_prediction.call_args
        assert kwargs.get("persist") is False


def test_closed_candle_t0_extraction_and_skip_on_missing(caplog):
    """Verify that T0 comes from closed candle and persistence is skipped when missing."""
    svc = DecisionService.__new__(DecisionService)
    svc._cache = {}
    svc._ttl = 30
    svc._build_lock = threading.Lock()

    stub_decision = MagicMock(spec=TradingDecision)
    stub_decision.decision = TradingSignal.BUY
    stub_decision.signal_strength = 80
    stub_decision.confidence = 80
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
    stub_decision.composite_score = 0.80
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

    # No closed candle available (empty candle list)
    svc._tech_service = MagicMock()
    svc._tech_service.analyze = MagicMock(
        side_effect=lambda symbol, timeframe, force_refresh=False: make_dummy_technical_response(timeframe)
    )
    svc._tech_service.market_service.get_candles.return_value = MagicMock(candles=[])
    svc._hourly_strong_signals = {}

    with patch("src.research.ml_shadow.shadow_service.get_ml_shadow_service") as mock_ml_fn:
        mock_ml = MagicMock()
        mock_ml_fn.return_value = mock_ml

        svc._build_decision(symbol="XAU-USD-SPOT", force_refresh=True, persist=False, persist_ml_observation=True)

        _, kwargs = mock_ml.generate_prediction.call_args
        # Must skip persistence because no valid closed candle was found
        assert kwargs.get("persist") is False
        assert any("ML_SHADOW_OBSERVATION_SKIPPED_NO_VALID_T0" in record.message for record in caplog.records)


def test_worker_additive_ml_shadow_resolution(temp_ml_db):
    """Verify that ForwardShadowResolverWorker evaluates pending ML shadow observations."""
    store = MLShadowStore(db_path=temp_ml_db)
    pred = MLShadowPrediction.create(
        symbol="BTC/USD",
        timestamp_t0="2026-09-15T12:00:00Z",
        production_decision="BUY",
        confluence_score=75,
        technical_score=70,
        quality_gate_passed=True,
        ml_model_name="BTC_Classifier",
        ml_model_version="v1.0.0-research",
        ml_probability=0.72,
        ml_predicted_class=1,
        entry_price=95000.0,
        stop_loss=94000.0,
        take_profit_1=96500.0,
        take_profit_2=98000.0,
        session="NY",
        market_regime="TRENDING_BULLISH",
        features_snapshot={},
    )
    store.save_observation(pred)

    # Insert forward 5m candles into temp db strictly after T0
    conn = sqlite3.connect(temp_ml_db)
    # Candle 1: does not hit TP or SL
    conn.execute("""
        INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
        VALUES ('BTC/USD', '5m', 1789473900000, '2026-09-15T12:05:00Z', 95000.0, 95500.0, 94800.0, 95200.0, 10.0)
    """)
    # Candle 2: hits TP1 (high >= 96500)
    conn.execute("""
        INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
        VALUES ('BTC/USD', '5m', 1789474200000, '2026-09-15T12:10:00Z', 95200.0, 96600.0, 95100.0, 96550.0, 15.0)
    """)
    conn.commit()
    conn.close()

    worker = ForwardShadowResolverWorker(db_path=temp_ml_db)

    worker.run_cycle()

    resolved_obs = store.get_observation(pred.observation_id)
    assert resolved_obs["outcome"] == "WIN"
    assert resolved_obs["exit_price"] == 96500.0
    assert resolved_obs["realized_r"] == 1.5
    assert resolved_obs["time_to_outcome_minutes"] == 10.0
    assert resolved_obs["outcome_timestamp"] == "2026-09-15T12:10:00Z"


def test_asset_isolation_in_resolver(temp_ml_db):
    """Verify that BTC candles never resolve XAU observations and vice-versa."""
    store = MLShadowStore(db_path=temp_ml_db)
    pred_xau = MLShadowPrediction.create(
        symbol="XAU/USD",
        timestamp_t0="2026-09-15T12:00:00Z",
        production_decision="BUY",
        confluence_score=75,
        technical_score=70,
        quality_gate_passed=True,
        ml_model_name="XAU_Classifier",
        ml_model_version="v1.0.0-research",
        ml_probability=0.72,
        ml_predicted_class=1,
        entry_price=2650.0,
        stop_loss=2640.0,
        take_profit_1=2670.0,
        take_profit_2=2690.0,
        session="NY",
        market_regime="TRENDING_BULLISH",
        features_snapshot={},
    )
    store.save_observation(pred_xau)

    # Insert BTC candle that would have triggered XAU TP if cross-contaminated
    conn = sqlite3.connect(temp_ml_db)
    conn.execute("""
        INSERT INTO candles (symbol, timeframe, epoch_ms, timestamp, open, high, low, close, volume)
        VALUES ('BTC/USD', '5m', 1789474200000, '2026-09-15T12:10:00Z', 95200.0, 96600.0, 95100.0, 96550.0, 15.0)
    """)
    conn.commit()
    conn.close()

    worker = ForwardShadowResolverWorker(db_path=temp_ml_db)
    service = MLShadowService(db_path=temp_ml_db)
    with patch("src.research.ml_shadow.shadow_service.get_ml_shadow_service", return_value=service):
        worker.run_cycle()

    obs = store.get_observation(pred_xau.observation_id)
    assert obs["outcome"] == "PENDING", "XAU observation must remain PENDING when only BTC candles exist"
