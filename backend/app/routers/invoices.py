from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth
from ..db import get_db
from ..models import Customer, Invoice, Order, Seller
from ..schemas import InvoiceOut

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/mine", response_model=list[InvoiceOut])
def my_invoices(db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    session_id = f"cust-{customer.id}"
    return (
        db.query(Invoice)
        .join(Order, Invoice.order_id == Order.id)
        .filter(Order.session_id == session_id)
        .order_by(Invoice.issued_at.desc())
        .all()
    )


@router.get("", response_model=list[InvoiceOut])
def all_invoices(db: Session = Depends(get_db), _seller: Seller = Depends(auth.get_current_seller)):
    return db.query(Invoice).order_by(Invoice.issued_at.desc()).all()


@router.get("/by-order/{order_id}", response_model=InvoiceOut)
def invoice_for_order(order_id: str, db: Session = Depends(get_db), principal=Depends(auth.get_current_principal)):
    role, who = principal
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if not invoice:
        raise HTTPException(404, "No invoice for this order yet.")
    if role == "customer":
        order = db.get(Order, order_id)
        if not order or order.session_id != f"cust-{who.id}":
            raise HTTPException(403, "This invoice does not belong to you.")
    return invoice
