"""Links a launched campaign's discount to what its targeted customer
actually sees and pays in the conversational checkout - otherwise a
campaign only ever produces a payment link the customer never sees inside
the app (routers/campaigns.py sends it out-of-band), and the catalog/chat
keep quoting full price even to a customer the merchant just offered a
discount to.

A customer is "eligible" for a campaign's price exactly when they were
actually targeted by it (a CampaignAction row exists for them) and the
campaign is still "completed" (i.e. live) - not just "belongs to the
matching segment", since campaigns are a personalized, bounded-recipient
outreach (max_recipients), not a storefront-wide sale. A seller-stopped
campaign moves to "cancelled" (routers/campaigns.py's /cancel endpoint) and
so stops matching here immediately - no separate flag or expiry check
needed, the status filter below is the single source of truth for "is this
discount still live".
"""

from sqlalchemy.orm import Session

from .models import Campaign, CampaignAction


def get_active_discount_percent(db: Session, customer_id: str | None, sku: str) -> int:
    """The best campaign discount this customer was actually offered on this
    SKU, or 0 if none. Picks the highest if more than one campaign targeted
    them for the same product."""
    if not customer_id or not sku:
        return 0

    best = (
        db.query(Campaign.discount_percent)
        .join(CampaignAction, CampaignAction.campaign_id == Campaign.id)
        .filter(
            CampaignAction.customer_id == customer_id,
            Campaign.product_sku == sku,
            Campaign.status == "completed",
        )
        .order_by(Campaign.discount_percent.desc())
        .first()
    )
    return best[0] if best else 0


def apply_discount(price_paise: int, discount_percent: int) -> int:
    return round(price_paise * (1 - discount_percent / 100))
