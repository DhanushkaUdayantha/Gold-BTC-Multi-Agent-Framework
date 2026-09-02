"""
Evaluation Metrics for ML Classification and Quantitative Trading Performance.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, log_loss, brier_score_loss
)

class MetricsCalculator:
    """Calculates dual-domain ML classification and trading performance metrics."""

    @staticmethod
    def calculate_classification_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray
    ) -> Dict[str, float]:
        """Calculates standard classification quality metrics."""
        if len(y_true) == 0:
            return {}

        # Handle single class edge cases safely
        unique_classes = np.unique(y_true)
        if len(unique_classes) < 2:
            roc_auc = 0.5
            pr_auc = 0.5
            ll = 0.0
        else:
            try:
                roc_auc = float(roc_auc_score(y_true, y_prob))
                pr_auc = float(average_precision_score(y_true, y_prob))
                ll = float(log_loss(y_true, y_prob, eps=1e-7))
            except Exception:
                roc_auc = 0.5
                pr_auc = 0.5
                ll = 0.0

        brier = float(brier_score_loss(y_true, y_prob))

        return {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "log_loss": round(ll, 4),
            "brier_score": round(brier, 4),
        }

    @staticmethod
    def calculate_trading_metrics(
        df: pd.DataFrame,
        filter_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Calculates trading expectancy, payoff, profit factor, and max drawdown."""
        sub_df = df[filter_mask] if filter_mask is not None else df
        n = len(sub_df)
        if n == 0:
            return {
                "n": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
                "avg_win_r": 0.0, "avg_loss_r": 0.0, "ev_r": 0.0,
                "profit_factor": 0.0, "total_r": 0.0, "max_drawdown": 0.0,
                "sharpe_ratio": 0.0, "sortino_ratio": 0.0
            }

        wins = sub_df[sub_df["target_binary"] == 1]
        losses = sub_df[sub_df["target_binary"] == 0]
        n_wins = len(wins)
        n_losses = len(losses)
        wr = (n_wins / n) * 100.0

        # R-values
        r_series = sub_df["realized_r"].values
        total_r = float(np.sum(r_series))
        ev_r = float(np.mean(r_series))

        win_r_vals = wins["realized_r"].values
        loss_r_vals = losses["realized_r"].values

        avg_win_r = float(np.mean(win_r_vals)) if len(win_r_vals) > 0 else 0.0
        avg_loss_r = float(np.mean(loss_r_vals)) if len(loss_r_vals) > 0 else 0.0

        total_win_r = float(np.sum(win_r_vals)) if len(win_r_vals) > 0 else 0.0
        total_loss_r = abs(float(np.sum(loss_r_vals))) if len(loss_r_vals) > 0 else 0.0

        pf = (total_win_r / total_loss_r) if total_loss_r > 0 else (99.0 if total_win_r > 0 else 0.0)

        # Max Drawdown
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for r_val in r_series:
            cum += r_val
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd

        # Sharpe & Sortino (per-trade basis)
        std_r = float(np.std(r_series)) if len(r_series) > 1 else 1.0
        sharpe = (ev_r / std_r) if std_r > 0 else 0.0

        downside_r = r_series[r_series < 0]
        downside_std = float(np.std(downside_r)) if len(downside_r) > 1 else 1.0
        sortino = (ev_r / downside_std) if downside_std > 0 else 0.0

        return {
            "n": int(n),
            "wins": int(n_wins),
            "losses": int(n_losses),
            "win_rate": round(float(wr), 2),
            "avg_win_r": round(float(avg_win_r), 2),
            "avg_loss_r": round(float(avg_loss_r), 2),
            "ev_r": round(float(ev_r), 4),
            "profit_factor": round(float(pf), 2),
            "total_r": round(float(total_r), 2),
            "max_drawdown": round(float(max_dd), 2),
            "sharpe_ratio": round(float(sharpe), 3),
            "sortino_ratio": round(float(sortino), 3)
        }
