"""Static info about the payment methods/card networks this merchant
accepts via Razorpay - offers and EMI eligibility for the checkout agent to
explain once a shopper names their card. Offers are structured (percent +
cap) so they can be computed against the shopper's actual cart total rather
than shown as generic marketing text. Purely informational (network,
offers, EMI plans); never a place to collect an actual card number/CVV/
expiry. Those are entered on Razorpay's own hosted payment link page, which
this app's chat agent never sees or touches - that's the whole point of
using payment links instead of a raw card form.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Offer:
    label: str
    kind: str  # "discount" (reduces amount paid now) | "cashback" (credited after payment)
    percent: float
    max_amount_paise: int = 0  # 0 = uncapped


@dataclass(frozen=True)
class EmiPlan:
    tenure_months: int
    interest_rate_percent: float  # 0 = no-cost EMI, bank/merchant-subsidized


@dataclass(frozen=True)
class PaymentMethodInfo:
    network: str
    accepted: bool
    offers: list[Offer] = field(default_factory=list)
    emi_available: bool = False
    emi_min_order_paise: int = 0
    emi_plans: list[EmiPlan] = field(default_factory=list)
    notes: str = ""


PAYMENT_METHODS: dict[str, PaymentMethodInfo] = {
    "visa": PaymentMethodInfo(
        network="Visa",
        accepted=True,
        offers=[
            Offer(label="Instant discount this week", kind="discount", percent=5, max_amount_paise=50000),
            Offer(label="HDFC Visa cashback", kind="cashback", percent=2),
        ],
        emi_available=True,
        emi_min_order_paise=300000,  # INR 3,000
        emi_plans=[
            EmiPlan(tenure_months=3, interest_rate_percent=0),
            EmiPlan(tenure_months=6, interest_rate_percent=13),
            EmiPlan(tenure_months=9, interest_rate_percent=13),
        ],
        notes="No-cost EMI on the 3-month plan; 6/9-month plans carry standard bank interest.",
    ),
    "mastercard": PaymentMethodInfo(
        network="Mastercard",
        accepted=True,
        offers=[Offer(label="ICICI Mastercard discount", kind="discount", percent=10, max_amount_paise=50000)],
        emi_available=True,
        emi_min_order_paise=300000,
        emi_plans=[
            EmiPlan(tenure_months=3, interest_rate_percent=0),
            EmiPlan(tenure_months=6, interest_rate_percent=0),
        ],
        notes="Both EMI tenures are no-cost (0% interest), merchant-subsidized.",
    ),
    "rupay": PaymentMethodInfo(
        network="RuPay",
        accepted=True,
        offers=[Offer(label="RuPay cashback, credited within 7 days", kind="cashback", percent=2)],
        emi_available=True,
        emi_min_order_paise=500000,  # INR 5,000
        emi_plans=[
            EmiPlan(tenure_months=3, interest_rate_percent=14),
            EmiPlan(tenure_months=6, interest_rate_percent=14),
            EmiPlan(tenure_months=12, interest_rate_percent=14),
        ],
        notes="EMI needs a minimum order of INR 5,000; standard bank interest applies on all tenures.",
    ),
    "amex": PaymentMethodInfo(
        network="American Express",
        accepted=True,
        offers=[],
        emi_available=True,
        emi_min_order_paise=1000000,  # INR 10,000
        emi_plans=[
            EmiPlan(tenure_months=6, interest_rate_percent=15),
            EmiPlan(tenure_months=12, interest_rate_percent=15),
        ],
        notes="Standard Amex Membership Rewards points apply - no extra merchant offer right now. "
        "Amex EMI needs a higher minimum order (INR 10,000) than other networks.",
    ),
    "upi": PaymentMethodInfo(
        network="UPI",
        accepted=True,
        offers=[],
        emi_available=False,
        notes="Instant payment, no card needed. No EMI on UPI - it's a direct debit, not a credit line.",
    ),
    "netbanking": PaymentMethodInfo(
        network="Netbanking",
        accepted=True,
        offers=[],
        emi_available=False,
        notes="Direct bank transfer for all major Indian banks - no EMI or card offers apply.",
    ),
    "diners": PaymentMethodInfo(network="Diners Club", accepted=False, notes="Not currently accepted by this merchant."),
}


def describe(network: str = "") -> list[PaymentMethodInfo]:
    key = network.strip().lower()
    if not key:
        return list(PAYMENT_METHODS.values())
    for name, info in PAYMENT_METHODS.items():
        if name in key or key in name:
            return [info]
    return [
        PaymentMethodInfo(
            network=network,
            accepted=False,
            notes="Not a recognized network - accepted options are Visa, Mastercard, RuPay, Amex, UPI, and netbanking.",
        )
    ]


def compute_offer(offer: Offer, subtotal_paise: int) -> dict:
    """Apply an offer's percent/cap against a real cart subtotal, returning
    the actual rupee amounts instead of a generic "X% off" description."""
    raw_amount = round(subtotal_paise * offer.percent / 100)
    amount_paise = min(raw_amount, offer.max_amount_paise) if offer.max_amount_paise else raw_amount
    price_after_paise = subtotal_paise - amount_paise if offer.kind == "discount" else subtotal_paise
    return {
        "label": offer.label,
        "kind": offer.kind,
        "percent": offer.percent,
        "amount_paise": amount_paise,
        "price_after_paise": price_after_paise,
    }
