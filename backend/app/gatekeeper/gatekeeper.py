"""The gatekeeper every money-moving tool call must pass through.

Two layers, always both applied:
  1. Hard bounds (policy.check_hard_bounds) - deterministic, cannot be
     talked around by an LLM, and work even with zero LLM configured.
  2. LLM-as-gatekeeper - a dedicated Strands agent, separate from whichever
     agent proposed the action, that reasons about context (is this
     copy honest, does this look abusive/duplicated) and must return a
     structured allow/deny + reason. Fails closed: if the LLM errs or
     isn't configured, the action still holds on rule-based allow but is
     flagged as unreviewed by an LLM in the audit trail.

Every single evaluation - allowed or denied - is written to the audit log
by the caller, so the full reasoning trail is inspectable after the fact.
"""

import logging
from dataclasses import dataclass

from strands import Agent
from strands.models.model import Model

from ..llm.model_factory import LLMNotConfiguredError, get_model
from ..schemas import GatekeeperDecision
from .policy import ProposedAction, check_hard_bounds

logger = logging.getLogger(__name__)

GATEKEEPER_SYSTEM_PROMPT = """You are a strict, independent financial risk-and-policy gatekeeper sitting \
between a merchant's autonomous commerce agents and real money movement (Razorpay test-mode orders and \
payment links).

Every action you review has ALREADY passed hard numeric bounds (per-order cap, discount cap, campaign \
budget cap, recipient cap) enforced separately in code you cannot override. Your job is the contextual \
layer on top: does this specific action make business sense, is any customer-facing copy honest and \
non-manipulative, does anything about it look abusive, duplicated, or exploitative even though it is \
numerically within policy?

Be decisive. Default to allow when an action is unremarkable and within bounds. Deny (allow=false) when \
you spot a concrete, explainable problem - not on vague unease. Always give a one to two sentence reason \
a merchant ops person could read and immediately understand. List concrete risk_flags (short strings) \
when relevant, empty list otherwise. Respond only via the structured output."""


@dataclass
class GatekeeperVerdict:
    allow: bool
    reason: str
    decided_by: str  # "rule_engine" | "llm_gatekeeper" | "rule_engine+llm_gatekeeper"
    policy_refs: list[str]
    risk_flags: list[str]


def _build_review_prompt(action: ProposedAction) -> str:
    lines = [
        f"actor: {action.actor}",
        f"action_type: {action.action_type}",
        f"amount: INR {action.amount_paise / 100:,.2f}",
        f"description: {action.description}",
    ]
    for key, value in action.context.items():
        lines.append(f"context.{key}: {value}")
    return "Review this proposed money action:\n" + "\n".join(lines)


def _llm_review(action: ProposedAction, model: Model | None = None) -> GatekeeperDecision:
    agent = Agent(model=model or get_model(), system_prompt=GATEKEEPER_SYSTEM_PROMPT, tools=[])
    result = agent(_build_review_prompt(action), structured_output_model=GatekeeperDecision)
    decision = result.structured_output
    if decision is None:
        raise RuntimeError("LLM gatekeeper returned no structured output")
    return decision


def evaluate(action: ProposedAction) -> GatekeeperVerdict:
    rule_verdict = check_hard_bounds(action)

    if not rule_verdict.allow:
        return GatekeeperVerdict(
            allow=False,
            reason=rule_verdict.reason,
            decided_by="rule_engine",
            policy_refs=rule_verdict.policy_refs,
            risk_flags=["hard_bound_exceeded"],
        )

    try:
        llm_decision = _llm_review(action)
    except LLMNotConfiguredError as exc:
        logger.info("Gatekeeper LLM not configured, falling back to rule-only allow: %s", exc)
        return GatekeeperVerdict(
            allow=True,
            reason=rule_verdict.reason + " (LLM gatekeeper not configured - rule-based bounds only.)",
            decided_by="rule_engine",
            policy_refs=rule_verdict.policy_refs,
            risk_flags=["llm_gatekeeper_unavailable"],
        )
    except Exception as exc:  # noqa: BLE001 - fail closed on any LLM/gatekeeper error
        logger.exception("Gatekeeper LLM review failed, failing closed (deny)")
        return GatekeeperVerdict(
            allow=False,
            reason=f"LLM gatekeeper errored during review, denying for safety: {exc}",
            decided_by="llm_gatekeeper",
            policy_refs=rule_verdict.policy_refs,
            risk_flags=["gatekeeper_error"],
        )

    return GatekeeperVerdict(
        allow=llm_decision.allow,
        reason=llm_decision.reason,
        decided_by="rule_engine+llm_gatekeeper",
        policy_refs=rule_verdict.policy_refs,
        risk_flags=llm_decision.risk_flags,
    )
