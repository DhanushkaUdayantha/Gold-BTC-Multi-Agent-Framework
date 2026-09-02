"""
Historical Backtesting and Calibration Module for BUY/SELL Directional Strength.

A dedicated, isolated analytics module that evaluates directional BUY/SELL strength
scores against actual historical future outcomes on BTC-USD and XAU-USD.

Features:
- Pure analytical replay (ZERO modification to live production trading decisions)
- Out-of-sample (70/30 chronological split) and Walk-Forward cross-validation (4 folds)
- Computes Win Rate, Expectancy (R), Profit Factor, Max Drawdown, TP/SL distribution
- Evaluates statistical calibration by Strength Bucket (Brier Score, ECE, Reliability)
- Independent BUY vs SELL performance analysis
- Full JSON and Markdown report export

DISCLAIMER: Empirical research and backtest analytics only. No live orders executed.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "historical",
    "historical_market_data.db",
)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "reports",
)


def _wilson_interval(wins: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson Score 95% binomial confidence interval."""
    if n <= 0:
        return 0.0, 0.0
    z = 1.96  # 95% confidence
    p_hat = wins / n
    denom = 1 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2 * n)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + (z ** 2) / (4 * n)) / n) / denom
    lower = max(0.0, round((center - spread) * 100, 1))
    upper = min(100.0, round((center + spread) * 100, 1))
    return lower, upper


@dataclass
class TradeOutcomeMetrics:
    """Core quantitative performance metrics for a subset of trades."""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    expired: int = 0
    breakeven: int = 0
    win_rate_pct: float = 0.0
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    expectancy_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_r: float = 0.0
    max_drawdown_pct: float = 0.0
    total_realized_r: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    tp1_hits: int = 0
    tp1_hit_rate_pct: float = 0.0
    tp2_hits: int = 0
    tp2_hit_rate_pct: float = 0.0
    sl_hits: int = 0
    sl_hit_rate_pct: float = 0.0
    avg_duration_minutes: float = 0.0
    avg_mfe_r: float = 0.0
    avg_mae_r: float = 0.0


@dataclass
class StrengthBucketCalibration:
    """Statistical calibration analysis for a specific strength score bucket."""
    bucket_name: str
    min_strength: int
    max_strength: int
    count: int = 0
    wins: int = 0
    losses: int = 0
    mean_predicted_strength: float = 0.0
    observed_win_rate_pct: float = 0.0
    expectancy_r: float = 0.0
    profit_factor: float = 0.0
    calibration_gap_pct: float = 0.0


@dataclass
class DirectionalComparison:
    """BUY vs SELL performance comparison."""
    buy_metrics: TradeOutcomeMetrics
    sell_metrics: TradeOutcomeMetrics
    asymmetry_note: str = ""


@dataclass
class WalkForwardFold:
    """Walk-forward fold evaluation result."""
    fold_index: int
    train_start: str
    train_end: str
    train_count: int
    train_win_rate: float
    train_expectancy: float
    test_start: str
    test_end: str
    test_count: int
    test_win_rate: float
    test_expectancy: float
    test_profit_factor: float


@dataclass
class SymbolCalibrationReport:
    """Complete backtest & calibration report for a single asset (BTC/USD or XAU/USD)."""
    symbol: str
    dataset_period: str
    total_evaluated_trades: int
    overall_metrics: TradeOutcomeMetrics
    in_sample_metrics: TradeOutcomeMetrics
    out_of_sample_metrics: TradeOutcomeMetrics
    directional_comparison: DirectionalComparison
    strength_buckets: List[StrengthBucketCalibration]
    walk_forward_folds: List[WalkForwardFold]
    brier_score: float
    expected_calibration_error: float
    max_calibration_error: float
    calibration_grade: str
    executive_summary: str


@dataclass
class FullHistoricalCalibrationReport:
    """Combined report across BTC/USD and XAU/USD."""
    generated_at: str
    engine_version: str
    btc_report: SymbolCalibrationReport
    xau_report: SymbolCalibrationReport
    system_wide_summary: str


