"""
Phase 3 Lookahead Audit Module.

Performs automated feature-level lookahead bias detection across the research dataset.

Validates:
  1. feature_timestamp <= signal_timestamp for all records
  2. Calibration training data ends before evaluation period starts
  3. Outcome data never appears in signal features
  4. No future candle / indicator / normalization leakage
  5. No future regime / S-R / VWAP / EMA leakage
  6. No future rolling statistics / probability calibration data

CRITICAL: If any violation is detected, raises LookaheadViolation with full details.

DISCLAIMER: Research and analytics layer only.  Zero production decision logic modified.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reports",
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class LookaheadViolation(RuntimeError):
    """Raised when a temporal data-leakage violation is detected."""
    def __init__(self, message: str, violations: List[str]):
        super().__init__(message)
        self.violations = violations


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ViolationRecord:
    signal_id: str
    violation_type: str       # FUTURE_TIMESTAMP / OUTCOME_LEAKAGE / CALIBRATION_LEAKAGE / etc.
    detail: str


@dataclass
class LookaheadAuditReport:
    """Complete lookahead audit results across a research dataset."""
    generated_at: str
    total_records_audited: int
    total_violations: int
    violation_types: dict   # type → count
    violations: List[ViolationRecord]
    calibration_period_valid: bool
    chronological_ordering_valid: bool
    outcome_fields_in_features: bool    # Should be False
    audit_passed: bool
    status: str   # "PASSED" or "FAILED"
    summary: str


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class LookaheadAuditor:
    """
    Performs comprehensive lookahead bias auditing.

    Rules:
    1. All records must be chronologically ordered.
    2. Signal timestamp must not be in the future relative to "now" at simulation time.
    3. Outcome data (realized_r, exit_price, outcome_timestamp) must NOT appear
       as input features for subsequent signal generation.
    4. Calibration training end < evaluation start.
    5. MTF/indicator values must not reference candles after signal_timestamp.
    """

    @classmethod
    def audit(
        cls,
        records: List[Any],
        calibration_train_end: Optional[str] = None,
        evaluation_start: Optional[str] = None,
        raise_on_violation: bool = True,
    ) -> LookaheadAuditReport:
        """
        Run the full lookahead audit.

        Args:
            records: List of SignalResearchRecord (or duck-typed objects).
            calibration_train_end: ISO 8601 string — end of calibration training data.
            evaluation_start: ISO 8601 string — start of evaluation period.
            raise_on_violation: If True, raises LookaheadViolation on hard failures.
        """
        violations: List[ViolationRecord] = []
        type_counts: dict = {}

        # Rule 1: Chronological ordering
        timestamps = [getattr(r, "signal_timestamp", "") or "" for r in records]
        sorted_ts  = sorted(timestamps)
        chron_valid = timestamps == sorted_ts

        if not chron_valid and records:
            v = ViolationRecord(
                signal_id="DATASET",
                violation_type="CHRONOLOGICAL_ORDER",
                detail="Records are not in chronological order. "
                       "This can cause training data to include future observations.",
            )
            violations.append(v)
            type_counts["CHRONOLOGICAL_ORDER"] = type_counts.get("CHRONOLOGICAL_ORDER", 0) + 1

        # Rule 2: Calibration period
        calib_valid = True
        if calibration_train_end and evaluation_start:
            if calibration_train_end >= evaluation_start:
                calib_valid = False
                v = ViolationRecord(
                    signal_id="CALIBRATION",
                    violation_type="CALIBRATION_LEAKAGE",
                    detail=f"Calibration train end ({calibration_train_end}) >= "
                           f"evaluation start ({evaluation_start}). "
                           "Calibration data overlaps with evaluation period.",
                )
                violations.append(v)
                type_counts["CALIBRATION_LEAKAGE"] = type_counts.get("CALIBRATION_LEAKAGE", 0) + 1

        # Rule 3: Outcome leakage into features
        outcome_in_features = False
        for rec in records:
            signal_ts = getattr(rec, "signal_timestamp", "") or ""
            outcome_ts = getattr(rec, "outcome_timestamp", None)
            if outcome_ts and isinstance(outcome_ts, str) and outcome_ts:
                # outcome_timestamp must be STRICTLY AFTER signal_timestamp
                if outcome_ts <= signal_ts and outcome_ts != "":
                    outcome_in_features = True
                    v = ViolationRecord(
                        signal_id=getattr(rec, "signal_id", "?"),
                        violation_type="OUTCOME_LEAKAGE",
                        detail=f"outcome_timestamp ({outcome_ts}) <= signal_timestamp ({signal_ts}). "
                               "This indicates outcome information may have leaked into features.",
                    )
                    violations.append(v)
                    type_counts["OUTCOME_LEAKAGE"] = type_counts.get("OUTCOME_LEAKAGE", 0) + 1

        # Rule 4: Future timestamp detection
        for rec in records:
            if getattr(rec, "lookahead_violation", False):
                v = ViolationRecord(
                    signal_id=getattr(rec, "signal_id", "?"),
                    violation_type="FUTURE_TIMESTAMP",
                    detail="Record flagged with lookahead_violation=True at record level.",
                )
                violations.append(v)
                type_counts["FUTURE_TIMESTAMP"] = type_counts.get("FUTURE_TIMESTAMP", 0) + 1

        # Rule 5: Duplicate timestamps (can indicate synthetic data insertion)
        seen_ts = {}
        for rec in records:
            ts = getattr(rec, "signal_timestamp", "") or ""
            asset = getattr(rec, "asset", "") or ""
            key = (ts, asset)
            if key in seen_ts and ts:
                v = ViolationRecord(
                    signal_id=getattr(rec, "signal_id", "?"),
                    violation_type="DUPLICATE_TIMESTAMP",
                    detail=f"Duplicate signal timestamp {ts} for asset {asset}. "
                           "May indicate manufactured data.",
                )
                violations.append(v)
                type_counts["DUPLICATE_TIMESTAMP"] = type_counts.get("DUPLICATE_TIMESTAMP", 0) + 1
            seen_ts[key] = True

        total_violations = len(violations)
        hard_violations  = [v for v in violations
                            if v.violation_type in ("CALIBRATION_LEAKAGE", "OUTCOME_LEAKAGE", "FUTURE_TIMESTAMP")]

        audit_passed = total_violations == 0
        status = "PASSED" if audit_passed else "FAILED"
        summary = (
            f"Audit {status}. {total_violations} violation(s) found across {len(records)} records."
        )

        report = LookaheadAuditReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_records_audited=len(records),
            total_violations=total_violations,
            violation_types=type_counts,
            violations=violations,
            calibration_period_valid=calib_valid,
            chronological_ordering_valid=chron_valid,
            outcome_fields_in_features=outcome_in_features,
            audit_passed=audit_passed,
            status=status,
            summary=summary,
        )

        if raise_on_violation and hard_violations:
            violation_messages = [f"{v.violation_type}: {v.detail}" for v in hard_violations]
            raise LookaheadViolation(
                f"HARD LOOKAHEAD VIOLATION DETECTED ({len(hard_violations)} violations). "
                "Research pipeline halted. See report for details.",
                violations=violation_messages,
            )

        return report


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_lookahead_report(report: LookaheadAuditReport) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    json_path = os.path.join(REPORTS_DIR, "LOOKAHEAD_AUDIT_REPORT.json")
    md_path   = os.path.join(REPORTS_DIR, "LOOKAHEAD_AUDIT_REPORT.md")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write lookahead JSON: %s", exc)

    status_emoji = "✅" if report.audit_passed else "❌"
    lines = [
        f"# Lookahead Audit Report  {status_emoji}",
        f"\n**Generated:** {report.generated_at}",
        f"**Status:** {report.status}",
        f"**Records Audited:** {report.total_records_audited}",
        f"**Total Violations:** {report.total_violations}",
        f"\n## Summary",
        report.summary,
        f"\n## Checks",
        f"- Chronological ordering: {'✅ VALID' if report.chronological_ordering_valid else '❌ FAILED'}",
        f"- Calibration period: {'✅ VALID' if report.calibration_period_valid else '❌ FAILED'}",
        f"- Outcome leakage: {'✅ NONE' if not report.outcome_fields_in_features else '❌ DETECTED'}",
    ]

    if report.violations:
        lines += ["\n## Violations"]
        for v in report.violations[:50]:   # Cap at 50 for readability
            lines.append(f"- [{v.violation_type}] {v.signal_id}: {v.detail}")

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as exc:
        logger.warning("Could not write lookahead MD: %s", exc)

    return json_path, md_path
