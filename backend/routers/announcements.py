import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role, is_demo_teacher_email, can_see_demo_content, demo_user_ids
from notify import notify

router = APIRouter(tags=["announcements"])


class AnnouncementBody(BaseModel):
    title: str
    body: str
    course_id: Optional[str] = None


@router.get("/announcements")
async def list_announcements(user: dict = Depends(get_current_user)):
    if user["role"] == "teacher":
        # teacher sees own announcements + admin-posted global announcements
        query = {"$or": [{"teacher_id": user["id"]}, {"posted_by_role": "admin"}]}
    elif user["role"] == "admin":
        query = {}
    else:
        # students: all (global) + those linked to their enrolled courses
        enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(500)
        my_courses = [e["course_id"] for e in enrollments]
        query = {"$or": [{"course_id": None}, {"course_id": {"$exists": False}}, {"course_id": {"$in": my_courses}}]}
        if not can_see_demo_content(user):
            query["demo_scope"] = {"$ne": True}
    docs = await db.announcements.find(query).sort("created_at", -1).to_list(200)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.post("/announcements")
async def create_announcement(body: AnnouncementBody, user: dict = Depends(require_role("teacher", "admin"))):
    course_name = None
    if body.course_id:
        course = await db.courses.find_one({"_id": body.course_id})
        if not course:
            raise HTTPException(status_code=404, detail="Linked course not found")
        # teacher must own the course
        if user["role"] == "teacher" and course.get("teacher_id") != user["id"]:
            raise HTTPException(status_code=403, detail="You can only post to your own courses")
        course_name = course["title"]
    doc = {
        "_id": str(uuid.uuid4()),
        "title": body.title,
        "body": body.body,
        "course_id": body.course_id,
        "course_name": course_name,
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "posted_by_role": user["role"],
        "demo_scope": is_demo_teacher_email(user.get("email", "")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.announcements.insert_one(doc)
    # notify recipients — skip demo students when announcement is not from demo teacher, and vice versa
    if body.course_id:
        enrollments = await db.enrollments.find({"course_id": body.course_id}).to_list(2000)
        student_ids = [e["student_id"] for e in enrollments]
    else:
        student_q = {"role": "student"}
        if doc["demo_scope"]:
            student_q["is_demo"] = True  # demo teacher's global announcements → only demo student
        else:
            student_q["is_demo"] = {"$ne": True}  # real teachers → skip demo students
        students = await db.users.find(student_q).to_list(2000)
        student_ids = [s["_id"] for s in students]
    await notify(student_ids, "New announcement", body.title, "/app/announcements")
    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    query = {"_id": announcement_id} if user["role"] == "admin" else {"_id": announcement_id, "teacher_id": user["id"]}
    result = await db.announcements.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"message": "Announcement deleted"}
