import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, optional_user, require_role, can_see_demo_content, is_demo_teacher_email
from notify import notify, email_template, ACADEMY_NAME

router = APIRouter(tags=["courses"])


class CourseBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    thumbnail: str = ""
    price: float = 0
    is_free: bool = False
    duration: str = ""
    published: bool = True


class SectionBody(BaseModel):
    title: str


class SubTopicBody(BaseModel):
    title: str
    order: Optional[int] = None


class SubTopicReorderBody(BaseModel):
    sub_topic_ids: List[str]


class LessonReorderBody(BaseModel):
    lesson_ids: List[str]


class EnrollBody(BaseModel):
    batch_id: Optional[str] = None


class LessonNote(BaseModel):
    title: str
    url: str


class LessonBody(BaseModel):
    title: str
    url: str = ""
    duration: str = ""
    notes: List[LessonNote] = []


def course_out(doc: dict) -> dict:
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/courses")
async def list_courses(user: dict | None = Depends(optional_user)):
    query = {"published": True}
    if not can_see_demo_content(user):
        query["demo_scope"] = {"$ne": True}
    docs = await db.courses.find(query).sort("created_at", -1).to_list(200)
    return [course_out(d) for d in docs]


@router.get("/teacher/courses")
async def teacher_courses(user: dict = Depends(require_role("teacher", "admin"))):
    docs = await db.courses.find({"teacher_id": user["id"]}).sort("created_at", -1).to_list(200)
    ids = [d["_id"] for d in docs]
    counts = {
        c["_id"]: c["n"]
        for c in await db.enrollments.aggregate([
            {"$match": {"course_id": {"$in": ids}}},
            {"$group": {"_id": "$course_id", "n": {"$sum": 1}}},
        ]).to_list(500)
    }
    result = []
    for d in docs:
        d = course_out(d)
        d["enrolled_count"] = counts.get(d["id"], 0)
        result.append(d)
    return result


