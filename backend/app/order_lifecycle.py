"""Cancelling/expiring an unpaid order - the counterpart to payment_confirmation.py's
"mark paid" path. A "created" order (payment link issued, never confirmed
paid or failed) otherwise sits open forever and keeps consuming the
customer's max_orders_per_session budget even after they've abandoned it
(refreshed the browser, exited the chat, started over). Cancelling frees
that budget back up; the cart itself is untouched either way, same as a
failed payment, so a shopper can always just rebuild or retry.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import audit
from .config import get_settings
from .models import Order


def cancel_order(db: Session, order: Order, *, reason: str) -> bool:
    """Cancel a single order still in "created" status. No-op (returns False)
    for any other status - an order that's already paid/failed/denied/
    cancelled is a closed transaction record, never rewritten."""
    if order.status != "created":
        return False

    previous_status = order.status
    order.status = "cancelled"
    db.commit()

    audit.record_info(
        db,
        actor=order.source,
        action_type="order_cancelled",
        description=f"Order {order.id} cancelled - {reason}",
        correlation_id=audit.new_correlation_id(),
        amount_paise=order.amount_paise,
        reasoning=reason,
        before_state={"status": previous_status},
        after_state={"status": "cancelled"},
    )
    return True


def expire_abandoned_orders(db: Session, session_id: str) -> int:
    """Auto-cancel this session's "created" orders that have sat unconfirmed
    past the abandoned-order TTL. Called lazily at checkout time (no
    background worker in this app) so a stale payment attempt from a
    refreshed browser or an exited chat stops blocking new ones."""
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.abandoned_order_ttl_minutes)
    stale = (
        db.query(Order)
        .filter(Order.session_id == session_id, Order.status == "created", Order.created_at < cutoff)
        .all()
    )
    count = 0
    for order in stale:
        if cancel_order(db, order, reason=f"abandoned - no confirmation within {settings.abandoned_order_ttl_minutes} minutes"):
            count += 1
    return count
