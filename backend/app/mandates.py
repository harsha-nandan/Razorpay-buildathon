"""Spending-mandate math: how much of a customer-issued authorization has
been used, and how much is left, computed on demand from the orders that
were actually attributed to it - not a running counter that would need
resetting on a schedule.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import Mandate, Order

_WINDOWS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


def window_start(mandate: Mandate) -> datetime | None:
    """None means no rolling window - the whole lifetime of the mandate."""
    delta = _WINDOWS.get(mandate.period)
    if not delta:
        return None
    return datetime.now(timezone.utc) - delta


def spent_paise(db: Session, mandate: Mandate) -> int:
    q = db.query(Order).filter(Order.mandate_id == mandate.id, Order.status.in_(("created", "paid")))
    start = window_start(mandate)
    if start:
        q = q.filter(Order.created_at >= start)
    return sum(o.amount_paise for o in q.all())


def remaining_paise(db: Session, mandate: Mandate) -> int:
    return max(0, mandate.max_amount_paise - spent_paise(db, mandate))
