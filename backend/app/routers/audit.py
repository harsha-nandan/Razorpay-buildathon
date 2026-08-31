from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import auth
from ..db import get_db
from ..models import AuditLogEntry
from ..schemas import AuditEntryOut

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(auth.get_current_seller)])


@router.get("", response_model=list[AuditEntryOut])
def list_audit(
    actor: str | None = None,
    decision: str | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc())
    if actor:
        q = q.filter(AuditLogEntry.actor == actor)
    if decision:
        q = q.filter(AuditLogEntry.decision == decision)
    return q.limit(limit).all()