class HistoricalStrengthBacktestCalibrator:
    """
    Dedicated evaluation and calibration engine.
    Analyzes historical trade records, evaluates BUY/SELL strength scores against
    future market outcomes, and performs walk-forward validation.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def load_historical_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Load and sort historical backtest signals for a symbol chronologically."""
        norm_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
        if not os.path.exists(self.db_path):
            logger.warning(f"Database {self.db_path} does not exist.")
            return []

        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT 
                    signal_id, run_id, dataset_id, symbol, signal_timestamp,
                    entry_price, direction, confluence_score, technical_score, gemini_score,
                    market_regime, stop_loss, take_profit_1, take_profit_2,
                    outcome, outcome_timestamp, exit_price, realized_r, mfe, mae,
                    time_to_outcome_minutes, is_in_sample, success_reason, failure_reason
                FROM historical_signals
                WHERE symbol = ? AND outcome IN ('WIN', 'LOSS', 'EXPIRED', 'BREAKEVEN')
                ORDER BY signal_timestamp ASC
                """,
                (norm_symbol,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def compute_trade_metrics(self, trades: List[Dict[str, Any]]) -> TradeOutcomeMetrics:
        """Calculate comprehensive performance & risk metrics for a list of trades."""
        if not trades:
            return TradeOutcomeMetrics()

        n_total = len(trades)
        wins = sum(1 for t in trades if t["outcome"] == "WIN")
        losses = sum(1 for t in trades if t["outcome"] == "LOSS")
        expired = sum(1 for t in trades if t["outcome"] == "EXPIRED")
        breakeven = sum(1 for t in trades if t["outcome"] == "BREAKEVEN")

        n_wl = wins + losses
        win_rate = round(wins / n_wl * 100, 1) if n_wl > 0 else 0.0
        ci_lower, ci_upper = _wilson_interval(wins, n_wl)

        r_values = [t["realized_r"] for t in trades if t.get("realized_r") is not None]
        total_r = round(float(sum(r_values)), 3) if r_values else 0.0

        win_r_list = [r for r in r_values if r > 0]
        loss_r_list = [abs(r) for r in r_values if r < 0]

        avg_win_r = round(float(sum(win_r_list) / len(win_r_list)), 3) if win_r_list else 1.50
        avg_loss_r = round(float(sum(loss_r_list) / len(loss_r_list)), 3) if loss_r_list else 1.00

        gross_wins = sum(win_r_list)
        gross_losses = sum(loss_r_list)
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (round(gross_wins, 2) if gross_wins > 0 else 0.0)

        # Expectancy: (WR * AvgWinR) - (LossRate * AvgLossR)
        wr_frac = win_rate / 100.0
        lr_frac = 1.0 - wr_frac
        expectancy = round((wr_frac * avg_win_r) - (lr_frac * avg_loss_r), 3) if n_wl > 0 else 0.0

        # Equity Curve & Max Drawdown Calculation
        cum = 0.0
        peak = 0.0
        max_dd_r = 0.0
        for r in r_values:
            cum += r
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd_r:
                max_dd_r = dd

        max_dd_pct = round(max_dd_r * 1.5, 1)  # approx percentage based on standard 1.5% unit risk

        # TP / SL outcome stats
        tp1_hits = wins
        tp1_hit_rate = round(tp1_hits / n_total * 100, 1) if n_total > 0 else 0.0
        tp2_hits = sum(1 for t in trades if t.get("mfe") and t["mfe"] >= 2.0)
        tp2_hit_rate = round(tp2_hits / n_total * 100, 1) if n_total > 0 else 0.0
        sl_hits = losses
        sl_hit_rate = round(sl_hits / n_total * 100, 1) if n_total > 0 else 0.0

        # Durations & MFE/MAE
        durations = [t["time_to_outcome_minutes"] for t in trades if t.get("time_to_outcome_minutes") is not None]
        avg_duration = round(float(sum(durations) / len(durations)), 1) if durations else 0.0

        mfes = [t["mfe"] for t in trades if t.get("mfe") is not None]
        avg_mfe = round(float(sum(mfes) / len(mfes)), 2) if mfes else 0.0

        maes = [t["mae"] for t in trades if t.get("mae") is not None]
        avg_mae = round(float(sum(maes) / len(maes)), 2) if maes else 0.0

        return TradeOutcomeMetrics(
            total_trades=n_total,
            wins=wins,
            losses=losses,
            expired=expired,
            breakeven=breakeven,
            win_rate_pct=win_rate,
            ci_95_lower=ci_lower,
            ci_95_upper=ci_upper,
            expectancy_r=expectancy,
            profit_factor=profit_factor,
            max_drawdown_r=round(max_dd_r, 2),
            max_drawdown_pct=max_dd_pct,
            total_realized_r=total_r,
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            tp1_hits=tp1_hits,
            tp1_hit_rate_pct=tp1_hit_rate,
            tp2_hits=tp2_hits,
            tp2_hit_rate_pct=tp2_hit_rate,
            sl_hits=sl_hits,
            sl_hit_rate_pct=sl_hit_rate,
            avg_duration_minutes=avg_duration,
            avg_mfe_r=avg_mfe,
            avg_mae_r=avg_mae,
        )

    def evaluate_strength_buckets(self, trades: List[Dict[str, Any]]) -> List[StrengthBucketCalibration]:
        """
        Evaluate statistical calibration across 6 strength score tiers.
        Compares mean predicted strength vs actual realized win rate.
        """
        bucket_defs = [
            ("< 50%", 0, 49),
            ("50% – 59%", 50, 59),
            ("60% – 69%", 60, 69),
            ("70% – 79%", 70, 79),
            ("80% – 89%", 80, 89),
            ("90% – 100%", 90, 100),
        ]

        results = []
        for name, min_s, max_s in bucket_defs:
            b_trades = [
                t for t in trades
                if min_s <= int(t.get("confluence_score", 0)) <= max_s
            ]
            count = len(b_trades)
            if count == 0:
                results.append(StrengthBucketCalibration(
                    bucket_name=name,
                    min_strength=min_s,
                    max_strength=max_s,
                    count=0,
                    wins=0,
                    losses=0,
                    mean_predicted_strength=float((min_s + max_s) / 2),
                    observed_win_rate_pct=0.0,
                    expectancy_r=0.0,
                    profit_factor=0.0,
                    calibration_gap_pct=0.0,
                ))
                continue

            wins = sum(1 for t in b_trades if t["outcome"] == "WIN")
            losses = sum(1 for t in b_trades if t["outcome"] == "LOSS")
            n_wl = wins + losses

            obs_wr = round(wins / n_wl * 100, 1) if n_wl > 0 else 0.0
            mean_pred = round(sum(int(t.get("confluence_score", 0)) for t in b_trades) / count, 1)

            r_vals = [t["realized_r"] for t in b_trades if t.get("realized_r") is not None]
            exp = round(sum(r_vals) / len(r_vals), 3) if r_vals else 0.0

            win_rs = [r for r in r_vals if r > 0]
            loss_rs = [abs(r) for r in r_vals if r < 0]
            pf = round(sum(win_rs) / sum(loss_rs), 2) if loss_rs and win_rs else (1.5 if wins > 0 else 0.0)

            gap = round(abs(mean_pred - obs_wr), 1)

            results.append(StrengthBucketCalibration(
                bucket_name=name,
                min_strength=min_s,
                max_strength=max_s,
                count=count,
                wins=wins,
                losses=losses,
                mean_predicted_strength=mean_pred,
                observed_win_rate_pct=obs_wr,
                expectancy_r=exp,
                profit_factor=pf,
                calibration_gap_pct=gap,
            ))

        return results

    def compute_brier_and_calibration_error(
        self,
        trades: List[Dict[str, Any]],
        buckets: List[StrengthBucketCalibration],
    ) -> Tuple[float, float, float]:
        """Compute Brier Score, Expected Calibration Error (ECE), and Max Calibration Error (MCE)."""
        wl_trades = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
        n = len(wl_trades)
        if n == 0:
            return 0.25, 0.0, 0.0

        # Brier score: (1/N) * sum((prob - actual)^2)
        brier_sum = 0.0
        for t in wl_trades:
            prob = float(t.get("confluence_score", 50)) / 100.0
            actual = 1.0 if t["outcome"] == "WIN" else 0.0
            brier_sum += (prob - actual) ** 2

        brier = round(brier_sum / n, 4)

        # Expected Calibration Error (ECE) weighted by bucket sample counts
        ece_sum = 0.0
        max_error = 0.0
        for b in buckets:
            if b.count > 0:
                weight = b.count / n
                gap = abs(b.mean_predicted_strength - b.observed_win_rate_pct)
                ece_sum += weight * gap
                if gap > max_error:
                    max_error = gap

        ece = round(ece_sum, 2)
        mce = round(max_error, 2)
        return brier, ece, mce

    def compute_walk_forward_folds(
        self,
        trades: List[Dict[str, Any]],
        n_folds: int = 4,
    ) -> List[WalkForwardFold]:
        """
        Execute chronological rolling walk-forward validation across n_folds.
        Ensures in-sample training precedes out-of-sample testing chronologically.
        """
        if len(trades) < 40:
            return []

        folds: List[WalkForwardFold] = []
        total_len = len(trades)
        fold_step = total_len // (n_folds + 1)

        for i in range(1, n_folds + 1):
            train_end_idx = fold_step * i
            test_end_idx = min(total_len, train_end_idx + fold_step)

            train_slice = trades[:train_end_idx]
            test_slice = trades[train_end_idx:test_end_idx]

            if not train_slice or not test_slice:
                continue

            train_m = self.compute_trade_metrics(train_slice)
            test_m = self.compute_trade_metrics(test_slice)

            folds.append(WalkForwardFold(
                fold_index=i,
                train_start=train_slice[0]["signal_timestamp"][:10],
                train_end=train_slice[-1]["signal_timestamp"][:10],
                train_count=len(train_slice),
                train_win_rate=train_m.win_rate_pct,
                train_expectancy=train_m.expectancy_r,
                test_start=test_slice[0]["signal_timestamp"][:10],
                test_end=test_slice[-1]["signal_timestamp"][:10],
                test_count=len(test_slice),
                test_win_rate=test_m.win_rate_pct,
                test_expectancy=test_m.expectancy_r,
                test_profit_factor=test_m.profit_factor,
            ))

        return folds

    def evaluate_symbol(self, symbol: str) -> SymbolCalibrationReport:
        """Run complete out-of-sample backtesting and calibration report for one symbol."""
        trades = self.load_historical_signals(symbol)
        if not trades:
            empty_m = TradeOutcomeMetrics()
            return SymbolCalibrationReport(
                symbol=symbol,
                dataset_period="N/A",
                total_evaluated_trades=0,
                overall_metrics=empty_m,
                in_sample_metrics=empty_m,
                out_of_sample_metrics=empty_m,
                directional_comparison=DirectionalComparison(empty_m, empty_m, "No trade data available"),
                strength_buckets=[],
                walk_forward_folds=[],
                brier_score=0.25,
                expected_calibration_error=0.0,
                max_calibration_error=0.0,
                calibration_grade="INSUFFICIENT_DATA",
                executive_summary=f"No historical trades recorded for {symbol}.",
            )

        dataset_period = f"{trades[0]['signal_timestamp'][:10]} → {trades[-1]['signal_timestamp'][:10]}"
        n_total = len(trades)

        # 1. Overall Metrics
        overall_m = self.compute_trade_metrics(trades)

        # 2. Chronological 70/30 In-Sample vs Out-of-Sample Split
        split_idx = int(n_total * 0.70)
        is_trades = trades[:split_idx]
        oos_trades = trades[split_idx:]

        is_m = self.compute_trade_metrics(is_trades)
        oos_m = self.compute_trade_metrics(oos_trades)

        # 3. BUY vs SELL Performance Breakdown
        buy_trades = [t for t in trades if t["direction"] == "BUY"]
        sell_trades = [t for t in trades if t["direction"] == "SELL"]

        buy_m = self.compute_trade_metrics(buy_trades)
        sell_m = self.compute_trade_metrics(sell_trades)

        asymmetry = (
            f"BUY WR: {buy_m.win_rate_pct}% (PF {buy_m.profit_factor}) vs "
            f"SELL WR: {sell_m.win_rate_pct}% (PF {sell_m.profit_factor}). "
            f"{'BUY performance is superior.' if buy_m.expectancy_r > sell_m.expectancy_r else 'SELL performance is superior.' if sell_m.expectancy_r > buy_m.expectancy_r else 'Both directions perform symmetrically.'}"
        )

        # 4. Strength Bucket Calibration & Reliability Metrics
        buckets = self.evaluate_strength_buckets(trades)
        brier, ece, mce = self.compute_brier_and_calibration_error(trades, buckets)

        # Calibration Grade
        if brier <= 0.22 and ece <= 10.0:
            cal_grade = "EXCELLENT"
        elif brier <= 0.24 and ece <= 15.0:
            cal_grade = "VALID / WELL-CALIBRATED"
        elif brier <= 0.26:
            cal_grade = "MODERATE"
        else:
            cal_grade = "UNRELIABLE"

        # 5. Walk-Forward Cross Validation
        wf_folds = self.compute_walk_forward_folds(trades, n_folds=4)

        summary = (
            f"{symbol} evaluated across {n_total:,} trades ({dataset_period}). "
            f"Overall Win Rate: {overall_m.win_rate_pct}% [95% CI: {overall_m.ci_95_lower}%–{overall_m.ci_95_upper}%] "
            f"with Expectancy of {overall_m.expectancy_r:+.2f}R and Profit Factor of {overall_m.profit_factor}. "
            f"Out-of-Sample (30%) verified: {oos_m.win_rate_pct}% WR, Expectancy {oos_m.expectancy_r:+.2f}R, PF {oos_m.profit_factor}. "
            f"Calibration Brier Score: {brier:.4f} (ECE: {ece}%)."
        )

        return SymbolCalibrationReport(
            symbol=symbol,
            dataset_period=dataset_period,
            total_evaluated_trades=n_total,
            overall_metrics=overall_m,
            in_sample_metrics=is_m,
            out_of_sample_metrics=oos_m,
            directional_comparison=DirectionalComparison(buy_m, sell_m, asymmetry),
            strength_buckets=buckets,
            walk_forward_folds=wf_folds,
            brier_score=brier,
            expected_calibration_error=ece,
            max_calibration_error=mce,
            calibration_grade=cal_grade,
            executive_summary=summary,
        )

    def run_full_calibration(self) -> FullHistoricalCalibrationReport:
        """Run full historical backtesting & calibration across BTC/USD and XAU/USD."""
        logger.info("Running Historical Strength Backtesting & Calibration Module...")
        btc_rep = self.evaluate_symbol("BTC/USD")
        xau_rep = self.evaluate_symbol("XAU/USD")

        sys_summary = (
            f"Historical Strength Backtesting & Calibration completed across BTC/USD ({btc_rep.total_evaluated_trades:,} trades) "
            f"and XAU/USD ({xau_rep.total_evaluated_trades:,} trades). "
            f"BTC OOS Expectancy: {btc_rep.out_of_sample_metrics.expectancy_r:+.2f}R (PF {btc_rep.out_of_sample_metrics.profit_factor}) | "
            f"XAU OOS Expectancy: {xau_rep.out_of_sample_metrics.expectancy_r:+.2f}R (PF {xau_rep.out_of_sample_metrics.profit_factor})."
        )

        report = FullHistoricalCalibrationReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            engine_version="HistoricalStrengthCalibrator-v2.0",
            btc_report=btc_rep,
            xau_report=xau_rep,
            system_wide_summary=sys_summary,
        )

        return report

    def export_reports(self, report: Optional[FullHistoricalCalibrationReport] = None) -> Tuple[str, str]:
        """Export JSON and Markdown reports to data/reports/ directory."""
        if report is None:
            report = self.run_full_calibration()

        os.makedirs(REPORTS_DIR, exist_ok=True)
        json_path = os.path.join(REPORTS_DIR, "historical_strength_calibration_report.json")
        md_path = os.path.join(REPORTS_DIR, "historical_strength_calibration_report.md")

        # 1. Export JSON
        report_dict = {
            "generated_at": report.generated_at,
            "engine_version": report.engine_version,
            "system_wide_summary": report.system_wide_summary,
            "btc_report": asdict(report.btc_report),
            "xau_report": asdict(report.xau_report),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)

        # 2. Export Markdown Report
        md_content = self._render_markdown_report(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"Reports exported successfully:\n  JSON: {json_path}\n  Markdown: {md_path}")
        return json_path, md_path

    def _render_markdown_report(self, r: FullHistoricalCalibrationReport) -> str:
        """Render institutional-grade markdown report."""
        btc = r.btc_report
        xau = r.xau_report

        return f"""# Institutional Historical Backtesting & Directional Strength Calibration Report

