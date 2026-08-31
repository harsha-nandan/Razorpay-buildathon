import uuid

from sqlalchemy.orm import Session

from .gatekeeper.gatekeeper import GatekeeperVerdict
from .gatekeeper.policy import ProposedAction
from .models import AuditLogEntry


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def record(
    db: Session,
    *,
    action: ProposedAction,
    verdict: GatekeeperVerdict,
    correlation_id: str,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        correlation_id=correlation_id,
        actor=action.actor,
        action_type=action.action_type,
        description=action.description,
        amount_paise=action.amount_paise,
        decision="allow" if verdict.allow else "deny",
        decided_by=verdict.decided_by,
        reasoning=verdict.reason,
        policy_refs=verdict.policy_refs,
        before_state=before_state or {},
        after_state=after_state or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def record_info(
    db: Session,
    *,
    actor: str,
    action_type: str,
    description: str,
    correlation_id: str,
    amount_paise: int = 0,
    reasoning: str = "",
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> AuditLogEntry:
    """Record a non-gated informational step (e.g. a catalog search, or a
    payment outcome) so the full trace is reconstructable, not just the
    upfront money decisions."""
    entry = AuditLogEntry(
        correlation_id=correlation_id,
        actor=actor,
        action_type=action_type,
        description=description,
        amount_paise=amount_paise,
        decision="n/a",
        decided_by="n/a",
        reasoning=reasoning,
        policy_refs=[],
        before_state=before_state or {},
        after_state=after_state or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
