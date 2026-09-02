"""
Unit and Integration Tests for the Machine Learning Research Subsystem.
"""
import pytest
import numpy as np
import pandas as pd
import os

from src.research.ml.config import MLConfig
from src.research.ml.leakage_detection import LeakageDetector, FEATURE_CATALOG
from src.research.ml.dataset_builder import DatasetBuilder
from src.research.ml.feature_engineering import FeatureEngineer
from src.research.ml.split import TimeSeriesSplitter
from src.research.ml.preprocessing import DataPreprocessor
from src.research.ml.metrics import MetricsCalculator
from src.research.ml.models import ModelFactory
from src.research.ml.calibration import ProbabilityCalibrator
from src.research.ml.walk_forward import WalkForwardValidator
from src.research.ml.artifacts import ArtifactManager

class TestMLResearchSubsystem:

    @pytest.fixture
    def mock_signal_df(self):
        """Generates a synthetic point-in-time signal dataframe for deterministic testing."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="15min")
        return pd.DataFrame({
            "signal_id": [f"SIG-{i:04d}" for i in range(n)],
            "run_id": ["RUN-TEST"] * n,
            "dataset_id": ["DS-TEST"] * n,
            "symbol": ["BTC/USD"] * (n // 2) + ["XAU/USD"] * (n // 2),
            "signal_timestamp": [d.isoformat() for d in dates],
            "entry_price": np.linspace(50000, 55000, n),
            "direction": ["BUY" if i % 2 == 0 else "SELL" for i in range(n)],
            "confluence_score": np.random.randint(40, 80, n),
            "technical_score": np.random.randint(30, 70, n),
            "gemini_score": np.random.randint(0, 10, n),
            "data_quality": ["HIGH"] * n,
            "gate_direction": ["BULLISH"] * (n // 2) + ["BEARISH"] * (n // 2),
            "market_regime": ["TRENDING_BULLISH"] * n,
            "session": ["LONDON"] * n,
            "hour_of_day": [d.hour for d in dates],
            "day_of_week": [d.weekday() for d in dates],
            "sl_dist_pct": [0.01] * n,
            "tp_sl_ratio": [1.5] * n,
            "score_HTF_Trend": [8] * n,
            "score_Market_Structure": [7] * n,
            "score_Momentum": [6] * n,
            "score_MTF_Alignment": [6] * n,
            "score_SR_Price_Action": [6] * n,
            "score_Breakout_Retest": [4] * n,
            "score_Supply_Demand": [4] * n,
            "score_Volume_Confirmation": [4] * n,
            "score_SMC_ICT": [4] * n,
            "score_ICT_Concepts": [3] * n,
            "score_Fibonacci_OTE": [3] * n,
            "score_Elliott_Wave": [3] * n,
            "score_VWAP": [3] * n,
            "score_EMA_MA_Stack": [3] * n,
            "score_RSI": [2] * n,
            "score_MACD": [2] * n,
            "score_Gemini_AI": [8] * n,
            "bias_MTF_Alignment": ["BULLISH" if i % 2 == 0 else "BEARISH" for i in range(n)],
            "bias_VWAP": ["BULLISH" if i % 2 == 0 else "BEARISH" for i in range(n)],
            "bias_Momentum": ["BULLISH" if i % 2 == 0 else "BEARISH" for i in range(n)],
            "bias_Volume_Confirmation": ["BULLISH" if i % 2 == 0 else "BEARISH" for i in range(n)],
            "target_binary": [1 if i % 3 != 0 else 0 for i in range(n)],
            "realized_r": [1.5 if i % 3 != 0 else -1.0 for i in range(n)],
            "outcome": ["WIN" if i % 3 != 0 else "LOSS" for i in range(n)]
        })

    def test_leakage_detector_clean(self):
        safe_features = ["confluence_score", "score_HTF_Trend", "bias_MTF_Alignment", "sl_dist_pct"]
        is_clean, audit = LeakageDetector.audit_features(safe_features)
        assert is_clean is True
        assert all(a["status"] == "SAFE" for a in audit)

    def test_leakage_detector_catches_unsafe_features(self):
        unsafe_features = ["confluence_score", "exit_price", "realized_r", "mfe"]
        is_clean, audit = LeakageDetector.audit_features(unsafe_features)
        assert is_clean is False
        unsafe_items = [a for a in audit if a["status"] == "UNSAFE"]
        assert len(unsafe_items) == 3

    def test_time_series_chronological_split(self, mock_signal_df):
        train, oos, holdout = TimeSeriesSplitter.train_oos_holdout_split(
            mock_signal_df, train_ratio=0.6, oos_ratio=0.2, holdout_ratio=0.2
        )
        assert len(train) == 60
        assert len(oos) == 20
        assert len(holdout) == 20

        # Verify strict timestamp monotonicity
        assert train["signal_timestamp"].max() <= oos["signal_timestamp"].min()
        assert oos["signal_timestamp"].max() <= holdout["signal_timestamp"].min()

    def test_feature_engineering_transform(self, mock_signal_df):
        transformed = FeatureEngineer.transform_features(mock_signal_df)
        cols = FeatureEngineer.get_feature_column_names()
        for col in cols:
            assert col in transformed.columns
        assert "mtf_aligned" in transformed.columns
        assert "vwap_aligned" in transformed.columns

    def test_preprocessor_fit_transform_no_leakage(self, mock_signal_df):
        transformed = FeatureEngineer.transform_features(mock_signal_df)
        cols = FeatureEngineer.get_feature_column_names()
        train, oos, _ = TimeSeriesSplitter.train_oos_holdout_split(transformed, 0.6, 0.2, 0.2)

        prep = DataPreprocessor(cols)
        X_train = prep.fit_transform(train)
        X_oos = prep.transform(oos)

        assert X_train.shape == (60, len(cols))
        assert X_oos.shape == (20, len(cols))
        assert np.isfinite(X_train).all()
        assert np.isfinite(X_oos).all()

    def test_metrics_calculator(self, mock_signal_df):
        y_true = np.array([1, 1, 0, 1, 0])
        y_pred = np.array([1, 1, 0, 0, 0])
        y_prob = np.array([0.9, 0.8, 0.2, 0.4, 0.1])

        cls_m = MetricsCalculator.calculate_classification_metrics(y_true, y_pred, y_prob)
        assert cls_m["accuracy"] == 0.80
        assert cls_m["precision"] == 1.00
        assert cls_m["brier_score"] >= 0.0

        trd_m = MetricsCalculator.calculate_trading_metrics(mock_signal_df)
        assert trd_m["n"] == 100
        assert trd_m["profit_factor"] > 0
        assert trd_m["max_drawdown"] >= 0

    def test_probability_calibrator(self):
        y_true = np.array([1, 1, 1, 0, 0, 1, 0, 0, 1, 1])
        y_prob = np.array([0.52, 0.53, 0.54, 0.51, 0.52, 0.65, 0.62, 0.61, 0.72, 0.75])
        calib = ProbabilityCalibrator.evaluate_calibration(y_true, y_prob)
        assert "brier_score" in calib
        assert "expected_calibration_error" in calib
        assert len(calib["buckets"]) > 0

    def test_models_instantiation_and_training(self, mock_signal_df):
        transformed = FeatureEngineer.transform_features(mock_signal_df)
        cols = FeatureEngineer.get_feature_column_names()
        prep = DataPreprocessor(cols)
        X = prep.fit_transform(transformed)
        y = transformed["target_binary"].values

        models = ModelFactory.get_available_models(random_state=42)
        assert "Logistic_Regression" in models
        assert "Random_Forest" in models
        assert "Gradient_Boosting" in models

        for name, model in models.items():
            model.fit(X, y)
            probs = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else model.predict(X).astype(float)
            assert len(probs) == len(y)
            assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    def test_walk_forward_validator(self, mock_signal_df):
        cols = FeatureEngineer.get_feature_column_names()
        wf = WalkForwardValidator(feature_cols=cols, model_name="Random_Forest")
        res = wf.run_walk_forward(mock_signal_df, n_folds=3, prob_threshold=0.50)
        assert "n_folds" in res
        assert "folds" in res
        assert len(res["folds"]) > 0
        assert "aggregate_trading_metrics" in res