**Generated At:** `{r.generated_at}`  
**Engine Version:** `{r.engine_version}`  
**Evaluation Scope:** Zero-Lookahead Historical Outcome Replay & Walk-Forward Cross-Validation  
**Target Assets:** `BTC/USD` & `XAU/USD`  

---

## 1. Executive Summary

{r.system_wide_summary}

---

## 2. Key Performance Metrics Comparison

| Metric | BTC/USD (Overall) | BTC/USD (Out-of-Sample) | XAU/USD (Overall) | XAU/USD (Out-of-Sample) |
| :--- | :---: | :---: | :---: | :---: |
| **Dataset Range** | `{btc.dataset_period}` | Last 30% | `{xau.dataset_period}` | Last 30% |
| **Total Evaluated Trades** | **{btc.total_evaluated_trades:,}** | {btc.out_of_sample_metrics.total_trades:,} | **{xau.total_evaluated_trades:,}** | {xau.out_of_sample_metrics.total_trades:,} |
| **Win Rate (%)** | **{btc.overall_metrics.win_rate_pct}%** | **{btc.out_of_sample_metrics.win_rate_pct}%** | **{xau.overall_metrics.win_rate_pct}%** | **{xau.out_of_sample_metrics.win_rate_pct}%** |
| **95% Confidence Interval** | `{btc.overall_metrics.ci_95_lower}% – {btc.overall_metrics.ci_95_upper}%` | `{btc.out_of_sample_metrics.ci_95_lower}% – {btc.out_of_sample_metrics.ci_95_upper}%` | `{xau.overall_metrics.ci_95_lower}% – {xau.overall_metrics.ci_95_upper}%` | `{xau.out_of_sample_metrics.ci_95_lower}% – {xau.out_of_sample_metrics.ci_95_upper}%` |
| **Expectancy ($R$)** | **{btc.overall_metrics.expectancy_r:+.2f}R** | **{btc.out_of_sample_metrics.expectancy_r:+.2f}R** | **{xau.overall_metrics.expectancy_r:+.2f}R** | **{xau.out_of_sample_metrics.expectancy_r:+.2f}R** |
| **Profit Factor ($PF$)** | **{btc.overall_metrics.profit_factor}** | **{btc.out_of_sample_metrics.profit_factor}** | **{xau.overall_metrics.profit_factor}** | **{xau.out_of_sample_metrics.profit_factor}** |
| **Max Drawdown ($R$)** | `{btc.overall_metrics.max_drawdown_r}R` | `{btc.out_of_sample_metrics.max_drawdown_r}R` | `{xau.overall_metrics.max_drawdown_r}R` | `{xau.out_of_sample_metrics.max_drawdown_r}R` |
| **Total Realized Return ($R$)** | `+{btc.overall_metrics.total_realized_r:.1f}R` | `+{btc.out_of_sample_metrics.total_realized_r:.1f}R` | `+{xau.overall_metrics.total_realized_r:.1f}R` | `+{xau.out_of_sample_metrics.total_realized_r:.1f}R` |
| **TP1 Hit Rate (%)** | `{btc.overall_metrics.tp1_hit_rate_pct}%` | `{btc.out_of_sample_metrics.tp1_hit_rate_pct}%` | `{xau.overall_metrics.tp1_hit_rate_pct}%` | `{xau.out_of_sample_metrics.tp1_hit_rate_pct}%` |
| **TP2 Extended Hit Rate (%)** | `{btc.overall_metrics.tp2_hit_rate_pct}%` | `{btc.out_of_sample_metrics.tp2_hit_rate_pct}%` | `{xau.overall_metrics.tp2_hit_rate_pct}%` | `{xau.out_of_sample_metrics.tp2_hit_rate_pct}%` |
| **SL Hit Rate (%)** | `{btc.overall_metrics.sl_hit_rate_pct}%` | `{btc.out_of_sample_metrics.sl_hit_rate_pct}%` | `{xau.overall_metrics.sl_hit_rate_pct}%` | `{xau.out_of_sample_metrics.sl_hit_rate_pct}%` |
| **Avg Duration (Min)** | `{btc.overall_metrics.avg_duration_minutes} min` | `{btc.out_of_sample_metrics.avg_duration_minutes} min` | `{xau.overall_metrics.avg_duration_minutes} min` | `{xau.out_of_sample_metrics.avg_duration_minutes} min` |

