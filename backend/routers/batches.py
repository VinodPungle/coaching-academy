# Batches: named sub-groups of students within a course (e.g. "Morning
# Batch", schedule-bound, optional capacity). Students without a batch are
# implicitly "self-paced". Batches are a course sub-resource, so every
# mutation here re-checks the calling teacher owns the parent course.
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["batches"])


class BatchBody(BaseModel):
    name: str
    start_date: str = ""
    schedule: str = ""
    capacity: Optional[int] = None


@router.get("/courses/{course_id}/batches")
async def list_batches(course_id: str, user: dict = Depends(get_current_user)):
    """List a course's batches with each one's live enrolled_count — open to
    any authenticated user (students need this to pick a batch at enrollment)."""
    docs = await db.batches.find({"course_id": course_id}).sort("created_at", 1).to_list(100)
    result = []
    for d in docs:
        d["id"] = d.pop("_id")
        d["enrolled_count"] = await db.enrollments.count_documents({"batch_id": d["id"]})
        result.append(d)
    return result


@router.post("/courses/{course_id}/batches")
async def create_batch(course_id: str, body: BatchBody, user: dict = Depends(require_role("teacher", "admin"))):
    """Owner-only. 404s (not 403) if the course doesn't exist or isn't theirs."""
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    doc = body.model_dump()
    doc.update({
        "_id": str(uuid.uuid4()),
        "course_id": course_id,
        "teacher_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.batches.insert_one(doc)
    doc["id"] = doc.pop("_id")
    doc["enrolled_count"] = 0
    return doc


@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    """Deletes the batch and un-assigns its students back to self-paced
    (batch_id -> None) rather than deleting their enrollments."""
    result = await db.batches.delete_one({"_id": batch_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Batch not found")
    await db.enrollments.update_many({"batch_id": batch_id}, {"$set": {"batch_id": None}})
    return {"message": "Batch deleted"}


@router.get("/batches/{batch_id}/students")
async def batch_students(batch_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    """Roster of students currently assigned to this batch."""
    enrollments = await db.enrollments.find({"batch_id": batch_id}).to_list(500)
    result = []
    for e in enrollments:
        student = await db.users.find_one({"_id": e["student_id"]})
        if student:
            result.append({
                "id": student["_id"],
                "name": student["name"],
                "email": student["email"],
                "enrolled_at": e.get("enrolled_at"),
            })
    return result
