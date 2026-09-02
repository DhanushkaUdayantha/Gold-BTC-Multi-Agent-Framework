"""
Feature Importance and Attribution Analyzer.
"""
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

class FeatureImportanceAnalyzer:
    """Calculates tree MDI and Permutation Importance across features."""

    @staticmethod
    def extract_tree_importance(model: Any, feature_names: List[str]) -> List[Dict[str, Any]]:
        """Extracts native Gini/MDI feature importance from tree models."""
        if not hasattr(model, "feature_importances_"):
            return []
        importances = model.feature_importances_
        results = []
        for name, imp in zip(feature_names, importances):
            results.append({
                "feature": name,
                "importance": round(float(imp), 4)
            })
        results.sort(key=lambda x: x["importance"], reverse=True)
        return results

    @staticmethod
    def extract_permutation_importance(
        model: Any,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str],
        random_state: int = 42
    ) -> List[Dict[str, Any]]:
        """Calculates permutation importance on out-of-sample validation data."""
        try:
            perm = permutation_importance(
                model, X_val, y_val, scoring="roc_auc", n_repeats=5, random_state=random_state
            )
            results = []
            for name, mean_imp, std_imp in zip(feature_names, perm.importances_mean, perm.importances_std):
                results.append({
                    "feature": name,
                    "importance_mean": round(float(mean_imp), 4),
                    "importance_std": round(float(std_imp), 4)
                })
            results.sort(key=lambda x: x["importance_mean"], reverse=True)
            return results
        except Exception:
            return []
