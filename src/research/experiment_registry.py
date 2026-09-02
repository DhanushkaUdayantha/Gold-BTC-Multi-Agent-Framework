"""
Phase 3 Experiment Registry.

Central registry for all Phase 3 experiments.  Provides:
  - Persistent experiment log (JSONL)
  - Deduplication via input fingerprints
  - Prevents re-running identical experiments with different random seeds
  - Full experiment provenance: inputs, outputs, code version, timestamp

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REGISTRY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "experiment_registry",
)
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "experiment_registry.jsonl")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ExperimentRecord:
    """Complete record of one research experiment."""
    experiment_id: str           # Unique hash
    experiment_type: str         # FILTER_ABLATION / POLICY_COMPARISON / ASSET_RESEARCH / etc.
    description: str
    code_version: str
    dataset_version: str
    started_at: str
    completed_at: str = ""
    status: str = "PENDING"      # PENDING / COMPLETED / FAILED

    # Inputs (summary / fingerprint — not full data)
    input_fingerprint: str = ""
    n_records: int = 0
    n_trades: int = 0
    date_range_start: str = ""
    date_range_end: str = ""
    assets: List[str] = field(default_factory=list)

    # Outputs (key metrics only)
    output_summary: Dict[str, Any] = field(default_factory=dict)
    output_paths: List[str] = field(default_factory=list)

    # Error (if FAILED)
    error_message: str = ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ExperimentRegistry:
    """
    Persistent experiment registry backed by a JSONL file.

    Thread-safety: Single-process read-append only.
    """

    def __init__(self, registry_dir: str = REGISTRY_DIR):
        self.registry_dir = registry_dir
        self.registry_file = os.path.join(registry_dir, "experiment_registry.jsonl")
        os.makedirs(registry_dir, exist_ok=True)
        self._cache: Dict[str, ExperimentRecord] = {}
        self._load()

    # ------------------------------------------------------------------ I/O

    def _load(self) -> None:
        """Load all existing records into cache."""
        if not os.path.exists(self.registry_file):
            return
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        rec = ExperimentRecord(**data)
                        self._cache[rec.experiment_id] = rec
                    except Exception as exc:
                        logger.warning("Could not deserialize registry line: %s", exc)
        except Exception as exc:
            logger.warning("Could not read registry file: %s", exc)

    def _append(self, record: ExperimentRecord) -> None:
        """Append one record to the JSONL file."""
        try:
            with open(self.registry_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), default=str) + "\n")
        except Exception as exc:
            logger.warning("Could not append to registry: %s", exc)

    # ------------------------------------------------------------------ API

    def register(
        self,
        experiment_type: str,
        description: str,
        dataset_version: str = "v1.0",
        code_version: str = "3.0",
        n_records: int = 0,
        n_trades: int = 0,
        date_range_start: str = "",
        date_range_end: str = "",
        assets: Optional[List[str]] = None,
        input_fingerprint: str = "",
    ) -> ExperimentRecord:
        """Register a new experiment and return its record."""
        now = datetime.now(timezone.utc).isoformat()
        exp_id = self._generate_id(experiment_type, description, dataset_version, now)

        record = ExperimentRecord(
            experiment_id=exp_id,
            experiment_type=experiment_type,
            description=description,
            code_version=code_version,
            dataset_version=dataset_version,
            started_at=now,
            n_records=n_records,
            n_trades=n_trades,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            assets=assets or [],
            input_fingerprint=input_fingerprint,
        )
        self._cache[exp_id] = record
        self._append(record)
        return record

    def complete(
        self,
        experiment_id: str,
        output_summary: Optional[Dict[str, Any]] = None,
        output_paths: Optional[List[str]] = None,
    ) -> Optional[ExperimentRecord]:
        """Mark an experiment as COMPLETED with optional output metadata."""
        rec = self._cache.get(experiment_id)
        if rec is None:
            logger.warning("Experiment not found: %s", experiment_id)
            return None
        rec.status = "COMPLETED"
        rec.completed_at = datetime.now(timezone.utc).isoformat()
        rec.output_summary = output_summary or {}
        rec.output_paths = output_paths or []
        self._append(rec)
        return rec

    def fail(self, experiment_id: str, error_message: str) -> Optional[ExperimentRecord]:
        """Mark an experiment as FAILED."""
        rec = self._cache.get(experiment_id)
        if rec is None:
            logger.warning("Experiment not found: %s", experiment_id)
            return None
        rec.status = "FAILED"
        rec.completed_at = datetime.now(timezone.utc).isoformat()
        rec.error_message = error_message
        self._append(rec)
        return rec

    def is_duplicate(self, experiment_type: str, input_fingerprint: str) -> bool:
        """
        Check if an equivalent experiment (same type + same data fingerprint)
        already ran successfully.
        """
        for rec in self._cache.values():
            if (rec.experiment_type == experiment_type
                    and rec.input_fingerprint == input_fingerprint
                    and rec.status == "COMPLETED"):
                return True
        return False

    def list_all(self) -> List[ExperimentRecord]:
        return list(self._cache.values())

    def list_by_type(self, experiment_type: str) -> List[ExperimentRecord]:
        return [r for r in self._cache.values() if r.experiment_type == experiment_type]

    def get_summary_md(self) -> str:
        """Return a Markdown summary of all registered experiments."""
        lines = [
            "# Experiment Registry Summary",
            f"\nTotal experiments: {len(self._cache)}",
            "\n| ID | Type | Status | Trades | Date |",
            "| --- | --- | --- | --- | --- |",
        ]
        for rec in sorted(self._cache.values(), key=lambda r: r.started_at, reverse=True):
            lines.append(
                f"| {rec.experiment_id[:12]} | {rec.experiment_type} "
                f"| {rec.status} | {rec.n_trades} | {rec.started_at[:10]} |"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _generate_id(exp_type: str, description: str, dataset_version: str, ts: str) -> str:
        raw = f"{exp_type}|{description}|{dataset_version}|{ts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_registry_instance: Optional[ExperimentRegistry] = None


def get_registry(registry_dir: str = REGISTRY_DIR) -> ExperimentRegistry:
    """Return the global singleton registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ExperimentRegistry(registry_dir)
    return _registry_instance


def reset_registry(registry_dir: str = REGISTRY_DIR) -> None:
    """Reset the singleton (primarily for testing)."""
    global _registry_instance
    _registry_instance = ExperimentRegistry(registry_dir)
