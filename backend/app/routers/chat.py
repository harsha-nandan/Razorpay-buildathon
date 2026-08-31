from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..agents import checkout_agent
from ..db import get_db
from ..models import Customer
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
        customer_name=customer.name,
        customer_email=customer.email,
        customer_contact=customer.phone,
    )
    return ChatMessageResponse(
        session_id=session_id, reply=result["reply"], trace=result["trace"], cart=result["cart"]
    )


@router.post("/reset")
def reset(customer: Customer = Depends(auth.get_current_customer)):
    session_id = _session_id_for(customer)
    checkout_agent.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}
