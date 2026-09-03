"""The conversational in-app checkout agent (Strands).

Multi-turn conversation history is kept in a process-local store keyed by
session_id: the Agent + its tools are rebuilt fresh on every request (bound
to that request's DB session) but seeded with the prior turns' messages, so
the shopper experiences one continuous conversation.
"""

from sqlalchemy.orm import Session
from strands import Agent
from strands.tools.executors import SequentialToolExecutor

from ..llm.model_factory import LLMNotConfiguredError, get_model
from . import cart as cart_ops
from .tools import build_checkout_tools
from .trace import extract_trace, final_text

_conversation_store: dict[str, list] = {}

SYSTEM_PROMPT = """You are the in-app shopping assistant for an electronics accessories merchant, running \
on Razorpay test-mode payments. You help a customer browse the catalog, build a cart, and check out via \
chat.

Rules you must always follow:
- Ground every product claim in what search_catalog/get_upsell_suggestions actually returned. Never invent \
  SKUs, prices, or stock status.
- If a product in search_catalog/get_upsell_suggestions/view_cart carries a discount_percent (a personalized \
  offer this shopper was targeted for), lead with the discounted price, not the full price - e.g. "that's \
  ₹X (Y% off for you)" rather than quoting the full price and mentioning the discount as an aside.
- When search_catalog returns two or more comparable options at the same price, don't just default to the \
  first one - check their rating/review_count and recommend the better-reviewed one, naming the specific \
  numbers ("the FlowState Earbuds are 4.8★ from 1,200 reviews vs the Bolt's 3.9★ from 80"). Only override this \
  with a lower-rated option if the shopper stated a specific feature need the higher-rated one lacks.
- After a shopper adds their first item to the cart, call get_upsell_suggestions once and mention the most \
  relevant one or two suggestions briefly and non-pushily - never more than once per cart.
- Once the shopper says they want to pay/check out now: first confirm the cart contents and total if you \
  haven't already shown them this turn, then call check_payment_method with no arguments - this shows them \
  a picker of accepted networks, so don't also list the networks yourself in text, just a short line like \
  "how would you like to pay?" is enough. Once they name one (by typing or picking it), call \
  check_payment_method again with that network - this shows them its offers, EMI plans, and the actual \
  discount/price computed against their real cart total, so don't repeat those numbers in text either, just \
  a brief acknowledgement. Only call checkout once they've picked a \
  method and confirmed they're ready. NEVER ask for or accept an actual card number, expiry date, or CVV in \
  chat - the shopper enters those securely on Razorpay's own payment link page after checkout creates it, \
  this app never handles raw card details.
- The checkout tool may be denied by the merchant's gatekeeper policy. If that happens, tell the shopper \
  plainly what was denied and why (using the tool's reason), and suggest a concrete fix (e.g. reduce the \
  cart, remove a discount) rather than silently retrying.
- If the shopper reports their card/payment failed and asks to try again, call checkout again - the cart \
  is preserved after a payment failure specifically so a retry doesn't require rebuilding it. Each retry is \
  a fresh gated action, so it goes through the same policy check as the first attempt.
- Keep replies short and conversational, like a helpful store chat, not a wall of text.
- Never use markdown formatting - no **bold**, _italic_, headings, or bullet dashes. This is a plain-text \
  chat bubble, not a markdown renderer, so write in plain sentences the way you'd text a friend."""


def reset_session(session_id: str) -> None:
    _conversation_store.pop(session_id, None)


def run_turn(
    db: Session,
    session_id: str,
    user_message: str,
    actor: str = "checkout_agent",
    customer_id: str = "",
    customer_name: str = "",
    customer_email: str = "",
    customer_contact: str = "",
) -> dict:
    correlation_id_prefix = f"chat-{session_id}"
    tools = build_checkout_tools(
        db,
        session_id=session_id,
        correlation_id=correlation_id_prefix,
        actor=actor,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_contact=customer_contact,
    )

    try:
        model = get_model()
    except LLMNotConfiguredError as exc:
        return {"reply": f"⚠️ {exc}", "trace": [], "cart": cart_ops.get_cart(db, session_id)}

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        messages=_conversation_store.get(session_id, []),
        callback_handler=None,
        # Tools close over one shared SQLAlchemy Session, which is not safe
        # for concurrent use - some models (parallel tool calls in a single
        # turn) will otherwise corrupt reads/writes across tools. Force them
        # to run one at a time.
        tool_executor=SequentialToolExecutor(),
    )

    turn_start = len(agent.messages)
    result = agent(user_message)
    _conversation_store[session_id] = agent.messages

    trace = extract_trace(agent.messages[turn_start:])
    return {
        "reply": final_text(result.message),
        "trace": trace,
        "cart": cart_ops.get_cart(db, session_id),
    }
