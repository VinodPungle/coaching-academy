import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role
from notify import notify, email_template

router = APIRouter(tags=["courses"])


class CourseBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    thumbnail: str = ""
    price: float = 0
    duration: str = ""
    published: bool = True


class SectionBody(BaseModel):
    title: str


class EnrollBody(BaseModel):
    batch_id: Optional[str] = None


class LessonBody(BaseModel):
    title: str
    type: str = "video"
    url: str = ""
    duration: str = ""


def course_out(doc: dict) -> dict:
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/courses")
async def list_courses():
    docs = await db.courses.find({"published": True}).sort("created_at", -1).to_list(200)
    return [course_out(d) for d in docs]


@router.get("/teacher/courses")
async def teacher_courses(user: dict = Depends(require_role("teacher", "admin"))):
    docs = await db.courses.find({"teacher_id": user["id"]}).sort("created_at", -1).to_list(200)
    result = []
    for d in docs:
        d = course_out(d)
        d["enrolled_count"] = await db.enrollments.count_documents({"course_id": d["id"]})
        result.append(d)
    return result


@router.get("/courses/{course_id}")
async def get_course(course_id: str, user: dict = Depends(get_current_user)):
    doc = await db.courses.find_one({"_id": course_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    doc = course_out(doc)
    enrollment = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
    doc["enrolled"] = enrollment is not None
    doc["completed_lessons"] = enrollment.get("completed_lessons", []) if enrollment else []
    doc["enrolled_count"] = await db.enrollments.count_documents({"course_id": course_id})
    doc["my_batch"] = None
    if enrollment and enrollment.get("batch_id"):
        batch = await db.batches.find_one({"_id": enrollment["batch_id"]})
        if batch:
            doc["my_batch"] = {"id": batch["_id"], "name": batch["name"], "schedule": batch.get("schedule", "")}
    return doc


@router.post("/courses")
async def create_course(body: CourseBody, user: dict = Depends(require_role("teacher", "admin"))):
    doc = body.model_dump()
    doc.update({
        "_id": str(uuid.uuid4()),
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "sections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.courses.insert_one(doc)
    return course_out(doc)


@router.put("/courses/{course_id}")
async def update_course(course_id: str, body: CourseBody, user: dict = Depends(require_role("teacher", "admin"))):
    doc = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    await db.courses.update_one({"_id": course_id}, {"$set": body.model_dump()})
    doc.update(body.model_dump())
    return course_out(doc)


@router.delete("/courses/{course_id}")
async def delete_course(course_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.courses.delete_one({"_id": course_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    await db.enrollments.delete_many({"course_id": course_id})
    return {"message": "Course deleted"}


@router.post("/courses/{course_id}/sections")
async def add_section(course_id: str, body: SectionBody, user: dict = Depends(require_role("teacher", "admin"))):
    section = {"id": str(uuid.uuid4()), "title": body.title, "lessons": []}
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]}, {"$push": {"sections": section}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return section


@router.post("/courses/{course_id}/sections/{section_id}/lessons")
async def add_lesson(course_id: str, section_id: str, body: LessonBody, user: dict = Depends(require_role("teacher", "admin"))):
    lesson = {"id": str(uuid.uuid4()), **body.model_dump()}
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"], "sections.id": section_id},
        {"$push": {"sections.$.lessons": lesson}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course or section not found")
    return lesson


@router.post("/courses/{course_id}/enroll")
async def enroll(course_id: str, body: Optional[EnrollBody] = None, user: dict = Depends(require_role("student"))):
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    batch_id = body.batch_id if body else None
    if batch_id:
        batch = await db.batches.find_one({"_id": batch_id, "course_id": course_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.get("capacity"):
            count = await db.enrollments.count_documents({"batch_id": batch_id})
            if count >= batch["capacity"]:
                raise HTTPException(status_code=400, detail="This batch is full")
    await db.enrollments.insert_one({
        "_id": str(uuid.uuid4()),
        "course_id": course_id,
        "student_id": user["id"],
        "batch_id": batch_id,
        "completed_lessons": [],
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
    })
    await notify(
        [user["id"]],
        "Enrollment confirmed",
        f"You are enrolled in {course['title']}.",
        f"/app/courses/{course_id}",
        email_subject=f"Welcome to {course['title']} — JAM Academy",
        email_html=email_template("Enrollment confirmed", f"Hi {user['name']},<br/><br/>You are now enrolled in <b>{course['title']}</b>. Head to your dashboard to start learning."),
    )
    await notify([course["teacher_id"]], "New student enrolled", f"{user['name']} enrolled in {course['title']}.", f"/app/courses/{course_id}")
    return {"message": "Enrolled successfully"}


@router.get("/student/enrollments")
async def my_enrollments(user: dict = Depends(require_role("student"))):
    enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(200)
    result = []
    for e in enrollments:
        course = await db.courses.find_one({"_id": e["course_id"]})
        if not course:
            continue
        course = course_out(course)
        total = sum(len(s.get("lessons", [])) for s in course.get("sections", []))
        done = len(e.get("completed_lessons", []))
        course["progress"] = round(done / total * 100) if total else 0
        course["completed_lessons"] = e.get("completed_lessons", [])
        result.append(course)
    return result


@router.post("/courses/{course_id}/lessons/{lesson_id}/complete")
async def complete_lesson(course_id: str, lesson_id: str, user: dict = Depends(require_role("student"))):
    result = await db.enrollments.update_one(
        {"course_id": course_id, "student_id": user["id"]},
        {"$addToSet": {"completed_lessons": lesson_id}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"message": "Lesson marked complete"}


@router.get("/courses/{course_id}/students")
async def course_students(course_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    enrollments = await db.enrollments.find({"course_id": course_id}).to_list(500)
    result = []
    for e in enrollments:
        student = await db.users.find_one({"_id": e["student_id"]})
        if student:
            result.append({
                "id": student["_id"],
                "name": student["name"],
                "email": student["email"],
                "enrolled_at": e.get("enrolled_at"),
                "completed_lessons": len(e.get("completed_lessons", [])),
            })
    return result
