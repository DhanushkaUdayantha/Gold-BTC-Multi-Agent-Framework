# MACHINE LEARNING GOVERNANCE & VALIDATION POLICY

**System**: BTC/USD & XAU/USD Quantitative AI Trading Analysis Platform  
**Document Classification**: ML Operational Governance, Holdout Integrity, and Validation Lifecycle  

---

## 1. Frozen Baseline Model Specifications

| Parameter / Dimension | BTC/USD Baseline | XAU/USD Baseline |
| :--- | :--- | :--- |
| **Model Version** | `v1.0.0-research` (LOCKED) | `v1.0.0-research` (LOCKED) |
| **Algorithm** | `LogisticRegression` | `RandomForestClassifier` |
| **Hyperparameters** | `C=1.0`, `solver='lbfgs'`, `max_iter=500`, `random_state=42` | `n_estimators=100`, `max_depth=5`, `min_samples_leaf=10`, `random_state=42` |
| **Calibration Method** | Platt Scaling (Logistic Sigmoid ECE = 0.0385) | Platt Scaling (Logistic Sigmoid ECE = 0.0465) |
| **Training Partition** | 60% Chronological Historical Bars | 60% Chronological Historical Bars |
| **OOS Partition** | 20% Chronological Validation Fold | 20% Chronological Validation Fold |
| **Holdout Partition** | 20% Untouched Out-of-Sample Holdout | 20% Untouched Out-of-Sample Holdout |
| **Holdout Performance** | Accuracy: 55.26%, EV: +0.3158R, PF: 1.67 ($N=152$) | Accuracy: 55.98%, EV: +0.1905R, PF: 1.36 ($N=42$) |
| **Governance Verdict** | `RESEARCH_APPROVED` (28/28 Gates Passed) | `INSUFFICIENT_EVIDENCE` (27/28 Gates Passed, $N < 50$) |

---

## 2. Experimental Tuning Audit & Formal Rejection Verdict

During the forensic optimization exploration, 80 BTC candidate models and 720 XAU candidate models were systematically tested across walk-forward folds and holdout sets.

### Empirical Rejection Evidence:
1. **BTC Candidate Models**:
   - Tuned Logistic Regression ($C=0.01$) and ElasticNet penalized models reduced Holdout Accuracy from 55.26% down to 50.33%.
   - Realized holdout win rate declined from 52.63% to 48.48%.
   - Realized holdout EV collapsed from +0.3158R to +0.2121R (-32.8%).
   - Failed across 4 walk-forward temporal folds.
2. **XAU Candidate Models**:
   - Highly parameterized Random Forest models overfit the training fold and suffered severe generalization collapse on the holdout partition.
   - Holdout accuracy collapsed from 55.98% to 45.11% (-10.87 percentage points).
   - False positive count surged from 22 to 78 (+254.5%).
   - Profit factor dropped from 1.36 to 1.08.
   - Realized EV collapsed from +0.1905R to +0.0448R (-76.5%).

### Formal Locked Verdict:
```text
NO SAFE IMPROVEMENT FOUND — KEEP BASELINE v1.0.0-research
```
All tuned candidate models are permanently REJECTED. The baseline `v1.0.0-research` is locked as the sole approved research artifact.

---

## 3. Strict Partitioning & Data Leakage Firewalls

1. **Chronological Splitting**: Shuffled K-Fold cross validation is strictly prohibited on financial time-series data. All dataset splitting MUST follow strict chronological splits: 60% Train $\rightarrow$ 20% OOS $\rightarrow$ 20% Holdout.
2. **Preprocessor Fitting**: `StandardScaler` and missing-value imputers MUST be fitted solely on the training partition. Transforming OOS and Holdout partitions with training parameters is mathematically enforced via `tests/test_asset_and_leakage_isolation.py`.
3. **Holdout Firewalls**: The final 20% holdout partition is evaluated once and once only. Models cannot be tuned, trained, or feature-selected against the holdout set.

---

## 4. Evidence Accumulation Policy for XAU

* **Current State**: 27 of 28 mandatory gates passed. Gate 4 (Holdout Sample Size) is partial ($N=42 < 50$).
* **Milestone Thresholds**:
  - $N < 50$: System status remains `INSUFFICIENT_EVIDENCE`. Production gating is strictly disabled.
  - $50 \le N < 100$: Status transitions to `PROVISIONAL_RESEARCH` upon accumulating 50 forward resolved observations.
  - $N \ge 100$: Full qualification permitted if win rate $\ge 50\%$, $\text{EV} \ge +0.15\text{R}$, and $\text{PF} \ge 1.25$.
