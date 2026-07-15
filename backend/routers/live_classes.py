import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role, is_demo_teacher_email, can_see_demo_content
from notify import notify
from zoom_service import zoom_configured, create_zoom_meeting

router = APIRouter(tags=["live-classes"])


@router.get("/live-classes/public/next")
async def next_public_live_class():
    """Public — returns the soonest upcoming live class open to all students,
    or the soonest live-now class. Prefers course_id == null (open to all).
    Demo-teacher-scoped classes are excluded from the public landing page."""
    now = datetime.now(timezone.utc)
    cursor = db.live_classes.find({"course_id": None, "demo_scope": {"$ne": True}}).sort("start_time", 1)
    async for c in cursor:
        try:
            start = datetime.fromisoformat(c["start_time"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        end = start + timedelta(minutes=int(c.get("duration_min") or 0))
        if end > now:
            return {"id": c["_id"], "title": c["title"], "subject": c.get("subject", ""), "start_time": c["start_time"], "duration_min": c.get("duration_min", 60)}
    return None


def _normalize_url(url: str) -> str:
    """Ensure external meeting links have an http/https protocol so browsers don't treat them as relative."""
    if not url:
        return ""
    trimmed = url.strip()
    if not trimmed:
        return ""
    if re.match(r"^https?://", trimmed, re.IGNORECASE):
        return trimmed
    return f"https://{trimmed.lstrip('/')}"


class LiveClassBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    start_time: str
    duration_min: int = 60
    meeting_link: str = ""
    course_id: Optional[str] = None
    batch_id: Optional[str] = None
    create_zoom: bool = False


@router.get("/zoom/config")
async def zoom_config(user: dict = Depends(require_role("teacher", "admin"))):
    return {"configured": zoom_configured()}


async def student_class_query(student_id: str) -> dict:
    enrollments = await db.enrollments.find({"student_id": student_id}).to_list(500)
    ors = [{"course_id": None}, {"course_id": {"$exists": False}}]
    for e in enrollments:
        ors.append({"course_id": e["course_id"], "batch_id": {"$in": [None, e.get("batch_id")]}})
    return {"$or": ors}


@router.get("/live-classes")
async def list_live_classes(course_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    if user["role"] in ("teacher", "admin"):
        query = {"teacher_id": user["id"]} if user["role"] == "teacher" else {}
    else:
        query = await student_class_query(user["id"])
        if not can_see_demo_content(user):
            query["demo_scope"] = {"$ne": True}
    if course_id:
        query = {**query, "course_id": course_id}
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
    doc.pop("create_zoom", None)
    doc["meeting_link"] = _normalize_url(doc.get("meeting_link", ""))
    zoom_meeting_id = None
    if body.create_zoom:
        if not zoom_configured():
            raise HTTPException(status_code=400, detail="Zoom is not configured yet. Add Zoom credentials in backend settings or paste a meeting link manually.")
        meeting = await create_zoom_meeting(body.title, body.start_time, body.duration_min)
        doc["meeting_link"] = _normalize_url(meeting["join_url"])
        zoom_meeting_id = meeting.get("id")
    doc.update({
        "_id": str(uuid.uuid4()),
        "course_id": body.course_id,
        "batch_id": body.batch_id if body.course_id else None,
        "course_name": course_name,
        "batch_name": batch_name,
        "zoom_meeting_id": zoom_meeting_id,
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "demo_scope": is_demo_teacher_email(user.get("email", "")),
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
        student_q = {"role": "student"}
        if doc.get("demo_scope"):
            student_q["is_demo"] = True
        else:
            student_q["is_demo"] = {"$ne": True}
        students = await db.users.find(student_q).to_list(2000)
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
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    result = await db.live_classes.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    await db.live_class_attendance.delete_many({"class_id": class_id})
    await db.comments.delete_many({"context_type": "recording", "context_id": class_id})
    return {"message": "Live class deleted"}


class RescheduleBody(BaseModel):
    start_time: str
    duration_min: Optional[int] = None
    meeting_link: Optional[str] = None


@router.put("/live-classes/{class_id}/reschedule")
async def reschedule_live_class(class_id: str, body: RescheduleBody, user: dict = Depends(require_role("teacher", "admin"))):
    # validate not in past
    try:
        new_start = datetime.fromisoformat(body.start_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time (use ISO 8601)")
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)
    if new_start < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot schedule a class in the past")
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    update = {"start_time": body.start_time}
    if body.duration_min is not None:
        if body.duration_min < 5 or body.duration_min > 720:
            raise HTTPException(status_code=400, detail="Duration must be between 5 and 720 minutes")
        update["duration_min"] = body.duration_min
    if body.meeting_link is not None:
        update["meeting_link"] = _normalize_url(body.meeting_link)
    result = await db.live_classes.update_one(query, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    # Notify enrolled students
    live = await db.live_classes.find_one({"_id": class_id})
    if live.get("course_id"):
        student_ids = [e["student_id"] for e in await db.enrollments.find({"course_id": live["course_id"]}).to_list(2000)]
    else:
        student_ids = [u["_id"] for u in await db.users.find({"role": "student"}).to_list(2000)]
    await notify(student_ids, "Live class rescheduled", f"{live['title']} has been rescheduled.", "/app/live")
    return {"message": "Rescheduled", "start_time": body.start_time}


class RecordingBody(BaseModel):
    recording_url: str


@router.put("/live-classes/{class_id}/recording")
async def set_recording(class_id: str, body: RecordingBody, user: dict = Depends(require_role("teacher", "admin"))):
    if not body.recording_url.strip():
        raise HTTPException(status_code=400, detail="Recording URL is required")
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    result = await db.live_classes.update_one(query, {"$set": {"recording_url": body.recording_url.strip()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    return {"message": "Recording attached", "recording_url": body.recording_url}


@router.delete("/live-classes/{class_id}/recording")
async def remove_recording(class_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    result = await db.live_classes.update_one(query, {"$unset": {"recording_url": ""}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    return {"message": "Recording removed"}


@router.post("/live-classes/{class_id}/attend")
async def mark_attendance(class_id: str, user: dict = Depends(require_role("student"))):
    live = await db.live_classes.find_one({"_id": class_id})
    if not live:
        raise HTTPException(status_code=404, detail="Live class not found")
    if live.get("course_id"):
        enrolled = await db.enrollments.find_one({"course_id": live["course_id"], "student_id": user["id"]})
        if not enrolled:
            raise HTTPException(status_code=403, detail="Enrol in this course to attend the class")
    # upsert: idempotent even if student clicks multiple times
    now = datetime.now(timezone.utc).isoformat()
    await db.live_class_attendance.update_one(
        {"class_id": class_id, "student_id": user["id"]},
        {"$setOnInsert": {
            "_id": str(uuid.uuid4()),
            "class_id": class_id,
            "student_id": user["id"],
            "student_name": user["name"],
            "attended_at": now,
        }},
        upsert=True,
    )
    return {"message": "Attendance recorded", "meeting_link": live.get("meeting_link", "")}


@router.get("/live-classes/{class_id}/attendance")
async def list_attendance(class_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    live = await db.live_classes.find_one(query)
    if not live:
        raise HTTPException(status_code=404, detail="Live class not found")
    rows = await db.live_class_attendance.find({"class_id": class_id}).sort("attended_at", 1).to_list(5000)
    return [{
        "student_id": r["student_id"],
        "student_name": r["student_name"],
        "attended_at": r["attended_at"],
    } for r in rows]


@router.get("/live-classes/{class_id}")
async def get_live_class(class_id: str, user: dict = Depends(get_current_user)):
    live = await db.live_classes.find_one({"_id": class_id})
    if not live:
        raise HTTPException(status_code=404, detail="Live class not found")
    # Access: student must be enrolled in linked course (or the class must be global)
    if user["role"] == "student" and live.get("course_id"):
        enrolled = await db.enrollments.find_one({"course_id": live["course_id"], "student_id": user["id"]})
        if not enrolled:
            raise HTTPException(status_code=403, detail="Enrol in this course to view this class")
    live["id"] = live.pop("_id")
    live.setdefault("comments_enabled", True)
    return live