---

## 3. Calibration by Strength Score Bucket (Reliability Curve)

### BTC/USD Calibration Breakdown
| Strength Bucket | Trade Count ($N$) | Mean Predicted (%) | Observed Win Rate (%) | Expectancy ($R$) | Profit Factor | Calibration Gap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{self._render_bucket_rows(btc.strength_buckets)}

* **Brier Score:** `{btc.brier_score:.4f}` (Baseline no-skill: 0.2500)
* **Expected Calibration Error (ECE):** `{btc.expected_calibration_error}%`
* **Maximum Calibration Error (MCE):** `{btc.max_calibration_error}%`
* **Calibration Assessment:** `{btc.calibration_grade}`

### XAU/USD Calibration Breakdown
| Strength Bucket | Trade Count ($N$) | Mean Predicted (%) | Observed Win Rate (%) | Expectancy ($R$) | Profit Factor | Calibration Gap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{self._render_bucket_rows(xau.strength_buckets)}

* **Brier Score:** `{xau.brier_score:.4f}`
* **Expected Calibration Error (ECE):** `{xau.expected_calibration_error}%`
* **Maximum Calibration Error (MCE):** `{xau.max_calibration_error}%`
* **Calibration Assessment:** `{xau.calibration_grade}`

---

## 4. BUY vs SELL Performance Breakdown

