"""
Baseline Models and Strategy Benchmark Comparator.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.research.ml.metrics import MetricsCalculator

class BaselineComparator:
    """Calculates non-ML benchmark performance across unfiltered and rule-based strategies."""

    @staticmethod
    def evaluate_rule_based_quality_gates(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Evaluates the production rule-based quality gates on the dataframe."""
        is_btc = "BTC" in symbol.upper()
        is_xau = "XAU" in symbol.upper()

        if is_btc:
            mask = (
                (df["confluence_score"] >= 58) &
                (
                    ((df["direction"] == "BUY") & (df["bias_MTF_Alignment"] == "BULLISH")) |
                    ((df["direction"] == "SELL") & (df["bias_MTF_Alignment"] == "BEARISH"))
                ) &
                ~(
                    (df["direction"] == "BUY") & (df["session"] == "ASIA") &
                    ~(
                        (df["bias_Volume_Confirmation"] == "BULLISH") |
                        ((df["bias_Momentum"] == "BULLISH") & (df["confluence_score"] >= 65))
                    )
                )
            )
        elif is_xau:
            mask = (
                (df["confluence_score"] >= 58) &
                (
                    ((df["direction"] == "BUY") & (df["bias_MTF_Alignment"] == "BULLISH")) |
                    ((df["direction"] == "SELL") & (df["bias_MTF_Alignment"] == "BEARISH"))
                ) &
                (
                    ((df["direction"] == "BUY") & (df["bias_VWAP"] == "BULLISH")) |
                    ((df["direction"] == "SELL") & (df["bias_VWAP"] == "BEARISH"))
                )
            )
        else:
            mask = df["confluence_score"] >= 58

        unfiltered_metrics = MetricsCalculator.calculate_trading_metrics(df)
        gated_metrics = MetricsCalculator.calculate_trading_metrics(df, filter_mask=mask)

        return {
            "unfiltered_baseline": unfiltered_metrics,
            "rule_based_gated": gated_metrics
        }
