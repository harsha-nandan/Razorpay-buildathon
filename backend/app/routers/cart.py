from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..agents import cart as cart_ops
from ..db import get_db
from ..models import Customer

router = APIRouter(prefix="/cart", tags=["cart"])


def _session_id_for(customer: Customer) -> str:
    return f"cust-{customer.id}"


@router.get("")
def get_cart(db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    items = cart_ops.get_cart(db, _session_id_for(customer))
    return {"cart": items, "subtotal_paise": cart_ops.cart_total_paise(items)}


@router.delete("/{sku}")
def remove_item(sku: str, db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    """Direct cart removal, bypassing the chat agent entirely - a quick UI
    action shouldn't have to wait on an LLM round-trip."""
    session_id = _session_id_for(customer)
    items = [i for i in cart_ops.get_cart(db, session_id) if i["sku"] != sku]
    cart_ops.save_cart(db, session_id, items)
    return {"cart": items, "subtotal_paise": cart_ops.cart_total_paise(items)}
