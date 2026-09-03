from datetime import datetime

from pydantic import BaseModel, Field


class CustomerRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str = ""


class SellerRegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    role: str
    profile: dict


class ChatMessageRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    trace: list[dict] = Field(default_factory=list)
    cart: list[dict] = Field(default_factory=list)


class CampaignRequest(BaseModel):
    name: str
    goal: str
    discount_percent: int
    target_segment: str = "repeat"
    product_sku: str
    max_recipients: int = 10


class AIBuyerRequest(BaseModel):
    intent: str
    budget_paise: int | None = None
    mandate_id: str | None = None


class MandateCreateRequest(BaseModel):
    label: str
    max_amount_paise: int
    period: str = "total"  # daily | weekly | monthly | total


class SimulatePaymentRequest(BaseModel):
    order_id: str
    outcome: str = "paid"  # "paid" | "failed"
    failure_code: str | None = None  # only used when outcome == "failed"; see payment_failures.py


class CampaignPlan(BaseModel):
    message_copy: str = Field(description="Short, honest customer-facing offer message (<220 chars).")
    reasoning: str = Field(description="One or two sentences on why this campaign should grow revenue.")


class GatekeeperDecision(BaseModel):
    allow: bool
    reason: str
    risk_flags: list[str] = Field(default_factory=list)


class InvoiceOut(BaseModel):
    id: str
    order_id: str
    invoice_number: str
    subtotal_paise: int
    tax_paise: int
    total_paise: int
    currency: str
    customer_name: str
    customer_email: str
    items: list[dict]
    issued_at: datetime

    model_config = {"from_attributes": True}


class AuditEntryOut(BaseModel):
    id: str
    timestamp: datetime
    correlation_id: str
    actor: str
    action_type: str
    description: str
    amount_paise: int
    decision: str
    decided_by: str
    reasoning: str
    policy_refs: list[str]
    before_state: dict
    after_state: dict

    model_config = {"from_attributes": True}
