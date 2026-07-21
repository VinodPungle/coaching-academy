# Aggregated "home page" data for students and teachers — each endpoint
# runs several counts/aggregations across other collections rather than
# exposing a single new one. Demo accounts' activity is excluded from
# these aggregates for everyone except the demo accounts themselves, so
# public-demo usage doesn't skew a real teacher's stats.
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from database import db
from auth_utils import require_role, can_see_demo_content, demo_user_ids
from routers.live_classes import student_class_query

router = APIRouter(tags=["dashboard"])


async def _demo_teacher_ids() -> list:
    """Return teacher-role user_ids that are flagged as demo."""
    ids = [u["_id"] async for u in db.users.find({"role": "teacher", "is_demo": True}, {"_id": 1})]
    return ids


@router.get("/dashboard/student")
async def student_dashboard(user: dict = Depends(require_role("student"))):
    """Student home page: enrollment/test/assignment counts, average test
    score, next 5 upcoming classes visible to this student, 3 latest
    announcements, and up to 8 free courses they haven't enrolled in yet."""
    now = datetime.now(timezone.utc).isoformat()
    hide_demo = not can_see_demo_content(user)
    demo_teachers = await _demo_teacher_ids() if hide_demo else []

    enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(200)
    enrolled_ids = {e["course_id"] for e in enrollments}
    attempts = await db.test_attempts.find({"student_id": user["id"]}).to_list(200)

    class_q = await student_class_query(user["id"])
    class_q = {**class_q, "start_time": {"$gte": now}}
    if hide_demo:
        class_q["demo_scope"] = {"$ne": True}
    upcoming = await db.live_classes.find(class_q).sort("start_time", 1).to_list(5)
    for c in upcoming:
        c["id"] = c.pop("_id")

    ann_q = {}
    if hide_demo:
        ann_q["demo_scope"] = {"$ne": True}
    announcements = await db.announcements.find(ann_q).sort("created_at", -1).to_list(3)
    for a in announcements:
        a["id"] = a.pop("_id")

    submissions = await db.submissions.count_documents({"student_id": user["id"]})
    assignments_q = {}
    if hide_demo:
        assignments_q["demo_scope"] = {"$ne": True}
    total_assignments = await db.assignments.count_documents(assignments_q)
    avg_score = 0
    if attempts:
        pcts = [a["score"] / a["total"] * 100 for a in attempts if a.get("total")]
        avg_score = round(sum(pcts) / len(pcts)) if pcts else 0
    free_q = {"published": True, "$or": [{"is_free": True}, {"price": 0}]}
    if hide_demo:
        free_q["demo_scope"] = {"$ne": True}
    free = await db.courses.find(free_q).sort("created_at", -1).to_list(50)
    free_courses = []
    for c in free:
        if c["_id"] in enrolled_ids:
            continue
        free_courses.append({
            "id": c["_id"],
            "title": c["title"],
            "subject": c["subject"],
            "description": (c.get("description") or "")[:140],
            "thumbnail": c.get("thumbnail", ""),
            "teacher_name": c.get("teacher_name"),
        })
    return {
        "enrolled_courses": len(enrollments),
        "tests_attempted": len(attempts),
        "avg_score_pct": avg_score,
        "pending_assignments": max(total_assignments - submissions, 0),
        "upcoming_classes": upcoming,
        "recent_announcements": announcements,
        "free_courses": free_courses[:8],
    }


