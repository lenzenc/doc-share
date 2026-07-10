import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class UploadError(BaseModel):
    filename: str
    detail: str


class UploadAck(BaseModel):
    household_id: str
    uploaded: list[DocumentOut]
    errors: list[UploadError]


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    occurred_at: datetime
    action: str
    household_id: str | None
    document_id: uuid.UUID | None
    object_key: str | None
    actor_ip: str | None
    actor_user_agent: str | None
    outcome: str
    detail: str | None
    prev_hash: str | None
    hash: str
