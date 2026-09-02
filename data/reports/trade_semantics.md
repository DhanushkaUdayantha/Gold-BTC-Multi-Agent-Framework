# Authoritative Trade & Outcome Semantics Specification

**Version:** 1.0  
**Status:** Authoritative Standard for All Research Modules  
**Compliance Requirement:** Mandatory across all research scripts and simulations

---

## 1. Signal Definition

A **Signal** is a point-in-time timestamped directional output produced by the analysis pipeline:
- **`BUY`**: Bullish trading candidate
- **`SELL`**: Bearish trading candidate
- **`WAIT`**: No action / neutral state

Each signal encapsulates point-in-time state ($t \le T$):
- Timestamp, Asset Symbol, Direction
- Model Probability ($0.0 \le P \le 1.0$)
- Entry Price, Stop Loss (SL), Take Profit 1 (TP1), Take Profit 2 (TP2)
- Market Regime (`LOW_VOLATILITY`, `TRENDING`, `RANGING`, `HIGH_VOLATILITY`)
- Directional Alignment Indicators (HTF, S/R, VWAP, EMA, Momentum)

---

## 2. Trade Definition

A **Trade** exists **ONLY** if:
1. Signal direction $\in \{\text{BUY}, \text{SELL}\}$
2. Entry price is strictly positive ($> 0$)
3. Stop Loss is strictly positive and valid relative to Entry:
   - For `BUY`: $\text{SL} < \text{Entry}$
   - For `SELL`: $\text{SL} > \text{Entry}$
4. Initial Risk distance $R = |\text{Entry} - \text{SL}| > 0$
5. Take Profit is valid relative to Entry:
   - For `BUY`: $\text{TP} > \text{Entry}$
   - For `SELL`: $\text{TP} < \text{Entry}$

> [!NOTE]
> `WAIT` signals are **NEVER** classified as trades. They represent neutral or sub-threshold market observation states.

---

## 3. Outcome & Resolution Semantics

Outcomes are evaluated chronologically forward from entry:

| Outcome | BUY Condition | SELL Condition | Realized R Value |
|---|---|---|:---:|
| **`WIN`** | TP reached before SL | TP reached before SL | **$+1.0\text{R}$** (or distance-based) |
| **`LOSS`** | SL reached before TP | SL reached before TP | **$-1.0\text{R}$** |
| **`BREAKEVEN`** | Exit price == Entry price | Exit price == Entry price | **$0.0\text{R}$** |
| **`EXPIRED`** | Max holding period elapsed | Max holding period elapsed | $(\text{Exit} - \text{Entry}) / R$ |
| **`INVALID`** | Missing or corrupted data | Missing or corrupted data | Excluded from statistics |

---

## 4. Ambiguous Candle Resolution Policy (Conservative Standard)

If a single price candle touches **BOTH** Take Profit and Stop Loss levels, and tick-by-tick order of occurrence cannot be established:

> [!CAUTION]
> **Strict Policy:** Resolve as **`LOSS` ($-1.0\text{R}$)**.  
> Under no circumstances may an ambiguous bar be resolved favorably as a WIN or assumed to have hit TP first.

---

## 5. Standardized Metric Formulations

### 1. Expectancy (R)
$$\text{Expectancy} = \frac{1}{N} \sum_{i=1}^N R_i$$

### 2. Profit Factor (PF)
$$\text{Profit Factor} = \frac{\sum_{R_i > 0} R_i}{\sum_{R_i < 0} |R_i|}$$

### 3. Maximum Drawdown (Peak-to-Valley R)
$$\text{DD}_t = \max_{0 \le s \le t}(\text{CumR}_s) - \text{CumR}_t, \quad \text{Max DD} = \max_t(\text{DD}_t)$$

### 4. Winner Retention & Loser Reduction
$$\text{Winner Retention} = \frac{N_{\text{Shadow Wins}}}{N_{\text{Base Wins}}} \times 100\%$$
$$\text{Loser Elimination} = \frac{N_{\text{Base Losses}} - N_{\text{Shadow Losses}}}{N_{\text{Base Losses}}} \times 100\%$$
