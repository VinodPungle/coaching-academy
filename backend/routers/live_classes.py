import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role
from notify import notify

router = APIRouter(tags=["live-classes"])


class LiveClassBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    start_time: str
    duration_min: int = 60
    meeting_link: str = ""
    course_id: Optional[str] = None
    batch_id: Optional[str] = None


async def student_class_query(student_id: str) -> dict:
    enrollments = await db.enrollments.find({"student_id": student_id}).to_list(500)
    ors = [{"course_id": None}, {"course_id": {"$exists": False}}]
    for e in enrollments:
        ors.append({"course_id": e["course_id"], "batch_id": {"$in": [None, e.get("batch_id")]}})
    return {"$or": ors}


@router.get("/live-classes")
async def list_live_classes(user: dict = Depends(get_current_user)):
    if user["role"] in ("teacher", "admin"):
        query = {"teacher_id": user["id"]}
    else:
        query = await student_class_query(user["id"])
    docs = await db.live_classes.find(query).sort("start_time", 1).to_list(200)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.post("/live-classes")
async def create_live_class(body: LiveClassBody, user: dict = Depends(require_role("teacher", "admin"))):
    course_name = None
    batch_name = None
    if body.course_id:
        course = await db.courses.find_one({"_id": body.course_id})
        if not course:
            raise HTTPException(status_code=404, detail="Linked course not found")
        course_name = course["title"]
        if body.batch_id:
            batch = await db.batches.find_one({"_id": body.batch_id, "course_id": body.course_id})
            if not batch:
                raise HTTPException(status_code=404, detail="Batch not found for this course")
            batch_name = batch["name"]
    doc = body.model_dump()
    doc.update({
        "_id": str(uuid.uuid4()),
        "course_id": body.course_id,
        "batch_id": body.batch_id if body.course_id else None,
        "course_name": course_name,
        "batch_name": batch_name,
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.live_classes.insert_one(doc)

    if body.course_id:
        enroll_q = {"course_id": body.course_id}
        if doc["batch_id"]:
            enroll_q["batch_id"] = doc["batch_id"]
        enrollments = await db.enrollments.find(enroll_q).to_list(1000)
        student_ids = [e["student_id"] for e in enrollments]
    else:
        students = await db.users.find({"role": "student"}).to_list(2000)
        student_ids = [s["_id"] for s in students]
    scope = f"{course_name}{' · ' + batch_name if batch_name else ''}" if course_name else "All students"
    await notify(
        student_ids,
        "New live class scheduled",
        f"{doc['title']} ({doc['subject']}) — {scope}",
        "/app/live",
    )

    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/live-classes/{class_id}")
async def delete_live_class(class_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.live_classes.delete_one({"_id": class_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    return {"message": "Live class deleted"}
