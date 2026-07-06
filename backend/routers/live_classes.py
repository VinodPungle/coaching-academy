import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["live-classes"])


class LiveClassBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    start_time: str
    duration_min: int = 60
    meeting_link: str = ""


@router.get("/live-classes")
async def list_live_classes(user: dict = Depends(get_current_user)):
    query = {}
    if user["role"] in ("teacher", "admin"):
        query = {"teacher_id": user["id"]}
    docs = await db.live_classes.find(query).sort("start_time", 1).to_list(200)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.post("/live-classes")
async def create_live_class(body: LiveClassBody, user: dict = Depends(require_role("teacher", "admin"))):
    doc = body.model_dump()
    doc.update({
        "_id": str(uuid.uuid4()),
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.live_classes.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/live-classes/{class_id}")
async def delete_live_class(class_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.live_classes.delete_one({"_id": class_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    return {"message": "Live class deleted"}
