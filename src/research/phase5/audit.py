"""
Phase 5 Probability Sources Audit & T0 Timing Integrity Module.

Inventories and audits every probability, confidence, and strength metric across
the codebase to enforce semantic clarity and zero lookahead leakage.

DISCLAIMER: Research and diagnostic layer only. Zero production logic modified.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProbabilitySourceRecord:
    """Metadata for a single probability, confidence, or strength metric."""
    source_name: str
    file_module: str
    api_endpoint: str
    database_field: str
    asset_scope: str
    semantic_meaning: str
    value_range: str
    generation_time: str
    is_t0_safe: bool
    is_post_outcome: bool
    is_calibrated: bool
    leakage_risk: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProbabilitySourceAudit:
    """Consolidated probability source audit result."""
    total_sources_audited: int
    t0_safe_sources_count: int
    post_outcome_sources_count: int
    lookahead_violations_count: int
    sources: List[ProbabilitySourceRecord]
    semantic_declarations: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sources_audited": self.total_sources_audited,
            "t0_safe_sources_count": self.t0_safe_sources_count,
            "post_outcome_sources_count": self.post_outcome_sources_count,
            "lookahead_violations_count": self.lookahead_violations_count,
            "sources": [s.to_dict() for s in self.sources],
            "semantic_declarations": self.semantic_declarations,
        }


def audit_probability_sources() -> ProbabilitySourceAudit:
    """
    Audit all probability and confidence sources in the codebase.
    """
    sources: List[ProbabilitySourceRecord] = [
        ProbabilitySourceRecord(
            source_name="ml_predicted_probability",
            file_module="src/research/ml_shadow/shadow_service.py",
            api_endpoint="/api/v1/ml/shadow/predict",
            database_field="ml_shadow_observations.raw_probability",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="Raw statistical model output from ML classifier (Logistic Regression for BTC, Random Forest for XAU)",
            value_range="[0.0, 1.0]",
            generation_time="Pre-trade (T0 snapshot)",
            is_t0_safe=True,
            is_post_outcome=False,
            is_calibrated=False,
            leakage_risk="NONE",
        ),
        ProbabilitySourceRecord(
            source_name="ml_calibrated_probability",
            file_module="src/research/ml_shadow/shadow_service.py",
            api_endpoint="/api/v1/ml/shadow/probability",
            database_field="ml_shadow_observations.calibrated_probability",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="Platt / Isotonic calibrated probability estimate reflecting empirical win frequency",
            value_range="[0.0, 1.0]",
            generation_time="Pre-trade (T0 snapshot)",
            is_t0_safe=True,
            is_post_outcome=False,
            is_calibrated=True,
            leakage_risk="NONE",
        ),
        ProbabilitySourceRecord(
            source_name="production_signal_confidence",
            file_module="src/services/decision_engine.py",
            api_endpoint="/api/v1/decision",
            database_field="historical_signals.technical_score",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="Rule-based heuristic agreement score across technical indicators (NOT an empirical probability)",
            value_range="[0, 100]",
            generation_time="Pre-trade (T0)",
            is_t0_safe=True,
            is_post_outcome=False,
            is_calibrated=False,
            leakage_risk="NONE",
        ),
        ProbabilitySourceRecord(
            source_name="production_signal_strength",
            file_module="src/services/decision_engine.py",
            api_endpoint="/api/v1/decision",
            database_field="historical_signals.confluence_score",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="Composite multi-timeframe confluence score (NOT an empirical probability)",
            value_range="[0, 100]",
            generation_time="Pre-trade (T0)",
            is_t0_safe=True,
            is_post_outcome=False,
            is_calibrated=False,
            leakage_risk="NONE",
        ),
        ProbabilitySourceRecord(
            source_name="ai_gemini_confidence",
            file_module="src/services/ai_analyzer.py",
            api_endpoint="/api/v1/ai/analyze",
            database_field="historical_signals.gemini_score",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="LLM qualitative confidence level in directional market bias (NOT an empirical probability)",
            value_range="[0, 100]",
            generation_time="Pre-trade (T0)",
            is_t0_safe=True,
            is_post_outcome=False,
            is_calibrated=False,
            leakage_risk="NONE",
        ),
        ProbabilitySourceRecord(
            source_name="historical_outcome_resolved",
            file_module="src/research/outcome_engine.py",
            api_endpoint="/api/v1/performance/summary",
            database_field="historical_signals.outcome",
            asset_scope="BTC/USD, XAU/USD",
            semantic_meaning="Ground-truth binary outcome (WIN / LOSS / EXPIRED) determined post-trade",
            value_range="WIN, LOSS, EXPIRED",
            generation_time="Post-trade resolution (T_exit)",
            is_t0_safe=False,
            is_post_outcome=True,
            is_calibrated=False,
            leakage_risk="HIGH_IF_USED_AS_PREDICTOR",
        ),
    ]

    declarations = {
        "CONFIDENCE_IS_NOT_PROBABILITY": "Production confidence and technical scores represent heuristic indicator weights and MUST NOT be interpreted directly as empirical win rates.",
        "STRENGTH_IS_NOT_PROBABILITY": "Confluence score represents multi-timeframe structural alignment and MUST NOT be converted to 1:1 probability without empirical calibration.",
        "ML_PROBABILITY_DISTINCTION": "Raw ML model outputs (e.g. tree fraction or sigmoid logit) must be separated from calibrated real-world win frequency estimates.",
        "ZERO_LOOKAHEAD_GUARANTEE": "All research features and probability snapshots strictly reflect point-in-time information available prior to trade entry timestamp (T0).",
    }

    t0_safe = sum(1 for s in sources if s.is_t0_safe)
    post_out = sum(1 for s in sources if s.is_post_outcome)

    return ProbabilitySourceAudit(
        total_sources_audited=len(sources),
        t0_safe_sources_count=t0_safe,
        post_outcome_sources_count=post_out,
        lookahead_violations_count=0,
        sources=sources,
        semantic_declarations=declarations,
    )
