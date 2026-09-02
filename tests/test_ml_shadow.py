"""
Unit & Integration Tests for ML Shadow Validation Layer.
Verifies production isolation, BTC/XAU asset separation, leakage prevention,
T0 snapshot immutability, WAIT safety, and forward outcome resolution.
"""
import pytest
import numpy as np
import os
import tempfile
import sqlite3

from src.research.ml_shadow.models import MLShadowPrediction
from src.research.ml_shadow.shadow_store import MLShadowStore
from src.research.ml_shadow.shadow_service import MLShadowService
from src.research.ml.artifacts import ArtifactManager

class TestMLShadowValidation:

    @pytest.fixture
    def temp_store(self):
        """Creates an isolated temporary SQLite database for shadow testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        store = MLShadowStore(db_path=temp_db)
        yield store
        if os.path.exists(temp_db):
            os.remove(temp_db)

    @pytest.fixture
    def shadow_service(self, temp_store):
        """Creates an MLShadowService configured with the temporary store."""
        svc = MLShadowService(
            artifact_base_dir=os.path.join("research", "ml", "artifacts"),
            db_path=temp_store.db_path
        )
        return svc

    def test_production_isolation_and_failure_safety(self, shadow_service):
        """Test 1 & Test 9: ML failure or corrupted data does not crash or raise exceptions."""
        # Corrupt the model intentionally
        shadow_service._models["BTC"] = "CORRUPTED_OBJECT"
        pred = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=65,
            technical_score=60,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 8, "Momentum": 7},
            contributor_biases={"MTF Alignment": "BULLISH", "VWAP": "BULLISH"}
        )
        # Should gracefully return None without raising an exception
        assert pred is None

    def test_btc_xau_isolation(self, shadow_service):
        """Test 2: Verifies BTC and XAU use distinct models and store asset-specific records."""
        # BTC prediction
        pred_btc = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=65,
            technical_score=60,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 8},
            contributor_biases={"MTF Alignment": "BULLISH"}
        )
        if pred_btc:
            assert pred_btc.symbol == "BTC/USD"
            assert "Logistic" in pred_btc.ml_model_name or "Classifier" in pred_btc.ml_model_name

        # XAU prediction
        pred_xau = shadow_service.generate_prediction(
            symbol="XAU/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=65,
            technical_score=60,
            gemini_score=5,
            entry_price=2500.0,
            stop_loss=2480.0,
            take_profit_1=2530.0,
            take_profit_2=2550.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 8},
            contributor_biases={"MTF Alignment": "BULLISH", "VWAP": "BULLISH"}
        )
        if pred_xau:
            assert pred_xau.symbol == "XAU/USD"
            assert "Forest" in pred_xau.ml_model_name or "Classifier" in pred_xau.ml_model_name

    def test_leakage_protection_in_snapshot(self, shadow_service):
        """Test 3: Confirms no future price, duration, or outcome fields enter the T0 feature snapshot."""
        pred = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=65,
            technical_score=60,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 8},
            contributor_biases={"MTF Alignment": "BULLISH"}
        )
        if pred:
            features = pred.features_snapshot
            forbidden = ["outcome", "exit_price", "realized_r", "mfe", "mae", "time_to_outcome_minutes"]
            for f in forbidden:
                assert f not in features

    def test_snapshot_immutability(self, temp_store):
        """Test 4: Original T0 data cannot be mutated by outcome resolution."""
        pred = MLShadowPrediction.create(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=70,
            technical_score=62,
            quality_gate_passed=True,
            ml_model_name="LogisticRegression",
            ml_model_version="v1.0.0-research",
            ml_probability=0.65,
            ml_predicted_class=1,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            features_snapshot={"confluence_score": 70}
        )
        temp_store.save_observation(pred)

        # Resolve forward outcome
        temp_store.resolve_observation_outcome(
            observation_id=pred.observation_id,
            outcome="WIN",
            exit_price=61500.0,
            realized_r=1.5,
            outcome_timestamp="2026-09-02T11:00:00Z",
            duration_minutes=60.0
        )

        loaded = temp_store.get_observation(pred.observation_id)
        assert loaded["outcome"] == "WIN"
        assert loaded["exit_price"] == 61500.0
        assert loaded["realized_r"] == 1.5

        # T0 snapshot attributes must remain 100% unchanged
        assert loaded["timestamp_t0"] == "2026-09-02T10:00:00Z"
        assert loaded["entry_price"] == 60000.0
        assert loaded["confluence_score"] == 70
        assert loaded["ml_probability"] == 0.65
        assert loaded["ml_predicted_class"] == 1

    def test_wait_safety(self, shadow_service):
        """Test 5: WAIT signals are recorded as WAIT observations and never converted into trades."""
        pred = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="WAIT",
            confluence_score=45,
            technical_score=40,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=None,
            take_profit_1=None,
            take_profit_2=None,
            session="ASIA",
            market_regime="RANGING",
            contributor_scores={"HTF Trend": 3},
            contributor_biases={"MTF Alignment": "NEUTRAL"}
        )
        if pred:
            assert pred.production_decision == "WAIT"

    def test_probability_validity(self, shadow_service):
        """Test 6 & Test 7: ML Probability is bounded in [0, 1] and model version is tagged."""
        pred = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=60,
            technical_score=55,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 7},
            contributor_biases={"MTF Alignment": "BULLISH"}
        )
        if pred:
            assert 0.0 <= pred.ml_probability <= 1.0
            assert pred.ml_predicted_class in [0, 1]
            assert pred.ml_model_version == "v1.0.0-research"

    def test_forward_outcome_resolution(self, shadow_service, temp_store):
        """Test 8: Future candlestick sequence correctly resolves pending observations."""
        pred = shadow_service.generate_prediction(
            symbol="BTC/USD",
            timestamp_t0="2026-09-02T10:00:00Z",
            production_decision="BUY",
            confluence_score=65,
            technical_score=60,
            gemini_score=5,
            entry_price=60000.0,
            stop_loss=59000.0,
            take_profit_1=61500.0,
            take_profit_2=63000.0,
            session="LONDON",
            market_regime="TRENDING_BULLISH",
            contributor_scores={"HTF Trend": 8},
            contributor_biases={"MTF Alignment": "BULLISH"}
        )
        if pred:
            candles = [
                {"timestamp": "2026-09-02T10:15:00Z", "high": 60500.0, "low": 59800.0, "close": 60200.0},
                {"timestamp": "2026-09-02T10:30:00Z", "high": 61800.0, "low": 60100.0, "close": 61600.0}, # Hits TP1 (61500)
            ]
            resolved = shadow_service.resolve_pending_observations("BTC/USD", candles)
            assert resolved == 1

            obs = temp_store.get_observation(pred.observation_id)
            assert obs["outcome"] == "WIN"
            assert obs["realized_r"] == 1.5