@router.get("/courses/{course_id}")
async def get_course(course_id: str, user: dict = Depends(get_current_user)):
    doc = await db.courses.find_one({"_id": course_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    if doc.get("demo_scope") and not can_see_demo_content(user) and doc.get("teacher_id") != user["id"]:
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
        "demo_scope": is_demo_teacher_email(user.get("email", "")),
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
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Section title is required")
    section = {
        "id": str(uuid.uuid4()),
        "title": body.title.strip(),
        "sub_topics": [
            {"id": str(uuid.uuid4()), "title": "Overview", "order": 0, "lessons": [], "comments_enabled": True}
        ],
    }
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]}, {"$push": {"sections": section}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return section


@router.put("/courses/{course_id}/sections/{section_id}")
async def rename_section(course_id: str, section_id: str, body: SectionBody, user: dict = Depends(require_role("teacher", "admin"))):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Section title is required")
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"], "sections.id": section_id},
        {"$set": {"sections.$.title": body.title.strip()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course or section not found")
    return {"message": "Section renamed"}


@router.delete("/courses/{course_id}/sections/{section_id}")
async def delete_section(course_id: str, section_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]},
        {"$pull": {"sections": {"id": section_id}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Section deleted"}


@router.post("/courses/{course_id}/sections/{section_id}/sub-topics")
async def add_sub_topic(course_id: str, section_id: str, body: SubTopicBody, user: dict = Depends(require_role("teacher", "admin"))):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Sub topic title is required")
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    section = next((s for s in course.get("sections", []) if s["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    existing_titles = {st["title"].lower() for st in section.get("sub_topics", [])}
    if body.title.strip().lower() in existing_titles:
        raise HTTPException(status_code=400, detail="A sub topic with this name already exists in this section")
    next_order = max((st.get("order", 0) for st in section.get("sub_topics", [])), default=-1) + 1
    sub_topic = {
        "id": str(uuid.uuid4()),
        "title": body.title.strip(),
        "order": body.order if body.order is not None else next_order,
        "lessons": [],
        "comments_enabled": True,
    }
    await db.courses.update_one(
        {"_id": course_id, "sections.id": section_id},
        {"$push": {"sections.$.sub_topics": sub_topic}},
    )
    return sub_topic


@router.put("/courses/{course_id}/sections/{section_id}/sub-topics/reorder")
async def reorder_sub_topics(course_id: str, section_id: str, body: SubTopicReorderBody, user: dict = Depends(require_role("teacher", "admin"))):
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for section in course.get("sections", []):
        if section["id"] == section_id:
            by_id = {st["id"]: st for st in section.get("sub_topics", [])}
            reordered = []
            for i, sid in enumerate(body.sub_topic_ids):
                if sid in by_id:
                    by_id[sid]["order"] = i
                    reordered.append(by_id[sid])
            # append any that were not included at the end
            for st in section.get("sub_topics", []):
                if st["id"] not in body.sub_topic_ids:
                    st["order"] = len(reordered)
                    reordered.append(st)
            section["sub_topics"] = reordered
            await db.courses.update_one({"_id": course_id}, {"$set": {"sections": course["sections"]}})
            return {"message": "Reordered"}
    raise HTTPException(status_code=404, detail="Section not found")


@router.put("/courses/{course_id}/sections/{section_id}/sub-topics/{sub_topic_id}")
async def update_sub_topic(course_id: str, section_id: str, sub_topic_id: str, body: SubTopicBody, user: dict = Depends(require_role("teacher", "admin"))):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Sub topic title is required")
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]},
        {"$set": {
            "sections.$[sec].sub_topics.$[st].title": body.title.strip(),
        }},
        array_filters=[{"sec.id": section_id}, {"st.id": sub_topic_id}],
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course/section/sub topic not found")
    return {"message": "Sub topic updated"}


@router.delete("/courses/{course_id}/sections/{section_id}/sub-topics/{sub_topic_id}")
async def delete_sub_topic(course_id: str, section_id: str, sub_topic_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    section = next((s for s in course.get("sections", []) if s["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    sub_topic = next((st for st in section.get("sub_topics", []) if st["id"] == sub_topic_id), None)
    if not sub_topic:
        raise HTTPException(status_code=404, detail="Sub topic not found")
    if sub_topic.get("lessons"):
        raise HTTPException(status_code=400, detail=f"Cannot delete — {len(sub_topic['lessons'])} lesson(s) exist. Delete lessons first or move them to another sub topic.")
    await db.courses.update_one(
        {"_id": course_id, "sections.id": section_id},
        {"$pull": {"sections.$.sub_topics": {"id": sub_topic_id}}},
    )
    return {"message": "Sub topic deleted"}


@router.post("/courses/{course_id}/sections/{section_id}/sub-topics/{sub_topic_id}/lessons")
async def add_lesson(course_id: str, section_id: str, sub_topic_id: str, body: LessonBody, user: dict = Depends(require_role("teacher", "admin"))):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Lesson title is required")
    if not body.url and not body.notes:
        raise HTTPException(status_code=400, detail="Provide a video URL and/or at least one notes file")
    lesson = {
        "id": str(uuid.uuid4()),
        "title": body.title.strip(),
        "url": body.url.strip(),
        "duration": body.duration.strip(),
        "notes": [n.model_dump() for n in body.notes],
        "type": "video" if body.url else "notes",  # kept for legacy UI badges
    }
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]},
        {"$push": {"sections.$[sec].sub_topics.$[st].lessons": lesson}},
        array_filters=[{"sec.id": section_id}, {"st.id": sub_topic_id}],
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course / section / sub topic not found")
    return lesson


@router.put("/courses/{course_id}/lessons/{lesson_id}")
async def update_lesson(course_id: str, lesson_id: str, body: LessonBody, user: dict = Depends(require_role("teacher", "admin"))):
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    found = False
    for section in course.get("sections", []):
        for st in section.get("sub_topics", []):
            for lesson in st.get("lessons", []):
                if lesson["id"] == lesson_id:
                    lesson["title"] = body.title.strip()
                    lesson["url"] = body.url.strip()
                    lesson["duration"] = body.duration.strip()
                    lesson["notes"] = [n.model_dump() for n in body.notes]
                    lesson["type"] = "video" if body.url else "notes"
                    found = True
    if not found:
        raise HTTPException(status_code=404, detail="Lesson not found")
    await db.courses.update_one({"_id": course_id}, {"$set": {"sections": course["sections"]}})
    return {"message": "Lesson updated"}


@router.put("/courses/{course_id}/sections/{section_id}/sub-topics/{sub_topic_id}/lessons/reorder")
async def reorder_lessons(course_id: str, section_id: str, sub_topic_id: str, body: LessonReorderBody, user: dict = Depends(require_role("teacher", "admin"))):
    course = await db.courses.find_one({"_id": course_id, "teacher_id": user["id"]})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for section in course.get("sections", []):
        if section["id"] != section_id:
            continue
        for st in section.get("sub_topics", []):
            if st["id"] != sub_topic_id:
                continue
            by_id = {l["id"]: l for l in st.get("lessons", [])}
            reordered = [by_id[lid] for lid in body.lesson_ids if lid in by_id]
            # append any lessons that were not included at the end (safety)
            reordered.extend([l for l in st.get("lessons", []) if l["id"] not in body.lesson_ids])
            st["lessons"] = reordered
            await db.courses.update_one({"_id": course_id}, {"$set": {"sections": course["sections"]}})
            return {"message": "Lessons reordered"}
        raise HTTPException(status_code=404, detail="Sub topic not found")
    raise HTTPException(status_code=404, detail="Section not found")


@router.delete("/courses/{course_id}/lessons/{lesson_id}")
async def delete_lesson(course_id: str, lesson_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]},
        {"$pull": {"sections.$[].sub_topics.$[].lessons": {"id": lesson_id}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    await db.enrollments.update_many(
        {"course_id": course_id},
        {"$pull": {"completed_lessons": lesson_id}},
    )
    return {"message": "Lesson deleted"}


@router.get("/courses/{course_id}/lessons/{lesson_id}")
async def get_lesson(course_id: str, lesson_id: str, user: dict = Depends(get_current_user)):
    """Return a single lesson with its context (section, sub topic, prev/next lesson ids)."""
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # student must be enrolled (teacher/admin can preview)
    if user["role"] == "student":
        enrollment = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
        if not enrollment:
            raise HTTPException(status_code=403, detail="Enrol in this course to view its lessons")
    # flat lesson list preserving order (Section → SubTopic → Lesson)
    ordered = []
    for section in course.get("sections", []):
        sub_topics = sorted(section.get("sub_topics", []), key=lambda st: st.get("order", 0))
        for st in sub_topics:
            for lesson in st.get("lessons", []):
                ordered.append({
                    "lesson": lesson,
                    "section_id": section["id"],
                    "section_title": section["title"],
                    "sub_topic_id": st["id"],
                    "sub_topic_title": st["title"],
                    "comments_enabled": st.get("comments_enabled", True),
                })
    idx = next((i for i, x in enumerate(ordered) if x["lesson"]["id"] == lesson_id), -1)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {
        **ordered[idx],
        "course_id": course_id,
        "course_title": course["title"],
        "prev_lesson_id": ordered[idx - 1]["lesson"]["id"] if idx > 0 else None,
        "next_lesson_id": ordered[idx + 1]["lesson"]["id"] if idx < len(ordered) - 1 else None,
    }


@router.post("/courses/{course_id}/enroll")
async def enroll(course_id: str, body: Optional[EnrollBody] = None, user: dict = Depends(require_role("student"))):
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")

    # Phase 7 + 8: gate paid enrollments unless the course is Free, or portal is in Demo mode.
    settings_doc = await db.settings.find_one({"_id": "portal_settings"}) or {}
    portal_mode = settings_doc.get("portal_mode", "live")
    is_free = bool(course.get("is_free")) or float(course.get("price", 0) or 0) == 0
    if not is_free and portal_mode != "demo":
        raise HTTPException(status_code=402, detail=f"This is a paid course (₹{course.get('price')}). Pay via UPI and ask the admin to record your payment.")

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
        email_subject=f"Welcome to {course['title']} — {ACADEMY_NAME}",
        email_html=email_template("Enrollment confirmed", f"Hi {user['name']},<br/><br/>You are now enrolled in <b>{course['title']}</b>. Head to your dashboard to start learning."),
        cc_admin=True,
    )
    await notify([course["teacher_id"]], "New student enrolled", f"{user['name']} enrolled in {course['title']}.", f"/app/courses/{course_id}")
    return {"message": "Enrolled successfully"}


@router.get("/student/enrollments")
async def my_enrollments(user: dict = Depends(require_role("student"))):
    enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(200)
    course_ids = [e["course_id"] for e in enrollments]
    courses = {c["_id"]: c for c in await db.courses.find({"_id": {"$in": course_ids}}).to_list(200)}
    result = []
    for e in enrollments:
        course = courses.get(e["course_id"])
        if not course:
            continue
        course = course_out(dict(course))
        total = sum(
            len(st.get("lessons", []))
            for s in course.get("sections", [])
            for st in s.get("sub_topics", [])
        )
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


class CommentsToggleBody(BaseModel):
    comments_enabled: bool


@router.put("/courses/{course_id}/sections/{section_id}/sub-topics/{sub_topic_id}/comments-toggle")
async def toggle_sub_topic_comments(course_id: str, section_id: str, sub_topic_id: str, body: CommentsToggleBody, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.courses.update_one(
        {"_id": course_id, "teacher_id": user["id"]},
        {"$set": {"sections.$[sec].sub_topics.$[st].comments_enabled": body.comments_enabled}},
        array_filters=[{"sec.id": section_id}, {"st.id": sub_topic_id}],
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course/section/sub topic not found")
    return {"message": "Updated", "comments_enabled": body.comments_enabled}


@router.get("/courses/{course_id}/students")
async def course_students(course_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    enrollments = await db.enrollments.find({"course_id": course_id}).to_list(500)
    student_ids = [e["student_id"] for e in enrollments]
    students = {s["_id"]: s for s in await db.users.find({"_id": {"$in": student_ids}}).to_list(500)}
    batches = {b["_id"]: b for b in await db.batches.find({"course_id": course_id}).to_list(200)}
    result = []
    for e in enrollments:
        student = students.get(e["student_id"])
        if student:
            batch = batches.get(e.get("batch_id")) if e.get("batch_id") else None
            result.append({
                "id": student["_id"],
                "name": student["name"],
                "email": student["email"],
                "enrolled_at": e.get("enrolled_at"),
                "completed_lessons": len(e.get("completed_lessons", [])),
                "batch_id": e.get("batch_id"),
                "batch_name": batch["name"] if batch else None,
                "enrollment_id": e["_id"],
            })
    return result


class MoveEnrollmentBody(BaseModel):
    batch_id: Optional[str] = None   # null => self-paced


@router.put("/courses/{course_id}/students/{student_id}/batch")
async def move_student_batch(course_id: str, student_id: str, body: MoveEnrollmentBody, user: dict = Depends(require_role("teacher", "admin"))):
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if user["role"] == "teacher" and course.get("teacher_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your course")
    enrollment = await db.enrollments.find_one({"course_id": course_id, "student_id": student_id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this course")
    target_batch_name = "Self-paced"
    if body.batch_id:
        batch = await db.batches.find_one({"_id": body.batch_id, "course_id": course_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found in this course")
        if batch.get("capacity"):
            in_batch = await db.enrollments.count_documents({"batch_id": body.batch_id, "student_id": {"$ne": student_id}})
            if in_batch >= batch["capacity"]:
                raise HTTPException(status_code=400, detail="Target batch is full")
        target_batch_name = batch["name"]
    await db.enrollments.update_one(
        {"_id": enrollment["_id"]},
        {"$set": {"batch_id": body.batch_id}},
    )
    await notify(
        [student_id],
        "Batch updated",
        f"Your batch for {course['title']} has been updated to {target_batch_name}.",
        f"/app/courses/{course_id}",
    )
    return {"message": "Student moved", "batch_id": body.batch_id}
