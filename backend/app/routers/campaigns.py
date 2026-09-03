from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit, auth
from ..agents import campaign_agent
from ..db import get_db
from ..models import Campaign
from ..schemas import CampaignRequest

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(auth.get_current_seller)])


def _campaign_out(c: Campaign) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "goal": c.goal,
        "discount_percent": c.discount_percent,
        "target_segment": c.target_segment,
        "product_sku": c.product_sku,
        "budget_paise": c.budget_paise,
        "max_recipients": c.max_recipients,
        "status": c.status,
        "message_copy": c.message_copy,
        "reasoning": c.reasoning,
        "spent_paise": c.spent_paise,
        "created_at": c.created_at,
        "recipients_reached": len(c.actions),
    }


@router.get("")
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [_campaign_out(c) for c in campaigns]


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    out = _campaign_out(c)
    out["actions"] = [
        {
            "customer_name": a.customer_name,
            "amount_paise": a.amount_paise,
            "payment_link_url": a.payment_link_url,
            "status": a.status,
        }
        for a in c.actions
    ]
    return out


@router.post("")
def create_campaign(req: CampaignRequest, db: Session = Depends(get_db)):
    try:
        campaign = campaign_agent.run_campaign(db, req)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _campaign_out(campaign)


@router.post("/{campaign_id}/cancel")
def cancel_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """End a live campaign's discount before its natural expiry. Only a
    "completed" (i.e. actually launched) campaign can be stopped - a
    "proposed"/"denied" one never went live, so there's nothing to end.
    campaign_pricing.get_active_discount_percent only matches
    status=="completed", so this takes effect immediately: the moment this
    commits, that campaign's price stops being offered anywhere (chat,
    search results, checkout) - already-issued payment links to recipients
    still work if they're clicked, same as any payment link once created,
    but no new customer will be quoted this price."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "campaign not found")
    if campaign.status != "completed":
        raise HTTPException(400, f"Campaign is '{campaign.status}', not live - nothing to stop.")

    previous_status = campaign.status
    campaign.status = "cancelled"
    db.commit()

    audit.record_info(
        db,
        actor="campaign_agent",
        action_type="campaign_cancelled",
        description=f"Campaign '{campaign.name}' ({campaign.id}) stopped by seller",
        correlation_id=audit.new_correlation_id(),
        amount_paise=campaign.spent_paise,
        reasoning="Stopped early by the merchant - discount no longer applies to new checkouts.",
        before_state={"status": previous_status},
        after_state={"status": "cancelled"},
    )
    return _campaign_out(campaign)


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Permanently remove a campaign and its recipient actions - full
    deletion, not a status change. Unlike /cancel (which only stops a live
    campaign's discount going forward and keeps the record), this works on
    a campaign in any status and erases it entirely, for cleaning up
    test/demo campaigns. The gatekeeper audit trail (/audit) is untouched -
    that's a permanent decision log, not campaign state - so a deleted
    campaign's launch/denial/cancel history is still inspectable there even
    after the campaign itself is gone."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "campaign not found")

    audit.record_info(
        db,
        actor="campaign_agent",
        action_type="campaign_deleted",
        description=f"Campaign '{campaign.name}' ({campaign.id}) deleted by seller",
        correlation_id=audit.new_correlation_id(),
        amount_paise=campaign.spent_paise,
        reasoning="Removed by the merchant.",
        before_state={"status": campaign.status},
        after_state={"status": "deleted"},
    )
    db.delete(campaign)
    db.commit()
    return {"status": "deleted", "id": campaign_id}
