"""
Daily Statistical Drift & Performance Degradation Monitoring Service.

Periodically evaluates distribution drift and rolling performance degradation:
- Writes audit records to data/monitoring/daily_drift_log.json.
- Strictly diagnostic and monitoring only. Zero automated triggers or production mutations.

DISCLAIMER: Advisory research layer only. Zero production trading logic modified.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.research.governance.drift_and_bias import run_drift_and_degradation_audit

logger = logging.getLogger(__name__)

_LOG_FILE = "data/monitoring/daily_drift_log.json"


class DailyDriftMonitor:
    """
    Executes scheduled monitoring snapshots for BTC/USD and XAU/USD.
    """

    def __init__(self, log_file: str = _LOG_FILE):
        self.log_file = log_file
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

    def run_daily_snapshot(self) -> Dict[str, Any]:
        """Record a single daily snapshot for both assets."""
        now_ts = datetime.now(timezone.utc).isoformat()

        btc_drift, btc_deg = run_drift_and_degradation_audit("BTC/USD")
        xau_drift, xau_deg = run_drift_and_degradation_audit("XAU/USD")

        snapshot = {
            "snapshot_timestamp_utc": now_ts,
            "btc_monitoring": {
                "drift": btc_drift.to_dict(),
                "degradation": btc_deg.to_dict(),
            },
            "xau_monitoring": {
                "drift": xau_drift.to_dict(),
                "degradation": xau_deg.to_dict(),
            },
            "system_invariants": {
                "automatic_retraining": False,
                "automatic_threshold_optimization": False,
                "production_gating_xau": False,
            },
            "disclaimer": "Monitoring only. Zero automatic production action.",
        }

        # Load existing snapshots
        existing = []
        if Path(self.log_file).exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            except Exception as exc:
                logger.error(f"Failed to read existing drift log: {exc}")
                existing = []

        existing.append(snapshot)
        # Keep last 90 daily snapshots
        if len(existing) > 90:
            existing = existing[-90:]

        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            logger.info(f"[Daily Drift Monitor] Snapshot successfully recorded at {now_ts}")
        except Exception as exc:
            logger.error(f"Failed to write daily drift log: {exc}")

        return snapshot


_daily_drift_monitor_instance: Optional[DailyDriftMonitor] = None


def get_daily_drift_monitor() -> DailyDriftMonitor:
    global _daily_drift_monitor_instance
    if _daily_drift_monitor_instance is None:
        _daily_drift_monitor_instance = DailyDriftMonitor()
    return _daily_drift_monitor_instance
