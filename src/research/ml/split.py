"""
Chronological Time-Series Splitter.
Strictly prevents lookahead leakage by respecting chronological order.
"""
from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np

class TimeSeriesSplitter:
    """Provides zero-lookahead chronological dataset splitting."""

    @staticmethod
    def train_oos_holdout_split(
        df: pd.DataFrame,
        train_ratio: float = 0.60,
        oos_ratio: float = 0.20,
        holdout_ratio: float = 0.20
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split dataframe into strictly chronological Train, OOS Validation, and Final Holdout."""
        n = len(df)
        t_idx = int(n * train_ratio)
        v_idx = int(n * (train_ratio + oos_ratio))

        train_df = df.iloc[:t_idx].copy().reset_index(drop=True)
        oos_df = df.iloc[t_idx:v_idx].copy().reset_index(drop=True)
        holdout_df = df.iloc[v_idx:].copy().reset_index(drop=True)

        return train_df, oos_df, holdout_df

    @staticmethod
    def get_walk_forward_folds(
        df: pd.DataFrame,
        n_folds: int = 4,
        min_train_ratio: float = 0.40
    ) -> List[Dict[str, Any]]:
        """
        Generates expanding-window walk-forward folds chronologically.
        Fold k: Train on [0 ... t_k], Validate on [t_k ... t_{k+1}]
        """
        n = len(df)
        min_train = int(n * min_train_ratio)
        remaining = n - min_train
        step = remaining // n_folds

        folds = []
        for i in range(n_folds):
            train_end = min_train + i * step
            val_end = min_train + (i + 1) * step if i < n_folds - 1 else n

            train_slice = df.iloc[:train_end].copy().reset_index(drop=True)
            val_slice = df.iloc[train_end:val_end].copy().reset_index(drop=True)

            folds.append({
                "fold": i + 1,
                "train_start_ts": train_slice["signal_timestamp"].iloc[0] if not train_slice.empty else "",
                "train_end_ts": train_slice["signal_timestamp"].iloc[-1] if not train_slice.empty else "",
                "val_start_ts": val_slice["signal_timestamp"].iloc[0] if not val_slice.empty else "",
                "val_end_ts": val_slice["signal_timestamp"].iloc[-1] if not val_slice.empty else "",
                "train_df": train_slice,
                "val_df": val_slice
            })

        return folds
