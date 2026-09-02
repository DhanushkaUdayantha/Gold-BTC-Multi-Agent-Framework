"""
Feature Engineering and Vectorization Pipeline for ML Research.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any

class FeatureEngineer:
    """Transforms raw point-in-time signal records into numerical feature matrices."""

    NUMERIC_COLS = [
        "confluence_score", "technical_score", "gemini_score",
        "hour_of_day", "day_of_week", "sl_dist_pct", "tp_sl_ratio",
        "score_HTF_Trend", "score_Market_Structure", "score_Momentum",
        "score_MTF_Alignment", "score_SR_Price_Action", "score_Breakout_Retest",
        "score_Supply_Demand", "score_Volume_Confirmation", "score_SMC_ICT",
        "score_ICT_Concepts", "score_Fibonacci_OTE", "score_Elliott_Wave",
        "score_VWAP", "score_EMA_MA_Stack", "score_RSI", "score_MACD", "score_Gemini_AI"
    ]

    CATEGORICAL_COLS = [
        "direction", "data_quality", "gate_direction", "market_regime", "session",
        "bias_MTF_Alignment", "bias_VWAP", "bias_Momentum", "bias_Volume_Confirmation"
    ]

    @classmethod
    def transform_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer domain-specific directional alignment features and numeric vectors."""
        feat_df = df.copy()

        # Direction alignment binary indicators
        is_buy = (feat_df["direction"] == "BUY").astype(int)
        
        feat_df["mtf_aligned"] = (
            (is_buy == 1) & (feat_df["bias_MTF_Alignment"] == "BULLISH") |
            (is_buy == 0) & (feat_df["bias_MTF_Alignment"] == "BEARISH")
        ).astype(int)

        feat_df["vwap_aligned"] = (
            (is_buy == 1) & (feat_df["bias_VWAP"] == "BULLISH") |
            (is_buy == 0) & (feat_df["bias_VWAP"] == "BEARISH")
        ).astype(int)

        feat_df["momentum_aligned"] = (
            (is_buy == 1) & (feat_df["bias_Momentum"] == "BULLISH") |
            (is_buy == 0) & (feat_df["bias_Momentum"] == "BEARISH")
        ).astype(int)

        feat_df["vol_aligned"] = (
            (is_buy == 1) & (feat_df["bias_Volume_Confirmation"] == "BULLISH") |
            (is_buy == 0) & (feat_df["bias_Volume_Confirmation"] == "BEARISH")
        ).astype(int)

        feat_df["is_asia_buy"] = (
            (is_buy == 1) & (feat_df["session"] == "ASIA")
        ).astype(int)

        feat_df["is_high_confluence"] = (feat_df["confluence_score"] >= 58).astype(int)

        return feat_df

    @classmethod
    def get_feature_column_names(cls) -> List[str]:
        """Returns the complete list of numeric feature names passed to ML models."""
        return cls.NUMERIC_COLS + [
            "mtf_aligned", "vwap_aligned", "momentum_aligned", "vol_aligned",
            "is_asia_buy", "is_high_confluence"
        ]
