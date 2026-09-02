"""
Performance Engine — computes empirical statistics from completed signal records.

Calculates:
- Overall win rate, expectancy, profit factor, max drawdown (R-based)
- Per confluence-score-band statistics (0-49, 50-59, ..., 90-100)
- Per-contributor/strategy statistics (17 contributors)
- Gemini AI performance + ablation analysis
- Pairwise contributor correlation (informational)
- Dataset integrity validation

IMPORTANT: All metrics are derived exclusively from completed historical signals.
No values are assumed, hardcoded, or fabricated.
Statistics are reported as "INSUFFICIENT DATA" when sample sizes are too small.

DISCLAIMER: Advisory analytical signals only. No real trades.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.models.signal_record import (
    SignalRecord,
    OverallStats,
    ScoreBandStats,
    StrategyStats,
    GeminiPerformanceStats,
    PerformanceReport,
    CalibrationResult,
    _score_band,
)

logger = logging.getLogger(__name__)

_MIN_STATS_SAMPLE = 10      # minimum signals required to compute win rate etc.
_SCORE_BANDS = ["0-49", "50-59", "60-69", "70-79", "80-89", "90-100"]


class PerformanceEngine:
    """
    Computes empirical performance metrics from completed SignalRecord objects.
    Caller is responsible for passing ONLY completed (terminal-outcome) records.
    """

    def compute_report(
        self,
        all_records: List[SignalRecord],
        calibration_result: Optional[CalibrationResult] = None,
    ) -> PerformanceReport:
        """Build a full PerformanceReport from all signal records."""
        now_iso = datetime.now(timezone.utc).isoformat()

        terminal = {"WIN", "LOSS", "BREAKEVEN", "EXPIRED", "INVALID"}
        completed = [
            r for r in all_records
            if (r.outcome and r.outcome.outcome in terminal
                and r.outcome.outcome not in ("EXPIRED", "INVALID"))
        ]
        expired = [r for r in all_records if r.outcome and r.outcome.outcome == "EXPIRED"]
        invalid = [r for r in all_records if r.outcome and r.outcome.outcome == "INVALID"]
        open_sigs = [r for r in all_records if not r.outcome or r.outcome.outcome == "OPEN"]

        # Dataset integrity
        issues, _ = self._validate_dataset(all_records)

        overall = self._compute_overall(completed)
        by_band = self._compute_by_band(completed)
        by_strategy = self._compute_by_strategy(completed)
        gemini_stats = self._compute_gemini_stats(completed)
        correlation = self._compute_correlation(completed)

        tx_included = any(
            r.outcome and r.outcome.transaction_cost_included for r in completed
        )
        tx_note = (
            "Spread deducted from realized R where bid/ask was available"
            if tx_included
            else "Transaction costs not included — spread/commission not deducted"
        )

        return PerformanceReport(
            generated_at=now_iso,
            symbol="XAU/USD",
            total_completed=len(completed),
            total_open=len(open_sigs),
            total_expired=len(expired),
            total_invalid=len(invalid),
            total_signals_recorded=len(all_records),
            overall=overall,
            by_score_band=by_band,
            by_strategy=by_strategy,
            calibration=calibration_result or CalibrationResult(
                calibration_status="INSUFFICIENT_DATA",
                sample_size=len(completed),
            ),
            gemini_analysis=gemini_stats,
            data_integrity_issues=issues,
            transaction_costs_included=tx_included,
            transaction_cost_note=tx_note,
            regime_analysis_available=False,
            correlation_analysis=correlation,
        )

    # ------------------------------------------------------------------
    # Overall statistics
    # ------------------------------------------------------------------

    def _compute_overall(self, completed: List[SignalRecord]) -> OverallStats:
        if not completed:
            return OverallStats(note="No completed signals yet")

        wins = [r for r in completed if r.outcome and r.outcome.outcome == "WIN"]
        losses = [r for r in completed if r.outcome and r.outcome.outcome == "LOSS"]
        breakevens = [r for r in completed if r.outcome and r.outcome.outcome == "BREAKEVEN"]

        n = len(completed)
        n_wins = len(wins)
        n_losses = len(losses)
        n_be = len(breakevens)

        if n < _MIN_STATS_SAMPLE:
            return OverallStats(
                total_signals=n, wins=n_wins, losses=n_losses, breakeven=n_be,
                note=f"Insufficient data (need ≥{_MIN_STATS_SAMPLE} completed signals, have {n})"
            )

        win_rate = n_wins / n if n > 0 else None
        loss_rate = n_losses / n if n > 0 else None

        win_rs = [r.outcome.realized_r for r in wins if r.outcome and r.outcome.realized_r is not None]
        loss_rs = [r.outcome.realized_r for r in losses if r.outcome and r.outcome.realized_r is not None]
        all_rs = [r.outcome.realized_r for r in completed if r.outcome and r.outcome.realized_r is not None]

        avg_win_r = _safe_mean(win_rs)
        avg_loss_r = _safe_mean(loss_rs)
        avg_r = _safe_mean(all_rs)

        gross_win = sum(r for r in win_rs if r > 0)
        gross_loss = abs(sum(r for r in loss_rs if r < 0))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None

        expectancy = None
        if win_rate is not None and avg_win_r is not None and avg_loss_r is not None and loss_rate is not None:
            expectancy = round(win_rate * avg_win_r + loss_rate * avg_loss_r, 4)

        max_dd = self._compute_max_drawdown_r(completed)

        mfes = [r.outcome.mfe for r in completed if r.outcome and r.outcome.mfe is not None]
        maes = [r.outcome.mae for r in completed if r.outcome and r.outcome.mae is not None]

        return OverallStats(
            total_signals=n,
            wins=n_wins,
            losses=n_losses,
            breakeven=n_be,
            win_rate=_pct(win_rate),
            average_win_r=_round4(avg_win_r),
            average_loss_r=_round4(avg_loss_r),
            average_r=_round4(avg_r),
            expectancy=_round4(expectancy),
            profit_factor=_round2(profit_factor),
            max_drawdown_r=_round4(max_dd),
            average_mfe=_round4(_safe_mean(mfes)),
            average_mae=_round4(_safe_mean(maes)),
            note=f"Based on {n} completed signals",
        )

    # ------------------------------------------------------------------
    # Score band statistics
    # ------------------------------------------------------------------

    def _compute_by_band(self, completed: List[SignalRecord]) -> List[ScoreBandStats]:
        stats = []
        for band in _SCORE_BANDS:
            band_signals = [r for r in completed if r.score_band == band]
            stats.append(self._band_stats(band, band_signals))
        return stats

    def _band_stats(self, band: str, signals: List[SignalRecord]) -> ScoreBandStats:
        n = len(signals)
        if n == 0:
            return ScoreBandStats(band=band, note="No signals in this band yet")

        wins = [r for r in signals if r.outcome and r.outcome.outcome == "WIN"]
        losses = [r for r in signals if r.outcome and r.outcome.outcome == "LOSS"]

        if n < _MIN_STATS_SAMPLE:
            return ScoreBandStats(
                band=band,
                sample_size=n,
                wins=len(wins),
                losses=len(losses),
                note=f"Insufficient data (need ≥{_MIN_STATS_SAMPLE}, have {n})",
            )

        win_rate = len(wins) / n
        loss_rate = len(losses) / n

        win_rs = [r.outcome.realized_r for r in wins if r.outcome and r.outcome.realized_r is not None]
        loss_rs = [r.outcome.realized_r for r in losses if r.outcome and r.outcome.realized_r is not None]
        all_rs = [r.outcome.realized_r for r in signals if r.outcome and r.outcome.realized_r is not None]

        avg_win_r = _safe_mean(win_rs) or 0.0
        avg_loss_r = _safe_mean(loss_rs) or 0.0
        avg_r = _safe_mean(all_rs)

        gross_win = sum(r for r in win_rs if r > 0)
        gross_loss = abs(sum(r for r in loss_rs if r < 0))
        pf = (gross_win / gross_loss) if gross_loss > 0 else None

        expectancy = round(win_rate * avg_win_r + loss_rate * avg_loss_r, 4)
        max_dd = self._compute_max_drawdown_r(signals)

        return ScoreBandStats(
            band=band,
            sample_size=n,
            wins=len(wins),
            losses=len(losses),
            win_rate=_pct(win_rate),
            average_r=_round4(avg_r),
            expectancy=_round4(expectancy),
            profit_factor=_round2(pf),
            max_drawdown_r=_round4(max_dd),
        )

    # ------------------------------------------------------------------
    # Strategy-level statistics
    # ------------------------------------------------------------------

    def _compute_by_strategy(self, completed: List[SignalRecord]) -> List[StrategyStats]:
        """
        Compute statistics for each contributor independently.
        A signal "uses" a contributor if that contributor's score > 0.
        """
        # Collect all contributor names from completed signals
        all_names: set = set()
        for r in completed:
            all_names.update(r.contributor_scores.keys())

        stats = []
        for name in sorted(all_names):
            relevant = [r for r in completed if r.contributor_scores.get(name, 0) > 0]
            stats.append(self._strategy_stats(name, relevant))
        return stats

    def _strategy_stats(self, name: str, signals: List[SignalRecord]) -> StrategyStats:
        n = len(signals)
        if n == 0:
            return StrategyStats(strategy_name=name, note="No signals with this contributor active")

        wins = [r for r in signals if r.outcome and r.outcome.outcome == "WIN"]
        losses = [r for r in signals if r.outcome and r.outcome.outcome == "LOSS"]

        if n < _MIN_STATS_SAMPLE:
            return StrategyStats(
                strategy_name=name,
                total_signals=n,
                wins=len(wins),
                losses=len(losses),
                note=f"Insufficient data (need ≥{_MIN_STATS_SAMPLE}, have {n})",
            )

        win_rate = len(wins) / n
        loss_rate = len(losses) / n

        win_rs = [r.outcome.realized_r for r in wins if r.outcome and r.outcome.realized_r is not None]
        loss_rs = [r.outcome.realized_r for r in losses if r.outcome and r.outcome.realized_r is not None]
        all_rs = [r.outcome.realized_r for r in signals if r.outcome and r.outcome.realized_r is not None]

        avg_win_r = _safe_mean(win_rs) or 0.0
        avg_loss_r = _safe_mean(loss_rs) or 0.0
        avg_r = _safe_mean(all_rs)

        gross_win = sum(r for r in win_rs if r > 0)
        gross_loss = abs(sum(r for r in loss_rs if r < 0))
        pf = (gross_win / gross_loss) if gross_loss > 0 else None

        expectancy = round(win_rate * avg_win_r + loss_rate * avg_loss_r, 4)
        max_dd = self._compute_max_drawdown_r(signals)

        mfes = [r.outcome.mfe for r in signals if r.outcome and r.outcome.mfe is not None]
        maes = [r.outcome.mae for r in signals if r.outcome and r.outcome.mae is not None]

        return StrategyStats(
            strategy_name=name,
            total_signals=n,
            wins=len(wins),
            losses=len(losses),
            win_rate=_pct(win_rate),
            average_r=_round4(avg_r),
            expectancy=_round4(expectancy),
            profit_factor=_round2(pf),
            max_drawdown_r=_round4(max_dd),
            average_mfe=_round4(_safe_mean(mfes)),
            average_mae=_round4(_safe_mean(maes)),
        )

    # ------------------------------------------------------------------
    # Gemini performance + ablation
    # ------------------------------------------------------------------

    def _compute_gemini_stats(self, completed: List[SignalRecord]) -> GeminiPerformanceStats:
        if not completed:
            return GeminiPerformanceStats()

        gemini_signals = [r for r in completed if r.gemini_score > 0]
        total = len(gemini_signals)

        if total < _MIN_STATS_SAMPLE:
            return GeminiPerformanceStats(
                total_gemini_signals=total,
                note=f"Insufficient Gemini data (need ≥{_MIN_STATS_SAMPLE}, have {total})",
            )

        # Direction accuracy: gemini bias matches signal direction?
        correct_dir = 0
        for r in gemini_signals:
            gemini_bias = r.contributor_biases.get("Gemini AI", "")
            if (r.direction == "BUY" and gemini_bias == "BULLISH") or \
               (r.direction == "SELL" and gemini_bias == "BEARISH"):
                correct_dir += 1
        dir_accuracy = correct_dir / total if total > 0 else None

        # Agreement rate with technical engine
        agreement_count = sum(
            1 for r in gemini_signals
            if r.gate_direction in ("BULLISH", "BEARISH") and (
                (r.direction == "BUY" and r.gate_direction == "BULLISH") or
                (r.direction == "SELL" and r.gate_direction == "BEARISH")
            )
        )
        agreement_rate = agreement_count / total if total > 0 else None
        conflict_rate = 1.0 - agreement_rate if agreement_rate is not None else None

        # Ablation: compare with-Gemini vs without-Gemini signals
        with_g = gemini_signals
        without_g = [r for r in completed if r.gemini_score == 0]

        n_with = len(with_g)
        n_without = len(without_g)

        ablation_note = "Ablation requires ≥50 completed signals in each group"
        with_wr = with_ex = without_wr = without_ex = None
        gemini_improves = None

        if n_with >= _MIN_STATS_SAMPLE and n_without >= _MIN_STATS_SAMPLE:
            with_wins = [r for r in with_g if r.outcome and r.outcome.outcome == "WIN"]
            without_wins = [r for r in without_g if r.outcome and r.outcome.outcome == "WIN"]
            with_wr = _pct(len(with_wins) / n_with)
            without_wr = _pct(len(without_wins) / n_without)
            with_rs = [r.outcome.realized_r for r in with_g if r.outcome and r.outcome.realized_r is not None]
            without_rs = [r.outcome.realized_r for r in without_g if r.outcome and r.outcome.realized_r is not None]
            with_ex = _round4(_safe_mean(with_rs))
            without_ex = _round4(_safe_mean(without_rs))
            # Only declare improvement if meaningfully better (>2ppt win rate + positive expectancy delta)
            if with_wr is not None and without_wr is not None:
                gemini_improves = (
                    (with_wr - without_wr > 2.0) and
                    (with_ex is not None and without_ex is not None and with_ex > without_ex)
                )
                ablation_note = (
                    f"Gemini group n={n_with}, No-Gemini group n={n_without}. "
                    f"Improvement: {'YES' if gemini_improves else 'NO (insufficient edge)'}"
                )

        return GeminiPerformanceStats(
            total_gemini_signals=total,
            gemini_direction_accuracy=_pct(dir_accuracy),
            gemini_agreement_rate=_pct(agreement_rate),
            gemini_conflict_rate=_pct(conflict_rate),
            ablation_with_gemini_win_rate=with_wr,
            ablation_without_gemini_win_rate=without_wr,
            ablation_with_gemini_expectancy=with_ex,
            ablation_without_gemini_expectancy=without_ex,
            ablation_sample_size=n_with + n_without,
            ablation_note=ablation_note,
            gemini_improves_performance=gemini_improves,
        )

    # ------------------------------------------------------------------
    # Correlation analysis (informational only)
    # ------------------------------------------------------------------

    def _compute_correlation(self, completed: List[SignalRecord]) -> Dict[str, Any]:
        """
        Compute pairwise contributor correlation (binary: was score > 0?).
        Returns informational dict — does NOT remove or modify any contributor.
        """
        if len(completed) < _MIN_STATS_SAMPLE:
            return {"note": "Insufficient data for correlation analysis"}

        # Build binary matrix
        all_names = sorted(set(
            name for r in completed for name in r.contributor_scores.keys()
        ))
        if len(all_names) < 2:
            return {"note": "Too few contributors for correlation analysis"}

        # Compute pairwise correlation of active flags
        high_correlation_pairs = []
        for i, n1 in enumerate(all_names):
            for j, n2 in enumerate(all_names):
                if j <= i:
                    continue
                v1 = [1 if r.contributor_scores.get(n1, 0) > 0 else 0 for r in completed]
                v2 = [1 if r.contributor_scores.get(n2, 0) > 0 else 0 for r in completed]
                corr = _pearson(v1, v2)
                if corr is not None and corr > 0.85:
                    high_correlation_pairs.append({
                        "contributors": [n1, n2],
                        "correlation": round(corr, 3),
                        "note": "High evidence correlation — apparent confluence may be less independent",
                    })

        return {
            "contributors_analyzed": len(all_names),
            "high_correlation_pairs": high_correlation_pairs,
            "note": (
                "High correlation does NOT mean contributors are removed. "
                "It is reported for transparency only."
            ),
        }

    # ------------------------------------------------------------------
    # Drawdown calculation (R-based)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_max_drawdown_r(signals: List[SignalRecord]) -> Optional[float]:
        """
        Compute maximum drawdown in R units from chronological signal sequence.
        Uses only completed signals with realized_r values.
        """
        rs = []
        try:
            chrono = sorted(
                signals,
                key=lambda r: r.signal_timestamp or "",
            )
            for r in chrono:
                if r.outcome and r.outcome.realized_r is not None:
                    rs.append(r.outcome.realized_r)
        except Exception:
            return None

        if not rs:
            return None

        peak = 0.0
        max_dd = 0.0
        cumulative = 0.0
        for r in rs:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return round(max_dd, 4) if max_dd > 0 else 0.0

    # ------------------------------------------------------------------
    # Dataset integrity
    # ------------------------------------------------------------------

    def _validate_dataset(self, all_records: List[SignalRecord]) -> Tuple[List[str], int]:
        """Delegate to repository validation logic."""
        from src.services.signal_repository import get_signal_repository
        return get_signal_repository().validate_dataset()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_mean(values: List) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _pct(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v * 100.0, 2)


def _round4(v: Optional[float]) -> Optional[float]:
    return round(v, 4) if v is not None else None


def _round2(v: Optional[float]) -> Optional[float]:
    return round(v, 2) if v is not None else None


def _pearson(x: List[float], y: List[float]) -> Optional[float]:
    """Simple Pearson correlation for two equal-length lists."""
    n = len(x)
    if n < 3 or len(y) != n:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - my) ** 2 for yi in y))
    denom = denom_x * denom_y
    if denom == 0:
        return None
    return num / denom


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine_instance: Optional[PerformanceEngine] = None


def get_performance_engine() -> PerformanceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PerformanceEngine()
    return _engine_instance
