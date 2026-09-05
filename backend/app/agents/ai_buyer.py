"""AI-buyer simulator: an external autonomous agent transacting with the
merchant end to end via the same catalog + gatekeeper + Razorpay machinery a
human shopper uses. This is the "sellable to AI buyers" / agent-to-agent
commerce path - no human in the loop, so the agent must decide and act on
its own, and every decision still passes the same bounded, gated checks.

The purchase flow follows an x402-style handshake (adapted to Razorpay
rails instead of x402's usual on-chain settlement): the first call quotes a
price and returns HTTP 402 Payment Required with payment instructions
instead of completing the purchase outright; a second call, presenting
proof of payment, actually confirms it. See routers/ai_buyer.py for the
HTTP-level mechanics.
"""

import json
import uuid

from sqlalchemy.orm import Session
from strands import Agent
from strands.tools.executors import SequentialToolExecutor

from ..llm.model_factory import LLMNotConfiguredError, get_model
from ..models import Invoice, Mandate, Order
from ..payment_confirmation import confirm_paid
from .tools import build_checkout_tools
from .trace import extract_trace, final_text

SYSTEM_PROMPT = """You are an autonomous AI purchasing agent acting on behalf of an external buyer. You are \
NOT a human and there is no human to ask follow-up questions - you must decide and act within this single \
turn using only the tools available.

Given a shopping intent and (optionally) a budget, you must:
1. Search the merchant's catalog for matching product(s).
2. Pick the best match(es) within budget - prefer exact fit over guessing. When multiple results are \
   comparable matches at the same price, don't just take the first one - compare their rating/review_count \
   and pick the better-reviewed option, stating the specific numbers in your reasoning (e.g. "chose the \
   FlowState Earbuds, 4.8★/1,200 reviews, over the Bolt at 3.9★/80 reviews"). A stated feature requirement the \
   higher-rated option lacks still overrides rating.
3. Add your chosen product(s) to the cart.
4. Optionally check get_upsell_suggestions, and add a complementary item ONLY if it clearly still fits the \
   stated budget.
5. Call checkout to complete the purchase. If you were given a spending mandate, stay within it - checkout \
   will be denied if you exceed it, same as going over budget.
6. If checkout is denied (e.g. the order is over the merchant's per-order cap), don't stop there - look at \
   the cart and find a real way back within policy: remove an item, or swap a product for a genuinely \
   cheaper alternative that still reasonably fits the buyer's intent, then call checkout again. Only report \
   a final denial, with the reason, once no such adjustment exists within the cart/budget - never invent a \
   workaround that isn't actually reflected in the cart (e.g. claiming a discount that was never applied).

Explain each decision briefly as you go so your reasoning is auditable. If nothing in the catalog matches \
the intent or budget, say so clearly instead of buying something unsuitable.

Never use markdown formatting - no **bold**, _italic_, headings, or bullet dashes. Write your report as \
plain sentences, not a markdown document."""


def _find_checkout_result(trace: list[dict]) -> dict | None:
    for item in reversed(trace):
        if item.get("type") == "tool_result" and item.get("tool") == "checkout" and item.get("output"):
            try:
                return json.loads(item["output"])
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def _has_tool_calls(trace: list[dict]) -> bool:
    return any(item.get("type") == "tool_call" for item in trace)


def _has_checkout_call(trace: list[dict]) -> bool:
    return any(item.get("type") == "tool_call" and item.get("tool") == "checkout" for item in trace)


