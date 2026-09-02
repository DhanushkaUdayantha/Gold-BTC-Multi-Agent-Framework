# ML Feature Leakage & Point-in-Time Audit Report

**Audit Date**: September 2, 2026  
**Objective**: Ensure 100% strict point-in-time feature isolation with zero future or post-trade information.

---

## 1. Feature Classification Summary

| Feature Name | Source Subsystem | Availability Time | Leakage Classification | Audit Rationale |
|---|---|:---:|:---:|---|
| `ambiguity_flag` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Simultaneous touch flag determined after T0. |
| `bias_MTF_Alignment` | `confluence_engine` | `T0` | **🟢 SAFE** | MTF direction consensus at T0. |
| `bias_Momentum` | `confluence_engine` | `T0` | **🟢 SAFE** | Momentum bias at T0. |
| `bias_VWAP` | `confluence_engine` | `T0` | **🟢 SAFE** | VWAP directional bias at T0. |
| `bias_Volume_Confirmation` | `confluence_engine` | `T0` | **🟢 SAFE** | Volume bias at T0. |
| `confluence_score` | `confluence_engine` | `T0` | **🟢 SAFE** | Total 17-factor score (0-100) computed at T0. |
| `data_quality` | `confluence_engine` | `T0` | **🟢 SAFE** | Freshness & completeness rating at T0. |
| `dataset_id` | `historical_signals` | `T0` | **🟢 SAFE** | Dataset metadata identifier. |
| `day_of_week` | `signal_timestamp` | `T0` | **🟢 SAFE** | Day of week (0=Mon, 6=Sun). |
| `direction` | `decision_engine` | `T0` | **🟢 SAFE** | Proposed trade direction (BUY/SELL). |
| `entry_price` | `market_snapshot` | `T0` | **🟢 SAFE** | Exact spot price at closed candle T0. |
| `exit_price` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Exit price after trade close. |
| `failure_reason` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Post-hoc failure attribution. |
| `gate_direction` | `confluence_engine` | `T0` | **🟢 SAFE** | Directional consensus gate at T0. |
| `gemini_score` | `confluence_engine` | `T0` | **🟢 SAFE** | Gemini AI confirmation score (0-10) computed at T0. |
| `hour_of_day` | `signal_timestamp` | `T0` | **🟢 SAFE** | UTC hour of signal timestamp. |
| `mae` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Maximum Adverse Excursion occurring after T0. |
| `market_regime` | `confluence_engine` | `T0` | **🟢 SAFE** | Volatility and trend regime at T0. |
| `max_r` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Peak R return reached after T0. |
| `mfe` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Maximum Favorable Excursion occurring after T0. |
| `outcome` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Target outcome label (WIN/LOSS) determined strictly after T0. |
| `outcome_timestamp` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Resolution time after trade close. |
| `realized_r` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Realized return multiple after trade close. |
| `run_id` | `historical_signals` | `T0` | **🟢 SAFE** | Experiment batch identifier. |
| `score_Breakout_Retest` | `confluence_engine` | `T0` | **🟢 SAFE** | Breakout confirmation score at T0. |
| `score_EMA_MA_Stack` | `confluence_engine` | `T0` | **🟢 SAFE** | EMA 20/50/200 stack score at T0. |
| `score_Elliott_Wave` | `confluence_engine` | `T0` | **🟢 SAFE** | Elliott wave classification score at T0. |
| `score_Fibonacci_OTE` | `confluence_engine` | `T0` | **🟢 SAFE** | Fibonacci discount/premium zone score at T0. |
| `score_Gemini_AI` | `confluence_engine` | `T0` | **🟢 SAFE** | AI confirmation score at T0. |
| `score_HTF_Trend` | `confluence_engine` | `T0` | **🟢 SAFE** | 1h/1d trend score at T0. |
| `score_ICT_Concepts` | `confluence_engine` | `T0` | **🟢 SAFE** | Fair Value Gap score at T0. |
| `score_MACD` | `confluence_engine` | `T0` | **🟢 SAFE** | MACD state & histogram score at T0. |
| `score_MTF_Alignment` | `confluence_engine` | `T0` | **🟢 SAFE** | Multi-timeframe agreement score at T0. |
| `score_Market_Structure` | `confluence_engine` | `T0` | **🟢 SAFE** | MSS/BOS structure score at T0. |
| `score_Momentum` | `confluence_engine` | `T0` | **🟢 SAFE** | 5m/15m momentum score at T0. |
| `score_RSI` | `confluence_engine` | `T0` | **🟢 SAFE** | RSI momentum score at T0. |
| `score_SMC_ICT` | `confluence_engine` | `T0` | **🟢 SAFE** | PDH/PDL sweep score at T0. |
| `score_SR_Price_Action` | `confluence_engine` | `T0` | **🟢 SAFE** | Support/Resistance reaction score at T0. |
| `score_Supply_Demand` | `confluence_engine` | `T0` | **🟢 SAFE** | Supply/Demand zone score at T0. |
| `score_VWAP` | `confluence_engine` | `T0` | **🟢 SAFE** | VWAP location & slope score at T0. |
| `score_Volume_Confirmation` | `confluence_engine` | `T0` | **🟢 SAFE** | Volume confirmation score at T0. |
| `session` | `ote_engine` | `T0` | **🟢 SAFE** | Active trading session (ASIA, LONDON, NY) at T0. |
| `signal_id` | `historical_signals` | `T0` | **🟢 SAFE** | Unique identifier only. |
| `signal_timestamp` | `historical_signals` | `T0` | **🟢 SAFE** | Chronological timestamp for ordering. |
| `sl_dist_pct` | `decision_engine` | `T0` | **🟢 SAFE** | Distance from entry to SL divided by entry price. |
| `snapshot_id` | `historical_signals` | `T0` | **🟢 SAFE** | Point-in-time state hash. |
| `success_reason` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Post-hoc success attribution. |
| `symbol` | `historical_signals` | `T0` | **🟢 SAFE** | Asset ticker symbol. |
| `technical_score` | `confluence_engine` | `T0` | **🟢 SAFE** | 16 technical factors sum (0-90) computed at T0. |
| `time_to_outcome_minutes` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Trade duration determined after trade close. |
| `tp_sl_ratio` | `decision_engine` | `T0` | **🟢 SAFE** | Planned TP1 distance divided by SL distance (1.5R). |
| `transaction_cost_deducted` | `outcome_tracker` | `> T0` | **🔴 UNSAFE (LEAKAGE)** | Post-hoc cost adjustment. |

---

## 2. Invariant Leakage Rules

1. **Zero Future Price Lookahead**: No forward candle highs, lows, or closes occurring after $T_0$ may enter feature matrices.
2. **Outcome Column Isolation**: Columns `outcome`, `exit_price`, `realized_r`, `mfe`, `mae`, `max_r`, and `time_to_outcome_minutes` are strictly reserved as evaluation targets and are barred from input vectors.
3. **Point-in-Time Immutable Snapshots**: All 17 contributor scores and biases are extracted from the immutable snapshot evaluated at closed candle $T_0$.

**Audit Verdict**: `LEAKAGE-SAFE CERTIFIED`