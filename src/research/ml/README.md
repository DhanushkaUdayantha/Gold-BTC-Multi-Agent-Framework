# Quantitative Machine Learning Research Subsystem

This subsystem provides research-only, non-destructive, and strictly leakage-safe machine learning experiments for the BTC/XAU AI Trading Analysis Platform.

## Architecture

```text
src/research/ml/
├── __init__.py               # Package init
├── config.py                 # Dataclasses & hyperparameter configs
├── leakage_detection.py      # Point-in-time feature catalog & leakage auditor
├── dataset_builder.py        # SQLite signal parser & tabular builder
├── feature_engineering.py    # Feature extraction & alignment indicators
├── split.py                  # Chronological time-series & walk-forward splitters
├── preprocessing.py          # Scaler & Imputer fitted strictly on Train
├── models.py                 # Scikit-learn baseline and ensemble classifiers
├── metrics.py                # Dual classification & trading expectancy metrics
├── calibration.py            # Probability reliability & Brier score analyzer
├── feature_importance.py     # Tree MDI & Permutation importance analyzer
├── walk_forward.py           # Multi-fold chronological walk-forward validator
├── baseline.py               # Rule-based vs ML comparative benchmarks
├── artifacts.py              # Serialization to research/ml/artifacts/
└── experiment.py             # Orchestrator & CLI runner
```

## Running the ML Experiment

```bash
python -m src.research.ml.experiment
```
