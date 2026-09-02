"""
Failure, Winner, and Drawdown Forensic Analysis Package.

Modules:
- failure_taxonomy: Deterministic classification of winning and losing trades.
- winner_analysis: Deep empirical profiling of winning trades.
- loser_analysis: Deep empirical profiling of losing trades.
- missed_winners: Missed opportunity & opportunity cost modeling.
- drawdown_analysis: Peak-to-trough drawdown decomposition and recovery tracking.
- clustering: Streak autocorrelation, loss clustering, and rolling metrics.
- segment_analysis: Multi-dimensional segment forensics (Regime, Session, Direction, Confluence, AI, MTF).
- validator: High-level forensic analysis orchestrator.

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
from __future__ import annotations

from src.research.failure_analysis.failure_taxonomy import (
    FAILURE_TAXONOMY_VERSION,
    FailureReason,
    SuccessReason,
    FailureClassification,
    SuccessClassification,
    classify_trade_failure,
    classify_trade_success,
)
from src.research.failure_analysis.winner_analysis import (
    WinnerProfile,
    analyze_winners,
)
from src.research.failure_analysis.loser_analysis import (
    LoserProfile,
    analyze_losers,
)
from src.research.failure_analysis.missed_winners import (
    MissedWinnerReport,
    analyze_missed_winners,
)
from src.research.failure_analysis.drawdown_analysis import (
    DrawdownReport,
    DrawdownEpisode,
    analyze_drawdowns,
)
from src.research.failure_analysis.clustering import (
    ClusteringReport,
    analyze_clustering,
)
from src.research.failure_analysis.segment_analysis import (
    SegmentBreakdown,
    MultiDimensionalForensics,
    run_segment_forensics,
)
from src.research.failure_analysis.validator import (
    AssetForensicAnalysis,
    run_full_failure_forensic_analysis,
)

__all__ = [
    "FAILURE_TAXONOMY_VERSION",
    "FailureReason",
    "SuccessReason",
    "FailureClassification",
    "SuccessClassification",
    "classify_trade_failure",
    "classify_trade_success",
    "WinnerProfile",
    "analyze_winners",
    "LoserProfile",
    "analyze_losers",
    "MissedWinnerReport",
    "analyze_missed_winners",
    "DrawdownReport",
    "DrawdownEpisode",
    "analyze_drawdowns",
    "ClusteringReport",
    "analyze_clustering",
    "SegmentBreakdown",
    "MultiDimensionalForensics",
    "run_segment_forensics",
    "AssetForensicAnalysis",
    "run_full_failure_forensic_analysis",
]
