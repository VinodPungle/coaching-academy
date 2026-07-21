# Generic file upload/download used across the app (lesson notes/videos,
# course syllabi, teacher profile photos, assignment submissions, etc.) —
# a single shared mechanism rather than one per feature. See
# storage_service.py for where the bytes actually end up (Azure Blob or
# local disk).
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from database import db
from auth_utils import get_current_user
import storage_service

router = APIRouter(tags=["files"])

# Legacy local dir — read-only fallback for files uploaded before object storage
LEGACY_UPLOAD_DIR = Path(__file__).parent.parent / "uploads"

DOC_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt", ".csv", ".ppt", ".pptx", ".xlsx", ".zip"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}
ALLOWED_EXT = DOC_EXT | VIDEO_EXT

DOC_MAX = 25 * 1024 * 1024              # 25 MB for docs / images / slides
VIDEO_MAX = 500 * 1024 * 1024           # 500 MB for videos


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Any authenticated user (any role) can upload — per-feature endpoints
    (e.g. courses.py's set_syllabus) apply their own additional rules (like
    "must be a PDF") after the file already exists as a generic upload.
    Reads the whole body into memory in 1 MB chunks (rather than streaming
    straight to disk) so it can forward the bytes to object storage; aborts
    early once the size cap is exceeded instead of accepting the full file
    first."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext or 'unknown'} not allowed. Allowed: {', '.join(sorted(ALLOWED_EXT))}",
        )
    is_video = ext in VIDEO_EXT
    max_size = VIDEO_MAX if is_video else DOC_MAX

    # Read entire body (respecting size cap) — safer than streaming to disk since we're
    # forwarding to object storage.
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_size:
            mb = max_size // (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"File too large (max {mb} MB for {'videos' if is_video else 'documents'})")

    if not storage_service.is_configured():
        raise HTTPException(status_code=500, detail="Object storage is not configured on the server. Contact the administrator.")

    file_id = str(uuid.uuid4())
    storage_path = storage_service.build_path(user["id"], file_id, ext)
    try:
        result = storage_service.put_object(storage_path, bytes(data), file.content_type or "application/octet-stream")
    except Exception as exc:  # noqa: BLE001 — surface a friendly error
        raise HTTPException(status_code=502, detail=f"Failed to upload file to storage: {exc}") from exc

    await db.files.insert_one({
        "_id": file_id,
        "filename": file.filename,
        "ext": ext,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "kind": "video" if is_video else "document",
        "uploader_id": user["id"],
        "storage_path": result.get("path", storage_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": file_id, "url": f"/api/files/{file_id}", "filename": file.filename, "size": result.get("size", len(data)), "kind": "video" if is_video else "document"}


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    """Deliberately unauthenticated — relies on the file_id UUID being
    unguessable rather than a permission check, so any code that deletes
    or replaces a file (see courses.py's syllabus replace/delete) must
    proactively remove the storage object + this metadata doc, since
    merely un-linking it elsewhere would leave the URL still working."""
    meta = await db.files.find_one({"_id": file_id})
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")

    storage_path = meta.get("storage_path")
    media_type = meta.get("content_type") or "application/octet-stream"
    filename = meta.get("filename") or f"{file_id}{meta.get('ext','')}"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}

    # New files: served from object storage
    if storage_path:
        try:
            data, ct = storage_service.get_object(storage_path)
            return Response(content=data, media_type=media_type or ct, headers=headers)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Failed to read from object storage: {exc}") from exc

    # Legacy files: still on the container disk (may or may not survive redeploys)
    legacy_path = LEGACY_UPLOAD_DIR / f"{file_id}{meta.get('ext','')}"
    if legacy_path.exists():
        return Response(content=legacy_path.read_bytes(), media_type=media_type, headers=headers)
    raise HTTPException(status_code=404, detail="File missing from storage")
