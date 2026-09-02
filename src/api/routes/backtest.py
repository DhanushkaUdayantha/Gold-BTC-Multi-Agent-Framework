"""
Historical Backtesting & Empirical Performance API Routes.

Exposes REST endpoints under /api/v1/backtest for:
- Dataset discovery and historical data downloading
- Asynchronous backtest job management
- Performance analytics, score bands, and strategy contribution breakdown
- Validated probability calibration reporting
- Paginated historical signal exploration with MFE/MAE
- Cumulative R equity curve data

DISCLAIMER: Advisory and empirical research only. Does not execute live broker orders.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from src.models.historical_data import (
    BacktestConfig,
    BacktestRunRecord,
    DatasetMetadata,
    DatasetQualityReport,
    BacktestPerformanceReport,
    HistoricalSignalRecord,
)
from src.services.historical_data_service import HistoricalDataService
from src.services.historical_backtest_runner import HistoricalBacktestRunner
from src.services.live_candle_ingestion_service import LiveCandleIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["Historical Backtesting"])


class DownloadDatasetRequest(BaseModel):
    symbol: str = "BTC/USD"                  # "BTC/USD" or "XAU/USD"
    timeframe: str = "15m"                   # "5m", "15m", "1h", "4h", "1d"
    start_date: str = "2023-01-01"           # YYYY-MM-DD
    end_date: Optional[str] = None           # YYYY-MM-DD
    max_candles: int = 15000


@router.get("/datasets", response_model=List[DatasetMetadata])
def list_datasets():
    """List all registered historical datasets and their data quality status for BTC/USD and XAU/USD."""
    service = HistoricalDataService.get_instance()
    return service.list_datasets()


@router.get("/datasets/status")
def get_dataset_status():
    """Get fast aggregate historical dataset status in sub-50ms (row counts, date bounds, signal stats)."""
    service = HistoricalDataService.get_instance()
    return service.get_fast_dataset_status()


@router.post("/dataset/download")
def download_dataset(req: DownloadDatasetRequest, background_tasks: BackgroundTasks):
    """
    Download real historical data for BTC (Binance BTC/USDT proxy) or Gold (Yahoo Finance GC=F proxy).
    """
    service = HistoricalDataService.get_instance()
    if "BTC" in req.symbol:
        saved, quality = service.download_binance_btc(
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date,
            max_candles=req.max_candles,
        )
        return {
            "status": "SUCCESS" if saved > 0 else "WARNING",
            "message": f"Ingested {saved} historical BTC candles ({req.timeframe}) from Binance.",
            "quality_report": quality,
        }
    elif "XAU" in req.symbol or "GOLD" in req.symbol.upper():
        saved, quality = service.download_yahoo_gold(
            timeframe=req.timeframe,
            range_period="60d",
        )
        return {
            "status": "SUCCESS" if saved > 0 else "WARNING",
            "message": f"Ingested {saved} historical Gold candles ({req.timeframe}) from Yahoo Finance.",
            "quality_report": quality,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol for automated download: {req.symbol}")


@router.post("/run", response_model=BacktestRunRecord)
def start_backtest(config: BacktestConfig):
    """
    Launch an asynchronous historical backtest job across the requested asset and date range.
    """
    runner = HistoricalBacktestRunner()
    run_record = runner.start_backtest_async(config)
    return run_record


@router.get("/runs", response_model=List[BacktestRunRecord])
def list_runs():
    """List all completed and ongoing historical backtest runs."""
    runner = HistoricalBacktestRunner()
    return runner.list_all_runs()


@router.get("/{run_id}", response_model=BacktestRunRecord)
def get_run(run_id: str):
    """Get the current execution lifecycle status and progress of a backtest run."""
    runner = HistoricalBacktestRunner()
    record = runner.get_run_status(run_id)
    if not record:
        # Check database
        runs = runner.list_all_runs()
        match = next((r for r in runs if r.run_id == run_id), None)
        if not match:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")
        return match
    return record


@router.get("/{run_id}/performance", response_model=BacktestPerformanceReport)
def get_run_performance(run_id: str):
    """Get comprehensive empirical performance analytics, score bands, and strategy breakdowns."""
    runner = HistoricalBacktestRunner()
    report = runner.get_run_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Performance report for {run_id} not found or not yet ready")
    return report


@router.get("/{run_id}/signals")
def get_run_signals(
    run_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    outcome: Optional[str] = None,
):
    """Get paginated historical signals with MFE/MAE, realized R, and contributor breakdowns."""
    runner = HistoricalBacktestRunner()
    signals, total = runner.get_run_signals(
        run_id=run_id,
        limit=limit,
        offset=offset,
        outcome_filter=outcome,
    )
    return {
        "run_id": run_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "signals": signals,
    }


@router.get("/{run_id}/calibration")
def get_run_calibration(run_id: str):
    """Get validated empirical calibration curve, Brier score, and train/val split metrics."""
    runner = HistoricalBacktestRunner()
    report = runner.get_run_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Calibration report for {run_id} not found")
    return {
        "run_id": run_id,
        "sample_size": report.sample_size,
        "training_size": report.training_size,
        "validation_size": report.validation_size,
        "calibration_status": report.calibration_status,
        "in_sample_win_rate": report.in_sample_win_rate,
        "out_of_sample_win_rate": report.out_of_sample_win_rate,
        "out_of_sample_brier_score": report.out_of_sample_brier_score,
        "out_of_sample_accuracy": report.out_of_sample_accuracy,
        "calibration_curve": report.calibration_curve,
    }


@router.get("/{run_id}/equity-curve")
def get_run_equity_curve(run_id: str):
    """Get cumulative R-multiple equity curve and drawdown series."""
    runner = HistoricalBacktestRunner()
    signals, total = runner.get_run_signals(run_id=run_id, limit=5000, offset=0)
    completed = [s for s in signals if s.outcome in ("WIN", "LOSS", "BREAKEVEN", "EXPIRED")]

    curve = []
    cum_r = 0.0
    peak_r = 0.0
    for s in completed:
        r_val = s.realized_r or 0.0
        cum_r += r_val
        if cum_r > peak_r:
            peak_r = cum_r
        dd_r = round(peak_r - cum_r, 3)
        curve.append({
            "timestamp": s.signal_timestamp,
            "trade_id": s.signal_id,
            "direction": s.direction,
            "outcome": s.outcome,
            "realized_r": r_val,
            "cumulative_r": round(cum_r, 3),
            "drawdown_r": dd_r,
        })

    return {
        "run_id": run_id,
        "total_trades": len(completed),
        "cumulative_r": round(cum_r, 3),
        "equity_curve": curve,
    }


# ── Live Ingestion Status ──────────────────────────────────────────────────

@router.get("/ingestion/status", tags=["Live Ingestion"])
def get_ingestion_status():
    """
    Return live 5m candle ingestion status per symbol.

    Reports:
    - last_candle_timestamp: the real-time latest candle stored
    - last_ingested_at:      when the ingestion daemon last ran
    - baseline_candles:      count from the original 2016-2026 dataset
    - live_candles_added:    count appended by the live daemon
    - total_candles:         baseline + live
    - status:                LIVE | SYNCING | CATCHING_UP | ERROR | INITIALIZING
    - last_error:            last provider error message, if any
    """
    try:
        ingestion_svc = LiveCandleIngestionService.get_instance()
        return ingestion_svc.get_ingestion_status()
    except Exception as exc:
        # Fallback: read directly from DB via HistoricalDataService
        try:
            svc = HistoricalDataService.get_instance()
            return svc.get_live_ingestion_status()
        except Exception:
            raise HTTPException(status_code=500, detail=f"Ingestion status unavailable: {exc}")


@router.get("/datasets/live-status", tags=["Live Ingestion"])
def get_live_dataset_status():
    """
    Enhanced dataset status combining the Kaggle baseline metadata with
    live ingestion extension data.

    Returns the full fast-status payload PLUS a `live_ingestion` dict
    per symbol containing:
      baseline_candles, live_candles_added, total_candles,
      latest_live_timestamp, ingestion_status.
    """
    service = HistoricalDataService.get_instance()
    status  = service.get_fast_dataset_status()
    return status


@router.get("/historical/intelligence", tags=["Historical Intelligence"])
def get_historical_intelligence(
    symbol:    str  = Query("XAU/USD", description="BTC/USD or XAU/USD"),
    direction: Optional[str] = Query(None, description="BUY, SELL, or None for both"),
):
    """
    Return pre-computed historical intelligence from completed backtest signals.

    Reads from the existing `historical_signals` table — no full-dataset scan.

    Returns per-direction:
    - sample_size, win_rate, loss_rate, expectancy, profit_factor
    - success_reasons (top 5), failure_reasons (top 5)
    - score_band breakdown
    - market_regime breakdown
    - latest signal timestamp
    """
    import json
    import sqlite3
    from src.services.historical_data_service import DB_PATH
    from collections import Counter

    norm_symbol = "BTC/USD" if "BTC" in symbol.upper() else "XAU/USD"
    directions  = ([direction.upper()] if direction else ["BUY", "SELL"])

    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        result: Dict[str, Any] = {"symbol": norm_symbol, "directions": {}}

        for d in directions:
            cur = conn.execute(
                """
                SELECT outcome, confluence_score, market_regime,
                       realized_r, success_reason, failure_reason,
                       signal_timestamp
                FROM historical_signals
                WHERE symbol=? AND direction=?
                  AND outcome IN ('WIN','LOSS','BREAKEVEN','EXPIRED')
                ORDER BY signal_timestamp DESC
                """,
                (norm_symbol, d),
            )
            rows = cur.fetchall()

            if not rows:
                result["directions"][d] = {"status": "INSUFFICIENT_DATA", "sample_size": 0}
                continue

            wins = sum(1 for r in rows if r["outcome"] == "WIN")
            losses = sum(1 for r in rows if r["outcome"] in ("LOSS", "EXPIRED"))
            n = len(rows)
            win_rate = round(wins / n * 100, 1) if n else 0.0

            r_vals = [r["realized_r"] for r in rows if r["realized_r"] is not None]
            expectancy = round(sum(r_vals) / len(r_vals), 3) if r_vals else 0.0

            win_rs  = [r for r in r_vals if r > 0]
            loss_rs = [abs(r) for r in r_vals if r < 0]
            profit_factor = (
                round(sum(win_rs) / sum(loss_rs), 2)
                if loss_rs and win_rs else None
            )

            # Score-band breakdown
            band_counter: Counter = Counter()
            band_wins:    Counter = Counter()
            for row in rows:
                sc = int(row["confluence_score"] or 0)
                band = (
                    "90-100" if sc >= 90 else
                    "80-89"  if sc >= 80 else
                    "70-79"  if sc >= 70 else
                    "60-69"  if sc >= 60 else
                    "50-59"  if sc >= 50 else "0-49"
                )
                band_counter[band] += 1
                if row["outcome"] == "WIN":
                    band_wins[band] += 1

            score_bands = [
                {
                    "band":    b,
                    "count":   cnt,
                    "wins":    band_wins[b],
                    "win_rate": round(band_wins[b] / cnt * 100, 1) if cnt else 0.0,
                }
                for b, cnt in sorted(band_counter.items())
            ]

            # Regime breakdown
            regime_counter: Counter = Counter()
            regime_wins:    Counter = Counter()
            for row in rows:
                reg = row["market_regime"] or "UNKNOWN"
                regime_counter[reg] += 1
                if row["outcome"] == "WIN":
                    regime_wins[reg] += 1

            regime_breakdown = [
                {
                    "regime":   reg,
                    "count":    cnt,
                    "win_rate": round(regime_wins[reg] / cnt * 100, 1) if cnt else 0.0,
                }
                for reg, cnt in regime_counter.most_common()
            ]

            # Top success/failure reasons
            success_reasons = [
                r for r in (row["success_reason"] for row in rows
                            if row["outcome"] == "WIN" and row["success_reason"])
                if r
            ]
            failure_reasons = [
                r for r in (row["failure_reason"] for row in rows
                            if row["outcome"] in ("LOSS","EXPIRED") and row["failure_reason"])
                if r
            ]

            top_success = [r for r, _ in Counter(success_reasons).most_common(5)]
            top_failure = [r for r, _ in Counter(failure_reasons).most_common(5)]

            latest_ts = rows[0]["signal_timestamp"] if rows else None

            result["directions"][d] = {
                "direction":        d,
                "sample_size":      n,
                "wins":             wins,
                "losses":           losses,
                "win_rate":         win_rate,
                "loss_rate":        round(100 - win_rate, 1),
                "expectancy":       expectancy,
                "profit_factor":    profit_factor,
                "score_bands":      score_bands,
                "regime_breakdown": regime_breakdown,
                "top_success_reasons": top_success,
                "top_failure_reasons": top_failure,
                "latest_signal_timestamp": latest_ts,
                "status": "AVAILABLE" if n >= 10 else "LIMITED",
            }

        return result
    finally:
        conn.close()


@router.get("/history/analytics", tags=["Historical Strategy Analytics"])
def get_historical_strategy_analytics(
    symbol: Optional[str] = Query(None, description="BTC/USD, XAU/USD, or ALL"),
    direction: Optional[str] = Query(None, description="BUY, SELL, or ALL"),
    outcome: Optional[str] = Query(None, description="WIN, LOSS, BREAKEVEN, EXPIRED, or ALL"),
    min_prob: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum calibrated probability (0.0 to 1.0)"),
    max_prob: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum calibrated probability (0.0 to 1.0)"),
    market_regime: Optional[str] = Query(None, description="LOW_VOLATILITY, TRENDING, RANGING, HIGH_VOLATILITY, or ALL"),
    qualification: Optional[str] = Query(None, description="QUALIFIED, NOT_QUALIFIED, or ALL"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD start date"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD end date"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Return validated historical strategy analytics, dynamic KPI summaries,
    rolling expectancy curves, and research benchmark comparisons.
    """
    from src.services.historical_strategy_analytics_service import HistoricalStrategyAnalyticsService
    service = HistoricalStrategyAnalyticsService.get_instance()
    return service.query_history_analytics(
        symbol=symbol,
        direction=direction,
        outcome=outcome,
        min_prob=min_prob,
        max_prob=max_prob,
        market_regime=market_regime,
        qualification_status=qualification,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
