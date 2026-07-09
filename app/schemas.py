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
