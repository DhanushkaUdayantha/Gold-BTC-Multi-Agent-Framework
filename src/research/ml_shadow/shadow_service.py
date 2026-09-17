"""
ML Shadow Service.
Downstream observer layer providing non-blocking, failure-isolated ML predictions and forward outcome tracking.
"""
import os
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from src.research.ml.artifacts import ArtifactManager
from src.research.ml.feature_engineering import FeatureEngineer
from src.research.ml.metrics import MetricsCalculator
from src.research.ml.calibration import ProbabilityCalibrator
from src.research.ml_shadow.models import MLShadowPrediction
from src.research.ml_shadow.shadow_store import MLShadowStore

logger = logging.getLogger("ml_shadow_service")

class MLShadowService:
    """Provides non-blocking, isolated ML shadow predictions and tracking."""

    def __init__(
        self,
        artifact_base_dir: str = os.path.join("research", "ml", "artifacts"),
        db_path: str = "data/historical/historical_market_data.db"
    ):
        self.artifact_mgr = ArtifactManager(base_dir=artifact_base_dir)
        self.store = MLShadowStore(db_path=db_path)
        self._models: Dict[str, Any] = {}
        self._preprocessors: Dict[str, Any] = {}
        self._model_names: Dict[str, str] = {}
        self._load_artifacts()

    def _get_asset_key(self, symbol: str) -> str:
        return "BTC" if "BTC" in symbol.upper() else "XAU"

    def _load_artifacts(self) -> None:
        """Attempts to load trained ML models for BTC and XAU."""
        for sym_key in ["BTC", "XAU"]:
            try:
                model = self.artifact_mgr.load_model(sym_key)
                prep = self.artifact_mgr.load_preprocessor(sym_key)
                if model is not None and prep is not None:
                    self._models[sym_key] = model
                    self._preprocessors[sym_key] = prep
                    self._model_names[sym_key] = type(model).__name__
                    logger.info(f"[ML SHADOW] Loaded model and preprocessor for {sym_key}: {self._model_names[sym_key]}")
                else:
                    logger.warning(f"[ML SHADOW] Artifacts missing for {sym_key}")
            except Exception as e:
                logger.error(f"[ML SHADOW] Failed to load artifacts for {sym_key}: {e}")

    def is_available(self, symbol: str) -> bool:
        """Returns True if the ML shadow model for the given symbol is ready."""
        sym_key = self._get_asset_key(symbol)
        return sym_key in self._models and sym_key in self._preprocessors

    def generate_prediction(
        self,
        symbol: str,
        timestamp_t0: str,
        production_decision: str,
        confluence_score: int,
        technical_score: int,
        gemini_score: int,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit_1: Optional[float],
        take_profit_2: Optional[float],
        session: str,
        market_regime: str,
        contributor_scores: Dict[str, int],
        contributor_biases: Dict[str, str],
        data_quality: str = "HIGH",
        gate_direction: str = "NONE",
        quality_gate_passed: bool = False,
        persist: bool = True
    ) -> Optional[MLShadowPrediction]:
        """
        Generates an isolated ML shadow prediction at T0.
        NEVER raises exceptions to caller. Fully failure-safe.
        """
        try:
            logger.info(f"[ML SHADOW] prediction started for {symbol} at {timestamp_t0}")
            sym_key = self._get_asset_key(symbol)

            if not self.is_available(symbol):
                logger.warning(f"[ML SHADOW] unavailable for {symbol}")
                return None

            model = self._models[sym_key]
            preprocessor = self._preprocessors[sym_key]
            model_name = self._model_names.get(sym_key, "ML_Classifier")

            # Parse time-derived features
            try:
                dt = datetime.fromisoformat(timestamp_t0.replace("Z", "+00:00"))
                hour = dt.hour
                dow = dt.weekday()
            except Exception:
                hour = 0
                dow = 0

            # Calculate risk ratios at T0
            entry_p = float(entry_price) if entry_price else 1.0
            sl_val = float(stop_loss) if stop_loss else entry_p * 0.99
            tp1_val = float(take_profit_1) if take_profit_1 else entry_p * 1.01

            sl_dist = abs(entry_p - sl_val)
            sl_dist_pct = (sl_dist / entry_p) if entry_p > 0 else 0.0
            tp_sl_ratio = (abs(tp1_val - entry_p) / sl_dist) if sl_dist > 0 else 1.5

            # Directional alignment checks
            dir_str = production_decision.upper()
            is_buy = 1 if "BUY" in dir_str else 0

            mtf_bias = contributor_biases.get("MTF Alignment", "NEUTRAL").upper()
            vwap_bias = contributor_biases.get("VWAP", "NEUTRAL").upper()
            mom_bias = contributor_biases.get("Momentum", "NEUTRAL").upper()
            vol_bias = contributor_biases.get("Volume Confirmation", "NEUTRAL").upper()

            mtf_aligned = 1 if ((is_buy and mtf_bias == "BULLISH") or (not is_buy and mtf_bias == "BEARISH")) else 0
            vwap_aligned = 1 if ((is_buy and vwap_bias == "BULLISH") or (not is_buy and vwap_bias == "BEARISH")) else 0
            mom_aligned = 1 if ((is_buy and mom_bias == "BULLISH") or (not is_buy and mom_bias == "BEARISH")) else 0
            vol_aligned = 1 if ((is_buy and vol_bias == "BULLISH") or (not is_buy and vol_bias == "BEARISH")) else 0
            is_asia_buy = 1 if (is_buy and session.upper() == "ASIA") else 0
            is_high_conf = 1 if confluence_score >= 58 else 0

            # Assemble feature record
            feature_record = {
                "confluence_score": confluence_score,
                "technical_score": technical_score,
                "gemini_score": gemini_score,
                "hour_of_day": hour,
                "day_of_week": dow,
                "sl_dist_pct": sl_dist_pct,
                "tp_sl_ratio": tp_sl_ratio,
                "score_HTF_Trend": int(contributor_scores.get("HTF Trend", 0)),
                "score_Market_Structure": int(contributor_scores.get("Market Structure", 0)),
                "score_Momentum": int(contributor_scores.get("Momentum", 0)),
                "score_MTF_Alignment": int(contributor_scores.get("MTF Alignment", 0)),
                "score_SR_Price_Action": int(contributor_scores.get("S/R Price Action", 0)),
                "score_Breakout_Retest": int(contributor_scores.get("Breakout / Retest", 0)),
                "score_Supply_Demand": int(contributor_scores.get("Supply & Demand", 0)),
                "score_Volume_Confirmation": int(contributor_scores.get("Volume Confirmation", 0)),
                "score_SMC_ICT": int(contributor_scores.get("SMC / ICT", 0)),
                "score_ICT_Concepts": int(contributor_scores.get("ICT Concepts", 0)),
                "score_Fibonacci_OTE": int(contributor_scores.get("Fibonacci OTE", 0)),
                "score_Elliott_Wave": int(contributor_scores.get("Elliott Wave", 0)),
                "score_VWAP": int(contributor_scores.get("VWAP", 0)),
                "score_EMA_MA_Stack": int(contributor_scores.get("EMA / MA Stack", 0)),
                "score_RSI": int(contributor_scores.get("RSI", 0)),
                "score_MACD": int(contributor_scores.get("MACD", 0)),
                "score_Gemini_AI": int(contributor_scores.get("Gemini AI", 0)),
                "mtf_aligned": mtf_aligned,
                "vwap_aligned": vwap_aligned,
                "momentum_aligned": mom_aligned,
                "vol_aligned": vol_aligned,
                "is_asia_buy": is_asia_buy,
                "is_high_confluence": is_high_conf
            }

            feature_df = pd.DataFrame([feature_record])
            X_vec = preprocessor.transform(feature_df)

            if hasattr(model, "predict_proba"):
                prob = float(model.predict_proba(X_vec)[0, 1])
            else:
                prob = float(model.predict(X_vec)[0])

            pred_class = 1 if prob >= 0.50 else 0

            prediction = MLShadowPrediction.create(
                symbol=symbol,
                timestamp_t0=timestamp_t0,
                production_decision=production_decision,
                confluence_score=confluence_score,
                technical_score=technical_score,
                quality_gate_passed=quality_gate_passed,
                ml_model_name=model_name,
                ml_model_version="v1.0.0-research",
                ml_probability=prob,
                ml_predicted_class=pred_class,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                session=session,
                market_regime=market_regime,
                features_snapshot=feature_record
            )

            # Save immutable observation
            if persist:
                self.store.save_observation(prediction)
                logger.info(f"[ML SHADOW] prediction completed and saved: {sym_key} prob={prob:.4f} class={pred_class}")
            else:
                logger.info(f"[ML SHADOW] prediction completed (ephemeral/no-persist): {sym_key} prob={prob:.4f} class={pred_class}")
            return prediction

        except Exception as e:
            logger.error(f"[ML SHADOW] prediction failed for {symbol}: {e}")
            return None

    def resolve_pending_observations(
        self,
        symbol: str,
        forward_candles: List[Dict[str, Any]],
        max_horizon_candles: int = 50
    ) -> int:
        """
        Resolves forward trade outcomes against subsequent closed market candles.
        Never alters T0 feature snapshot data.
        """
        pending = self.store.get_pending_observations(symbol=symbol)
        if not pending or not forward_candles:
            return 0

        resolved_count = 0
        for obs in pending:
            obs_id = obs["observation_id"]
            obs_ts = obs["timestamp_t0"]
            dec = obs["production_decision"].upper()
            entry_p = float(obs["entry_price"]) if obs.get("entry_price") is not None else 0.0
            sl = float(obs["stop_loss"]) if obs.get("stop_loss") else None
            tp1 = float(obs["take_profit_1"]) if obs.get("take_profit_1") else None

            # Skip resolution if WAIT decision or missing SL/TP/Entry (no directional trading targets)
            if "WAIT" in dec or sl is None or tp1 is None or entry_p <= 0:
                self.store.resolve_observation_outcome(
                    observation_id=obs_id,
                    outcome="OBSERVED_WAIT",
                    exit_price=entry_p,
                    realized_r=0.0,
                    outcome_timestamp=obs_ts,
                    duration_minutes=0.0
                )
                resolved_count += 1
                continue

            # Find candles occurring after T0
            relevant_candles = [c for c in forward_candles if c.get("timestamp", "") > obs_ts]
            if not relevant_candles:
                continue

            is_buy = "BUY" in dec
            outcome = None
            exit_p = None
            outcome_ts = None
            dur_min = 0.0

            for idx, c in enumerate(relevant_candles[:max_horizon_candles]):
                c_high = float(c.get("high", c.get("close", entry_p)))
                c_low = float(c.get("low", c.get("close", entry_p)))
                c_ts = c.get("timestamp", obs_ts)

                if is_buy:
                    if c_low <= sl:
                        outcome = "LOSS"
                        exit_p = sl
                        outcome_ts = c_ts
                        try:
                            t0_dt = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
                            out_dt = datetime.fromisoformat(c_ts.replace("Z", "+00:00"))
                            dur_min = round(max(0.0, (out_dt - t0_dt).total_seconds() / 60.0), 2)
                        except Exception:
                            dur_min = (idx + 1) * 15.0
                        break
                    elif c_high >= tp1:
                        outcome = "WIN"
                        exit_p = tp1
                        outcome_ts = c_ts
                        try:
                            t0_dt = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
                            out_dt = datetime.fromisoformat(c_ts.replace("Z", "+00:00"))
                            dur_min = round(max(0.0, (out_dt - t0_dt).total_seconds() / 60.0), 2)
                        except Exception:
                            dur_min = (idx + 1) * 15.0
                        break
                else: # SELL
                    if c_high >= sl:
                        outcome = "LOSS"
                        exit_p = sl
                        outcome_ts = c_ts
                        try:
                            t0_dt = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
                            out_dt = datetime.fromisoformat(c_ts.replace("Z", "+00:00"))
                            dur_min = round(max(0.0, (out_dt - t0_dt).total_seconds() / 60.0), 2)
                        except Exception:
                            dur_min = (idx + 1) * 15.0
                        break
                    elif c_low <= tp1:
                        outcome = "WIN"
                        exit_p = tp1
                        outcome_ts = c_ts
                        try:
                            t0_dt = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
                            out_dt = datetime.fromisoformat(c_ts.replace("Z", "+00:00"))
                            dur_min = round(max(0.0, (out_dt - t0_dt).total_seconds() / 60.0), 2)
                        except Exception:
                            dur_min = (idx + 1) * 15.0
                        break

            if outcome is None and len(relevant_candles) >= max_horizon_candles:
                outcome = "EXPIRED"
                exit_p = float(relevant_candles[-1].get("close", entry_p))
                outcome_ts = relevant_candles[-1].get("timestamp", obs_ts)
                try:
                    t0_dt = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
                    out_dt = datetime.fromisoformat(outcome_ts.replace("Z", "+00:00"))
                    dur_min = round(max(0.0, (out_dt - t0_dt).total_seconds() / 60.0), 2)
                except Exception:
                    dur_min = max_horizon_candles * 15.0

            if outcome is not None:
                sl_dist = abs(entry_p - sl)
                if outcome == "WIN":
                    realized_r = 1.5
                elif outcome == "LOSS":
                    realized_r = -1.0
                else:
                    price_diff = (exit_p - entry_p) if is_buy else (entry_p - exit_p)
                    realized_r = round(price_diff / sl_dist, 2) if sl_dist > 0 else 0.0

                self.store.resolve_observation_outcome(
                    observation_id=obs_id,
                    outcome=outcome,
                    exit_price=exit_p,
                    realized_r=realized_r,
                    outcome_timestamp=outcome_ts,
                    duration_minutes=dur_min
                )
                resolved_count += 1

        return resolved_count

    def get_forward_validation_metrics(self, symbol: str) -> Dict[str, Any]:
        """
        Calculates forward validation performance on resolved live observations.

        Parameters
        ----------
        symbol:
            Required. Must be a recognizable BTC or XAU variant.
            Normalized internally via normalize_ml_symbol().
            Cross-asset aggregation is not supported — never pass None.
        """
        from src.research.ml_shadow.symbol_utils import normalize_ml_symbol
        canonical = normalize_ml_symbol(symbol)
        all_obs = self.store.get_all_observations(symbol=canonical)
        total_n = len(all_obs)
        pending_n = sum(1 for o in all_obs if o["outcome"] == "PENDING")
        resolved_trades = [o for o in all_obs if o["outcome"] in ["WIN", "LOSS"]]
        resolved_n = len(resolved_trades)
        wait_n = sum(1 for o in all_obs if o["outcome"] == "OBSERVED_WAIT")
        expired_n = sum(1 for o in all_obs if o["outcome"] == "EXPIRED")
        directional_candidates = sum(1 for o in all_obs if (o.get("production_decision") or "").upper() in ["BUY", "SELL"])
        missing_entry_n = sum(1 for o in all_obs if (o.get("production_decision") or "").upper() in ["BUY", "SELL"] and not o.get("entry_price"))
        missing_sl_n = sum(1 for o in all_obs if (o.get("production_decision") or "").upper() in ["BUY", "SELL"] and not o.get("stop_loss"))
        missing_tp_n = sum(1 for o in all_obs if (o.get("production_decision") or "").upper() in ["BUY", "SELL"] and not o.get("take_profit_1"))

        diagnostics = {
            "total_observations": total_n,
            "wait_non_trade_observations": wait_n,
            "eligible_directional_candidates": directional_candidates,
            "resolved_trades": resolved_n,
            "pending_trades": pending_n,
            "expired_trades": expired_n,
            "missing_entry": missing_entry_n,
            "missing_sl": missing_sl_n,
            "missing_tp": missing_tp_n,
        }

        if resolved_n == 0:
            return {
                "symbol": canonical,
                "status": "FORWARD VALIDATION IN PROGRESS",
                "total_observations": total_n,
                "pending_observations": pending_n,
                "resolved_trades": 0,
                "wait_observations": wait_n,
                "milestone_reached": "0/25",
                "brier_score": None,
                "win_rate": None,
                "ev_r": None,
                "profit_factor": None,
                "diagnostics": diagnostics,
            }

        df = pd.DataFrame(resolved_trades)
        y_true = np.where(df["outcome"] == "WIN", 1, 0)
        y_prob = df["ml_probability"].values
        realized_r = df["realized_r"].values

        calib = ProbabilityCalibrator.evaluate_calibration(y_true, y_prob, realized_r=realized_r)

        wins = int(np.sum(y_true))
        losses = resolved_n - wins
        wr = round(float((wins / resolved_n) * 100.0), 2)
        ev_r = round(float(np.mean(realized_r)), 4)

        tot_win_r = float(np.sum(realized_r[realized_r > 0]))
        tot_loss_r = abs(float(np.sum(realized_r[realized_r < 0])))
        pf = round(tot_win_r / tot_loss_r, 2) if tot_loss_r > 0 else (99.0 if tot_win_r > 0 else 0.0)

        # Milestone tracking
        if resolved_n >= 100:
            milestone = "100/100 (Full Milestone Reached)"
        elif resolved_n >= 50:
            milestone = "50/100 Milestone Reached"
        elif resolved_n >= 25:
            milestone = "25/100 Milestone Reached"
        else:
            milestone = f"{resolved_n}/25 (Early Observation Phase)"

        return {
            "symbol": canonical,
            "status": "FORWARD VALIDATION IN PROGRESS",
            "total_observations": total_n,
            "pending_observations": pending_n,
            "resolved_trades": resolved_n,
            "wait_observations": wait_n,
            "milestone_reached": milestone,
            "win_rate": wr,
            "ev_r": ev_r,
            "profit_factor": pf,
            "brier_score": calib["brier_score"],
            "calibration": calib,
            "diagnostics": diagnostics,
        }

_GLOBAL_ML_SHADOW_SERVICE: Optional[MLShadowService] = None

def get_ml_shadow_service() -> MLShadowService:
    global _GLOBAL_ML_SHADOW_SERVICE
    if _GLOBAL_ML_SHADOW_SERVICE is None:
        _GLOBAL_ML_SHADOW_SERVICE = MLShadowService()
    return _GLOBAL_ML_SHADOW_SERVICE
