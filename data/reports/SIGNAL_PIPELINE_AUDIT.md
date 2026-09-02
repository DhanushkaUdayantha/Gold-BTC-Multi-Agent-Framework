# Signal Pipeline Audit Report — Phase 4

**Generated:** 2026-09-02T19:54:31.772772+00:00
**Pipeline Version:** `4.0`  |  **Audit Verdict:** ✅ `HEALTHY`

## Summary
Signal Pipeline Audit complete. Audited all 14 stages across live data, technical analysis, AI reasoning, calibration, decision synthesis, trade parameters, and outcome resolution. All 14 stages classified as HEALTHY / NO_CHANGE_REQUIRED. Production decision architecture remains completely frozen and isolated.

> ⚠️ **SAFETY ASSERTION:**
> *"Production decision behavior unchanged. All strategy gating, optimization, and adaptive research remain isolated from the live production decision path."*

## End-to-End Pipeline Stage Audit Table
| Stage | Name | Current File | Status | Inputs | Outputs | Known Risk | Change Needed |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Live Data Ingestion | `src/services/market_data_service.py` | `NO_CHANGE_REQUIRED` | Binance/CoinGecko/MT5/Synthetic multi-timeframe candles (1d, 1h, 15m, 5m) | Clean OHLCV DataFrames with timestamps & volume | Network latency, missing bars during API disconnection | None. Production data fetching is isolated and healthy. |
| 2 | Data Quality & Integrity Guard | `src/research/data_quality.py` | `NO_CHANGE_REQUIRED` | OHLCV candles & timestamps | DataQualityReport (candle_count, is_sufficient, quality_grade) | Stale data leading to delayed technical computations | None. Data quality grade A established in research. |
| 3 | Multi-Timeframe Technical Indicators | `src/services/technical_analysis_service.py` | `NO_CHANGE_REQUIRED` | OHLCV candles per timeframe (1d, 1h, 15m, 5m) | TechnicalAnalysisResponse (EMA 20/50/200, RSI, MACD, ATR, S/R levels) | Indicator lag during sudden volatility breakouts | None. Standard mathematical indicators verified. |
| 4 | Market Structure & Regime Classification | `src/services/ote_engine.py` | `NO_CHANGE_REQUIRED` | Technical summaries, swing highs/lows, EMA stacking | MarketCondition (TRENDING_BULLISH, TRENDING_BEARISH, RANGING, HIGH_VOLATILITY) | Regime transition lag at market inflection points | None in production. Research layer evaluates regime stability. |
| 5 | AI Analysis & Reasoning Engine | `src/services/ai_analysis_service.py` | `NO_CHANGE_REQUIRED` | Technical indicators, support/resistance, market regime, MTF trends | AIAnalysisResponse (bias, confidence, reasoning, key factors) | LLM API rate limits, non-deterministic phrasing | None. Rule-based fallback analyzer guarantees continuous operation. |
| 6 | Raw Confidence & Strength Generation | `src/services/decision_engine.py` | `NO_CHANGE_REQUIRED` | AI confidence (0-100), technical confirmation count, confluence score | raw_strength (0-100), composite_score | Raw strength is an indicator score, not a calibrated statistical probability | None in production. Research treats strength separately from probability. |
| 7 | Probability Reliability Calibration | `src/research/ai_calibration.py` | `HEALTHY` | Raw strength & confidence score | Calibrated win probability (0.0 to 1.0), Brier score, ECE | Distributional drift between training regimes and live market | Research-only Platt logistic calibration verified (ECE <= 0.025). |
| 8 | Historical Evidence & Pattern Matching | `src/services/historical_intelligence.py` | `NO_CHANGE_REQUIRED` | Current indicator cluster & market regime | Historical match count, historical win rate, historical expectancy | Small historical sample size in rare regime combinations | None. System enforces minimum sample guards. |
| 9 | Validated Strategy Layer (Shadow) | `src/services/validated_strategy_layer.py` | `NO_CHANGE_REQUIRED` | Point-in-time observation features | ValidatedStrategyEvaluation (qualified, gating_policy, shadow_decision) | Over-filtering leading to missed profitable opportunities | None in production. Research evaluates Policy A-E under shadow gating. |
| 10 | Risk / Expected Value Assessment | `src/services/decision_engine.py` | `NO_CHANGE_REQUIRED` | Calibrated probability, potential reward, stop distance | Expected value (R), RiskLevel, minimum risk-to-reward ratio check | Fixed R:R assumptions when market ATR shifts abruptly | None in production. Counterfactual research analyzes adaptive SL/TP. |
| 11 | Base Decision Synthesis | `src/services/decision_engine.py` | `NO_CHANGE_REQUIRED` | MultiTimeframeTechnicalInput, AIAnalysisResponse | TradingDecision (BUY / SELL / WAIT, confidence, composite_score) | Conflicting MTF momentum creating false breakouts | None. DecisionEngine.evaluate() is frozen and production-isolated. |
| 12 | Trade Parameter Generation (Entry, SL, TP) | `src/services/decision_engine.py` | `NO_CHANGE_REQUIRED` | Current price, ATR, support/resistance, market structure levels | entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio | Stop hunt sweeps in tight consolidation zones | None in production. Counterfactual analysis tests parameter variants. |
| 13 | Signal Persistence & Logging | `src/services/point_in_time_validator.py` | `NO_CHANGE_REQUIRED` | TradingDecision snapshot, features JSON, timestamp | historical_signals database record with immutable snapshot | Duplicate signal logs during concurrent evaluations | None. Primary key & timestamp deduplication active. |
| 14 | Ex-Post Outcome & Trade Quality Tracking | `src/research/outcome_engine.py` | `NO_CHANGE_REQUIRED` | Forward price trajectory candles, entry, SL, TP | OutcomeLabel (WIN, LOSS, BREAKEVEN, EXPIRED, AMBIGUOUS), realized_R, MFE, MAE | Same-candle ambiguous TP/SL touches | None. Conservative SL-first ordering standard enforced. |