@router.get("/dashboard/teacher/analytics")
async def teacher_analytics(user: dict = Depends(require_role("teacher", "admin"))):
    """Per-course/per-test/per-assignment breakdown for the teacher's
    analytics view — enrollment counts, attempt counts + average score,
    and submission/grading progress, each computed via a single Mongo
    aggregation (grouped by the parent id) instead of looping per-item."""
    courses = await db.courses.find({"teacher_id": user["id"]}).to_list(100)
    course_ids = [c["_id"] for c in courses]
    demo_students = [u["_id"] async for u in db.users.find({"is_demo": True}, {"_id": 1})]
    enroll_match = {"course_id": {"$in": course_ids}}
    if demo_students:
        enroll_match["student_id"] = {"$nin": demo_students}
    enroll_counts = {
        r["_id"]: r["n"]
        for r in await db.enrollments.aggregate([
            {"$match": enroll_match},
            {"$group": {"_id": "$course_id", "n": {"$sum": 1}}},
        ]).to_list(500)
    }
    course_stats = [{"title": c["title"], "students": enroll_counts.get(c["_id"], 0)} for c in courses]

    tests = await db.tests.find({"teacher_id": user["id"]}).to_list(100)
    test_ids = [t["_id"] for t in tests]
    attempt_match = {"test_id": {"$in": test_ids}}
    if demo_students:
        attempt_match["student_id"] = {"$nin": demo_students}
    attempt_agg = {
        r["_id"]: r
        for r in await db.test_attempts.aggregate([
            {"$match": attempt_match},
            {"$group": {
                "_id": "$test_id",
                "n": {"$sum": 1},
                "avg": {"$avg": {"$cond": [{"$gt": ["$total", 0]}, {"$multiply": [{"$divide": ["$score", "$total"]}, 100]}, 0]}},
            }},
        ]).to_list(500)
    }
    test_stats = [
        {"title": t["title"], "attempts": attempt_agg.get(t["_id"], {}).get("n", 0),
         "avg_pct": round(attempt_agg.get(t["_id"], {}).get("avg") or 0)}
        for t in tests
    ]

    assignments = await db.assignments.find({"teacher_id": user["id"]}).to_list(100)
    assignment_ids = [a["_id"] for a in assignments]
    sub_match = {"assignment_id": {"$in": assignment_ids}}
    if demo_students:
        sub_match["student_id"] = {"$nin": demo_students}
    sub_agg = {
        r["_id"]: r
        for r in await db.submissions.aggregate([
            {"$match": sub_match},
            {"$group": {
                "_id": "$assignment_id",
                "submitted": {"$sum": 1},
                "graded": {"$sum": {"$cond": [{"$ne": ["$grade", None]}, 1, 0]}},
            }},
        ]).to_list(500)
    }
    assignment_stats = []
    for a in assignments:
        r = sub_agg.get(a["_id"], {})
        submitted = r.get("submitted", 0)
        graded = r.get("graded", 0)
        assignment_stats.append({"title": a["title"], "submitted": submitted, "graded": graded, "pending": submitted - graded})
    return {"courses": course_stats, "tests": test_stats, "assignments": assignment_stats}


@router.get("/dashboard/teacher")
async def teacher_dashboard(user: dict = Depends(require_role("teacher", "admin"))):
    """Teacher home page: high-level totals (courses/students/tests/attempts)
    plus the next 5 of their own upcoming live classes."""
    now = datetime.now(timezone.utc).isoformat()
    demo_ids = await demo_user_ids()
    # Exclude demo students from the teacher's aggregate counts (unless the teacher IS the demo teacher).
    exclude_demo = user["id"] not in demo_ids
    courses = await db.courses.find({"teacher_id": user["id"]}).to_list(200)
    course_ids = [c["_id"] for c in courses]
    enroll_q = {"course_id": {"$in": course_ids}}
    if exclude_demo and demo_ids:
        enroll_q["student_id"] = {"$nin": demo_ids}
    total_students = await db.enrollments.count_documents(enroll_q)
    tests = await db.tests.count_documents({"teacher_id": user["id"]})
    upcoming = await db.live_classes.find({"teacher_id": user["id"], "start_time": {"$gte": now}}).sort("start_time", 1).to_list(5)
    for c in upcoming:
        c["id"] = c.pop("_id")
    test_docs = await db.tests.find({"teacher_id": user["id"]}).to_list(200)
    test_ids = [t["_id"] for t in test_docs]
    attempt_q = {"test_id": {"$in": test_ids}}
    if exclude_demo and demo_ids:
        attempt_q["student_id"] = {"$nin": demo_ids}
    attempts = await db.test_attempts.count_documents(attempt_q)
    return {
        "total_courses": len(courses),
        "total_students": total_students,
        "total_tests": tests,
        "total_attempts": attempts,
        "upcoming_classes": upcoming,
    }
