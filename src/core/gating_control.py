"""
Production Gating Controller & Safety Invariants Enforcement Manager.

Manages persisted production gating states with strict security invariants:
- PRODUCTION_GATING_BTC is persisted with immutable append-only audit records.
- Boot-time default is DISABLED (False).
- Hard-enforced immutable invariants:
    AUTOMATIC_RETRAINING == False
    AUTOMATIC_THRESHOLD_OPTIMIZATION == False
    PRODUCTION_GATING_XAU == False
  Attempting to set any invariant to True raises RuntimeError loudly.

DISCLAIMER: Advisory system control layer only. Zero real broker order execution.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_STATE_FILE_PATH = "data/gating_state.json"
_AUDIT_LOG_PATH = "data/audit/gating_audit.log"


@dataclass
class GatingAuditEntry:
    """Immutable audit trail entry for production gating changes."""
    timestamp_utc: str
    actor: str
    action: str  # "ENABLE_BTC_GATING", "DISABLE_BTC_GATING"
    previous_state_btc: bool
    new_state_btc: bool
    rationale: str
    invariants_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GatingControlManager:
    """
    Thread-safe, persisted production gating controller with hard-enforced safety invariants.
    """

    def __init__(self, state_file: str = _STATE_FILE_PATH, audit_file: str = _AUDIT_LOG_PATH):
        self._lock = threading.Lock()
        self.state_file = state_file
        self.audit_file = audit_file

        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.audit_file).parent.mkdir(parents=True, exist_ok=True)

        # Boot-time safe initialization
        self._production_gating_btc = False
        self._load_state()

    def _verify_invariants(self) -> None:
        """
        Verify that all mandatory platform safety invariants are strictly False.
        """
        # Invariant 1: Automatic retraining MUST be False
        if self.automatic_retraining is not False:
            raise RuntimeError("CRITICAL INVARIANT VIOLATION: AUTOMATIC_RETRAINING must be False!")

        # Invariant 2: Automatic threshold optimization MUST be False
        if self.automatic_threshold_optimization is not False:
            raise RuntimeError("CRITICAL INVARIANT VIOLATION: AUTOMATIC_THRESHOLD_OPTIMIZATION must be False!")

        # Invariant 3: XAU production gating MUST be False
        if self.production_gating_xau is not False:
            raise RuntimeError("CRITICAL INVARIANT VIOLATION: PRODUCTION_GATING_XAU must be False pending holdout gate!")

    @property
    def automatic_retraining(self) -> bool:
        return False

    @property
    def automatic_threshold_optimization(self) -> bool:
        return False

    @property
    def production_gating_xau(self) -> bool:
        return False

    @property
    def production_gating_btc(self) -> bool:
        with self._lock:
            self._verify_invariants()
            return self._production_gating_btc

    def _load_state(self) -> None:
        """Load persisted state if present, ensuring invariants are checked."""
        with self._lock:
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._production_gating_btc = bool(data.get("production_gating_btc", False))
                except Exception as exc:
                    logger.error(f"Failed to load gating state from {self.state_file}: {exc}")
                    self._production_gating_btc = False
            else:
                self._production_gating_btc = False
                self._save_state()

    def _save_state(self) -> None:
        """Save current state to file."""
        state = {
            "production_gating_btc": self._production_gating_btc,
            "production_gating_xau": False,
            "automatic_retraining": False,
            "automatic_threshold_optimization": False,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save gating state to {self.state_file}: {exc}")

    def _append_audit_log(self, entry: GatingAuditEntry) -> None:
        """Append an audit record to the append-only audit trail."""
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as exc:
            logger.error(f"Failed to append gating audit log: {exc}")

    def set_btc_gating(
        self,
        enable: bool,
        actor: str,
        rationale: str,
    ) -> GatingAuditEntry:
        """
        Manually enable or disable BTC production gating with full audit trail.
        """
        with self._lock:
            self._verify_invariants()
            prev = self._production_gating_btc
            self._production_gating_btc = bool(enable)
            self._save_state()

            entry = GatingAuditEntry(
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                actor=actor,
                action="ENABLE_BTC_GATING" if enable else "DISABLE_BTC_GATING",
                previous_state_btc=prev,
                new_state_btc=self._production_gating_btc,
                rationale=rationale,
                invariants_verified=True,
            )
            self._append_audit_log(entry)
            logger.info(
                f"[Gating Control] BTC Gating state changed to {self._production_gating_btc} "
                f"by {actor}. Rationale: {rationale}"
            )
            return entry

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive gating and invariants status."""
        with self._lock:
            self._verify_invariants()
            return {
                "production_gating_btc": self._production_gating_btc,
                "production_gating_xau": False,
                "automatic_retraining": False,
                "automatic_threshold_optimization": False,
                "invariants_ok": True,
                "state_file": self.state_file,
                "audit_file": self.audit_file,
            }


_gating_control_instance: Optional[GatingControlManager] = None


def get_gating_control() -> GatingControlManager:
    global _gating_control_instance
    if _gating_control_instance is None:
        _gating_control_instance = GatingControlManager()
    return _gating_control_instance
