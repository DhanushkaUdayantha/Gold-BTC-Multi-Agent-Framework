"""
Model Definitions and Model Registry for ML Research.
Provides baseline and ensemble classifiers strictly utilizing available scikit-learn algorithms.
"""
from typing import Dict, Any, Type, Optional
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier

class ModelFactory:
    """Instantiates calibrated baseline and ensemble classifiers."""

    @staticmethod
    def get_available_models(random_state: int = 42) -> Dict[str, Any]:
        """Returns instantiated model pipeline candidates."""
        return {
            "Majority_Baseline": DummyClassifier(strategy="most_frequent"),
            "Logistic_Regression": LogisticRegression(
                C=1.0, solver="lbfgs", max_iter=500, random_state=random_state
            ),
            "Random_Forest": RandomForestClassifier(
                n_estimators=100, max_depth=5, min_samples_leaf=10, random_state=random_state, n_jobs=-1
            ),
            "Gradient_Boosting": GradientBoostingClassifier(
                n_estimators=100, learning_rate=0.05, max_depth=3, min_samples_leaf=10, random_state=random_state
            ),
            "Hist_Gradient_Boosting": HistGradientBoostingClassifier(
                max_iter=100, learning_rate=0.05, max_depth=3, min_samples_leaf=10, random_state=random_state
            )
        }
