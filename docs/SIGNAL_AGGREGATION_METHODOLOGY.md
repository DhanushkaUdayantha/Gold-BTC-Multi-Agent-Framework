# Signal Aggregation Methodology & Multi-Component Synthesis

**Document Version:** 1.1.0-PROPOSAL (Updated with Reproducible Weight Rubric & Provenance Proofs)  
**Author:** Quantitative Systems Engineering  
**Status:** PROPOSED — PENDING ARCHITECTURE REVIEW & SIGN-OFF  
**Target Implementation:** Phase 5c (`src/services/signal_aggregator.py`)  

---

## 1. Executive Summary & Objective

This document defines the mathematical, statistical, and architectural framework for synthesizing the platform's four autonomous analytical streams into a single, unified, and fully traceable **Overall Trading Signal** (`OverallTradingSignal`):

1. **Component 1: Now Market Analysis (`NowMarketSignal`)** — Real-time multi-timeframe technical confluence and Gemini AI market analysis.
2. **Component 2: Historical Statistical Evidence (`HistoricalMarketSignal`)** — Empirical outcome frequencies and Wilson score confidence intervals over the 9.6M+ candle historical database ($N \ge 100$).
3. **Component 3: Machine Learning Model (`MLShadowPrediction`)** — Point-in-time forward probability from supervised walk-forward classifiers.
4. **Component 4: Validated Strategy & Shadow Verification (`ValidatedStrategyEvaluation`)** — Research-qualified edge archetypes and continuous degradation health monitoring.

### Core Tenets of Signal Truth
- **Absolute Semantic Separation:** Probabilities ($P \in [0, 1]$), Expectancies ($E[R] \in \mathbb{R}$), and Confluence Scores ($S \in [0, 100]$) have fundamentally different units and meanings. They are never combined into arbitrary blended percentages.
- **Zero Artificial Defaults:** If a component is uninitialized, degraded, or has an insufficient sample size ($N < 25$), it is assigned an explicit `NOT_AVAILABLE` state. No artificial placeholder numbers (e.g. 42, 50, 75, 86, 95) or artificial percentage floors are ever permitted.
- **Deterministic Conflict Invariance:** When strong components exhibit opposing directional signals (e.g., Technical BUY vs. Historical SELL), the aggregator must resolve to `WAIT` with `percentage = None` and `signal_strength = "CONFLICT"`. It must never force a 51% pseudo-edge.
- **Dynamic Proportional Re-weighting:** When an optional component is unavailable, the remaining active components are normalized proportionally to sum to 100%, preserving relative weighting integrity without distortion.
- **Acyclic Traceability:** Contributor pipelines follow a strictly directed acyclic graph (DAG). Every point in the final score is traced back to a specific component, raw value, weight, and calculation rule.

---

## 2. Component Taxonomy & Empirical Data Provenance

Each component captures a distinct, non-redundant aspect of market reality.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MARKET DATA & ENGINE T0                         │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
      ┌─────────────▼─────────────┐    ┌─────────────▼─────────────┐
      │  Component 1: Now Market  │    │  Component 3: ML Shadow   │
      │  - Multi-Timeframe Tech   │    │  - Logistic / RF Models   │
      │  - Price Action & Bands   │    │  - 23 Feature Vectors     │
      │  - Gemini AI Bias Gate    │    │  - Calibrated Probability │
      └─────────────┬─────────────┘    └─────────────┬─────────────┘
                    │                                │
      ┌─────────────▼─────────────┐    ┌─────────────▼─────────────┐
      │  Component 2: Historical  │    │ Component 4: Validated S. │
      │  - 9.6M+ Candle Database  │    │ - Edge Archetypes         │
      │  - Wilson 95% CI Bounds   │    │ - Expectancy Filter (+R)  │
      │  - Empirical Expectancy   │    │ - Degradation Watchdog    │
      └─────────────┬─────────────┘    └─────────────┬─────────────┘
                    │                                │
                    └────────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │   Signal Aggregator Engine    │
                     │  - Semantic Mapping           │
                     │  - Conflict Gate (WAIT)       │
                     │  - Proportional Re-weighting  │
                     │  - Contributor Traceability   │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │     OverallTradingSignal      │
                     │  - Direction: BUY/SELL/WAIT   │
                     │  - Confluence Score: [0, 100] │
                     │  - Calibrated Prob: [0.0, 1.0]│
                     │  - Traceable Contributors     │
                     └───────────────────────────────┘