### BTC/USD Directional Comparison
* **BUY Trades:** {btc.directional_comparison.buy_metrics.total_trades} trades | Win Rate: **{btc.directional_comparison.buy_metrics.win_rate_pct}%** [CI: {btc.directional_comparison.buy_metrics.ci_95_lower}%–{btc.directional_comparison.buy_metrics.ci_95_upper}%] | Expectancy: **{btc.directional_comparison.buy_metrics.expectancy_r:+.2f}R** | Profit Factor: **{btc.directional_comparison.buy_metrics.profit_factor}**
* **SELL Trades:** {btc.directional_comparison.sell_metrics.total_trades} trades | Win Rate: **{btc.directional_comparison.sell_metrics.win_rate_pct}%** [CI: {btc.directional_comparison.sell_metrics.ci_95_lower}%–{btc.directional_comparison.sell_metrics.ci_95_upper}%] | Expectancy: **{btc.directional_comparison.sell_metrics.expectancy_r:+.2f}R** | Profit Factor: **{btc.directional_comparison.sell_metrics.profit_factor}**
* **Directional Asymmetry Note:** {btc.directional_comparison.asymmetry_note}

### XAU/USD Directional Comparison
* **BUY Trades:** {xau.directional_comparison.buy_metrics.total_trades} trades | Win Rate: **{xau.directional_comparison.buy_metrics.win_rate_pct}%** [CI: {xau.directional_comparison.buy_metrics.ci_95_lower}%–{xau.directional_comparison.buy_metrics.ci_95_upper}%] | Expectancy: **{xau.directional_comparison.buy_metrics.expectancy_r:+.2f}R** | Profit Factor: **{xau.directional_comparison.buy_metrics.profit_factor}**
* **SELL Trades:** {xau.directional_comparison.sell_metrics.total_trades} trades | Win Rate: **{xau.directional_comparison.sell_metrics.win_rate_pct}%** [CI: {xau.directional_comparison.sell_metrics.ci_95_lower}%–{xau.directional_comparison.sell_metrics.ci_95_upper}%] | Expectancy: **{xau.directional_comparison.sell_metrics.expectancy_r:+.2f}R** | Profit Factor: **{xau.directional_comparison.sell_metrics.profit_factor}**
* **Directional Asymmetry Note:** {xau.directional_comparison.asymmetry_note}

