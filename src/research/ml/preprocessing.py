"""
Preprocessing and Scaling Pipeline.
Fits scalers exclusively on Training data and transforms OOS/Holdout without leakage.
"""
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

class DataPreprocessor:
    """Preprocesses feature matrices safely without lookahead leakage."""

    def __init__(self, feature_cols: List[str]):
        self.feature_cols = feature_cols
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self._is_fitted = False

    def fit(self, train_df: pd.DataFrame) -> "DataPreprocessor":
        """Fits imputer and scaler strictly on the training partition."""
        X_train = train_df[self.feature_cols].values
        X_imp = self.imputer.fit_transform(X_train)
        self.scaler.fit(X_imp)
        self._is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms a dataframe using pre-fitted parameters."""
        if not self._is_fitted:
            raise RuntimeError("Preprocessor must be fitted on training data before transforming.")
        X = df[self.feature_cols].values
        X_imp = self.imputer.transform(X)
        return self.scaler.transform(X_imp)

    def fit_transform(self, train_df: pd.DataFrame) -> np.ndarray:
        return self.fit(train_df).transform(train_df)
