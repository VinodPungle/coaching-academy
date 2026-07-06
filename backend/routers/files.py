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

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt", ".csv", ".pptx", ".xlsx", ".zip"}
MAX_SIZE = 25 * 1024 * 1024
CHUNK = 1024 * 1024


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type {ext or 'unknown'} not allowed. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
    file_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{file_id}{ext}"
    size = 0
    with open(dest, "wb") as out:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SIZE:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="File too large (max 25 MB)")
            out.write(chunk)
    await db.files.insert_one({
        "_id": file_id,
        "filename": file.filename,
        "ext": ext,
        "content_type": file.content_type,
        "size": size,
        "uploader_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": file_id, "url": f"/api/files/{file_id}", "filename": file.filename, "size": size}


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    meta = await db.files.find_one({"_id": file_id})
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    path = UPLOAD_DIR / f"{file_id}{meta['ext']}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(path, filename=meta["filename"], media_type=meta.get("content_type") or "application/octet-stream")
