# Master Research Threshold Register

**Research Policy Version:** `1.0`  |  **Threshold Spec Version:** `1.0`
**Generated:** 2026-09-02T19:27:53.234311+00:00
**Total Thresholds Defined:** 19

> **NON-NEGOTIABLE RULE:** Every research threshold has an explicit mathematical formula, input variables, minimum sample size, and unrounded boundary operator. Magic numbers are strictly prohibited.

## Threshold Catalog
| Threshold Name | Value | Preferred | Operator | Min N | Unit | Calculation Method |
| --- | --- | --- | --- | --- | --- | --- |
| `CALIBRATION_BRIER_MAX` | 0.25 | 0.2 | `<=` | 100 | score | mean((pred_prob - actual_outcome)^2) |
| `CALIBRATION_ECE_MAX` | 0.1 | 0.05 | `<=` | 100 | error_rate | sum(N_bucket / N_total * abs(pred_prob - emp_rate)) |
| `DATA_QUALITY_LOOKAHEAD_VIOLATIONS` | 0.0 | 0.0 | `==` | 1 | violations | count(temporal sequence, future feature, calibration overlap violations) |
| `DRAWDOWN_CONCENTRATION_THRESHOLD` | 0.5 | 0.35 | `<` | 30 | ratio | category_drawdown_r / total_max_drawdown_r |
| `EXPECTANCY_MINIMUM` | 0.15 | 0.2 | `>=` | 500 | R | sum(realized_R) / N |
| `HOLDOUT_EXPECTANCY_MINIMUM` | 0.0 | 0.05 | `>` | 50 | R | sum(holdout_realized_r) / N_holdout |
| `HOLDOUT_PF_MINIMUM` | 1.1 | 1.2 | `>=` | 50 | ratio | holdout_gross_profit_r / holdout_gross_loss_r |
| `LOSER_REDUCTION_MINIMUM` | 0.5 | 0.65 | `>=` | 100 | ratio | removed_losing_trades / all_base_losing_trades |
| `MAX_DRAWDOWN_BENCHMARK_RATIO` | 1.25 | 1.0 | `<=` | 500 | multiplier | observed_max_dd_r / benchmark_max_dd_r |
| `MINIMUM_RESEARCH_SAMPLE` | 500.0 | 750.0 | `>=` | 500 | trades | count(BUY/SELL trades with valid entry, SL, TP and resolved outcome) |
| `OOS_EXPECTANCY_MINIMUM` | 0.0 | 0.1 | `>` | 100 | R | sum(oos_realized_r) / N_oos |
| `PROFIT_FACTOR_MINIMUM` | 1.2 | 1.3 | `>=` | 500 | ratio | sum(realized_R > 0) / abs(sum(realized_R < 0)) |
| `REGIME_SAMPLE_MINIMUM` | 100.0 | 200.0 | `>=` | 100 | trades | count(trades within market regime) |
| `ROLLING_NEGATIVE_RATIO_MAX` | 0.1 | 0.05 | `<=` | 200 | ratio | count(rolling_50_exp < 0) / count(valid_50_windows) |
| `SESSION_SAMPLE_MINIMUM` | 100.0 | 200.0 | `>=` | 100 | trades | count(trades within session) |
| `STATISTICAL_ALPHA` | 0.05 | 0.01 | `<` | 30 | significance_level | alpha / N_comparisons for family-wide error control |
| `TOTAL_R_MINIMUM` | 0.0 | 50.0 | `>` | 100 | R | sum(realized_R_1 ... realized_R_t) |
| `WALK_FORWARD_POSITIVE_RATIO` | 0.75 | 0.8 | `>=` | 4 | ratio | count(oos_fold_exp > 0) / count(total_oos_folds) |
| `WINNER_RETENTION_MINIMUM` | 0.4 | 0.6 | `>=` | 100 | ratio | retained_winning_trades / all_base_winning_trades |

## Detailed Mathematical Definitions

### `CALIBRATION_BRIER_MAX`
- **Threshold Value:** `0.25 score` (Preferred: `0.2`)
- **Boundary Operator:** `<=` (Pass: `Brier <= 0.25 (Below no-skill benchmark)` | Fail: `Brier > 0.25 (Worse than random coin flip)`)
- **Calculation Method:** `mean((pred_prob - actual_outcome)^2)`
- **Denominator:** Total resolved probabilistic signals
- **Input Variables:** `predicted_probabilities, binary_outcomes`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** Evaluation sample

### `CALIBRATION_ECE_MAX`
- **Threshold Value:** `0.1 error_rate` (Preferred: `0.05`)
- **Boundary Operator:** `<=` (Pass: `ECE <= 0.10 (Preferred <= 0.05)` | Fail: `ECE > 0.10`)
- **Calculation Method:** `sum(N_bucket / N_total * abs(pred_prob - emp_rate))`
- **Denominator:** Total resolved probabilistic signals
- **Input Variables:** `bucket_probabilities, bucket_empirical_rates, bucket_counts`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** Calibration evaluation sample

