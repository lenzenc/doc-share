"""Tamper-evident audit trail.

Implements the "audit-trail alternative" to WORM storage added by the 2023
amendment to SEC Rule 17a-4 / FINRA Rule 4511 (see README's "Audit trail"
section for the regulatory context). Instead of physically immutable
storage, records are kept on ordinary Postgres, but every action against a
document is appended as an AuditEvent row, and rows are hash-chained so that
altering, deleting, or reordering any historical row is detectable.

No code path in this module ever updates or deletes an AuditEvent row.

Honest limitation: this app has no authentication, so there is no
authenticated "individual" to attribute events to. The best available actor
signals are captured instead: the client-supplied household_id (an
UNTRUSTED claim, not a verified identity) and network identity (IP, user
agent) from the request.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AuditEvent

logger = logging.getLogger(__name__)

# Arbitrary fixed key for the Postgres advisory lock used to serialize
# appenders. Any int64 constant works; it just needs to be consistent.
_CHAIN_LOCK_KEY = 741_100_733


def extract_actor(request: Request) -> tuple[str | None, str | None]:
    """Best-effort actor network identity from the request.

    Prefers X-Forwarded-For (first hop) / X-Real-IP in case the API is ever
    run behind a proxy, falling back to the direct peer address.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        real_ip = request.headers.get("x-real-ip")
        ip = real_ip.strip() if real_ip else (request.client.host if request.client else None)

    user_agent = request.headers.get("user-agent")
    return ip, user_agent


def _canonical(fields: dict) -> str:
    """Deterministic serialization fed into the hash. Sorted keys and a
    fixed separator so the same logical event always hashes the same way."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(fields: dict) -> str:
    return hashlib.sha256(_canonical(fields).encode("utf-8")).hexdigest()


def record_event(
    db: Session,
    *,
    action: str,
    outcome: str,
    request: Request,
    household_id: str | None = None,
    document_id: uuid.UUID | None = None,
    object_key: str | None = None,
    detail: str | None = None,
) -> AuditEvent:
    """Append one audit event, chained to the current tail.

    Caller controls the transaction (db.commit()); this only adds/flushes so
    the event can share the request's transaction (e.g. atomic with the
    Document row it describes on upload).

    A Postgres advisory transaction lock serializes concurrent appenders so
    two in-flight requests can't both read the same tail and compute
    conflicting seq/prev_hash values.
    """
    db.execute(select(func.pg_advisory_xact_lock(_CHAIN_LOCK_KEY)))

    tail = db.execute(
        select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1)
    ).scalar_one_or_none()
    seq = (tail.seq + 1) if tail else 1
    prev_hash = tail.hash if tail else None

    occurred_at = datetime.now(timezone.utc)
    actor_ip, actor_user_agent = extract_actor(request)

    fields = {
        "seq": seq,
        "occurred_at": occurred_at.isoformat(),
        "action": action,
        "household_id": household_id,
        "document_id": str(document_id) if document_id else None,
        "object_key": object_key,
        "actor_ip": actor_ip,
        "actor_user_agent": actor_user_agent,
        "outcome": outcome,
        "detail": detail,
        "prev_hash": prev_hash,
    }
    event_hash = _compute_hash(fields)

    event = AuditEvent(
        seq=seq,
        occurred_at=occurred_at,
        action=action,
        household_id=household_id,
        document_id=document_id,
        object_key=object_key,
        actor_ip=actor_ip,
        actor_user_agent=actor_user_agent,
        outcome=outcome,
        detail=detail,
        prev_hash=prev_hash,
        hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def record_read_event(
    db: Session,
    settings: Settings,
    *,
    action: str,
    outcome: str,
    request: Request,
    household_id: str | None = None,
    document_id: uuid.UUID | None = None,
    object_key: str | None = None,
    detail: str | None = None,
) -> AuditEvent | None:
    """Record + commit an audit event for a read (list/download) as its own
    unit of work, honoring settings.audit_fail_closed:

    - fail-closed (default): a write failure propagates, failing the request
      rather than serving an access that was never logged.
    - fail-open: the failure is swallowed and logged; the caller's response
      still goes out.

    Returns the event, or None if the write failed under fail-open.
    """
    try:
        event = record_event(
            db,
            action=action,
            outcome=outcome,
            request=request,
            household_id=household_id,
            document_id=document_id,
            object_key=object_key,
            detail=detail,
        )
        db.commit()
        return event
    except Exception:
        db.rollback()
        if settings.audit_fail_closed:
            raise
        logger.warning(
            "audit event write failed for action=%s; serving response anyway "
            "because audit_fail_closed=False",
            action,
            exc_info=True,
        )
        return None


@dataclass
class VerifyResult:
    ok: bool
    count: int
    first_bad_seq: int | None
    reason: str | None


def verify_chain(db: Session) -> VerifyResult:
    """Walk the full chain in seq order, recomputing each hash and checking
    seq contiguity + prev_hash linkage. Returns as soon as a break is found."""
    events = db.execute(select(AuditEvent).order_by(AuditEvent.seq.asc())).scalars().all()

    expected_seq = 1
    expected_prev_hash: str | None = None

    for event in events:
        if event.seq != expected_seq:
            return VerifyResult(
                ok=False,
                count=len(events),
                first_bad_seq=event.seq,
                reason=f"expected seq {expected_seq}, found {event.seq} (row missing or reordered)",
            )
        if event.prev_hash != expected_prev_hash:
            return VerifyResult(
                ok=False,
                count=len(events),
                first_bad_seq=event.seq,
                reason=f"prev_hash mismatch at seq {event.seq} (chain broken before this row)",
            )

        fields = {
            "seq": event.seq,
            "occurred_at": event.occurred_at.isoformat(),
            "action": event.action,
            "household_id": event.household_id,
            "document_id": str(event.document_id) if event.document_id else None,
            "object_key": event.object_key,
            "actor_ip": event.actor_ip,
            "actor_user_agent": event.actor_user_agent,
            "outcome": event.outcome,
            "detail": event.detail,
            "prev_hash": event.prev_hash,
        }
        recomputed = _compute_hash(fields)
        if recomputed != event.hash:
            return VerifyResult(
                ok=False,
                count=len(events),
                first_bad_seq=event.seq,
                reason=f"hash mismatch at seq {event.seq} (row contents modified after creation)",
            )

        expected_seq += 1
        expected_prev_hash = event.hash

    return VerifyResult(ok=True, count=len(events), first_bad_seq=None, reason=None)
