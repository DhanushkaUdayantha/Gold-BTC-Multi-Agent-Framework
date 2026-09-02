"""
Data structures for ML Shadow validation layer.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

@dataclass
class MLShadowPrediction:
    """Immutable point-in-time snapshot of an ML shadow prediction at T0."""
    observation_id: str
    symbol: str
    timestamp_t0: str
    production_decision: str
    confluence_score: int
    technical_score: int
    quality_gate_passed: bool
    ml_model_name: str
    ml_model_version: str
    ml_probability: float
    ml_predicted_class: int
    entry_price: float
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    session: str
    market_regime: str
    features_snapshot: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(
        cls,
        symbol: str,
        timestamp_t0: str,
        production_decision: str,
        confluence_score: int,
        technical_score: int,
        quality_gate_passed: bool,
        ml_model_name: str,
        ml_model_version: str,
        ml_probability: float,
        ml_predicted_class: int,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit_1: Optional[float],
        take_profit_2: Optional[float],
        session: str,
        market_regime: str,
        features_snapshot: Dict[str, Any]
    ) -> "MLShadowPrediction":
        return cls(
            observation_id=f"ML-SHADOW-{uuid.uuid4().hex[:12].upper()}",
            symbol=symbol,
            timestamp_t0=timestamp_t0,
            production_decision=production_decision,
            confluence_score=confluence_score,
            technical_score=technical_score,
            quality_gate_passed=quality_gate_passed,
            ml_model_name=ml_model_name,
            ml_model_version=ml_model_version,
            ml_probability=round(float(ml_probability), 4),
            ml_predicted_class=int(ml_predicted_class),
            entry_price=round(float(entry_price), 4),
            stop_loss=round(float(stop_loss), 4) if stop_loss is not None else None,
            take_profit_1=round(float(take_profit_1), 4) if take_profit_1 is not None else None,
            take_profit_2=round(float(take_profit_2), 4) if take_profit_2 is not None else None,
            session=session,
            market_regime=market_regime,
            features_snapshot=features_snapshot
        )
