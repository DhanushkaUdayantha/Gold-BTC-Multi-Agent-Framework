"""
Artifact Manager for ML Research.
Serializes metrics, calibration data, prediction tables, and trained joblib models.
"""
import os
import json
import joblib
import pandas as pd
from typing import Dict, Any, Optional

class ArtifactManager:
    """Manages serialization of research outputs and model binaries into asset-specific artifact folders."""

    def __init__(self, base_dir: str = os.path.join("research", "ml", "artifacts")):
        self.base_dir = base_dir

    def save_asset_artifacts(
        self,
        symbol_key: str,
        metrics: Dict[str, Any],
        calibration: Dict[str, Any],
        feature_importance: Dict[str, Any],
        walk_forward: Dict[str, Any],
        predictions_df: pd.DataFrame,
        model_obj: Optional[Any] = None,
        preprocessor_obj: Optional[Any] = None
    ) -> str:
        """Saves all JSON, CSV, and joblib artifacts for a given asset."""
        asset_dir = os.path.join(self.base_dir, symbol_key)
        os.makedirs(asset_dir, exist_ok=True)

        # Save JSON artifacts
        with open(os.path.join(asset_dir, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        with open(os.path.join(asset_dir, "calibration.json"), "w", encoding="utf-8") as f:
            json.dump(calibration, f, indent=2)

        with open(os.path.join(asset_dir, "feature_importance.json"), "w", encoding="utf-8") as f:
            json.dump(feature_importance, f, indent=2)

        with open(os.path.join(asset_dir, "walk_forward.json"), "w", encoding="utf-8") as f:
            json.dump(walk_forward, f, indent=2)

        # Save predictions CSV
        if not predictions_df.empty:
            predictions_df.to_csv(os.path.join(asset_dir, "predictions.csv"), index=False)

        # Save model and preprocessor binaries
        if model_obj is not None:
            joblib.dump(model_obj, os.path.join(asset_dir, "model.joblib"))

        if preprocessor_obj is not None:
            joblib.dump(preprocessor_obj, os.path.join(asset_dir, "preprocessor.joblib"))

        return asset_dir

    def load_model(self, symbol_key: str) -> Optional[Any]:
        """Loads serialized model binary if available."""
        model_path = os.path.join(self.base_dir, symbol_key, "model.joblib")
        if os.path.exists(model_path):
            return joblib.load(model_path)
        return None

    def load_preprocessor(self, symbol_key: str) -> Optional[Any]:
        """Loads serialized preprocessor binary if available."""
        prep_path = os.path.join(self.base_dir, symbol_key, "preprocessor.joblib")
        if os.path.exists(prep_path):
            return joblib.load(prep_path)
        return None
