from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth
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