### `DATA_QUALITY_LOOKAHEAD_VIOLATIONS`
- **Threshold Value:** `0.0 violations` (Preferred: `0.0`)
- **Boundary Operator:** `==` (Pass: `Lookahead violations == 0` | Fail: `Lookahead violations > 0 (Immediate experiment invalidation)`)
- **Calculation Method:** `count(temporal sequence, future feature, calibration overlap violations)`
- **Denominator:** All records audited
- **Input Variables:** `lookahead_violations_count`
- **Minimum Sample Size:** `1` (FAIL)
- **Measurement Window:** Full historical dataset

### `DRAWDOWN_CONCENTRATION_THRESHOLD`
- **Threshold Value:** `0.5 ratio` (Preferred: `0.35`)
- **Boundary Operator:** `<` (Pass: `Category contribution < 50%` | Fail: `Category contribution >= 50% (triggers concentration warning)`)
- **Calculation Method:** `category_drawdown_r / total_max_drawdown_r`
- **Denominator:** Total portfolio maximum drawdown in R
- **Input Variables:** `category_drawdown_r, total_max_drawdown_r`
- **Minimum Sample Size:** `30` (INSUFFICIENT_DATA)
- **Measurement Window:** Drawdown episodes

### `EXPECTANCY_MINIMUM`
- **Threshold Value:** `0.15 R` (Preferred: `0.2`)
- **Boundary Operator:** `>=` (Pass: `Expectancy >= +0.15R and 95% Bootstrap CI evaluated` | Fail: `Expectancy < +0.15R`)
- **Calculation Method:** `sum(realized_R) / N`
- **Denominator:** N = valid resolved trades
- **Input Variables:** `realized_r_series`
- **Minimum Sample Size:** `500` (INSUFFICIENT_DATA)
- **Measurement Window:** Full evaluation cohort

### `HOLDOUT_EXPECTANCY_MINIMUM`
- **Threshold Value:** `0.0 R` (Preferred: `0.05`)
- **Boundary Operator:** `>` (Pass: `Holdout Expectancy > 0.0R` | Fail: `Holdout Expectancy <= 0.0R`)
- **Calculation Method:** `sum(holdout_realized_r) / N_holdout`
- **Denominator:** Untouched holdout trade count
- **Input Variables:** `holdout_realized_r_series`
- **Minimum Sample Size:** `50` (INSUFFICIENT_DATA)
- **Measurement Window:** 15-20% untouched final chronological holdout

### `HOLDOUT_PF_MINIMUM`
- **Threshold Value:** `1.1 ratio` (Preferred: `1.2`)
- **Boundary Operator:** `>=` (Pass: `Holdout PF >= 1.10` | Fail: `Holdout PF < 1.10`)
- **Calculation Method:** `holdout_gross_profit_r / holdout_gross_loss_r`
- **Denominator:** Holdout gross loss R
- **Input Variables:** `holdout_gross_profit_r, holdout_gross_loss_r`
- **Minimum Sample Size:** `50` (INSUFFICIENT_DATA)
- **Measurement Window:** Untouched final holdout

### `LOSER_REDUCTION_MINIMUM`
- **Threshold Value:** `0.5 ratio` (Preferred: `0.65`)
- **Boundary Operator:** `>=` (Pass: `Loser reduction >= 50%` | Fail: `Loser reduction < 50%`)
- **Calculation Method:** `removed_losing_trades / all_base_losing_trades`
- **Denominator:** Total base losing trades
- **Input Variables:** `removed_losing_trades, all_base_losing_trades`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** Evaluation cohort

### `MAX_DRAWDOWN_BENCHMARK_RATIO`
- **Threshold Value:** `1.25 multiplier` (Preferred: `1.0`)
- **Boundary Operator:** `<=` (Pass: `ObservedDD <= 1.25 * BenchmarkDD` | Fail: `ObservedDD > 1.25 * BenchmarkDD`)
- **Calculation Method:** `observed_max_dd_r / benchmark_max_dd_r`
- **Denominator:** Validated historical benchmark drawdown
- **Input Variables:** `observed_max_dd_r, benchmark_max_dd_r`
- **Minimum Sample Size:** `500` (INSUFFICIENT_DATA)
- **Measurement Window:** Full chronological equity curve

### `MINIMUM_RESEARCH_SAMPLE`
- **Threshold Value:** `500.0 trades` (Preferred: `750.0`)
- **Boundary Operator:** `>=` (Pass: `N >= 500` | Fail: `N < 500`)
- **Calculation Method:** `count(BUY/SELL trades with valid entry, SL, TP and resolved outcome)`
- **Denominator:** All valid resolved trades (WAIT/INVALID excluded)
- **Input Variables:** `valid_resolved_trades`
- **Minimum Sample Size:** `500` (Automatic INSUFFICIENT_SAMPLE status)
- **Measurement Window:** Full evaluation cohort

