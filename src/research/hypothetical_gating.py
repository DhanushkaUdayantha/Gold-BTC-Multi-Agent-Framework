"""
Hypothetical Shadow Gating Engine.

Completely isolated research engine that evaluates hypothetical gating policies on historical signals.
Does NOT mutate or replace production decisions.

Evaluates 5 standard research gating policies:
- Policy A: Strict Qualification (Only QUALIFIED signals survive)
- Policy B: Qualification + Direction Agreement (QUALIFIED and base direction matches strategy)
- Policy C: 3/4 Confirmation (Confirmation score >= 3)
- Policy D: Conflict Filter (Suppress only directional conflicts, pass through others)
- Policy E: Strategy-Specific Gating (Asset-tailored parameters)

DISCLAIMER: Research and analytics layer only. Zero production decision logic modified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.trading_decision import ValidatedStrategyEvaluation
from src.research.trade_semantics import SignalDirection


class GatingPolicyType(str, Enum):
    POLICY_A_STRICT = "POLICY_A_STRICT"
    POLICY_B_DIRECTION_AGREEMENT = "POLICY_B_DIRECTION_AGREEMENT"
    POLICY_C_CONFIRMATION_3 = "POLICY_C_CONFIRMATION_3"
    POLICY_D_CONFLICT_FILTER = "POLICY_D_CONFLICT_FILTER"
    POLICY_E_STRATEGY_SPECIFIC = "POLICY_E_STRATEGY_SPECIFIC"


class GatingAction(str, Enum):
    KEEP = "KEEP"                          # Signal passed gating (remains BUY/SELL)
    REJECT = "REJECT"                      # Signal suppressed by gating (becomes WAIT)
    CONFLICT = "CONFLICT"                  # Signal suppressed due to directional conflict
    NO_STRATEGY = "NO_STRATEGY"            # No applicable strategy found
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"# Not enough data to evaluate


@dataclass(frozen=True)
class ShadowDecision:
    """Hypothetical gated decision record."""
    signal_id: str
    symbol: str
    timestamp: str
    base_direction: SignalDirection
    shadow_direction: SignalDirection
    action: GatingAction
    gating_policy: GatingPolicyType
    strategy_id: Optional[str]
    qualification_status: str
    confirmation_score: int
    probability: float
    regime: str
    reason: str


class HypotheticalGatingEngine:
    """
    Evaluator for hypothetical shadow gating policies.
    """

    @classmethod
    def evaluate_shadow_gate(
        cls,
        signal_id: str,
        symbol: str,
        timestamp: str,
        base_direction: str,  # "BUY", "SELL", "WAIT"
        val_eval: Optional[ValidatedStrategyEvaluation],
        policy: GatingPolicyType = GatingPolicyType.POLICY_A_STRICT,
    ) -> ShadowDecision:
        """
        Evaluate hypothetical gating on a base decision without mutating production.
        """
        base_dir_enum = SignalDirection(base_direction.upper()) if base_direction.upper() in ("BUY", "SELL", "WAIT") else SignalDirection.WAIT

        if base_dir_enum == SignalDirection.WAIT:
            return ShadowDecision(
                signal_id=signal_id,
                symbol=symbol,
                timestamp=timestamp,
                base_direction=base_dir_enum,
                shadow_direction=SignalDirection.WAIT,
                action=GatingAction.NO_STRATEGY,
                gating_policy=policy,
                strategy_id=val_eval.strategy_id if val_eval else None,
                qualification_status=val_eval.qualification_status if val_eval else "NONE",
                confirmation_score=val_eval.confirmation_score if val_eval else 0,
                probability=val_eval.probability if val_eval else 0.0,
                regime=val_eval.regime if val_eval else "UNKNOWN",
                reason="Base decision was already WAIT.",
            )

        if val_eval is None:
            return ShadowDecision(
                signal_id=signal_id,
                symbol=symbol,
                timestamp=timestamp,
                base_direction=base_dir_enum,
                shadow_direction=SignalDirection.WAIT,
                action=GatingAction.NO_STRATEGY,
                gating_policy=policy,
                strategy_id=None,
                qualification_status="INSUFFICIENT_DATA",
                confirmation_score=0,
                probability=0.0,
                regime="UNKNOWN",
                reason="No strategy evaluation provided.",
            )

        strat_id = val_eval.strategy_id
        qual_status = val_eval.qualification_status
        is_qualified = val_eval.qualified
        conf_score = val_eval.confirmation_score
        strat_dir = val_eval.direction
        prob = val_eval.probability
        regime = val_eval.regime

        # -------------------------------------------------------------------
        # Policy A: Strict Qualification
        # -------------------------------------------------------------------
        if policy == GatingPolicyType.POLICY_A_STRICT:
            if is_qualified and qual_status == "QUALIFIED":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=f"Strictly qualified under {strat_id}.",
                )
            elif qual_status == "CONFLICT":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=GatingAction.CONFLICT,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=val_eval.conflict_reason or "Directional conflict with validated strategy.",
                )
            else:
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=GatingAction.REJECT,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=f"Did not meet full criteria for {strat_id}.",
                )

        # -------------------------------------------------------------------
        # Policy B: Qualification + Direction Agreement
        # -------------------------------------------------------------------
        elif policy == GatingPolicyType.POLICY_B_DIRECTION_AGREEMENT:
            if is_qualified and (strat_dir == base_direction.upper()):
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=f"Qualified and directional agreement ({base_direction}).",
                )
            else:
                act = GatingAction.CONFLICT if qual_status == "CONFLICT" else GatingAction.REJECT
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=act,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="Failed directional agreement or qualification.",
                )

        # -------------------------------------------------------------------
        # Policy C: 3/4 Confirmation
        # -------------------------------------------------------------------
        elif policy == GatingPolicyType.POLICY_C_CONFIRMATION_3:
            if conf_score >= 3 and qual_status != "CONFLICT":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=f"Confirmation threshold met ({conf_score}/4).",
                )
            else:
                act = GatingAction.CONFLICT if qual_status == "CONFLICT" else GatingAction.REJECT
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=act,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason=f"Confirmation score sub-threshold ({conf_score}/4 < 3).",
                )

        # -------------------------------------------------------------------
        # Policy D: Conflict Filter Only (Passthrough unless Conflict)
        # -------------------------------------------------------------------
        elif policy == GatingPolicyType.POLICY_D_CONFLICT_FILTER:
            if qual_status == "CONFLICT":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=GatingAction.CONFLICT,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="Suppressed due to directional conflict.",
                )
            else:
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="Passthrough: no conflict detected.",
                )

        # -------------------------------------------------------------------
        # Policy E: Strategy-Specific Gating
        # -------------------------------------------------------------------
        elif policy == GatingPolicyType.POLICY_E_STRATEGY_SPECIFIC:
            is_btc = "BTC" in symbol.upper()
            is_xau = "XAU" in symbol.upper() or "GOLD" in symbol.upper()

            if is_btc and is_qualified and base_direction.upper() == "SELL":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="BTC SELL strategy-specific pass.",
                )
            elif is_xau and is_qualified and base_direction.upper() == "BUY":
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=base_dir_enum,
                    action=GatingAction.KEEP,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="XAU BUY strategy-specific pass.",
                )
            else:
                act = GatingAction.CONFLICT if qual_status == "CONFLICT" else GatingAction.REJECT
                return ShadowDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    timestamp=timestamp,
                    base_direction=base_dir_enum,
                    shadow_direction=SignalDirection.WAIT,
                    action=act,
                    gating_policy=policy,
                    strategy_id=strat_id,
                    qualification_status=qual_status,
                    confirmation_score=conf_score,
                    probability=prob,
                    regime=regime,
                    reason="Strategy-specific conditions not met.",
                )

        # Fallback default
        return ShadowDecision(
            signal_id=signal_id,
            symbol=symbol,
            timestamp=timestamp,
            base_direction=base_dir_enum,
            shadow_direction=SignalDirection.WAIT,
            action=GatingAction.REJECT,
            gating_policy=policy,
            strategy_id=strat_id,
            qualification_status=qual_status,
            confirmation_score=conf_score,
            probability=prob,
            regime=regime,
            reason="Unrecognized policy.",
        )
