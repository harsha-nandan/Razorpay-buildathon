from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, mandates as mandate_math
from ..db import get_db
from ..models import Customer, Mandate
from ..schemas import MandateCreateRequest

router = APIRouter(prefix="/mandates", tags=["mandates"])

VALID_PERIODS = {"daily", "weekly", "monthly", "total"}


def _mandate_out(db: Session, m: Mandate) -> dict:
    remaining = mandate_math.remaining_paise(db, m)
    return {
        "id": m.id,
        "label": m.label,
        "max_amount_paise": m.max_amount_paise,
        "period": m.period,
        "active": m.active,
        "spent_paise": m.max_amount_paise - remaining,
        "remaining_paise": remaining,
        "created_at": m.created_at,
    }


@router.get("")
def list_mandates(db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)):
    rows = db.query(Mandate).filter(Mandate.customer_id == customer.id).order_by(Mandate.created_at.desc()).all()
    return [_mandate_out(db, m) for m in rows]


@router.post("")
def create_mandate(
    req: MandateCreateRequest, db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)
):
    if req.period not in VALID_PERIODS:
        raise HTTPException(400, f"period must be one of {sorted(VALID_PERIODS)}")
    if req.max_amount_paise <= 0:
        raise HTTPException(400, "max_amount_paise must be positive")
    mandate = Mandate(
        customer_id=customer.id, label=req.label, max_amount_paise=req.max_amount_paise, period=req.period
    )
    db.add(mandate)
    db.commit()
    db.refresh(mandate)
    return _mandate_out(db, mandate)


@router.delete("/{mandate_id}")
def revoke_mandate(
    mandate_id: str, db: Session = Depends(get_db), customer: Customer = Depends(auth.get_current_customer)
):
    mandate = db.get(Mandate, mandate_id)
    if not mandate or mandate.customer_id != customer.id:
        raise HTTPException(404, "mandate not found")
    mandate.active = False
    db.commit()
    db.refresh(mandate)
    return _mandate_out(db, mandate)
