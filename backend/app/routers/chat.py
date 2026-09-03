from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..agents import checkout_agent
from ..db import get_db
from ..models import Customer, Order
from ..order_lifecycle import cancel_order
from ..schemas import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_id_for(customer: Customer) -> str:
    return f"cust-{customer.id}"


@router.post("/message", response_model=ChatMessageResponse)
def send_message(
    req: ChatMessageRequest,
    db: Session = Depends(get_db),
    customer: Customer = Depends(auth.get_current_customer),
):
    session_id = _session_id_for(customer)
    result = checkout_agent.run_turn(
        db,
        session_id,
        req.message,
        customer_id=customer.id,
        customer_name=customer.name,
        customer_email=customer.email,
        customer_contact=customer.phone,
    )
    return ChatMessageResponse(
        session_id=session_id, reply=result["reply"], trace=result["trace"], cart=result["cart"]
    )


@router.post("/reset")
def reset(db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    """Start a fresh chat session: clears the agent's conversation memory and
    cancels any of this session's still-unconfirmed ("created") payment
    attempts, so an abandoned checkout - browser refreshed, chat exited
    mid-payment - doesn't keep counting against max_orders_per_session. The
    cart itself is left untouched, same as after a failed payment."""
    session_id = _session_id_for(customer)
    checkout_agent.reset_session(session_id)

    pending = db.query(Order).filter(Order.session_id == session_id, Order.status == "created").all()
    for order in pending:
        cancel_order(db, order, reason="chat session reset")

    return {"status": "reset", "session_id": session_id, "cancelled_orders": len(pending)}
