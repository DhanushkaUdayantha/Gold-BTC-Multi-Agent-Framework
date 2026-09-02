"""
Phase 5 Research Package: Probability Calibration, Expected Value & No-Trade/WAIT Validation.

Modules:
- audit: Probability sources audit and T0 timing verification.
- calibration: Brier, ECE, MCE, Platt scaling, Isotonic regression, and reliability buckets.
- expected_value: Theoretical vs realized EV across probability bands.
- no_trade: WAIT/no-trade policies, opportunity cost, and filter selectivity.
- validation: OOS walk-forward, holdout protection, bootstrap, Monte Carlo, and drift checks.
- orchestrator: High-level Phase 5 research orchestrator.

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
from __future__ import annotations

from src.research.phase5.audit import (
    ProbabilitySourceAudit,
    audit_probability_sources,
)
from src.research.phase5.calibration import (
    ReliabilityBucket,
    CalibrationMetrics,
    evaluate_probability_calibration,
)
from src.research.phase5.expected_value import (
    ProbabilityBandEV,
    evaluate_expected_value_bands,
)
from src.research.phase5.no_trade import (
    NoTradePolicyResult,
    evaluate_no_trade_policies,
)
from src.research.phase5.validation import (
    WalkForwardCalibrationResult,
    BootstrapCalibrationResult,
    MonteCarloEVResult,
    CalibrationStabilityResult,
    run_phase5_validations,
)
from src.research.phase5.orchestrator import (
    Phase5AssetResult,
    run_full_phase5_research,
)

__all__ = [
    "ProbabilitySourceAudit",
    "audit_probability_sources",
    "ReliabilityBucket",
    "CalibrationMetrics",
    "evaluate_probability_calibration",
    "ProbabilityBandEV",
    "evaluate_expected_value_bands",
    "NoTradePolicyResult",
    "evaluate_no_trade_policies",
    "WalkForwardCalibrationResult",
    "BootstrapCalibrationResult",
    "MonteCarloEVResult",
    "CalibrationStabilityResult",
    "run_phase5_validations",
    "Phase5AssetResult",
    "run_full_phase5_research",
]
