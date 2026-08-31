from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit, auth
from ..config import get_settings
from ..db import get_db
from ..models import Customer, Order, Seller
from ..payment_confirmation import confirm_paid
from ..payment_failures import get_failure_detail
from ..razorpay_adapter.factory import get_gateway
from ..schemas import SimulatePaymentRequest

router = APIRouter(tags=["orders"])


def _order_out(o: Order) -> dict:
    return {
        "id": o.id,
        "session_id": o.session_id,
        "source": o.source,
        "amount_paise": o.amount_paise,
        "currency": o.currency,
        "status": o.status,
        "items": o.items,
        "payment_link_url": o.razorpay_payment_link_url,
        "failure_code": o.failure_code,
        "failure_reason": o.failure_reason,
        "failure_remedy": o.failure_remedy,
        "created_at": o.created_at,
    }


@router.get("/orders")
def list_orders(db: Session = Depends(get_db), _seller: Seller = Depends(auth.get_current_seller)):
    """All orders across every channel - merchant/seller view. This doubles
    as the transaction log: every attempt is its own row (a retry after a
    failure creates a new order/payment link rather than overwriting the
    old one), so failed and successful attempts are both preserved here."""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return [_order_out(o) for o in orders]


@router.get("/my/orders")
def list_my_orders(db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    """Just the signed-in customer's own transaction history."""
    session_id = f"cust-{customer.id}"
    orders = db.query(Order).filter(Order.session_id == session_id).order_by(Order.created_at.desc()).all()
    return [_order_out(o) for o in orders]


@router.post("/payments/simulate")
def simulate_payment(
    req: SimulatePaymentRequest,
    db: Session = Depends(get_db),
    customer: Customer = Depends(auth.get_current_customer),
):
    """Demo-only action: marks an order paid/failed so the UI can show a full
    order lifecycle without a real Razorpay Checkout card flow - this app has
    no webhook receiver, so a real payment's true confirmation would never
    otherwise reach it. Always forces the outcome in OUR database, in both
    mock and live gateway mode: real Razorpay test-mode payment links stay
    whatever they really are on Razorpay's side (only a real card payment on
    the payment_link_url changes that) - the audit trail is explicit about
    it being a simulated confirmation, not a real one, whenever a real
    gateway is in play.

    A "paid" outcome issues an invoice and clears the cart. A "failed"
    outcome records a specific, realistic decline reason and remedy (never
    just "payment failed") and leaves the cart intact so the shopper can
    retry checkout without rebuilding it. Both outcomes are written to the
    audit trail."""
    if req.outcome not in ("paid", "failed"):
        raise HTTPException(400, "outcome must be 'paid' or 'failed'")

    order = db.get(Order, req.order_id)
    if not order:
        raise HTTPException(404, "order not found")
    if order.session_id != f"cust-{customer.id}":
        raise HTTPException(403, "This order does not belong to you.")
    if not order.razorpay_payment_link_id:
        raise HTTPException(400, "order has no payment link to simulate")

    if req.outcome == "paid":
        confirmation = confirm_paid(db, order, customer_name=customer.name, customer_email=customer.email)
        result = _order_out(order)
        result["simulated"] = confirmation["simulated"]
        result["real_gateway_status"] = confirmation["real_gateway_status"]
        return result

    settings = get_settings()
    is_live = settings.razorpay_mode.lower() == "live"
    gateway = get_gateway()

    real_status = None
    if is_live:
        try:
            real_status = gateway.fetch_payment_link(order.razorpay_payment_link_id).get("status")
        except Exception:  # noqa: BLE001 - informational only, never blocks the demo action
            real_status = "unknown"
    else:
        # Keep the mock gateway's own internal record in sync too, even
        # though the order status below is what actually drives the app.
        gateway.simulate_payment(order.razorpay_payment_link_id, req.outcome)

    previous_status = order.status
    detail = get_failure_detail(req.failure_code)
    order.status = "failed"
    order.failure_code = detail.code
    order.failure_reason = detail.reason
    order.failure_remedy = detail.remedy
    db.commit()
    db.refresh(order)

    audit.record_info(
        db,
        actor=order.source,
        action_type="payment_failed",
        description=f"Payment declined for order {order.id} ({detail.code}) - cart preserved for retry",
        correlation_id=audit.new_correlation_id(),
        amount_paise=order.amount_paise,
        reasoning=f"{detail.reason} Remedy: {detail.remedy}",
        before_state={"status": previous_status},
        after_state={
            "status": "failed",
            "failure_code": detail.code,
            "simulated": True,
            **({"real_razorpay_status": real_status} if is_live else {}),
        },
    )

    result = _order_out(order)
    result["simulated"] = True
    result["real_gateway_status"] = real_status
    return result
