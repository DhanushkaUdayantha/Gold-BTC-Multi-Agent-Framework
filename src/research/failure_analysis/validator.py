"""
Consolidated Failure, Winner, and Drawdown Forensic Orchestrator.

Orchestrates all Phase 3 forensic analyses for BTC and XAU independently:
- Winner Empirical Profiling
- Loser Empirical Profiling
- Deterministic Failure Taxonomy Classification
- Missed Winner & Opportunity Cost Modeling
- Drawdown Peak-to-Trough Decomposition
- Loss/Win Streak Clustering
- Multi-Dimensional Segmentation

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.research.failure_analysis.failure_taxonomy import (
    FAILURE_TAXONOMY_VERSION,
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
    analyze_drawdowns,
)
from src.research.failure_analysis.clustering import (
    ClusteringReport,
    analyze_clustering,
)
from src.research.failure_analysis.segment_analysis import (
    MultiDimensionalForensics,
    run_segment_forensics,
)

logger = logging.getLogger(__name__)

DB_PATH = "data/historical/historical_market_data.db"


@dataclass
class AssetForensicAnalysis:
    """Full Phase 3 forensic analysis suite for a single asset."""
    symbol: str
    dataset_version: str
    failure_taxonomy_version: str
    analysis_timestamp_utc: str
    total_signals_recorded: int
    resolved_trades_count: int
    expired_signals_count: int
    winners: WinnerProfile
    losers: LoserProfile
    missed_winners: MissedWinnerReport
    drawdown: DrawdownReport
    clustering: ClusteringReport
    segments: MultiDimensionalForensics
    summary_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_historical_trades_from_db(symbol: str, db_path: str = DB_PATH) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Load resolved historical trades from SQLite database.
    
    Returns:
        (resolved_trades_list, resolved_count, expired_count)
    """
    if not os.path.exists(db_path):
        return [], 0, 0

    sym_query = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        rows = cur.execute(
            "SELECT * FROM historical_signals WHERE symbol = ? ORDER BY signal_timestamp ASC",
            (sym_query,),
        ).fetchall()
        conn.close()

        resolved: List[Dict[str, Any]] = []
        expired = 0

        for r in rows:
            outcome = r["outcome"]
            if outcome in ("WIN", "LOSS"):
                resolved.append(dict(r))
            elif outcome == "EXPIRED":
                expired += 1

        return resolved, len(resolved), expired
    except Exception as exc:
        logger.error(f"Error loading historical trades for {symbol}: {exc}")
        return [], 0, 0


def run_full_failure_forensic_analysis(
    symbol: str = "BTC/USD",
    db_path: str = DB_PATH,
) -> AssetForensicAnalysis:
    """
    Execute full Phase 3 failure, winner, and drawdown forensic suite for an asset.
    """
    sym_name = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"

    trades, resolved_n, expired_n = load_historical_trades_from_db(sym_name, db_path)

    # 1. Winner Analysis
    winners_res = analyze_winners(trades, symbol=sym_name)

    # 2. Loser Analysis
    losers_res = analyze_losers(trades, symbol=sym_name)

    # 3. Missed Winner & Opportunity Cost
    missed_res = analyze_missed_winners(trades, symbol=sym_name)

    # 4. Drawdown Analysis
    dd_res = analyze_drawdowns(trades, symbol=sym_name)

    # 5. Clustering Analysis
    cluster_res = analyze_clustering(trades, symbol=sym_name)

    # 6. Multi-Dimensional Segments
    seg_res = run_segment_forensics(trades, symbol=sym_name)

    # Verdict summary
    top_loser_reason = losers_res.top_failure_reasons[0]["reason"] if losers_res.top_failure_reasons else "UNKNOWN"
    top_winner_reason = winners_res.top_success_reasons[0]["reason"] if winners_res.top_success_reasons else "UNKNOWN"

    verdict = (
        f"{sym_name} Forensics: Analyzed {resolved_n} resolved trades. "
        f"Primary winner association: {top_winner_reason} ({winners_res.win_rate_pct}% WR). "
        f"Primary loss mechanism: {top_loser_reason} (Max DD: {dd_res.max_drawdown_r}R). "
        f"Serial autocorrelation: {cluster_res.autocorrelation_lag1}."
    )

    return AssetForensicAnalysis(
        symbol=sym_name,
        dataset_version="v2.1.0-historical-verified",
        failure_taxonomy_version=FAILURE_TAXONOMY_VERSION,
        analysis_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        total_signals_recorded=resolved_n + expired_n,
        resolved_trades_count=resolved_n,
        expired_signals_count=expired_n,
        winners=winners_res,
        losers=losers_res,
        missed_winners=missed_res,
        drawdown=dd_res,
        clustering=cluster_res,
        segments=seg_res,
        summary_verdict=verdict,
    )
