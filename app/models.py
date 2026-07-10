import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    household_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bucket: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    """One immutable row per action taken against a document (or a rejected
    attempt). Never updated or deleted by any code path — see app/audit.py.

    Rows form a hash chain (`prev_hash` -> `hash`) so that any modification,
    deletion, or reordering of a historical row is detectable via
    verify_chain(), without requiring physically WORM storage. This is the
    "audit-trail alternative" to WORM added by the 2023 amendment to SEC
    Rule 17a-4 (see README's Audit trail section).
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    seq: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    household_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    object_key: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str | None] = mapped_column(String, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
