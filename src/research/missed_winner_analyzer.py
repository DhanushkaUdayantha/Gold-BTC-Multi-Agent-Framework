"""
Phase 3 Missed Winner Analyzer.

Analyzes the cohort of winning trades that were rejected by hypothetical gating
(Policy A — Strict Qualification) to determine:

1. What features the 597 rejected winners share.
2. Which filter(s) rejected them.
3. Whether those rejections were justified.
4. Whether Policy A is overly restrictive.

Classification:
  OVERLY_RESTRICTIVE  — filter removes more winners than losers (by R) without justification
  APPROPRIATE         — filter removes materially more losers than winners
  INSUFFICIENT_DATA   — sample too small for conclusive analysis

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CohortStats:
    """Summary statistics for a trade sub-cohort."""
    cohort_name: str
    count: int
    win_rate_pct: float
    expectancy_r: float
    total_r: float
    avg_probability: float
    avg_confluence: float
    common_regimes: List[str] = field(default_factory=list)
    common_sessions: List[str] = field(default_factory=list)
    pct_htf_aligned: float = 0.0
    pct_vwap_aligned: float = 0.0
    pct_ema_aligned: float = 0.0
    pct_sr_aligned: float = 0.0
    pct_mom_aligned: float = 0.0
    avg_confirmation: float = 0.0


@dataclass
class FilterInspection:
    """Inspection of a single filter's impact on the missed-winner cohort."""
    filter_name: str
    missed_winners_rejected_by_this: int
    missed_winners_passed_by_this: int
    rejection_pct: float          # % of missed winners this filter catches
    justification: str            # WHY this filter rejects them


