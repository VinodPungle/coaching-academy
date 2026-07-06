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
    course_ids = [c["_id"] for c in courses]
    enroll_counts = {
        r["_id"]: r["n"]
        for r in await db.enrollments.aggregate([
            {"$match": {"course_id": {"$in": course_ids}}},
            {"$group": {"_id": "$course_id", "n": {"$sum": 1}}},
        ]).to_list(500)
    }
    course_stats = [{"title": c["title"], "students": enroll_counts.get(c["_id"], 0)} for c in courses]

    tests = await db.tests.find({"teacher_id": user["id"]}).to_list(100)
    test_ids = [t["_id"] for t in tests]
    attempt_agg = {
        r["_id"]: r
        for r in await db.test_attempts.aggregate([
            {"$match": {"test_id": {"$in": test_ids}}},
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
    sub_agg = {
        r["_id"]: r
        for r in await db.submissions.aggregate([
            {"$match": {"assignment_id": {"$in": assignment_ids}}},
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
