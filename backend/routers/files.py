import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from database import db
from auth_utils import get_current_user

router = APIRouter(tags=["files"])

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DOC_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt", ".csv", ".pptx", ".xlsx", ".zip"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v", ".ogg"}
ALLOWED_EXT = DOC_EXT | VIDEO_EXT

DOC_MAX = 25 * 1024 * 1024              # 25 MB for docs / images
VIDEO_MAX = 500 * 1024 * 1024           # 500 MB for videos
CHUNK = 1024 * 1024


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext or 'unknown'} not allowed. Allowed: {', '.join(sorted(ALLOWED_EXT))}",
        )
    is_video = ext in VIDEO_EXT
    max_size = VIDEO_MAX if is_video else DOC_MAX
    file_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{file_id}{ext}"
    size = 0
    with open(dest, "wb") as out:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > max_size:
                out.close()
                dest.unlink(missing_ok=True)
                mb = max_size // (1024 * 1024)
                raise HTTPException(status_code=400, detail=f"File too large (max {mb} MB for {'videos' if is_video else 'documents'})")
            out.write(chunk)
    await db.files.insert_one({
        "_id": file_id,
        "filename": file.filename,
        "ext": ext,
        "content_type": file.content_type,
        "size": size,
        "kind": "video" if is_video else "document",
        "uploader_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": file_id, "url": f"/api/files/{file_id}", "filename": file.filename, "size": size, "kind": "video" if is_video else "document"}


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    meta = await db.files.find_one({"_id": file_id})
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    path = UPLOAD_DIR / f"{file_id}{meta['ext']}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(path, filename=meta["filename"], media_type=meta.get("content_type") or "application/octet-stream")
