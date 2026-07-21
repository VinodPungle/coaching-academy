# Course-completion certificates. A certificate is generated on-demand the
# first time a student who has finished every lesson requests it (not
# proactively when they complete the last lesson) — subsequent requests
# just return the same already-issued certificate.
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth_utils import require_role

router = APIRouter(tags=["certificates"])


@router.get("/courses/{course_id}/certificate")
async def get_certificate(course_id: str, user: dict = Depends(require_role("student"))):
    """Get-or-create: 400s with a progress message if lessons remain
    incomplete; otherwise returns the existing certificate or mints a new
    one with a unique cert_no."""
    enrollment = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    total = sum(
        len(st.get("lessons", []))
        for s in course.get("sections", [])
        for st in s.get("sub_topics", [])
    )
    done = len(enrollment.get("completed_lessons", []))
    if total == 0 or done < total:
        raise HTTPException(status_code=400, detail=f"Complete all lessons to earn your certificate ({done}/{total} done)")
    existing = await db.certificates.find_one({"course_id": course_id, "student_id": user["id"]})
    if existing:
        existing["id"] = existing.pop("_id")
        return existing
    doc = {
        "_id": str(uuid.uuid4()),
        "cert_no": f"JAM-{uuid.uuid4().hex[:8].upper()}",
        "student_id": user["id"],
        "student_name": user["name"],
        "course_id": course_id,
        "course_title": course["title"],
        "subject": course.get("subject", ""),
        "teacher_name": course.get("teacher_name", ""),
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.certificates.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/student/certificates")
async def my_certificates(user: dict = Depends(require_role("student"))):
    """All certificates this student has already earned, newest first."""
    docs = await db.certificates.find({"student_id": user["id"]}).sort("issued_at", -1).to_list(100)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs
