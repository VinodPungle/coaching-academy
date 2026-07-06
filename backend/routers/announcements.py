import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["announcements"])


class AnnouncementBody(BaseModel):
    title: str
    body: str


@router.get("/announcements")
async def list_announcements(user: dict = Depends(get_current_user)):
    docs = await db.announcements.find({}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.post("/announcements")
async def create_announcement(body: AnnouncementBody, user: dict = Depends(require_role("teacher", "admin"))):
    doc = {
        "_id": str(uuid.uuid4()),
        "title": body.title,
        "body": body.body,
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.announcements.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.announcements.delete_one({"_id": announcement_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"message": "Announcement deleted"}