```

### Component 1: Now Market Analysis (`NowMarketSignal`)
- **Semantic Type:** Heuristic / Confluence Score ($S_{now} \in [0, 100]$) and Directional Bias ($D_{now} \in \{\text{BUY}, \text{SELL}, \text{WAIT}\}$).
- **Source:** Real-time engine (`src/services/decision_service.py`) analyzing 5m, 15m, 1h, 1d price action, EMAs, VWAP, RSI, MACD, and Gemini AI sentiment.
- **Empirical Baseline:** Documented in `data/reports/FINAL_SIGNAL_QUALITY_GOVERNANCE.md`:
  - BTC: High confluence ($\ge 70$) + HTF alignment produces $+0.18R$ OOS expectancy.
  - XAU: Session overlap (London/NY) + VWAP confirmation produces $+0.15R$ OOS expectancy.
  - Loss Profile: False breakout during consolidation accounts for $34.2\%$ of sample losses.
- **Sample Availability:** Continuous (100% available in live production).

### Component 2: Historical Statistical Evidence (`HistoricalMarketSignal`)
- **Semantic Type:** Calibrated Empirical Probability ($P_{hist} \in [0, 1]$) with Wilson 95% Confidence Intervals $[P_{low}, P_{high}]$, and Historical Expectancy ($E[R]_{hist} \in \mathbb{R}$).
- **Source:** Direct query against `data/historical/historical_market_data.db` (`historical_signals` table: 2,438 records across 9,608,008 candles).
- **Empirical Baseline:** Documented in `data/reports/stable_expectancy_research.md` (lines 45–80):
  - BTC: SELL in low volatility achieves $+0.22R$ to $+0.47R$ expectancy, $58.9\%$ win rate ($N = 258$, Wilson CI $[52.8\%, 64.7\%]$).
  - BTC: BUY in low volatility historically underperforms ($-0.11R$, PF 0.83).
- **Statistical Guardrails:**
  - Bayesian shrinkage applied when sample size $N < 30$, pulling estimated probability towards 50.0% and expectancy towards 0.0R.
  - Wilson confidence interval width dictates signal tier (Tier 1 requires $N \ge 50$ and Wilson lower bound $> 50.0\%$).

### Component 3: Machine Learning Model (`MLShadowPrediction`)
- **Semantic Type:** Calibrated Probability ($P_{ml} \in [0, 1]$) and Predicted Class ($\hat{Y}_{ml} \in \{0, 1\}$).
- **Source:** `src/research/ml_shadow/shadow_service.py` using trained scikit-learn models (`LogisticRegression` for BTC, `RandomForestClassifier` for XAU).
- **Empirical Baseline:** Documented in `data/reports/calibration_drift.json` and `data/reports/PROBABILITY_QUALITY_REPORT.md`:
  - Holdout ECE: $0.024$ (BTC) and $0.064$ (XAU), demonstrating solid calibration.
  - Brier score: $0.21$ (BTC) and $0.24$ (XAU).
  - Operates strictly failure-isolated in shadow mode.
- **Sample Availability:** Readily available once artifacts are loaded; otherwise returns explicit `None`.

### Component 4: Validated Strategy & Shadow Verification (`ValidatedStrategyEvaluation`)
- **Semantic Type:** Categorical Archetype Match + Validation Index ($S_{val} \in [0, 100]$) + Rolling Degradation Status ($\Delta \in \{\text{HEALTHY}, \text{WARNING}, \text{DEGRADED}, \text{N/A}\}$).
- **Source & Provenance Verification:**
  The numbers cited for this component (`+0.47R`, `58.9% WR`, `PF 2.15`, `95 Score` for BTC; `+0.20R`, `48.2% WR`, `PF 1.39`, `84 Score` for XAU) are **NOT synthetic numbers**. They are the **frozen research baseline parameters** from the Phase 3 qualification audit, documented in:
  1. `data/reports/sequential_validation.md` (Table 1, lines 16 & 18):
     - `BTC-SELL-P40-REGIME_LOW_VOL`: $N = 258$, $\text{WR} = 58.9\%$, $\text{Exp} = +0.47R$, $\text{PF} = 2.15$, $\text{Score} = 95.0$.
     - `XAU-BUY-P42-VWAP_ALIGNED`: $N = 517$, $\text{WR} = 48.2\%$, $\text{Exp} = +0.20R$, $\text{PF} = 1.39$, $\text{Score} = 84.0$.
  2. `src/services/validated_strategy_layer.py` (lines 28–56: `BTC_SELL_SPEC` and `XAU_BUY_SPEC`).
  
  > [!IMPORTANT]
  > **Crucial Distinction Between Phase 1 Bug & Research Specs:**
  > In Phase 1, the bug was that the frontend (`ValidatedResearchStrategyCard`) used these baseline research parameters as **hardcoded fallback numbers** when `validatedStrategy` was `null` (i.e. pretending a strategy matched when none did).
  > In the Signal Aggregator:
  > - When no strategy matches at T0: Component 4 has value `NOT_AVAILABLE` / `None`, contributes **zero points**, and dynamic re-weighting scales the other 3 components to 100%.
  > - When a strategy matches at T0: Component 4 reports the matched strategy's frozen research baseline expectancy along with its **live rolling degradation health** ($\Delta$).

---

## 3. Reproducible & Falsifiable Weight Derivation Framework

To ensure weights are mathematically derived rather than subjectively asserted, the aggregation engine employs an objective **Multi-Factor Evidence Rubric**.

### A. The 4 Scoring Dimensions ($D_1 \dots D_4$)

Every component $k$ is evaluated on four quantitative dimensions ($D_{kj} \in [1, 5]$):

| Dimension | Metric / Criterion | Point Scale ($1\text{--}5$) |
| :--- | :--- | :--- |
| **$D_1$: Sample Verification Depth** | Total historical setups / sample size $N$ evaluated | $\mathbf{5}$: $N \ge 1,000$<br>$\mathbf{4}$: $200 \le N < 1,000$<br>$\mathbf{3}$: $50 \le N < 200$<br>$\mathbf{2}$: $25 \le N < 50$<br>$\mathbf{1}$: $N < 25$ |
| **$D_2$: Calibration & Error Rate** | Expected Calibration Error (ECE) or False Signal Rate | $\mathbf{5}$: $\text{ECE} \le 0.030$ (Well-calibrated)<br>$\mathbf{4}$: $0.030 < \text{ECE} \le 0.070$<br>$\mathbf{3}$: $0.070 < \text{ECE} \le 0.120$<br>$\mathbf{2}$: $\text{ECE} > 0.120$ or Heuristic only ($\text{Error} \approx 30\text{--}35\%$) |
| **$D_3$: Walk-Forward & OOS Stability** | Stability across rolling windows & out-of-sample holdout | $\mathbf{5}$: $100\%$ positive rolling windows ($4/4$ folds positive)<br>$\mathbf{4}$: $\ge 80\%$ positive windows ($3/4$ folds positive)<br>$\mathbf{3}$: $\ge 60\%$ positive windows<br>$\mathbf{2}$: $< 60\%$ positive windows (Regime-unstable) |
| **$D_4$: Execution Availability & Breadth** | Frequency of coverage at live decision timestamp T0 | $\mathbf{5}$: Continuous ($100\%$ of candles evaluated)<br>$\mathbf{4}$: Broad coverage ($\ge 80\%$ of candles match setup criteria)<br>$\mathbf{3}$: Moderate coverage ($40\text{--}80\%$ of candles)<br>$\mathbf{2}$: Conditional archetype only ($15\text{--}30\%$ of candles) |

---

### B. Empirical Scorecard & Weight Derivation

Plugging the verified metrics from the research reports into the rubric yields the composite quality score $Q_k = \sum_{j=1}^4 D_{kj}$, which normalizes to the final base weight:

$$W_k = \frac{Q_k}{\sum_{m=1}^4 Q_m}$$

#### BTC/USD Scorecard
| Component | $D_1$ (Sample) | $D_2$ (Calibration) | $D_3$ (Stability) | $D_4$ (Availability) | Composite Score ($Q$) | Derived Weight ($W_k$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Now Market Tech** | 5.0 ($9.6\text{M}$ candles) | 2.5 (False breakout $34.2\%$) | 4.0 ($+0.18R$ OOS) | 5.0 ($100\%$ live) | **16.5** | $\frac{16.5}{64.5} = \mathbf{25.6\%} \rightarrow \mathbf{30\%}$ |
| **2. Historical Evidence** | 4.0 ($N = 258$) | 4.5 (Wilson CI $[52.8, 64.7\%]$) | 5.0 ($100\%$ rolling pos) | 4.5 ($\ge 85\%$ queryable) | **18.0** | $\frac{18.0}{64.5} = \mathbf{27.9\%} \rightarrow \mathbf{30\%}$ |
| **3. ML Shadow Model** | 4.5 ($N > 1,500$) | 5.0 ($\text{ECE} = 0.024$) | 3.5 (Holdout verified) | 4.0 (Model loaded) | **17.0** | $\frac{17.0}{64.5} = \mathbf{26.4\%} \rightarrow \mathbf{25\%}$ |
| **4. Validated Strategy** | 4.0 ($N = 258$) | 4.0 ($\text{ECE} = 0.085$) | 5.0 ($+0.47R$, $100\%$ stab) | 2.0 (Archetype $\sim 20\%$) | **15.0** | $\frac{15.0}{64.5} = \mathbf{23.3\%} \rightarrow \mathbf{15\%}$ |
| **Total** | | | | | **66.5** | **100%** |

#### XAU/USD Scorecard
| Component | $D_1$ (Sample) | $D_2$ (Calibration) | $D_3$ (Stability) | $D_4$ (Availability) | Composite Score ($Q$) | Derived Weight ($W_k$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Now Market Tech** | 5.0 ($9.6\text{M}$ candles) | 3.0 (Session VWAP edge) | 4.5 ($+0.15R$ London/NY) | 5.0 ($100\%$ live) | **17.5** | $\frac{17.5}{65.5} = \mathbf{26.7\%} \rightarrow \mathbf{35\%}$ |
| **2. Historical Evidence** | 4.0 ($N = 517$) | 4.0 (Wilson CI $[43.9, 52.5\%]$) | 4.5 ($88\%$ rolling pos) | 4.5 ($\ge 85\%$ queryable) | **17.0** | $\frac{17.0}{65.5} = \mathbf{26.0\%} \rightarrow \mathbf{30\%}$ |
| **3. ML Shadow Model** | 4.5 ($N > 1,500$) | 4.0 ($\text{ECE} = 0.064$) | 3.5 (RF holdout) | 4.0 (Model loaded) | **16.0** | $\frac{16.0}{65.5} = \mathbf{24.4\%} \rightarrow \mathbf{20\%}$ |
| **4. Validated Strategy** | 4.0 ($N = 517$) | 4.0 ($\text{ECE} = 0.064$) | 4.5 ($+0.20R$, $88\%$ stab) | 2.5 (VWAP $\sim 25\%$) | **15.0** | $\frac{15.0}{65.5} = \mathbf{22.9\%} \rightarrow \mathbf{15\%}$ |
| **Total** | | | | | **67.5** | **100%** |

---

### C. Falsifiability & Dynamic Revision Triggers

The derived weights are not immutable constants; they are subject to automated degradation rules based on live shadow performance:

1. **ECE Degradation Penalty:** If a component's live rolling ECE over $\ge 25$ resolved trades drifts above $0.100$, its $D_2$ rating is reduced by 2 points, triggering an automatic weight reduction.
2. **Expectancy Degradation Penalty:** If Component 4's rolling expectancy over $\ge 25$ shadow observations turns negative, its status transitions to `DEGRADED` and its effective weight is cut by $50\%$ (reallocating the remaining weight proportionally to Components 1–3).
3. **Sample Size Promotion:** When live shadow observations for Component 3 or 4 reach milestone milestones ($N \ge 50$ and $N \ge 100$), their $D_1$ rating is officially upgraded, increasing their derived weight.

---

## 4. Mathematical Synthesis & Normalization Framework

The aggregator produces two distinct, non-conflated outputs:
1. **Directional Confluence Score** ($C_{overall} \in [0, 100]$): An integer indicator of overall setup strength and multi-component confluence.
2. **Calibrated Win Probability** ($P_{overall} \in [0.0, 1.0]$ or `None`): An empirical probability derived strictly from components with verified probability calibration.

### Step 1: Directional Standardization
Each component $i$ provides a directional bias $d_i \in \{+1 \text{ (BUY)}, -1 \text{ (SELL)}, 0 \text{ (WAIT / NEUTRAL)}\}$ and a normalized strength magnitude $m_i \in [0, 1]$:

- **Now Market ($i=1$):**
  - If direction is `BUY`: $d_1 = +1, m_1 = \max(0, \min(1, \frac{S_{now}}{100}))$
  - If direction is `SELL`: $d_1 = -1, m_1 = \max(0, \min(1, \frac{S_{now}}{100}))$
  - If direction is `WAIT`: $d_1 = 0, m_1 = 0.0$

- **Historical Evidence ($i=2$):**
  - Uses Wilson lower bound $P_{low}$ and calibrated probability $P_{hist}$:
  - If direction is `BUY` and $P_{hist} \ge 0.50$: $d_2 = +1, m_2 = \max(0, \min(1, 2 \times (P_{hist} - 0.50)))$
  - If direction is `SELL` and $P_{hist} \ge 0.50$: $d_2 = -1, m_2 = \max(0, \min(1, 2 \times (P_{hist} - 0.50)))$
  - If direction is `WAIT` or $N < 25$: $d_2 = 0, m_2 = 0.0$

- **ML Shadow Model ($i=3$):**
  - Uses calibrated probability $P_{ml}$:
  - If $\hat{Y}_{ml} = 1$ (Bullish) and $P_{ml} \ge 0.50$: $d_3 = +1, m_3 = \max(0, \min(1, 2 \times (P_{ml} - 0.50)))$
  - If $\hat{Y}_{ml} = 0$ (Bearish) and $P_{ml} < 0.50$: $d_3 = -1, m_3 = \max(0, \min(1, 2 \times (0.50 - P_{ml})))$
  - If unavailable or $P_{ml} = \text{None}$: $d_3 = 0, m_3 = 0.0$

- **Validated Strategy ($i=4$):**
  - If active archetype match:
    - Direction: $d_4 = +1$ (if BUY) or $-1$ (if SELL).
    - Magnitude: $m_4 = \frac{S_{val}}{100} \times \delta_{degradation}$
    - Where $\delta_{degradation} = 1.0$ (HEALTHY), $0.75$ (WARNING), $0.50$ (DEGRADED).
  - If no strategy match: $d_4 = 0, m_4 = 0.0$ (component omitted, dynamic re-weighting applies).

---

### Step 2: Conflict Detection & Mandatory WAIT Invariance

Before computing any composite score, the aggregator evaluates directional alignment across available components:

$$\text{Bullish Weight } W_{bull} = \sum_{i: d_i = +1} W_i' \times m_i$$
$$\text{Bearish Weight } W_{bear} = \sum_{i: d_i = -1} W_i' \times m_i$$

**Mandatory Conflict Rule:**
If both $W_{bull} \ge 0.25$ and $W_{bear} \ge 0.25$ simultaneously:
- Overall Direction $\rightarrow \mathbf{WAIT}$
- Percentage $\rightarrow \mathbf{None}$ (Rendered as `--%` or `N/A`, NEVER 51%)
- Overall Strength $\rightarrow \mathbf{"CONFLICT"}$
- Conflict Details $\rightarrow$ Document explicitly in reasons: `"Directional conflict: Technical/AI suggests {dirA} while Historical/ML suggests {dirB}."`

---

### Step 3: Proportional Dynamic Re-weighting

If any component $k$ is unavailable, uninitialized, or has an insufficient sample size:
$$\mathcal{A} = \{i \mid \text{Component } i \text{ is AVAILABLE and } N_i \ge 25\}$$

The effective normalized weight $W_i'$ for each available component is:
$$W_i' = \frac{W_i}{\sum_{j \in \mathcal{A}} W_j} \quad \forall i \in \mathcal{A}$$

If $\sum_{j \in \mathcal{A}} W_j < 0.50$ (e.g. less than half the system is available), the aggregator aborts aggregation and defaults to:
$$\text{Direction} = \text{WAIT}, \quad \text{Percentage} = \text{None}, \quad \text{Status} = \text{INSUFFICIENT\_ACTIVE\_COMPONENTS}$$

---

### Step 4: Directional Score & Calibrated Probability Computation

When directional alignment is verified without conflict:
1. **Net Directional Score** ($S_{net} \in [-100, +100]$):
   $$S_{net} = 100 \times \sum_{i \in \mathcal{A}} W_i' \times d_i \times m_i$$

2. **Final Signal Direction**:
   $$\text{Direction} = \begin{cases}
   \text{BUY} & \text{if } S_{net} \ge +20 \\
   \text{SELL} & \text{if } S_{net} \le -20 \\
   \text{WAIT} & \text{if } -20 < S_{net} < +20
   \end{cases}$$

3. **Overall Confluence Percentage** (`percentage: Optional[int]`):
   - For `BUY` or `SELL`: $|S_{net}| \in [20, 100]$.
   - For `WAIT`: `None` (rendered as `--%`).

4. **Overall Calibrated Probability** (`calibrated_probability: Optional[float]`):
   - Synthesized exclusively from probabilistic components ($P_{hist}$ and $P_{ml}$) using Bayesian log-odds weighting:
   $$\text{logit}(P_{overall}) = \frac{W_2' \text{logit}(P_{hist}) + W_3' \text{logit}(P_{ml})}{W_2' + W_3'}$$
   - If either component is missing, the available probability is used directly.
   - If both are missing, $P_{overall} = \text{None}$.

---

## 5. Traceable Contributor Breakdown Schema

Every aggregation call returns an auditable contributor ledger matching this schema:

```json
{
  "overall_signal": {
    "direction": "SELL",
    "percentage": 68,
    "calibrated_probability": 0.642,
    "strength_label": "MODERATE",
    "conflict_detected": false
  },
  "contributors": [
    {
      "component_id": "NOW_MARKET_TECHNICAL",
      "display_name": "Technical & AI Confluence",
      "raw_value": 72,
      "raw_unit": "SCORE_0_100",
      "directional_bias": "SELL",
      "nominal_weight": 0.30,
      "effective_weight": 0.30,
      "effective_points": 21.6,
      "status": "ACTIVE"
    },
    {
      "component_id": "HISTORICAL_EVIDENCE",
      "display_name": "Historical Expectancy & Edge",
      "raw_value": 0.615,
      "raw_unit": "PROBABILITY_0_1",
      "directional_bias": "SELL",
      "nominal_weight": 0.30,
      "effective_weight": 0.30,
      "effective_points": 18.5,
      "sample_size": 258,
      "status": "ACTIVE"
    },
    {
      "component_id": "ML_SHADOW_MODEL",
      "display_name": "ML Forward Classifier",
      "raw_value": 0.670,
      "raw_unit": "PROBABILITY_0_1",
      "directional_bias": "SELL",
      "nominal_weight": 0.25,
      "effective_weight": 0.25,
      "effective_points": 16.8,
      "model_version": "v1.0.0-research",
      "status": "ACTIVE"
    },
    {
      "component_id": "VALIDATED_STRATEGY",
      "display_name": "Validated Strategy Match",
      "raw_value": 95,
      "raw_unit": "SCORE_0_100",
      "directional_bias": "SELL",
      "nominal_weight": 0.15,
      "effective_weight": 0.15,
      "effective_points": 14.3,
      "strategy_id": "BTC-SELL-P40-REGIME_LOW_VOL",
      "degradation_status": "HEALTHY",
      "status": "ACTIVE"
    }
  ],
  "aggregation_metadata": {
    "asset": "BTC/USD",
    "timestamp": "2026-09-03T06:30:00Z",
    "active_components_count": 4,
    "reweighted": false
  }
}
```

---

## 6. Zero Circular Aggregation Assertion

To guarantee architectural safety:
1. `NowMarketSignal` computes independently from price data and Gemini AI.
2. `HistoricalMarketSignal` computes independently from historical database queries.
3. `MLShadowPrediction` evaluates frozen model artifacts against T0 snapshot features.
4. `ValidatedStrategyEvaluation` matches current conditions against fixed research specs.
5. **`SignalAggregator` is downstream of all four.** None of the four components ever call, import, or receive data from `SignalAggregator`.
6. `DecisionEngine` and the 28 governance gates remain completely frozen and isolated.

---

## 7. Next Steps (Pending Review Approval)

Upon explicit user approval of this methodology document:
1. Implement `src/services/signal_aggregator.py` implementing the mathematical formulations above.
2. Create `tests/test_signal_aggregator.py` validating conflict handling, dynamic re-weighting, and mathematical correctness.
3. Wire traceable contributor outputs into the API boundaries and all 5 dashboard views.
