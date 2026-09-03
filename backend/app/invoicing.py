"""Invoice issuance - fires exactly once, the moment a payment is confirmed
paid. Idempotent: calling it twice for the same order returns the existing
invoice rather than double-billing.

Amounts on the order are treated as GST-inclusive (standard Razorpay/India
convention) and broken back out into subtotal + tax for the printed invoice.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import Invoice, Order

GST_RATE = 0.18


def _next_invoice_number(db: Session) -> str:
    # Derived from the highest existing number this year, not a row count -
    # a count drifts out of sync (and starts colliding with real numbers)
    # the moment any invoice is ever deleted, since deleting one leaves a
    # gap that count+1 doesn't account for.
    year = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"
    highest = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    next_seq = int(highest[0].removeprefix(prefix)) + 1 if highest else 1
    return f"{prefix}{next_seq:05d}"


def issue_invoice(db: Session, order: Order, customer_name: str = "", customer_email: str = "") -> Invoice:
    existing = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    if existing:
        return existing

    total = order.amount_paise
    subtotal = round(total / (1 + GST_RATE))
    tax = total - subtotal

    invoice = Invoice(
        order_id=order.id,
        invoice_number=_next_invoice_number(db),
        subtotal_paise=subtotal,
        tax_paise=tax,
        total_paise=total,
        currency=order.currency,
        customer_name=customer_name,
        customer_email=customer_email,
        items=order.items,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