def run_purchase(db: Session, intent: str, budget_paise: int | None, mandate: Mandate | None = None) -> dict:
    """Phase 1 of the handshake: decide, build a cart, and get gatekeeper
    approval - but stop short of confirming payment. The caller (the
    router) turns an "approved" result into an HTTP 402 quote."""
    session_id = f"aibuyer-{uuid.uuid4().hex[:10]}"
    correlation_id = f"aibuyer-{session_id}"
    tools = build_checkout_tools(
        db, session_id=session_id, correlation_id=correlation_id, actor="ai_buyer", mandate=mandate
    )

    try:
        model = get_model()
    except LLMNotConfiguredError as exc:
        return {"session_id": session_id, "reply": f"⚠️ {exc}", "trace": [], "status": "error"}

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        callback_handler=None,
        # See checkout_agent.py - tools share one non-thread-safe DB Session.
        tool_executor=SequentialToolExecutor(),
    )

    budget_line = f"\nbudget_inr: {budget_paise / 100:,.2f}" if budget_paise else "\nbudget_inr: no explicit limit"
    mandate_line = (
        f"\nspending_mandate: '{mandate.label}', up to INR {mandate.max_amount_paise / 100:,.2f} per {mandate.period}"
        if mandate
        else ""
    )
    result = agent(f"buyer_intent: {intent}{budget_line}{mandate_line}")
    trace = extract_trace(agent.messages)

    # This agent is meant to decide AND act with no human to prompt a retry.
    # A model that narrates an action ("I'll add it... now checking out")
    # without ever calling the corresponding tool is a known failure mode,
    # especially on compound intents ("a smartwatch and whatever goes well
    # with it") with smaller/local models - and it can stall at any point:
    # never searching at all, searching once and stopping, or building a
    # cart and still never calling checkout. The one thing that reliably
    # signals "this attempt never actually reached a purchase decision" is
    # checkout never being called, regardless of which step it stalled at.
    # Nudge it forward - in the same session, so it can see what it already
    # claimed - a bounded couple of times before accepting "nothing
    # happened" as final; each nudge is a no-op cost-wise once it commits.
    for _ in range(2):
        if _has_checkout_call(trace):
            break
        nudge = (
            "You responded without calling any tool. Call search_catalog for the buyer's intent now - "
            "you must actually search, not just describe what you would do."
            if not _has_tool_calls(trace)
            else "You described what to do next but didn't actually call the tool for it - nothing has "
            "happened yet beyond what's shown above. Continue now: call add_to_cart/get_upsell_suggestions "
            "as needed, then call checkout once the cart is ready. If nothing suitable exists, say so "
            "plainly instead of describing an action you're not taking."
        )
        result = agent(nudge)
        trace = extract_trace(agent.messages)

    # A checkout call happening at all doesn't mean the run is done - a
    # denial (most commonly the per-order cap) is a recoverable state, not a
    # final one, but a model will sometimes report the denial and stop there
    # instead of adjusting the cart per the system prompt's step 6. Nudge it
    # to actually retry with a cheaper cart rather than accepting the first
    # denial as the end of the run; bounded the same way as the loop above,
    # so a cart that's still over cap after two genuine attempts to shrink it
    # ends in a real, reported denial instead of looping forever.
    for _ in range(2):
        checkout_result = _find_checkout_result(trace)
        if not checkout_result or checkout_result.get("status") != "denied":
            break
        nudge = (
            f"Checkout was denied: {checkout_result.get('reason')} Don't just report this as final - adjust "
            "the cart (remove an item, or swap for a cheaper product that still reasonably fits the intent) "
            "and call checkout again. Only report a final denial if no such adjustment brings it within policy."
        )
        result = agent(nudge)
        trace = extract_trace(agent.messages)

    checkout_result = _find_checkout_result(trace)

    # This flow is intentionally unauthenticated - no customer to attach the
    # order to - so the natural-language ask that drove it would otherwise
    # be lost the moment this response is sent. Stamp it onto whichever
    # order(s) checkout created for this run (0, 1, or 2 - e.g. one denied
    # attempt followed by an adjusted, approved retry) so the AI Buyer
    # Simulator's run history can show it later.
    run_orders = db.query(Order).filter(Order.session_id == session_id).all()
    for order in run_orders:
        order.buyer_intent = intent
        order.requested_budget_paise = budget_paise
    if run_orders:
        db.commit()

    payload: dict = {"session_id": session_id, "reply": final_text(result.message), "trace": trace}
    if checkout_result and checkout_result.get("status") == "approved":
        payload.update(
            status="payment_required",
            order_id=checkout_result["order_id"],
            amount_paise=checkout_result["amount_paise"],
            payment_link=checkout_result["payment_link"],
        )
    elif checkout_result and checkout_result.get("status") == "denied":
        payload.update(status="denied", reason=checkout_result.get("reason"))
    else:
        payload["status"] = "no_purchase"
    return payload


def confirm_purchase(db: Session, order_id: str) -> dict:
    """Phase 2 of the handshake: the caller presents an order id as proof of
    payment (via the X-PAYMENT header - see routers/ai_buyer.py) and this
    confirms it, issuing the invoice exactly like the human checkout flow's
    simulate-pay action does."""
    order = db.query(Order).filter(Order.id == order_id, Order.source == "ai_buyer").first()
    if not order:
        return {"status": "error", "reason": "Unknown AI-buyer order - nothing to confirm."}

    confirmation = confirm_paid(db, order, customer_name="AI buyer (agent-to-agent)", customer_email="")
    invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    return {
        "status": "completed",
        "order_id": order.id,
        "amount_paise": order.amount_paise,
        "invoice_number": invoice.invoice_number if invoice else None,
        "simulated": confirmation["simulated"],
        "real_gateway_status": confirmation["real_gateway_status"],
    }
