"""Shared "mark an order paid" logic, used by both the customer checkout
flow's simulate button and the AI-buyer's x402 payment-confirmation step.
Centralized so both paths stay honest about the same thing: this app has no
webhook receiver, so any "paid" state here is a demo confirmation forced in
OUR database - never a claim that the real Razorpay link was actually paid,
which is called out explicitly whenever a live (non-mock) gateway is active.
"""

from sqlalchemy.orm import Session

from . import audit, invoicing
from .agents import cart as cart_ops
from .config import get_settings
from .models import Order
from .razorpay_adapter.factory import get_gateway


def confirm_paid(db: Session, order: Order, *, customer_name: str = "", customer_email: str = "") -> dict:
    """Idempotent: calling this on an already-paid order just reports its
    existing state instead of re-issuing an invoice or re-writing history."""
    settings = get_settings()
    is_live = settings.razorpay_mode.lower() == "live"
    gateway = get_gateway()

    real_status = None
    if is_live:
        try:
            real_status = gateway.fetch_payment_link(order.razorpay_payment_link_id).get("status")
        except Exception:  # noqa: BLE001 - informational only, never blocks confirmation
            real_status = "unknown"

    if order.status == "paid":
        return {"already_paid": True, "simulated": True, "real_gateway_status": real_status}

    previous_status = order.status
    order.status = "paid"
    db.commit()
    db.refresh(order)

    invoicing.issue_invoice(db, order, customer_name=customer_name, customer_email=customer_email)
    cart_ops.clear_cart(db, order.session_id)

    correlation_id = audit.new_correlation_id()
    audit.record_info(
        db,
        actor=order.source,
        action_type="payment_confirmed",
        description=f"Payment confirmed for order {order.id}"
        + (" (simulated - real Razorpay link is unpaid)" if is_live else ""),
        correlation_id=correlation_id,
        amount_paise=order.amount_paise,
        before_state={"status": previous_status},
        after_state={
            "status": "paid",
            "invoice_issued": True,
            "simulated": True,
            **({"real_razorpay_status": real_status} if is_live else {}),
        },
    )
    return {"already_paid": False, "simulated": True, "real_gateway_status": real_status}
