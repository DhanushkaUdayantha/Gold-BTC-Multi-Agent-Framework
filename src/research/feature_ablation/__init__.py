"""
Feature Importance, Ablation & Signal Quality Hardening Package.

Modules:
- inventory: Repository feature inventory and T0 timing audit.
- importance: Classical & ML feature importance with fold stability analysis.
- ablation: Single-feature and filter ablation across Train, OOS, and Holdout.
- stability: Redundancy, missingness, distribution drift, and stability metrics.
- registry: Structured research experiment registry.
- validator: Consolidated Phase 4 research orchestrator.

DISCLAIMER: Research and diagnostic layer only. Zero production trading logic modified.
"""
from __future__ import annotations

from src.research.feature_ablation.inventory import (
    FeatureMetadata,
    FeatureInventory,
    build_feature_inventory,
    audit_feature_timing,
)
from src.research.feature_ablation.importance import (
    FeatureImportanceResult,
    MLImportanceResult,
    calculate_feature_importance,
    calculate_ml_importance,
)
from src.research.feature_ablation.ablation import (
    AblationExperimentResult,
    run_feature_ablation,
    run_filter_research,
)
from src.research.feature_ablation.stability import (
    StabilityReport,
    RedundancyAnalysis,
    MissingnessAnalysis,
    DistributionStabilityReport,
    analyze_feature_stability,
    analyze_feature_redundancy,
    analyze_feature_missingness,
    analyze_distribution_stability,
)
from src.research.feature_ablation.registry import (
    ExperimentRecord,
    ExperimentRegistry,
    get_experiment_registry,
)
from src.research.feature_ablation.validator import (
    Phase4ForensicResult,
    run_full_phase4_analysis,
)

__all__ = [
    "FeatureMetadata",
    "FeatureInventory",
    "build_feature_inventory",
    "audit_feature_timing",
    "FeatureImportanceResult",
    "MLImportanceResult",
    "calculate_feature_importance",
    "calculate_ml_importance",
    "AblationExperimentResult",
    "run_feature_ablation",
    "run_filter_research",
    "StabilityReport",
    "RedundancyAnalysis",
    "MissingnessAnalysis",
    "DistributionStabilityReport",
    "analyze_feature_stability",
    "analyze_feature_redundancy",
    "analyze_feature_missingness",
    "analyze_distribution_stability",
    "ExperimentRecord",
    "ExperimentRegistry",
    "get_experiment_registry",
    "Phase4ForensicResult",
    "run_full_phase4_analysis",
]
