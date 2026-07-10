from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditEvent
from app.schemas import AuditEventOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(household_id: str, db: Session = Depends(get_db)) -> list[AuditEventOut]:
    """Produce a household's audit trail, newest first. Read-only — this
    endpoint itself is intentionally not audited to avoid an infinite
    regress of "someone viewed the audit log" events for every trail view."""
    household_id = household_id.strip()
    if not household_id:
        raise HTTPException(status_code=400, detail="household_id is required")

    stmt = (
        select(AuditEvent)
        .where(AuditEvent.household_id == household_id)
        .order_by(AuditEvent.seq.desc())
    )
    events = db.execute(stmt).scalars().all()
    return [AuditEventOut.model_validate(event) for event in events]
