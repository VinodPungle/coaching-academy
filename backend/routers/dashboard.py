from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from database import db
from auth_utils import require_role
from routers.live_classes import student_class_query

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/student")
async def student_dashboard(user: dict = Depends(require_role("student"))):
    now = datetime.now(timezone.utc).isoformat()
    enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(200)
    attempts = await db.test_attempts.find({"student_id": user["id"]}).to_list(200)
    class_q = await student_class_query(user["id"])
    upcoming = await db.live_classes.find({**class_q, "start_time": {"$gte": now}}).sort("start_time", 1).to_list(5)
    for c in upcoming:
        c["id"] = c.pop("_id")
    announcements = await db.announcements.find({}).sort("created_at", -1).to_list(3)
    for a in announcements:
        a["id"] = a.pop("_id")
    submissions = await db.submissions.count_documents({"student_id": user["id"]})
    total_assignments = await db.assignments.count_documents({})
    avg_score = 0
    if attempts:
        pcts = [a["score"] / a["total"] * 100 for a in attempts if a.get("total")]
        avg_score = round(sum(pcts) / len(pcts)) if pcts else 0
    return {
        "enrolled_courses": len(enrollments),
        "tests_attempted": len(attempts),
        "avg_score_pct": avg_score,
        "pending_assignments": max(total_assignments - submissions, 0),
        "upcoming_classes": upcoming,
        "recent_announcements": announcements,
    }


@router.get("/dashboard/teacher/analytics")
async def teacher_analytics(user: dict = Depends(require_role("teacher", "admin"))):
    courses = await db.courses.find({"teacher_id": user["id"]}).to_list(100)
    course_stats = []
    for c in courses:
        count = await db.enrollments.count_documents({"course_id": c["_id"]})
        course_stats.append({"title": c["title"], "students": count})
    tests = await db.tests.find({"teacher_id": user["id"]}).to_list(100)
    test_stats = []
    for t in tests:
        attempts = await db.test_attempts.find({"test_id": t["_id"]}).to_list(1000)
        pcts = [a["score"] / a["total"] * 100 for a in attempts if a.get("total")]
        test_stats.append({
            "title": t["title"],
            "attempts": len(attempts),
            "avg_pct": round(sum(pcts) / len(pcts)) if pcts else 0,
        })
    assignments = await db.assignments.find({"teacher_id": user["id"]}).to_list(100)
    assignment_stats = []
    for a in assignments:
        subs = await db.submissions.find({"assignment_id": a["_id"]}).to_list(1000)
        graded = len([s for s in subs if s.get("grade") is not None])
        assignment_stats.append({"title": a["title"], "submitted": len(subs), "graded": graded, "pending": len(subs) - graded})
    return {"courses": course_stats, "tests": test_stats, "assignments": assignment_stats}


@router.get("/dashboard/teacher")
async def teacher_dashboard(user: dict = Depends(require_role("teacher", "admin"))):
    now = datetime.now(timezone.utc).isoformat()
    courses = await db.courses.find({"teacher_id": user["id"]}).to_list(200)
    course_ids = [c["_id"] for c in courses]
    total_students = await db.enrollments.count_documents({"course_id": {"$in": course_ids}})
    tests = await db.tests.count_documents({"teacher_id": user["id"]})
    upcoming = await db.live_classes.find({"teacher_id": user["id"], "start_time": {"$gte": now}}).sort("start_time", 1).to_list(5)
    for c in upcoming:
        c["id"] = c.pop("_id")
    test_docs = await db.tests.find({"teacher_id": user["id"]}).to_list(200)
    test_ids = [t["_id"] for t in test_docs]
    attempts = await db.test_attempts.count_documents({"test_id": {"$in": test_ids}})
    return {
        "total_courses": len(courses),
        "total_students": total_students,
        "total_tests": tests,
        "total_attempts": attempts,
        "upcoming_classes": upcoming,
    }
