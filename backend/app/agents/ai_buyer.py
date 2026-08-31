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
2. Pick the best match(es) within budget - prefer exact fit over guessing.
3. Add your chosen product(s) to the cart.
4. Optionally check get_upsell_suggestions, and add a complementary item ONLY if it clearly still fits the \
   stated budget.
5. Call checkout to complete the purchase. If you were given a spending mandate, stay within it - checkout \
   will be denied if you exceed it, same as going over budget.
6. If checkout is denied by the gatekeeper, report the denial reason plainly - do not retry with a made-up \
   workaround.

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
    checkout_result = _find_checkout_result(trace)

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
