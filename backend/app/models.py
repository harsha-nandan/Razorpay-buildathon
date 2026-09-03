import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    price_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="INR")
    image_url: Mapped[str] = mapped_column(String, default="")
    in_stock: Mapped[bool] = mapped_column(default=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    complements: Mapped[list] = mapped_column(JSON, default=list)  # SKUs suggested as cross-sell
    rating: Mapped[float] = mapped_column(Float, default=0.0)  # 0-5 stars
    review_count: Mapped[int] = mapped_column(Integer, default=0)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    segment: Mapped[str] = mapped_column(String, index=True, default="general")
    lifetime_value_paise: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CartSession(Base):
    __tablename__ = "cart_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    items: Mapped[list] = mapped_column(JSON, default=list)  # [{sku, title, price_paise, quantity}]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Mandate(Base):
    """A customer-issued, self-imposed spending authorization for an
    autonomous agent (the AI buyer) acting on their behalf - the same
    mechanism NPCI's UAP / AP2 describe: an agent may act, but only within a
    limit the human explicitly pre-authorized. Checked by the gatekeeper in
    addition to (never instead of) the merchant's own policy bounds."""

    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    label: Mapped[str] = mapped_column(String)
    max_amount_paise: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String, default="total")  # daily | weekly | monthly | total
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, default="checkout_agent")  # checkout_agent | ai_buyer | campaign_agent
    razorpay_order_id: Mapped[str] = mapped_column(String, default="")
    razorpay_payment_link_id: Mapped[str] = mapped_column(String, default="")
    razorpay_payment_link_url: Mapped[str] = mapped_column(String, default="")
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="INR")
    status: Mapped[str] = mapped_column(String, default="created")  # created|paid|failed|denied|cancelled
    items: Mapped[list] = mapped_column(JSON, default=list)
    upsell_accepted: Mapped[list] = mapped_column(JSON, default=list)
    failure_code: Mapped[str] = mapped_column(String, default="")
    failure_reason: Mapped[str] = mapped_column(String, default="")
    failure_remedy: Mapped[str] = mapped_column(String, default="")
    mandate_id: Mapped[str | None] = mapped_column(ForeignKey("mandates.id"), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Only ever set for source="ai_buyer" - the natural-language ask that led
    # to this order, so the AI Buyer Simulator's run history can show it
    # without a customer identity to key off of (that flow is intentionally
    # unauthenticated - see agents/ai_buyer.py).
    buyer_intent: Mapped[str] = mapped_column(String, default="")
    requested_budget_paise: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)


class Invoice(Base):
    """Issued exactly once, the moment an order's payment is confirmed paid.
    Never issued for denied or failed orders - there's nothing to bill."""

    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    subtotal_paise: Mapped[int] = mapped_column(Integer)
    tax_paise: Mapped[int] = mapped_column(Integer)
    total_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="INR")
    customer_name: Mapped[str] = mapped_column(String, default="")
    customer_email: Mapped[str] = mapped_column(String, default="")
    items: Mapped[list] = mapped_column(JSON, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["Order"] = relationship()


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    goal: Mapped[str] = mapped_column(String, default="")
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    target_segment: Mapped[str] = mapped_column(String, default="repeat")
    product_sku: Mapped[str] = mapped_column(String, default="")
    budget_paise: Mapped[int] = mapped_column(Integer, default=0)
    max_recipients: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="proposed")  # proposed|denied|completed|cancelled
    message_copy: Mapped[str] = mapped_column(String, default="")
    reasoning: Mapped[str] = mapped_column(String, default="")
    spent_paise: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    actions: Mapped[list["CampaignAction"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignAction(Base):
    __tablename__ = "campaign_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    customer_id: Mapped[str] = mapped_column(String)
    customer_name: Mapped[str] = mapped_column(String)
    amount_paise: Mapped[int] = mapped_column(Integer)
    payment_link_url: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    campaign: Mapped["Campaign"] = relationship(back_populates="actions")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    correlation_id: Mapped[str] = mapped_column(String, index=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String, index=True)  # checkout_agent|upsell_agent|campaign_agent|ai_buyer
    action_type: Mapped[str] = mapped_column(String, index=True)  # create_order|create_payment_link|launch_campaign...
    description: Mapped[str] = mapped_column(String, default="")
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str] = mapped_column(String, default="n/a")  # allow|deny|n/a
    decided_by: Mapped[str] = mapped_column(String, default="rule_engine")  # rule_engine|llm_gatekeeper
    reasoning: Mapped[str] = mapped_column(String, default="")
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)
    before_state: Mapped[dict] = mapped_column(JSON, default=dict)
    after_state: Mapped[dict] = mapped_column(JSON, default=dict)