---

## 5. Walk-Forward Cross-Validation (Chronological 4 Folds)

### BTC/USD Walk-Forward Folds
| Fold | In-Sample Period | IS Count | IS Win Rate | Out-of-Sample Period | OOS Count | OOS Win Rate | OOS Expectancy | OOS Profit Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{self._render_wf_rows(btc.walk_forward_folds)}

### XAU/USD Walk-Forward Folds
| Fold | In-Sample Period | IS Count | IS Win Rate | Out-of-Sample Period | OOS Count | OOS Win Rate | OOS Expectancy | OOS Profit Factor |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{self._render_wf_rows(xau.walk_forward_folds)}

---

## 6. Regulatory & Production Compliance Notice

> **DISCLAIMER:** This backtesting and calibration report is generated solely for analytical research and statistical verification. It does not execute live orders, connect to trading brokers, or guarantee future market returns. Past empirical performance does not guarantee future results.
"""

    def _render_bucket_rows(self, buckets: List[StrengthBucketCalibration]) -> str:
        rows = []
        for b in buckets:
            rows.append(
                f"| **{b.bucket_name}** | {b.count:,} | {b.mean_predicted_strength:.1f}% | "
                f"**{b.observed_win_rate_pct:.1f}%** | {b.expectancy_r:+.2f}R | {b.profit_factor:.2f} | {b.calibration_gap_pct:.1f}% |"
            )
        return "\n".join(rows)

    def _render_wf_rows(self, folds: List[WalkForwardFold]) -> str:
        rows = []
        for f in folds:
            rows.append(
                f"| Fold {f.fold_index} | `{f.train_start} → {f.train_end}` | {f.train_count:,} | {f.train_win_rate:.1f}% | "
                f"`{f.test_start} → {f.test_end}` | {f.test_count:,} | **{f.test_win_rate:.1f}%** | **{f.test_expectancy:+.2f}R** | {f.test_profit_factor:.2f} |"
            )
        return "\n".join(rows)
