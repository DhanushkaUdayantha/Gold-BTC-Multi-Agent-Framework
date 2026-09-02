"""
Phase 6 -> Phase 33 Research & Governance Framework.

Integrates Forward Shadow Validation, Strategy Qualification, Execution Stress,
Drift Monitoring, Multiple Testing, and Final Governance Decision.

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
from __future__ import annotations

from src.research.governance.forward_shadow import (
    ForwardSignalSnapshot,
    ForwardShadowEngine,
    get_forward_shadow_engine,
)
from src.research.governance.filters_and_strategies import (
    ResearchStrategy,
    StrategyQualificationReport,
    ShadowGatingPolicy,
    evaluate_research_strategies,
    evaluate_shadow_gating_policies,
)
from src.research.governance.stress_and_robustness import (
    ExecutionStressReport,
    RobustnessMultiDimensionReport,
    CoverageOpportunityReport,
    run_execution_stress_tests,
    run_multidimensional_robustness,
    run_coverage_analysis,
)
from src.research.governance.drift_and_bias import (
    DriftMonitoringReport,
    DegradationMonitoringReport,
    OverfittingAuditReport,
    MultipleTestingAuditReport,
    run_drift_and_degradation_audit,
    run_overfitting_and_significance_audit,
)
from src.research.governance.engine import (
    PhaseStatusRecord,
    MasterGovernanceDecision,
    run_full_phase6_to_33_governance,
)

__all__ = [
    "ForwardSignalSnapshot",
    "ForwardShadowEngine",
    "get_forward_shadow_engine",
    "ResearchStrategy",
    "StrategyQualificationReport",
    "ShadowGatingPolicy",
    "evaluate_research_strategies",
    "evaluate_shadow_gating_policies",
    "ExecutionStressReport",
    "RobustnessMultiDimensionReport",
    "CoverageOpportunityReport",
    "run_execution_stress_tests",
    "run_multidimensional_robustness",
    "run_coverage_analysis",
    "DriftMonitoringReport",
    "DegradationMonitoringReport",
    "OverfittingAuditReport",
    "MultipleTestingAuditReport",
    "run_drift_and_degradation_audit",
    "run_overfitting_and_significance_audit",
    "PhaseStatusRecord",
    "MasterGovernanceDecision",
    "run_full_phase6_to_33_governance",
]