### `OOS_EXPECTANCY_MINIMUM`
- **Threshold Value:** `0.0 R` (Preferred: `0.1`)
- **Boundary Operator:** `>` (Pass: `OOS Expectancy > 0.0R` | Fail: `OOS Expectancy <= 0.0R`)
- **Calculation Method:** `sum(oos_realized_r) / N_oos`
- **Denominator:** Out-of-sample trade count
- **Input Variables:** `oos_realized_r_series`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** 20% chronological out-of-sample window

### `PROFIT_FACTOR_MINIMUM`
- **Threshold Value:** `1.2 ratio` (Preferred: `1.3`)
- **Boundary Operator:** `>=` (Pass: `PF >= 1.20` | Fail: `PF < 1.20`)
- **Calculation Method:** `sum(realized_R > 0) / abs(sum(realized_R < 0))`
- **Denominator:** Total gross loss R (if 0, marked NO-LOSS-SAMPLE)
- **Input Variables:** `positive_realized_r, negative_realized_r`
- **Minimum Sample Size:** `500` (INSUFFICIENT_DATA)
- **Measurement Window:** Full evaluation cohort

### `REGIME_SAMPLE_MINIMUM`
- **Threshold Value:** `100.0 trades` (Preferred: `200.0`)
- **Boundary Operator:** `>=` (Pass: `N_regime >= 100` | Fail: `N_regime < 100 -> INSUFFICIENT_SAMPLE`)
- **Calculation Method:** `count(trades within market regime)`
- **Denominator:** Trades within specific regime
- **Input Variables:** `regime_trade_count`
- **Minimum Sample Size:** `100` (INSUFFICIENT_SAMPLE)
- **Measurement Window:** Regime partition

### `ROLLING_NEGATIVE_RATIO_MAX`
- **Threshold Value:** `0.1 ratio` (Preferred: `0.05`)
- **Boundary Operator:** `<=` (Pass: `NegativeWindowRatio <= 10%` | Fail: `NegativeWindowRatio > 10%`)
- **Calculation Method:** `count(rolling_50_exp < 0) / count(valid_50_windows)`
- **Denominator:** All valid 50-trade sliding windows
- **Input Variables:** `rolling_50_expectancies`
- **Minimum Sample Size:** `200` (INSUFFICIENT_DATA)
- **Measurement Window:** 50-trade rolling windows

### `SESSION_SAMPLE_MINIMUM`
- **Threshold Value:** `100.0 trades` (Preferred: `200.0`)
- **Boundary Operator:** `>=` (Pass: `N_session >= 100` | Fail: `N_session < 100 -> INSUFFICIENT_SAMPLE`)
- **Calculation Method:** `count(trades within session)`
- **Denominator:** Trades within specific session
- **Input Variables:** `session_trade_count`
- **Minimum Sample Size:** `100` (INSUFFICIENT_SAMPLE)
- **Measurement Window:** Session partition

### `STATISTICAL_ALPHA`
- **Threshold Value:** `0.05 significance_level` (Preferred: `0.01`)
- **Boundary Operator:** `<` (Pass: `p < corrected_alpha` | Fail: `p >= corrected_alpha`)
- **Calculation Method:** `alpha / N_comparisons for family-wide error control`
- **Denominator:** Number of simultaneously tested hypotheses
- **Input Variables:** `raw_p_value, bonferroni_corrected_alpha`
- **Minimum Sample Size:** `30` (INSUFFICIENT_DATA)
- **Measurement Window:** Experiment hypothesis family

### `TOTAL_R_MINIMUM`
- **Threshold Value:** `0.0 R` (Preferred: `50.0`)
- **Boundary Operator:** `>` (Pass: `Total R > 0` | Fail: `Total R <= 0`)
- **Calculation Method:** `sum(realized_R_1 ... realized_R_t)`
- **Denominator:** Full trade sequence
- **Input Variables:** `cumulative_realized_r`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** Full evaluation cohort

### `WALK_FORWARD_POSITIVE_RATIO`
- **Threshold Value:** `0.75 ratio` (Preferred: `0.8`)
- **Boundary Operator:** `>=` (Pass: `WFPositiveRatio >= 75%` | Fail: `WFPositiveRatio < 75%`)
- **Calculation Method:** `count(oos_fold_exp > 0) / count(total_oos_folds)`
- **Denominator:** Total chronological OOS folds
- **Input Variables:** `oos_fold_expectancies`
- **Minimum Sample Size:** `4` (INSUFFICIENT_DATA)
- **Measurement Window:** Chronological walk-forward folds

### `WINNER_RETENTION_MINIMUM`
- **Threshold Value:** `0.4 ratio` (Preferred: `0.6`)
- **Boundary Operator:** `>=` (Pass: `Winner retention >= 40%` | Fail: `Winner retention < 40%`)
- **Calculation Method:** `retained_winning_trades / all_base_winning_trades`
- **Denominator:** Total base winning trades
- **Input Variables:** `retained_winning_trades, all_base_winning_trades`
- **Minimum Sample Size:** `100` (INSUFFICIENT_DATA)
- **Measurement Window:** Evaluation cohort