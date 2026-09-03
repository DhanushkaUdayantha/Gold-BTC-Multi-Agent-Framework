# Signal Aggregation Methodology & Multi-Component Synthesis

**Document Version:** 1.0.0-PROPOSAL  
**Author:** Quantitative Systems Engineering  
**Status:** PROPOSED — PENDING ARCHITECTURE REVIEW & SIGN-OFF  
**Target Implementation:** Phase 5c (`src/services/signal_aggregator.py`)  

---

## 1. Executive Summary & Objective

This document defines the mathematical, statistical, and architectural framework for synthesizing the platform's four autonomous analytical streams into a single, unified, and fully traceable **Overall Trading Signal** (`OverallTradingSignal`):

1. **Component 1: Now Market Analysis (`NowMarketSignal`)** — Real-time technical confluence and Gemini AI market analysis.
2. **Component 2: Historical Statistical Evidence (`HistoricalMarketSignal`)** — Long-term empirical outcome frequencies from the 9.6M+ candle historical database ($N \ge 100$).
3. **Component 3: Machine Learning Model (`MLShadowPrediction`)** — Point-in-time forward probability from trained, failure-isolated classifiers.
4. **Component 4: Validated Strategy & Shadow Verification (`ValidatedStrategyEvaluation`)** — Validated edge archetypes and continuous degradation health monitoring.

### Core Tenets of Signal Truth
- **Absolute Semantic Separation:** Probabilities ($P \in [0, 1]$), Expectancies ($E[R] \in \mathbb{R}$), and Confluence Scores ($S \in [0, 100]$) have fundamentally different units and meanings. They are never combined into arbitrary blended percentages.
- **Zero Artificial Defaults:** If a component is uninitialized, degraded, or has an insufficient sample size ($N < 25$), it is assigned an explicit `NOT_AVAILABLE` state. No artificial placeholder numbers (e.g. 42, 50, 75, 86, 95) or artificial percentage floors are ever permitted.
- **Deterministic Conflict Invariance:** When strong components exhibit opposing directional signals (e.g., Technical BUY vs. Historical SELL), the aggregator must resolve to `WAIT` with `percentage = None` and `signal_strength = "CONFLICT"`. It must never force a 51% pseudo-edge.
- **Dynamic Proportional Re-weighting:** When an optional component is unavailable, the remaining active components are normalized proportionally to sum to 100%, preserving relative weighting integrity without distortion.
- **Acyclic Traceability:** Contributor pipelines follow a strictly directed acyclic graph (DAG). Every point in the final score is traced back to a specific component, raw value, weight, and calculation rule.

---

## 2. Component Taxonomy & Empirical Performance Profiles

Each of the four components captures a distinct, non-redundant aspect of market reality.

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
- **Measurement:** Multi-timeframe trend alignment (1d, 1h, 15m, 5m), EMA stacks, VWAP proximity, momentum indicators (RSI, MACD), and Gemini AI macroeconomic sentiment.
- **Empirical Edge:**
  - High confluence ($\ge 70$) aligned with higher-timeframe trend produces $+0.18R$ OOS expectancy on BTC and $+0.15R$ on XAU.
  - However, during choppy consolidation, momentum indicators produce false breakouts (accounting for 34.2% of sample losses).
- **Sample Availability:** 100% available in live real-time operation.

### Component 2: Historical Statistical Evidence (`HistoricalMarketSignal`)
- **Semantic Type:** Calibrated Empirical Probability ($P_{hist} \in [0, 1]$) with Wilson Score 95% Confidence Intervals $[P_{low}, P_{high}]$, and Historical Expectancy ($E[R]_{hist} \in \mathbb{R}$).
- **Measurement:** Lookback across 2,438 historically recorded system signals and 9.6M candles matching the current setup's regime, confluence band, and session.
- **Empirical Edge:**
  - BTC SELL setups in low-volatility regimes demonstrate strong historical edge (+0.22R to +0.47R, PF > 1.41).
  - BTC BUY setups in low-volatility regimes historically underperform (-0.11R, PF 0.83).
- **Statistical Guardrails:**
  - Bayesian shrinkage applied when sample size $N < 30$, pulling estimated probability towards 50.0% and expectancy towards 0.0R.
  - Wilson confidence interval width dictates signal tier (Tier 1 requires $N \ge 50$ and Wilson lower bound $> 50.0\%$).

