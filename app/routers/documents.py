import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.config import Settings, get_settings
from app.database import get_db
from app.models import Document
from app.schemas import DocumentOut, UploadAck, UploadError
from app.storage import presigned_download_url, upload_fileobj

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=UploadAck)
def upload_documents(
    request: Request,
    household_id: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadAck:
    household_id = household_id.strip()
    if not household_id:
        raise HTTPException(status_code=400, detail="household_id is required")

    uploaded: list[DocumentOut] = []
    errors: list[UploadError] = []

    for upload in files:
        error = _validate_upload(upload, settings)
        if error:
            errors.append(UploadError(filename=upload.filename or "unknown", detail=error))
            audit.record_event(
                db,
                action="document.upload_rejected",
                outcome="error",
                request=request,
                household_id=household_id,
                detail=f"{upload.filename or 'unknown'}: {error}",
            )
            continue

        object_key = f"{household_id}/{uuid.uuid4()}-{upload.filename}"
        try:
            upload_fileobj(
                upload.file, settings.minio_bucket, object_key, upload.content_type
            )
        except Exception as exc:  # pragma: no cover - defensive, surfaced to client
            errors.append(
                UploadError(filename=upload.filename or "unknown", detail=f"storage error: {exc}")
            )
            audit.record_event(
                db,
                action="document.upload_rejected",
                outcome="error",
                request=request,
                household_id=household_id,
                object_key=object_key,
                detail=f"{upload.filename or 'unknown'}: storage error: {exc}",
            )
            continue

        size = upload.size if upload.size is not None else upload.file.tell()
        document = Document(
            household_id=household_id,
            original_filename=upload.filename or "unknown",
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=size,
            bucket=settings.minio_bucket,
            object_key=object_key,
        )
        db.add(document)
        db.flush()
        audit.record_event(
            db,
            action="document.upload",
            outcome="success",
            request=request,
            household_id=household_id,
            document_id=document.id,
            object_key=object_key,
            detail=document.original_filename,
        )
        uploaded.append(DocumentOut.model_validate(document))

    db.commit()
    return UploadAck(household_id=household_id, uploaded=uploaded, errors=errors)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    request: Request,
    household_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[DocumentOut]:
    household_id = household_id.strip()
    if not household_id:
        raise HTTPException(status_code=400, detail="household_id is required")

    stmt = (
        select(Document)
        .where(Document.household_id == household_id)
        .order_by(Document.uploaded_at.desc())
    )
    documents = db.execute(stmt).scalars().all()
    audit.record_read_event(
        db,
        settings,
        action="document.list",
        outcome="success",
        request=request,
        household_id=household_id,
        detail=f"count={len(documents)}",
    )
    return [DocumentOut.model_validate(doc) for doc in documents]


@router.get("/{document_id}/download")
def download_document(
    request: Request,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    document = db.get(Document, document_id)
    if document is None:
        audit.record_read_event(
            db,
            settings,
            action="document.download_not_found",
            outcome="error",
            request=request,
            document_id=document_id,
            detail="document not found",
        )
        raise HTTPException(status_code=404, detail="document not found")

    audit.record_read_event(
        db,
        settings,
        action="document.download",
        outcome="success",
        request=request,
        household_id=document.household_id,
        document_id=document.id,
        object_key=document.object_key,
    )

    url = presigned_download_url(
        document.bucket, document.object_key, settings.presigned_url_expiry_seconds
    )
    return RedirectResponse(url=url, status_code=302)


def _validate_upload(upload: UploadFile, settings: Settings) -> str | None:
    if not upload.filename:
        return "missing filename"
    if upload.content_type not in settings.allowed_content_types_set:
        return f"unsupported content type: {upload.content_type}"

    upload.file.seek(0, 2)  # seek to end
    size = upload.file.tell()
    upload.file.seek(0)
    if size > settings.max_upload_bytes:
        return f"file exceeds {settings.max_upload_bytes} byte limit"
    if size == 0:
        return "file is empty"

    return None
