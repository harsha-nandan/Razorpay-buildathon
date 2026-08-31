from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..db import get_db
from ..models import AuditLogEntry, Campaign, Order

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(auth.get_current_seller)])


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    campaigns = db.query(Campaign).all()
    audit_entries = db.query(AuditLogEntry).all()

    paid_orders = [o for o in orders if o.status == "paid"]
    denied_orders = [o for o in orders if o.status == "denied"]
    failed_orders = [o for o in orders if o.status == "failed"]

    revenue_by_day: dict[str, int] = defaultdict(int)
    for o in paid_orders:
        revenue_by_day[o.created_at.date().isoformat()] += o.amount_paise

    revenue_by_source: dict[str, int] = defaultdict(int)
    for o in paid_orders:
        revenue_by_source[o.source] += o.amount_paise

    gatekeeper_allows = len([a for a in audit_entries if a.decision == "allow"])
    gatekeeper_denies = len([a for a in audit_entries if a.decision == "deny"])

    # Funnel: every checkout attempt is an order row (denied ones included),
    # so this is derivable straight from Order status without any separate
    # event tracking. "Approved" = passed the gatekeeper; "paid" = actually
    # converted. The attempted->approved drop-off is the gate at work; the
    # approved->paid drop-off is ordinary payment abandonment/failure.
    attempted = len(orders)
    approved = len([o for o in orders if o.status != "denied"])
    paid = len(paid_orders)

    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"attempted": 0, "approved": 0, "paid": 0})
    for o in orders:
        by_source[o.source]["attempted"] += 1
        if o.status != "denied":
            by_source[o.source]["approved"] += 1
        if o.status == "paid":
            by_source[o.source]["paid"] += 1

    return {
        "total_revenue_paise": sum(o.amount_paise for o in paid_orders),
        "orders_created": len(orders),
        "orders_paid": len(paid_orders),
        "orders_denied": len(denied_orders),
        "orders_failed": len(failed_orders),
        "campaigns_total": len(campaigns),
        "campaigns_running_or_completed": len([c for c in campaigns if c.status in ("running", "completed")]),
        "campaigns_denied": len([c for c in campaigns if c.status == "denied"]),
        "gatekeeper_allows": gatekeeper_allows,
        "gatekeeper_denies": gatekeeper_denies,
        "revenue_by_day": sorted(({"date": d, "revenue_paise": v} for d, v in revenue_by_day.items()), key=lambda x: x["date"]),
        "revenue_by_source": [{"source": s, "revenue_paise": v} for s, v in revenue_by_source.items()],
        "funnel": {
            "stages": [
                {"stage": "Checkout attempted", "count": attempted},
                {"stage": "Approved by gatekeeper", "count": approved},
                {"stage": "Payment completed", "count": paid},
            ],
            "by_source": [{"source": s, **counts} for s, counts in by_source.items()],
        },
    }