### Component 3: Machine Learning Model (`MLShadowPrediction`)
- **Semantic Type:** Calibrated Probability ($P_{ml} \in [0, 1]$) and Predicted Class ($\hat{Y}_{ml} \in \{0, 1\}$).
- **Measurement:** Supervised walk-forward models (scikit-learn Logistic Regression for BTC, Random Forest for XAU) trained on frozen walk-forward splits evaluating 23 normalized features at T0.
- **Empirical Edge:**
  - Well-calibrated with Expected Calibration Error (ECE) $\le 0.025$ and Brier score $< 0.22$.
  - Operates completely non-blocking in shadow mode with zero feedback into base decision execution.
- **Sample Availability:** Readily available for BTC and XAU once artifacts are loaded; otherwise returns explicit `None`.

### Component 4: Validated Strategy & Shadow Verification (`ValidatedStrategyEvaluation`)
- **Semantic Type:** Categorical Archetype Match + Validation Index ($S_{val} \in [0, 100]$) + Rolling Degradation Status ($\Delta \in \{\text{HEALTHY}, \text{WARNING}, \text{DEGRADED}, \text{N/A}\}$).
- **Measurement:** 
  - BTC: `BTC-SELL-P40-REGIME_LOW_VOL` (Expectancy: $+0.47R$, WR: $58.9\%$, PF: $2.15$, Validation Score: $95/100$).
  - XAU: `XAU-BUY-P42-VWAP_ALIGNED` (Expectancy: $+0.20R$, WR: $48.2\%$, PF: $1.39$, Validation Score: $84/100$).
- **Empirical Edge:**
  - Highest per-trade expectancy of any individual component (+0.47R on BTC), but low activation frequency (only triggers on strict archetype conditions).
- **Degradation Governance:**
  - If rolling forward win rate drops $> 10\%$ below research expectancy, status transitions to `WARNING`.
  - If rolling expectancy turns negative over $\ge 25$ live shadow observations, status transitions to `DEGRADED`, triggering a 50% penalty on this component's contribution.

---

## 3. Proposed Component Weighting Model

Because Bitcoin and Gold possess differing market microstructure dynamics—Bitcoin exhibiting strong momentum persistence in trending regimes and pronounced directional asymmetry in low volatility, whereas Gold exhibits strong mean-reversion around VWAP and session-specific liquidity bounds—the weighting framework proposes asset-specific calibration.

### Proposed Base Weights ($W_i$)

| Component | Key Metric | BTC/USD Weight | XAU/USD Weight | Rationale & Empirical Grounding |
| :--- | :--- | :---: | :---: | :--- |
| **1. Now Market Analysis** | Confluence Score ($0\text{--}100$) | **35%** | **40%** | Primary real-time execution gate. Higher weight on XAU due to tight session-bound structure (London/NY overlap). |
| **2. Historical Evidence** | Wilson Calibrated Prob & Exp ($R$) | **30%** | **30%** | Anchors the setup to empirical base rates over 9.6M+ candles. Equal weight across both assets. |
| **3. ML Shadow Model** | Calibrated Prob ($0.0\text{--}1.0$) | **20%** | **15%** | BTC exhibits higher linear predictability across feature combinations; XAU Random Forest is more conservative. |
| **4. Validated Strategy** | Archetype Match & Degradation | **15%** | **15%** | High expectancy edge (+0.47R / +0.20R) when active; penalizes signal if degradation is detected. |
| **Total** | | **100%** | **100%** | Normalized base sum. |

---

## 4. Mathematical Synthesis & Normalization Framework

To prevent unit mixing and preserve data integrity, the aggregator computes two distinct outputs:
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
      "nominal_weight": 0.35,
      "effective_weight": 0.35,
      "effective_points": 25.2,
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
      "sample_size": 142,
      "status": "ACTIVE"
    },
    {
      "component_id": "ML_SHADOW_MODEL",
      "display_name": "ML Forward Classifier",
      "raw_value": 0.670,
      "raw_unit": "PROBABILITY_0_1",
      "directional_bias": "SELL",
      "nominal_weight": 0.20,
      "effective_weight": 0.20,
      "effective_points": 13.4,
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
      "effective_points": 10.9,
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