@dataclass
class MissedWinnerReport:
    """Complete analysis of rejected winning trades."""
    # Cohort statistics
    rejected_winners: CohortStats
    retained_winners: CohortStats
    rejected_losers: CohortStats
    retained_losers: CohortStats

    # Key findings
    winner_retention_pct: float        # % of all winners that passed gating
    loser_reduction_pct: float         # % of all losers that were removed
    winner_r_lost: float               # Total R from rejected winners
    loser_r_saved: float               # Total R saved by removing losers
    net_r_impact: float                # loser_r_saved - winner_r_lost
    selectivity_score: float           # loser_reduction / winner_rejection (>1 = beneficial)
    benefit_cost_ratio: float          # loser_r_saved / winner_r_lost

    # Feature comparison: rejected winners vs retained winners
    feature_diff: Dict[str, float] = field(default_factory=dict)

    # Filter attribution
    filter_inspections: List[FilterInspection] = field(default_factory=list)
    top_rejecting_filters: List[str] = field(default_factory=list)

    # Common characteristics of rejected winners
    common_characteristics: List[str] = field(default_factory=list)

    # Classification
    policy_classification: str = "INSUFFICIENT_DATA"   # OVERLY_RESTRICTIVE / APPROPRIATE / INSUFFICIENT_DATA
    evidence: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # BTC vs XAU split
    btc_missed_count: int = 0
    xau_missed_count: int = 0


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class MissedWinnerAnalyzer:
    """
    Analyzes rejected winners from hypothetical Policy A gating.

    Input records must have the following attributes (duck-typed):
      - outcome: "WIN" / "LOSS" / "EXPIRED"
      - realized_r: float
      - gating.would_qualify_policy_a: bool   (True = passed gating)
      - asset, regime, session
      - indicators.vwap_aligned, ema_aligned, sr_aligned, mom_aligned
      - mtf.htf_aligned
      - strategy_scores.confluence_score, confirmation_score
      - ai.ai_probability
    """

    MIN_SAMPLE_THRESHOLD = 30

    @classmethod
    def analyze(
        cls,
        records: List[Any],
        policy_attr: str = "would_qualify_policy_a",
    ) -> MissedWinnerReport:
        """
        Run the full missed-winner analysis.

        ``policy_attr`` is the attribute name on ``gating`` that indicates
        whether the signal passed Policy A.
        """
        # Partition
        all_trades = [r for r in records if getattr(r, "is_trade", False) or
                      getattr(r, "outcome", "") in ("WIN", "LOSS", "EXPIRED")]

        def passed(r: Any) -> bool:
            gating = getattr(r, "gating", None)
            if gating is None:
                return True  # No gating info → assume passed
            return bool(getattr(gating, policy_attr, True))

        def is_win(r: Any) -> bool:
            return getattr(r, "outcome", "") == "WIN"

        def is_loss(r: Any) -> bool:
            return getattr(r, "outcome", "") in ("LOSS", "EXPIRED")

        rejected_winners = [r for r in all_trades if not passed(r) and is_win(r)]
        retained_winners = [r for r in all_trades if passed(r) and is_win(r)]
        rejected_losers  = [r for r in all_trades if not passed(r) and is_loss(r)]
        retained_losers  = [r for r in all_trades if passed(r) and is_loss(r)]

        all_winners = retained_winners + rejected_winners
        all_losers  = retained_losers + rejected_losers

        # Cohort statistics
        rw_stats  = cls._cohort_stats("REJECTED_WINNERS", rejected_winners)
        ret_stats = cls._cohort_stats("RETAINED_WINNERS", retained_winners)
        rl_stats  = cls._cohort_stats("REJECTED_LOSERS", rejected_losers)
        retl_stats= cls._cohort_stats("RETAINED_LOSERS", retained_losers)

        # Core metrics
        total_winners = len(all_winners)
        total_losers  = len(all_losers)
        wr_ret_pct = round(len(retained_winners) / max(total_winners, 1) * 100, 1)
        lr_red_pct = round(len(rejected_losers)  / max(total_losers, 1)  * 100, 1)

        winner_r_lost = sum(getattr(r, "realized_r", 0.0) or 0.0 for r in rejected_winners)
        loser_r_saved = abs(sum(getattr(r, "realized_r", 0.0) or 0.0 for r in rejected_losers))
        net_r = round(loser_r_saved - winner_r_lost, 2)
        selectivity = round(lr_red_pct / max(100 - wr_ret_pct, 0.01), 2)
        bcr = round(loser_r_saved / max(abs(winner_r_lost), 0.01), 2)

        # Feature comparison
        feature_diff = cls._compare_features(rejected_winners, retained_winners)

        # Common characteristics
        common_chars = cls._find_common_characteristics(rejected_winners, rw_stats)

        # Filter attribution
        filter_insp = cls._inspect_filters(rejected_winners)
        top_filters = [f.filter_name for f in sorted(filter_insp, key=lambda x: x.rejection_pct, reverse=True)[:3]]

        # Asset split
        btc_missed = sum(1 for r in rejected_winners if "BTC" in getattr(r, "asset", ""))
        xau_missed = sum(1 for r in rejected_winners if "XAU" in getattr(r, "asset", ""))

        # Policy classification
        classification, evidence, recommendations = cls._classify_policy(
            wr_ret_pct, lr_red_pct, bcr, len(rejected_winners), len(rejected_losers)
        )

        return MissedWinnerReport(
            rejected_winners=rw_stats,
            retained_winners=ret_stats,
            rejected_losers=rl_stats,
            retained_losers=retl_stats,
            winner_retention_pct=wr_ret_pct,
            loser_reduction_pct=lr_red_pct,
            winner_r_lost=round(winner_r_lost, 2),
            loser_r_saved=round(loser_r_saved, 2),
            net_r_impact=net_r,
            selectivity_score=selectivity,
            benefit_cost_ratio=bcr,
            feature_diff=feature_diff,
            filter_inspections=filter_insp,
            top_rejecting_filters=top_filters,
            common_characteristics=common_chars,
            policy_classification=classification,
            evidence=evidence,
            recommendations=recommendations,
            btc_missed_count=btc_missed,
            xau_missed_count=xau_missed,
        )

    # ------------------------------------------------------------------ helpers

    @classmethod
    def _cohort_stats(cls, name: str, records: List[Any]) -> CohortStats:
        if not records:
            return CohortStats(name, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

        wins = [r for r in records if getattr(r, "outcome", "") == "WIN"]
        r_vals = [getattr(r, "realized_r", 0.0) or 0.0 for r in records]
        probs = [getattr(getattr(r, "ai", None), "ai_probability", 0.0) or 0.0 for r in records]
        confl = [getattr(getattr(r, "strategy_scores", None), "confluence_score", 0) or 0 for r in records]
        confs = [getattr(getattr(r, "strategy_scores", None), "confirmation_score", 0) or 0 for r in records]

        from collections import Counter
        regime_ctr = Counter(getattr(r, "regime", "UNKNOWN") for r in records)
        session_ctr = Counter(getattr(r, "session", "UNKNOWN") for r in records)

        def pct_attr(attr_path: str) -> float:
            hits = 0
            for r in records:
                parts = attr_path.split(".")
                obj = r
                for p in parts:
                    obj = getattr(obj, p, None)
                    if obj is None:
                        break
                if obj:
                    hits += 1
            return round(hits / len(records) * 100, 1)

        return CohortStats(
            cohort_name=name,
            count=len(records),
            win_rate_pct=round(len(wins) / len(records) * 100, 1),
            expectancy_r=round(float(np.mean(r_vals)), 3),
            total_r=round(float(np.sum(r_vals)), 2),
            avg_probability=round(float(np.mean(probs)), 3),
            avg_confluence=round(float(np.mean(confl)), 1),
            common_regimes=[k for k, _ in regime_ctr.most_common(3)],
            common_sessions=[k for k, _ in session_ctr.most_common(3)],
            pct_htf_aligned=pct_attr("mtf.htf_aligned"),
            pct_vwap_aligned=pct_attr("indicators.vwap_aligned"),
            pct_ema_aligned=pct_attr("indicators.ema_aligned"),
            pct_sr_aligned=pct_attr("indicators.sr_aligned"),
            pct_mom_aligned=pct_attr("indicators.momentum_aligned"),
            avg_confirmation=round(float(np.mean(confs)), 1),
        )

    @staticmethod
    def _compare_features(
        rejected_winners: List[Any],
        retained_winners: List[Any],
    ) -> Dict[str, float]:
        """
        Compute difference in feature averages between the two cohorts.
        Positive = rejected winners have HIGHER value; negative = lower.
        """
        if not rejected_winners or not retained_winners:
            return {}

        def avg(records: List[Any], attr_path: str) -> float:
            vals = []
            for r in records:
                obj = r
                for p in attr_path.split("."):
                    obj = getattr(obj, p, None)
                    if obj is None:
                        break
                if isinstance(obj, (int, float, bool)):
                    vals.append(float(obj))
            return float(np.mean(vals)) if vals else 0.0

        attrs = {
            "ai_probability": "ai.ai_probability",
            "confluence_score": "strategy_scores.confluence_score",
            "confirmation_score": "strategy_scores.confirmation_score",
            "htf_aligned": "mtf.htf_aligned",
            "vwap_aligned": "indicators.vwap_aligned",
            "ema_aligned": "indicators.ema_aligned",
            "sr_aligned": "indicators.sr_aligned",
            "momentum_aligned": "indicators.momentum_aligned",
        }
        return {
            k: round(avg(rejected_winners, path) - avg(retained_winners, path), 3)
            for k, path in attrs.items()
        }

    @staticmethod
    def _inspect_filters(rejected_winners: List[Any]) -> List[FilterInspection]:
        """Approximate attribution of rejections to individual filters."""
        total = max(len(rejected_winners), 1)
        inspections = []

        filters_to_check = [
            ("VWAP_ALIGNMENT", "indicators.vwap_aligned", False,
             "Signal direction not confirmed by VWAP"),
            ("EMA_ALIGNMENT", "indicators.ema_aligned", False,
             "EMA stack not aligned with signal"),
            ("HTF_ALIGNMENT", "mtf.htf_aligned", False,
             "Higher-timeframe trend disagrees"),
            ("MOMENTUM", "indicators.momentum_aligned", False,
             "Momentum indicator not aligned"),
            ("SR_ALIGNMENT", "indicators.sr_aligned", False,
             "S/R not in favour of signal"),
        ]

        for fname, attr_path, reject_val, justification in filters_to_check:
            rejected_by = 0
            for r in rejected_winners:
                obj = r
                for p in attr_path.split("."):
                    obj = getattr(obj, p, None)
                    if obj is None:
                        break
                val = bool(obj) if isinstance(obj, (int, float, bool)) else False
                if val == reject_val:
                    rejected_by += 1

            inspections.append(FilterInspection(
                filter_name=fname,
                missed_winners_rejected_by_this=rejected_by,
                missed_winners_passed_by_this=total - rejected_by,
                rejection_pct=round(rejected_by / total * 100, 1),
                justification=justification,
            ))

        return inspections

    @staticmethod
    def _find_common_characteristics(
        rejected_winners: List[Any],
        stats: CohortStats,
    ) -> List[str]:
        chars = []
        if not rejected_winners:
            return chars
        if stats.avg_probability < 0.45:
            chars.append(f"Low avg AI probability ({stats.avg_probability:.2%}) — below 45% threshold")
        if stats.pct_htf_aligned < 40:
            chars.append(f"Low HTF alignment ({stats.pct_htf_aligned}%) — trend often opposes signal")
        if stats.pct_vwap_aligned < 40:
            chars.append(f"Low VWAP alignment ({stats.pct_vwap_aligned}%) — signal against VWAP")
        if stats.common_regimes:
            chars.append(f"Most common regime: {stats.common_regimes[0]}")
        if stats.common_sessions:
            chars.append(f"Most common session: {stats.common_sessions[0]}")
        if stats.avg_confirmation <= 1.5:
            chars.append(f"Low average confirmation score ({stats.avg_confirmation:.1f})")
        return chars

    @staticmethod
    def _classify_policy(
        wr_ret_pct: float,
        lr_red_pct: float,
        bcr: float,
        n_missed_winners: int,
        n_rejected_losers: int,
    ) -> Tuple[str, List[str], List[str]]:
        evidence = []
        recommendations = []

        if n_missed_winners < 30:
            return "INSUFFICIENT_DATA", ["Sample < 30 missed winners"], []

        # Beneficial if BCR > 1.5 and loser reduction > winner rejection
        if bcr >= 1.5 and lr_red_pct > (100 - wr_ret_pct) * 1.3:
            evidence.append(f"BCR={bcr:.2f} — saves materially more loser R than it misses in winner R")
            evidence.append(f"Loser reduction {lr_red_pct:.1f}% >> winner rejection {100-wr_ret_pct:.1f}%")
            recommendations.append("Policy A is broadly appropriate; consider asset-specific relaxation")
            return "APPROPRIATE", evidence, recommendations

        # Overly restrictive if too many winners are removed and BCR < 1.0
        if bcr < 1.0 and (100 - wr_ret_pct) > lr_red_pct * 0.8:
            evidence.append(f"BCR={bcr:.2f} — removes more winner R than loser R")
            evidence.append(f"Winner rejection {100-wr_ret_pct:.1f}% ≈ loser reduction {lr_red_pct:.1f}%")
            recommendations.append("Policy A may be over-filtering; investigate VWAP and HTF conditions separately")
            recommendations.append("Consider regime-specific relaxation for TRENDING markets")
            return "OVERLY_RESTRICTIVE", evidence, recommendations

        evidence.append(f"BCR={bcr:.2f}; winner retention={wr_ret_pct:.1f}%; loser reduction={lr_red_pct:.1f}%")
        recommendations.append("Evidence is mixed; further asset-specific ablation recommended")
        return "APPROPRIATE", evidence, recommendations
