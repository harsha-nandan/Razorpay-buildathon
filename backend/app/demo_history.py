"""Backdated demo history - orders, invoices, campaigns, and audit entries
spread across the last week - so the Dashboard, Orders, and Audit Trail
pages look like a real running store the instant someone opens the app,
instead of an empty shell they have to populate by hand first.

Deliberately built without any LLM calls (fast, deterministic, works with
zero keys) by constructing the same audit-log shape the real gatekeeper
produces, rather than actually invoking it.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import invoicing
from .models import AuditLogEntry, Campaign, CampaignAction, Customer, Order, Product
from .payment_failures import get_failure_detail


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _days_ago(n: int, hour: int = 11) -> datetime:
    return (datetime.now(timezone.utc) - timedelta(days=n)).replace(hour=hour, minute=0, second=0, microsecond=0)


def _order_items(products: dict[str, Product], *skus_and_qty: tuple[str, int]) -> list[dict]:
    return [
        {
            "sku": sku,
            "title": products[sku].title,
            "price_paise": products[sku].price_paise,
            "quantity": qty,
        }
        for sku, qty in skus_and_qty
    ]


def _make_order(
    db: Session,
    *,
    customer: Customer,
    items: list[dict],
    status: str,
    source: str,
    when: datetime,
    failure_code: str | None = None,
) -> Order:
    amount_paise = sum(i["price_paise"] * i["quantity"] for i in items)
    session_id = f"cust-{customer.id}"
    link_id = f"plink_demo_{_uid()}"
    order = Order(
        id=_uid(),
        session_id=session_id,
        source=source,
        razorpay_payment_link_id=link_id,
        razorpay_payment_link_url=f"https://rzp.io/mock/{link_id}",
        amount_paise=amount_paise,
        status=status,
        items=items,
        created_at=when,
    )
    if status == "failed" and failure_code:
        detail = get_failure_detail(failure_code)
        order.failure_code = detail.code
        order.failure_reason = detail.reason
        order.failure_remedy = detail.remedy
    db.add(order)
    db.flush()

    correlation_id = _uid()
    if status in ("created", "paid"):
        db.add(
            AuditLogEntry(
                id=_uid(),
                timestamp=when,
                correlation_id=correlation_id,
                actor=source,
                action_type="create_payment_link",
                description=f"Checkout for {len(items)} item(s), session {session_id}",
                amount_paise=amount_paise,
                decision="allow",
                decided_by="rule_engine+llm_gatekeeper",
                reasoning="Within all configured hard bounds. No manipulative copy or abusive pattern detected.",
                policy_refs=["max_single_order_paise=500000", "max_orders_per_session=5"],
                before_state={"cart": items},
                after_state={"order_id": order.id, "payment_link_id": link_id, "status": "created"},
            )
        )
    if status == "paid":
        invoicing.issue_invoice(db, order, customer_name=customer.name, customer_email=customer.email)
        db.add(
            AuditLogEntry(
                id=_uid(),
                timestamp=when + timedelta(minutes=6),
                correlation_id=correlation_id,
                actor=source,
                action_type="payment_confirmed",
                description=f"Payment confirmed for order {order.id}",
                amount_paise=amount_paise,
                decision="n/a",
                decided_by="n/a",
                reasoning="",
                policy_refs=[],
                before_state={"status": "created"},
                after_state={"status": "paid", "invoice_issued": True},
            )
        )
    elif status == "failed":
        detail = get_failure_detail(failure_code)
        db.add(
            AuditLogEntry(
                id=_uid(),
                timestamp=when + timedelta(minutes=4),
                correlation_id=correlation_id,
                actor=source,
                action_type="payment_failed",
                description=f"Payment declined for order {order.id} ({detail.code}) - cart preserved for retry",
                amount_paise=amount_paise,
                decision="n/a",
                decided_by="n/a",
                reasoning=f"{detail.reason} Remedy: {detail.remedy}",
                policy_refs=[],
                before_state={"status": "created"},
                after_state={"status": "failed", "failure_code": detail.code},
            )
        )
    elif status == "denied":
        db.add(
            AuditLogEntry(
                id=_uid(),
                timestamp=when,
                correlation_id=correlation_id,
                actor=source,
                action_type="create_payment_link",
                description=f"Checkout for {len(items)} item(s), session {session_id}",
                amount_paise=amount_paise,
                decision="deny",
                decided_by="rule_engine",
                reasoning=f"Order amount ₹{amount_paise / 100:,.2f} exceeds the per-order cap of ₹5,000.00.",
                policy_refs=["max_single_order_paise=500000"],
                before_state={"cart": items},
                after_state={"order_id": order.id, "status": "denied"},
            )
        )
    return order


def seed_demo_history(db: Session) -> None:
    if db.query(Order).count() > 0:
        return

    products = {p.sku: p for p in db.query(Product).all()}
    customers = {c.email: c for c in db.query(Customer).all()}
    if not products or not customers:
        return

    ananya = customers["ananya.rao@example.com"]
    rohit = customers["rohit.verma@example.com"]
    meera = customers["meera.iyer@example.com"]
    kabir = customers["kabir.shah@example.com"]
    priya = customers["priya.nair@example.com"]
    devansh = customers["devansh.gupta@example.com"]
    sara = customers["sara.khan@example.com"]
    arjun = customers["arjun.menon@example.com"]

    # --- Day -6 ---
    _make_order(db, customer=ananya, items=_order_items(products, ("EARBUDS-01", 1)), status="paid", source="checkout_agent", when=_days_ago(6, 10))
    _make_order(db, customer=rohit, items=_order_items(products, ("POWERBANK-01", 1)), status="paid", source="ai_buyer", when=_days_ago(6, 15))

    # --- Day -5: watch + upsell, and a failure followed by a successful retry ---
    _make_order(db, customer=rohit, items=_order_items(products, ("WATCH-01", 1), ("WATCHBAND-01", 1)), status="paid", source="checkout_agent", when=_days_ago(5, 9))
    _make_order(db, customer=meera, items=_order_items(products, ("SPEAKER-01", 1)), status="failed", source="checkout_agent", when=_days_ago(5, 14), failure_code="insufficient_funds")
    _make_order(db, customer=meera, items=_order_items(products, ("SPEAKER-01", 1)), status="paid", source="checkout_agent", when=_days_ago(5, 14) + timedelta(minutes=20))

    # --- Day -4: AI buyer purchase, and a hard-bound denial (cart too large) ---
    _make_order(db, customer=priya, items=_order_items(products, ("KEYBOARD-01", 1)), status="paid", source="ai_buyer", when=_days_ago(4, 11))
    _make_order(db, customer=kabir, items=_order_items(products, ("KEYBOARD-01", 10)), status="denied", source="checkout_agent", when=_days_ago(4, 16))

    # --- Day -3: campaign-driven purchase ---
    _make_order(db, customer=priya, items=_order_items(products, ("CASE-EARBUDS-01", 1), ("EARBUDS-01", 1)), status="paid", source="checkout_agent", when=_days_ago(3, 10))
    _make_order(db, customer=sara, items=_order_items(products, ("WATCH-01", 1)), status="paid", source="campaign_agent", when=_days_ago(3, 13))

    # --- Day -2: an abandoned failure (no retry), and a second AI-buyer denial ---
    _make_order(db, customer=devansh, items=_order_items(products, ("WATCH-01", 1)), status="failed", source="checkout_agent", when=_days_ago(2, 12), failure_code="card_declined_by_issuer")
    _make_order(db, customer=arjun, items=_order_items(products, ("SPEAKER-01", 1), ("KEYBOARD-01", 1)), status="denied", source="ai_buyer", when=_days_ago(2, 17))

    # --- Day -1 ---
    _make_order(db, customer=arjun, items=_order_items(products, ("POWERBANK-01", 1), ("SLEEVE-01", 1)), status="paid", source="checkout_agent", when=_days_ago(1, 10))
    _make_order(db, customer=ananya, items=_order_items(products, ("KEYBOARD-01", 1)), status="paid", source="checkout_agent", when=_days_ago(1, 15))

    # --- Today ---
    _make_order(db, customer=devansh, items=_order_items(products, ("EARBUDS-01", 1)), status="paid", source="ai_buyer", when=_days_ago(0, 9))

    # --- Campaigns: two approved, one denied for exceeding the discount cap ---
    vip_campaign = Campaign(
        id=_uid(),
        name="VIP Early Access: Chrono Smartwatch",
        goal="Reward VIP customers with early access pricing to drive repeat high-value purchases.",
        discount_percent=15,
        target_segment="vip",
        product_sku="WATCH-01",
        budget_paise=0,
        max_recipients=10,
        status="completed",
        message_copy="VIP early access: 15% off the Chrono Smartwatch, this week only.",
        reasoning="VIP customers have the highest lifetime value - a modest discount on a premium product should "
        "lift repeat purchase rate without eroding margin much.",
        created_at=_days_ago(3, 9),
    )
    watch_price = products["WATCH-01"].price_paise
    watch_discounted = round(watch_price * 0.85)
    watch_discount_cost = watch_price - watch_discounted
    vip_campaign.spent_paise = watch_discount_cost * 2
    db.add(vip_campaign)
    db.flush()
    for cust in (ananya, sara):
        db.add(
            CampaignAction(
                id=_uid(),
                campaign_id=vip_campaign.id,
                customer_id=cust.id,
                customer_name=cust.name,
                amount_paise=watch_discounted,
                payment_link_url=f"https://rzp.io/mock/plink_demo_{_uid()}",
                status="sent",
                created_at=_days_ago(3, 9),
            )
        )
    db.add(
        AuditLogEntry(
            id=_uid(),
            timestamp=_days_ago(3, 9),
            correlation_id=_uid(),
            actor="campaign_agent",
            action_type="launch_campaign_batch",
            description=f"Launch 'VIP Early Access: Chrono Smartwatch': 15% off to 2 'vip' customers",
            amount_paise=vip_campaign.spent_paise,
            decision="allow",
            decided_by="rule_engine+llm_gatekeeper",
            reasoning="Within discount and budget caps; offer copy is honest and non-manipulative.",
            policy_refs=["max_discount_percent=40", "daily_campaign_budget_paise=2000000"],
            before_state={"campaign_id": vip_campaign.id, "status": "proposed"},
            after_state={"campaign_id": vip_campaign.id, "status": "completed", "recipients_reached": 2},
        )
    )

    winback_campaign = Campaign(
        id=_uid(),
        name="Winback: Lapsed Customers",
        goal="Re-engage customers who haven't ordered in a while with a meaningful discount.",
        discount_percent=20,
        target_segment="lapsed",
        product_sku="POWERBANK-01",
        budget_paise=0,
        max_recipients=10,
        status="completed",
        message_copy="We miss you - 20% off the Volt Power Bank, just for you.",
        reasoning="Lapsed customers respond better to a clear, meaningful discount than a token gesture.",
        created_at=_days_ago(2, 9),
    )
    pb_price = products["POWERBANK-01"].price_paise
    pb_discounted = round(pb_price * 0.80)
    pb_discount_cost = pb_price - pb_discounted
    winback_campaign.spent_paise = pb_discount_cost * 2
    db.add(winback_campaign)
    db.flush()
    for cust in (devansh, arjun):
        db.add(
            CampaignAction(
                id=_uid(),
                campaign_id=winback_campaign.id,
                customer_id=cust.id,
                customer_name=cust.name,
                amount_paise=pb_discounted,
                payment_link_url=f"https://rzp.io/mock/plink_demo_{_uid()}",
                status="sent",
                created_at=_days_ago(2, 9),
            )
        )
    db.add(
        AuditLogEntry(
            id=_uid(),
            timestamp=_days_ago(2, 9),
            correlation_id=_uid(),
            actor="campaign_agent",
            action_type="launch_campaign_batch",
            description="Launch 'Winback: Lapsed Customers': 20% off to 2 'lapsed' customers",
            amount_paise=winback_campaign.spent_paise,
            decision="allow",
            decided_by="rule_engine+llm_gatekeeper",
            reasoning="Within discount and budget caps; targets a segment with clear re-engagement upside.",
            policy_refs=["max_discount_percent=40", "daily_campaign_budget_paise=2000000"],
            before_state={"campaign_id": winback_campaign.id, "status": "proposed"},
            after_state={"campaign_id": winback_campaign.id, "status": "completed", "recipients_reached": 2},
        )
    )

    denied_campaign = Campaign(
        id=_uid(),
        name="Flash 60% Off Keyboards",
        goal="Clear keyboard inventory fast with an aggressive discount.",
        discount_percent=60,
        target_segment="general",
        product_sku="KEYBOARD-01",
        budget_paise=0,
        max_recipients=25,
        status="denied",
        message_copy="",
        reasoning="Denied by gatekeeper: Discount of 60% exceeds the max allowed 40%.",
        created_at=_days_ago(1, 9),
    )
    db.add(denied_campaign)
    db.flush()
    db.add(
        AuditLogEntry(
            id=_uid(),
            timestamp=_days_ago(1, 9),
            correlation_id=_uid(),
            actor="campaign_agent",
            action_type="launch_campaign_batch",
            description="Launch 'Flash 60% Off Keyboards': 60% off to up to 25 'general' customers",
            amount_paise=0,
            decision="deny",
            decided_by="rule_engine",
            reasoning="Discount of 60% exceeds the max allowed 40%.",
            policy_refs=["max_discount_percent=40"],
            before_state={"campaign_id": denied_campaign.id, "status": "proposed"},
            after_state={"campaign_id": denied_campaign.id, "status": "denied"},
        )
    )

    db.commit()
