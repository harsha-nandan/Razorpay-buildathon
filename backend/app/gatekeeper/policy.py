from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings


@dataclass
class ProposedAction:
    """A money-moving action an agent wants to take, before it happens."""

    actor: str  # checkout_agent | upsell_agent | campaign_agent | ai_buyer
    action_type: str  # create_payment_link | launch_campaign_batch
    amount_paise: int
    currency: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleVerdict:
    allow: bool
    reason: str
    policy_refs: list[str]


def check_hard_bounds(action: ProposedAction) -> RuleVerdict:
    """Deterministic, LLM-independent bounds. These can never be talked around.

    This is the layer that keeps every money action "bounded" per the brief,
    regardless of whether an LLM gatekeeper is configured or how it reasons.
    """
    settings = get_settings()
    refs: list[str] = []

    if action.currency != "INR":
        return RuleVerdict(False, f"Unsupported currency '{action.currency}'.", ["currency=INR"])

    if action.action_type == "create_payment_link":
        refs.append(f"max_single_order_paise={settings.max_single_order_paise}")
        if action.amount_paise > settings.max_single_order_paise:
            return RuleVerdict(
                False,
                f"Order amount {_inr(action.amount_paise)} exceeds the per-order cap of "
                f"{_inr(settings.max_single_order_paise)}.",
                refs,
            )

        mandate_remaining_paise = action.context.get("mandate_remaining_paise")
        if mandate_remaining_paise is not None:
            refs.append("mandate_remaining_paise")
            if action.amount_paise > mandate_remaining_paise:
                mandate_label = action.context.get("mandate_label", "this mandate")
                return RuleVerdict(
                    False,
                    f"Order amount {_inr(action.amount_paise)} exceeds the {_inr(mandate_remaining_paise)} "
                    f"remaining on the customer's spending mandate ({mandate_label}) - the agent is not "
                    f"authorized to spend beyond what the customer pre-approved.",
                    refs,
                )

        orders_this_session = action.context.get("orders_this_session", 0)
        refs.append(f"max_orders_per_session={settings.max_orders_per_session}")
        if orders_this_session >= settings.max_orders_per_session:
            return RuleVerdict(
                False,
                f"Session has already created {orders_this_session} orders, "
                f"at the cap of {settings.max_orders_per_session}.",
                refs,
            )

        discount_percent = action.context.get("discount_percent", 0)
        refs.append(f"max_discount_percent={settings.max_discount_percent}")
        if discount_percent > settings.max_discount_percent:
            return RuleVerdict(
                False,
                f"Discount of {discount_percent}% exceeds the max allowed {settings.max_discount_percent}%.",
                refs,
            )

    elif action.action_type == "launch_campaign_batch":
        discount_percent = action.context.get("discount_percent", 0)
        refs.append(f"max_discount_percent={settings.max_discount_percent}")
        if discount_percent > settings.max_discount_percent:
            return RuleVerdict(
                False,
                f"Campaign discount of {discount_percent}% exceeds the max allowed "
                f"{settings.max_discount_percent}%.",
                refs,
            )

        recipients = action.context.get("recipients", 0)
        refs.append(f"max_campaign_recipients={settings.max_campaign_recipients}")
        if recipients > settings.max_campaign_recipients:
            return RuleVerdict(
                False,
                f"Campaign targets {recipients} recipients, over the cap of "
                f"{settings.max_campaign_recipients}.",
                refs,
            )

        budget_spent_today = action.context.get("budget_spent_today", 0)
        refs.append(f"daily_campaign_budget_paise={settings.daily_campaign_budget_paise}")
        if budget_spent_today + action.amount_paise > settings.daily_campaign_budget_paise:
            remaining = max(settings.daily_campaign_budget_paise - budget_spent_today, 0)
            return RuleVerdict(
                False,
                f"Campaign would spend {_inr(action.amount_paise)} but only {_inr(remaining)} "
                f"remains of today's {_inr(settings.daily_campaign_budget_paise)} budget.",
                refs,
            )

    if action.amount_paise <= 0:
        return RuleVerdict(False, "Amount must be positive.", refs + ["amount>0"])

    return RuleVerdict(True, "Within all configured hard bounds.", refs)


def _inr(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"