## Detailed Stage Review

### Stage 1: Live Data Ingestion
- **File:** `src/services/market_data_service.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Binance/CoinGecko/MT5/Synthetic multi-timeframe candles (1d, 1h, 15m, 5m)
- **Outputs:** Clean OHLCV DataFrames with timestamps & volume
- **Known Risk:** Network latency, missing bars during API disconnection
- **Change Needed:** None. Production data fetching is isolated and healthy.
- **Audit Notes:** Verified candle validation and timezone normalization.

### Stage 2: Data Quality & Integrity Guard
- **File:** `src/research/data_quality.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** OHLCV candles & timestamps
- **Outputs:** DataQualityReport (candle_count, is_sufficient, quality_grade)
- **Known Risk:** Stale data leading to delayed technical computations
- **Change Needed:** None. Data quality grade A established in research.
- **Audit Notes:** Audited in Phase 0 & 3.

### Stage 3: Multi-Timeframe Technical Indicators
- **File:** `src/services/technical_analysis_service.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** OHLCV candles per timeframe (1d, 1h, 15m, 5m)
- **Outputs:** TechnicalAnalysisResponse (EMA 20/50/200, RSI, MACD, ATR, S/R levels)
- **Known Risk:** Indicator lag during sudden volatility breakouts
- **Change Needed:** None. Standard mathematical indicators verified.
- **Audit Notes:** Deterministic indicator calculations across all timeframes.

### Stage 4: Market Structure & Regime Classification
- **File:** `src/services/ote_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Technical summaries, swing highs/lows, EMA stacking
- **Outputs:** MarketCondition (TRENDING_BULLISH, TRENDING_BEARISH, RANGING, HIGH_VOLATILITY)
- **Known Risk:** Regime transition lag at market inflection points
- **Change Needed:** None in production. Research layer evaluates regime stability.
- **Audit Notes:** OTE & SMC sweep detection operating deterministically.

### Stage 5: AI Analysis & Reasoning Engine
- **File:** `src/services/ai_analysis_service.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Technical indicators, support/resistance, market regime, MTF trends
- **Outputs:** AIAnalysisResponse (bias, confidence, reasoning, key factors)
- **Known Risk:** LLM API rate limits, non-deterministic phrasing
- **Change Needed:** None. Rule-based fallback analyzer guarantees continuous operation.
- **Audit Notes:** Fallback provider provides graceful degradation with 0 crashes.

### Stage 6: Raw Confidence & Strength Generation
- **File:** `src/services/decision_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** AI confidence (0-100), technical confirmation count, confluence score
- **Outputs:** raw_strength (0-100), composite_score
- **Known Risk:** Raw strength is an indicator score, not a calibrated statistical probability
- **Change Needed:** None in production. Research treats strength separately from probability.
- **Audit Notes:** Documented in Master Threshold Spec.

