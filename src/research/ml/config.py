"""
Configuration settings and dataclasses for ML Research.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os

@dataclass
class SplitConfig:
    train_ratio: float = 0.60
    oos_ratio: float = 0.20
    holdout_ratio: float = 0.20
    walk_forward_folds: int = 4
    min_train_samples: int = 150

@dataclass
class ModelConfig:
    random_state: int = 42
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = 5
    gb_n_estimators: int = 100
    gb_learning_rate: float = 0.05
    gb_max_depth: int = 3
    lr_c: float = 1.0

@dataclass
class ArtifactConfig:
    base_artifact_dir: str = os.path.join("research", "ml", "artifacts")
    report_path: str = "PYTHON_ML_RESEARCH_REPORT.md"
    leakage_audit_path: str = "ML_FEATURE_LEAKAGE_AUDIT.md"

@dataclass
class MLConfig:
    db_path: str = os.path.join("data", "historical", "historical_market_data.db")
    symbols: List[str] = field(default_factory=lambda: ["BTC/USD", "XAU/USD"])
    split: SplitConfig = field(default_factory=SplitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    artifacts: ArtifactConfig = field(default_factory=ArtifactConfig)
    probability_thresholds: List[float] = field(default_factory=lambda: [0.50, 0.52, 0.55, 0.58, 0.60])
