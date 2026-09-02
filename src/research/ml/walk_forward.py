"""
Walk-Forward Validation Engine for Time-Series Trading ML.
"""
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from src.research.ml.split import TimeSeriesSplitter
from src.research.ml.preprocessing import DataPreprocessor
from src.research.ml.feature_engineering import FeatureEngineer
from src.research.ml.models import ModelFactory
from src.research.ml.metrics import MetricsCalculator

class WalkForwardValidator:
    """Executes multi-fold chronological walk-forward validation."""

    def __init__(self, feature_cols: List[str], model_name: str = "Random_Forest"):
        self.feature_cols = feature_cols
        self.model_name = model_name

    def run_walk_forward(
        self,
        df: pd.DataFrame,
        n_folds: int = 4,
        prob_threshold: float = 0.50
    ) -> Dict[str, Any]:
        """Runs chronological walk-forward validation across expanding folds."""
        feat_df = FeatureEngineer.transform_features(df)
        folds = TimeSeriesSplitter.get_walk_forward_folds(feat_df, n_folds=n_folds)

        fold_results = []
        all_val_preds = []
        all_val_probs = []
        all_val_targets = []
        all_val_df_list = []

        for fold in folds:
            f_num = fold["fold"]
            train_df = fold["train_df"]
            val_df = fold["val_df"]

            if len(train_df) < 50 or len(val_df) < 20:
                continue

            # Preprocessing (fit strictly on train)
            prep = DataPreprocessor(self.feature_cols)
            X_train = prep.fit_transform(train_df)
            y_train = train_df["target_binary"].values

            X_val = prep.transform(val_df)
            y_val = val_df["target_binary"].values

            # Fit model
            models = ModelFactory.get_available_models()
            model = models.get(self.model_name, models["Random_Forest"])
            model.fit(X_train, y_train)

            # Predict probabilities
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X_val)[:, 1]
            else:
                probs = model.predict(X_val).astype(float)

            preds = (probs >= prob_threshold).astype(int)

            # Metrics
            cls_m = MetricsCalculator.calculate_classification_metrics(y_val, preds, probs)
            trd_m = MetricsCalculator.calculate_trading_metrics(val_df, filter_mask=(probs >= prob_threshold))

            fold_results.append({
                "fold": f_num,
                "train_n": len(train_df),
                "val_n": len(val_df),
                "train_start": fold["train_start_ts"],
                "train_end": fold["train_end_ts"],
                "val_start": fold["val_start_ts"],
                "val_end": fold["val_end_ts"],
                "classification_metrics": cls_m,
                "trading_metrics": trd_m
            })

            all_val_preds.extend(preds)
            all_val_probs.extend(probs)
            all_val_targets.extend(y_val)
            all_val_df_list.append(val_df)

        combined_val_df = pd.concat(all_val_df_list, ignore_index=True) if all_val_df_list else pd.DataFrame()
        combined_cls_m = MetricsCalculator.calculate_classification_metrics(
            np.array(all_val_targets), np.array(all_val_preds), np.array(all_val_probs)
        )
        combined_trd_m = MetricsCalculator.calculate_trading_metrics(
            combined_val_df, filter_mask=(np.array(all_val_probs) >= prob_threshold)
        )

        return {
            "model_name": self.model_name,
            "probability_threshold": prob_threshold,
            "n_folds": len(fold_results),
            "folds": fold_results,
            "aggregate_classification_metrics": combined_cls_m,
            "aggregate_trading_metrics": combined_trd_m
        }