### Stage 7: Probability Reliability Calibration
- **File:** `src/research/ai_calibration.py`
- **Status:** `HEALTHY`
- **Inputs:** Raw strength & confidence score
- **Outputs:** Calibrated win probability (0.0 to 1.0), Brier score, ECE
- **Known Risk:** Distributional drift between training regimes and live market
- **Change Needed:** Research-only Platt logistic calibration verified (ECE <= 0.025).
- **Audit Notes:** Platt scaling strictly trained on 60% Train split.

### Stage 8: Historical Evidence & Pattern Matching
- **File:** `src/services/historical_intelligence.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Current indicator cluster & market regime
- **Outputs:** Historical match count, historical win rate, historical expectancy
- **Known Risk:** Small historical sample size in rare regime combinations
- **Change Needed:** None. System enforces minimum sample guards.
- **Audit Notes:** Point-in-time historical retrieval.

### Stage 9: Validated Strategy Layer (Shadow)
- **File:** `src/services/validated_strategy_layer.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Point-in-time observation features
- **Outputs:** ValidatedStrategyEvaluation (qualified, gating_policy, shadow_decision)
- **Known Risk:** Over-filtering leading to missed profitable opportunities
- **Change Needed:** None in production. Research evaluates Policy A-E under shadow gating.
- **Audit Notes:** Production GATING = DISABLED verified.

### Stage 10: Risk / Expected Value Assessment
- **File:** `src/services/decision_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Calibrated probability, potential reward, stop distance
- **Outputs:** Expected value (R), RiskLevel, minimum risk-to-reward ratio check
- **Known Risk:** Fixed R:R assumptions when market ATR shifts abruptly
- **Change Needed:** None in production. Counterfactual research analyzes adaptive SL/TP.
- **Audit Notes:** Guarantees negative EV signals are suppressed to WAIT.

### Stage 11: Base Decision Synthesis
- **File:** `src/services/decision_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** MultiTimeframeTechnicalInput, AIAnalysisResponse
- **Outputs:** TradingDecision (BUY / SELL / WAIT, confidence, composite_score)
- **Known Risk:** Conflicting MTF momentum creating false breakouts
- **Change Needed:** None. DecisionEngine.evaluate() is frozen and production-isolated.
- **Audit Notes:** 100% deterministic evaluation pipeline.

### Stage 12: Trade Parameter Generation (Entry, SL, TP)
- **File:** `src/services/decision_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Current price, ATR, support/resistance, market structure levels
- **Outputs:** entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio
- **Known Risk:** Stop hunt sweeps in tight consolidation zones
- **Change Needed:** None in production. Counterfactual analysis tests parameter variants.
- **Audit Notes:** Calculates 1:1.5 to 1:3.0 minimum risk-reward.

### Stage 13: Signal Persistence & Logging
- **File:** `src/services/point_in_time_validator.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** TradingDecision snapshot, features JSON, timestamp
- **Outputs:** historical_signals database record with immutable snapshot
- **Known Risk:** Duplicate signal logs during concurrent evaluations
- **Change Needed:** None. Primary key & timestamp deduplication active.
- **Audit Notes:** Verified in SQLite table historical_signals.

### Stage 14: Ex-Post Outcome & Trade Quality Tracking
- **File:** `src/research/outcome_engine.py`
- **Status:** `NO_CHANGE_REQUIRED`
- **Inputs:** Forward price trajectory candles, entry, SL, TP
- **Outputs:** OutcomeLabel (WIN, LOSS, BREAKEVEN, EXPIRED, AMBIGUOUS), realized_R, MFE, MAE
- **Known Risk:** Same-candle ambiguous TP/SL touches
- **Change Needed:** None. Conservative SL-first ordering standard enforced.
- **Audit Notes:** OutcomeEngine serves as single authoritative evaluator.