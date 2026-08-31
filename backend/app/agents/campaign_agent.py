"""Campaign orchestrator agent (Strands).

The LLM's job is narrow and honest: draft customer-facing offer copy and a
one-line business rationale. It never decides the discount, the recipient
count, or the budget - those are deterministic, policy-bounded, and pass
through the same gatekeeper as every other money action before a single
payment link goes out.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from strands import Agent

from .. import audit
from ..gatekeeper.gatekeeper import evaluate as gatekeeper_evaluate
from ..gatekeeper.policy import ProposedAction
from ..llm.model_factory import LLMNotConfiguredError, get_model
from ..models import Campaign, CampaignAction, Customer, Product
from ..razorpay_adapter.factory import get_gateway
from ..schemas import CampaignPlan, CampaignRequest

SYSTEM_PROMPT = """You are a merchant growth campaign copywriter. Given a campaign goal, a discount, a \
target customer segment, and a product, write a short, honest, non-manipulative customer-facing offer \
message (under 220 characters, no fake urgency, no all-caps shouting, no misleading claims) and one or two \
sentences explaining why this campaign should grow revenue for the merchant. Plain text only - no markdown \
(no **bold**, _italic_, or bullet dashes) in either field. Respond only via the structured output."""


def _budget_spent_today(db: Session) -> int:
    today = datetime.now(timezone.utc).date()
    total = 0
    for campaign in db.query(Campaign).filter(Campaign.status.in_(["running", "completed"])).all():
        if campaign.created_at.date() == today:
            total += campaign.spent_paise
    return total


def run_campaign(db: Session, req: CampaignRequest) -> Campaign:
    product = db.query(Product).filter(Product.sku == req.product_sku).first()
    if not product:
        raise ValueError(f"No product with SKU '{req.product_sku}'")

    recipients = (
        db.query(Customer)
        .filter(Customer.segment == req.target_segment)
        .limit(req.max_recipients)
        .all()
    )
    discounted_price_paise = round(product.price_paise * (1 - req.discount_percent / 100))
    discount_cost_per_recipient = product.price_paise - discounted_price_paise
    total_discount_exposure_paise = discount_cost_per_recipient * len(recipients)

    try:
        model = get_model()
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=[], callback_handler=None)
        prompt = (
            f"goal: {req.goal}\nproduct: {product.title} (INR {product.price_paise / 100:,.2f})\n"
            f"discount_percent: {req.discount_percent}\ndiscounted_price: INR "
            f"{discounted_price_paise / 100:,.2f}\ntarget_segment: {req.target_segment}\n"
            f"recipient_count: {len(recipients)}"
        )
        result = agent(prompt, structured_output_model=CampaignPlan)
        plan = result.structured_output
        message_copy = plan.message_copy if plan else f"{req.discount_percent}% off {product.title} - {req.goal}"
        reasoning = plan.reasoning if plan else ""
    except LLMNotConfiguredError:
        message_copy = f"{req.discount_percent}% off {product.title} for you - {req.goal}"
        reasoning = "LLM not configured - using a template offer message."

    campaign = Campaign(
        name=req.name,
        goal=req.goal,
        discount_percent=req.discount_percent,
        target_segment=req.target_segment,
        product_sku=req.product_sku,
        budget_paise=total_discount_exposure_paise,
        max_recipients=req.max_recipients,
        message_copy=message_copy,
        reasoning=reasoning,
        status="proposed",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    correlation_id = f"campaign-{campaign.id}"
    action = ProposedAction(
        actor="campaign_agent",
        action_type="launch_campaign_batch",
        amount_paise=total_discount_exposure_paise,
        currency="INR",
        description=f"Launch '{req.name}': {req.discount_percent}% off {product.title} to "
        f"{len(recipients)} '{req.target_segment}' customers",
        context={
            "discount_percent": req.discount_percent,
            "recipients": len(recipients),
            "budget_spent_today": _budget_spent_today(db),
        },
    )
    verdict = gatekeeper_evaluate(action)

    if not verdict.allow:
        campaign.status = "denied"
        campaign.reasoning = f"{campaign.reasoning}\n\nDenied by gatekeeper: {verdict.reason}".strip()
        db.commit()
        audit.record(
            db,
            action=action,
            verdict=verdict,
            correlation_id=correlation_id,
            before_state={"campaign_id": campaign.id, "status": "proposed"},
            after_state={"campaign_id": campaign.id, "status": "denied"},
        )
        return campaign

    gateway = get_gateway()
    for customer in recipients:
        link = gateway.create_payment_link(
            amount_paise=discounted_price_paise,
            currency="INR",
            description=f"{campaign.name}: {message_copy}",
            customer_name=customer.name,
            customer_email=customer.email,
            customer_contact=customer.phone,
            notes={"campaign_id": campaign.id, "sku": product.sku},
        )
        db.add(
            CampaignAction(
                campaign_id=campaign.id,
                customer_id=customer.id,
                customer_name=customer.name,
                amount_paise=discounted_price_paise,
                payment_link_url=link["short_url"],
                status="sent",
            )
        )

    campaign.status = "completed" if recipients else "completed"
    campaign.spent_paise = total_discount_exposure_paise
    db.commit()
    db.refresh(campaign)

    audit.record(
        db,
        action=action,
        verdict=verdict,
        correlation_id=correlation_id,
        before_state={"campaign_id": campaign.id, "status": "proposed"},
        after_state={"campaign_id": campaign.id, "status": campaign.status, "recipients_reached": len(recipients)},
    )
    return campaign
