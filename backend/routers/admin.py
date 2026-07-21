# Admin-only platform oversight: dashboard stats, user management
# (search/role-change/delete), per-teacher breakdowns, and a top-performers
# leaderboard. Every endpoint requires require_role("admin"); most also
# exclude demo accounts/content from real-platform aggregates so public
# demo activity doesn't skew what the admin sees.
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import require_role, demo_user_ids

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleBody(BaseModel):
    role: str


@router.get("/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    """Top-level platform counters (students, teachers, courses,
    enrollments, tests, attempts, revenue) plus the 6 most recently
    registered users — all excluding demo accounts/content."""
    demo_ids = await demo_user_ids()
    real_user_q = {"is_demo": {"$ne": True}}
    students = await db.users.count_documents({"role": "student", **real_user_q})
    teachers = await db.users.count_documents({"role": "teacher", **real_user_q})
    courses = await db.courses.count_documents({"demo_scope": {"$ne": True}})
    enroll_q = {"student_id": {"$nin": demo_ids}} if demo_ids else {}
    enrollments = await db.enrollments.count_documents(enroll_q)
    tests = await db.tests.count_documents({"demo_scope": {"$ne": True}})
    attempts_q = {"student_id": {"$nin": demo_ids}} if demo_ids else {}
    attempts = await db.test_attempts.count_documents(attempts_q)
    revenue_match = {"status": "paid", "is_test_txn": {"$ne": True}}
    if demo_ids:
        revenue_match["student_id"] = {"$nin": demo_ids}
    revenue_agg = await db.payments.aggregate([
        {"$match": revenue_match},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]).to_list(1)
    revenue = revenue_agg[0]["total"] if revenue_agg else 0
    paid_count = revenue_agg[0]["count"] if revenue_agg else 0
    recent = await db.users.find({"is_demo": {"$ne": True}}, {"password_hash": 0}).sort("created_at", -1).to_list(6)
    for r in recent:
        r["id"] = r.pop("_id")
    return {
        "students": students,
        "teachers": teachers,
        "courses": courses,
        "enrollments": enrollments,
        "tests": tests,
        "attempts": attempts,
        "revenue": revenue,
        "paid_count": paid_count,
        "recent_users": recent,
    }


@router.get("/users")
async def admin_users(q: Optional[str] = None, role: Optional[str] = None, user: dict = Depends(require_role("admin"))):
    """Search/filter every user (any role, including demo — this endpoint
    is not demo-filtered since admins need to see everything)."""
    query = {}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    if role in ("student", "teacher", "admin"):
        query["role"] = role
    docs = await db.users.find(query, {"password_hash": 0}).sort("created_at", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
        d.setdefault("phone", "")
    return docs


class CleanupResponse(BaseModel):
    deleted: int
    deleted_users: List[str]


@router.post("/cleanup-test-users")
async def cleanup_test_users(user: dict = Depends(require_role("admin"))):
    """Delete users whose name starts with 'TEST_' or 'TEST ' (test artefacts). Also cleans their courses/enrollments.
    Housekeeping endpoint for wiping accounts left behind by automated test
    suites (see backend/tests/*.py, which create TEST_-prefixed users)."""
    query = {"$or": [
        {"name": {"$regex": "^TEST[_ ]", "$options": "i"}},
        {"email": {"$regex": "^test[_-]?(teach|it3|new)", "$options": "i"}},
    ], "role": {"$ne": "admin"}}
    victims = await db.users.find(query, {"_id": 1, "name": 1, "email": 1, "role": 1}).to_list(1000)
    deleted_names = []
    for v in victims:
        uid = v["_id"]
        # cascade: remove their courses/tests/assignments/live-classes/enrollments/attempts
        their_courses = await db.courses.find({"teacher_id": uid}, {"_id": 1}).to_list(1000)
        their_course_ids = [c["_id"] for c in their_courses]
        if their_course_ids:
            await db.enrollments.delete_many({"course_id": {"$in": their_course_ids}})
            await db.batches.delete_many({"course_id": {"$in": their_course_ids}})
        await db.courses.delete_many({"teacher_id": uid})
        await db.tests.delete_many({"teacher_id": uid})
        await db.assignments.delete_many({"teacher_id": uid})
        await db.live_classes.delete_many({"teacher_id": uid})
        await db.announcements.delete_many({"teacher_id": uid})
        await db.enrollments.delete_many({"student_id": uid})
        await db.test_attempts.delete_many({"student_id": uid})
        await db.submissions.delete_many({"student_id": uid})
        await db.notifications.delete_many({"user_id": uid})
        await db.users.delete_one({"_id": uid})
        deleted_names.append(f"{v['name']} ({v['email']})")
    return {"deleted": len(victims), "deleted_users": deleted_names}


@router.put("/users/{user_id}/role")
async def change_role(user_id: str, body: RoleBody, user: dict = Depends(require_role("admin"))):
    """Change a user's role. Self-role-change is blocked so an admin can't
    accidentally lock themselves out of admin tools."""
    if body.role not in ("student", "teacher", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    result = await db.users.update_one({"_id": user_id}, {"$set": {"role": body.role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"Role updated to {body.role}"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_role("admin"))):
    """Deletes a user and cascades all of their owned data — for a teacher
    this includes every course they created (and everything nested under
    those courses' enrollments/tests/etc.), so this is destructive and
    irreversible; there's no soft-delete/undo."""
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    target = await db.users.find_one({"_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.delete_one({"_id": user_id})
    await db.enrollments.delete_many({"student_id": user_id})
    await db.test_attempts.delete_many({"student_id": user_id})
    await db.submissions.delete_many({"student_id": user_id})
    await db.notifications.delete_many({"user_id": user_id})
    await db.certificates.delete_many({"student_id": user_id})
    if target["role"] == "teacher":
        courses = await db.courses.find({"teacher_id": user_id}).to_list(500)
        course_ids = [c["_id"] for c in courses]
        await db.courses.delete_many({"teacher_id": user_id})
        await db.enrollments.delete_many({"course_id": {"$in": course_ids}})
        await db.batches.delete_many({"teacher_id": user_id})
        tests = await db.tests.find({"teacher_id": user_id}).to_list(500)
        await db.test_attempts.delete_many({"test_id": {"$in": [t["_id"] for t in tests]}})
        await db.tests.delete_many({"teacher_id": user_id})
        assignments = await db.assignments.find({"teacher_id": user_id}).to_list(500)
        await db.submissions.delete_many({"assignment_id": {"$in": [a["_id"] for a in assignments]}})
        await db.assignments.delete_many({"teacher_id": user_id})
        await db.live_classes.delete_many({"teacher_id": user_id})
        await db.announcements.delete_many({"teacher_id": user_id})
    return {"message": f"User {target['name']} and related data deleted"}


@router.get("/payments")
async def admin_payments(user: dict = Depends(require_role("admin"))):
    """All real (non-demo, non-test) payments plus their total, newest first."""
    demo_ids = await demo_user_ids()
    query = {"is_test_txn": {"$ne": True}}
    if demo_ids:
        query["student_id"] = {"$nin": demo_ids}
    docs = await db.payments.find(query).sort("created_at", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
    total = sum(d["amount"] for d in docs if d["status"] == "paid")
    return {"payments": docs, "total_revenue": total}


@router.get("/teachers")
async def admin_teachers(user: dict = Depends(require_role("admin"))):
    """Per-teacher breakdown: courses, students, tests, live classes, assignments (upcoming/past).
    Every count below is computed with one grouped aggregation per
    metric (not per-teacher loops), then merged into each teacher's row."""
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    teachers = await db.users.find({"role": "teacher", "is_demo": {"$ne": True}}, {"password_hash": 0}).sort("created_at", -1).to_list(500)
    if not teachers:
        return []
    tids = [t["_id"] for t in teachers]

    course_counts = {r["_id"]: r["n"] for r in await db.courses.aggregate([
        {"$match": {"teacher_id": {"$in": tids}}},
        {"$group": {"_id": "$teacher_id", "n": {"$sum": 1}}},
    ]).to_list(1000)}
    test_counts = {r["_id"]: r["n"] for r in await db.tests.aggregate([
        {"$match": {"teacher_id": {"$in": tids}}},
        {"$group": {"_id": "$teacher_id", "n": {"$sum": 1}}},
    ]).to_list(1000)}
    assignment_counts = {r["_id"]: r["n"] for r in await db.assignments.aggregate([
        {"$match": {"teacher_id": {"$in": tids}}},
        {"$group": {"_id": "$teacher_id", "n": {"$sum": 1}}},
    ]).to_list(1000)}
    upcoming_lc = {r["_id"]: r["n"] for r in await db.live_classes.aggregate([
        {"$match": {"teacher_id": {"$in": tids}, "start_time": {"$gte": now_iso}}},
        {"$group": {"_id": "$teacher_id", "n": {"$sum": 1}}},
    ]).to_list(1000)}
    past_lc = {r["_id"]: r["n"] for r in await db.live_classes.aggregate([
        {"$match": {"teacher_id": {"$in": tids}, "start_time": {"$lt": now_iso}}},
        {"$group": {"_id": "$teacher_id", "n": {"$sum": 1}}},
    ]).to_list(1000)}
    # students enrolled per teacher (via their courses)
    courses_by_teacher = {}
    async for c in db.courses.find({"teacher_id": {"$in": tids}}, {"_id": 1, "teacher_id": 1}):
        courses_by_teacher.setdefault(c["teacher_id"], []).append(c["_id"])
    student_counts = {}
    for tid, cids in courses_by_teacher.items():
        student_counts[tid] = await db.enrollments.count_documents({"course_id": {"$in": cids}})

    result = []
    for t in teachers:
        tid = t["_id"]
        result.append({
            "id": tid,
            "name": t["name"],
            "email": t["email"],
            "phone": t.get("phone", ""),
            "created_at": t.get("created_at"),
            "courses": course_counts.get(tid, 0),
            "students": student_counts.get(tid, 0),
            "tests": test_counts.get(tid, 0),
            "assignments": assignment_counts.get(tid, 0),
            "upcoming_classes": upcoming_lc.get(tid, 0),
            "past_classes": past_lc.get(tid, 0),
        })
    return result


@router.get("/teachers/{teacher_id}/detail")
async def admin_teacher_detail(teacher_id: str, user: dict = Depends(require_role("admin"))):
    """Drill-down for one teacher: their courses (with student counts),
    tests (with attempt counts), live classes, and assignments — the
    expanded view behind admin_teachers()'s summary row."""
    teacher = await db.users.find_one({"_id": teacher_id, "role": "teacher"}, {"password_hash": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher["id"] = teacher.pop("_id")
    courses = await db.courses.find({"teacher_id": teacher_id}).to_list(200)
    course_ids = [c["_id"] for c in courses]
    enroll_counts = {r["_id"]: r["n"] for r in await db.enrollments.aggregate([
        {"$match": {"course_id": {"$in": course_ids}}},
        {"$group": {"_id": "$course_id", "n": {"$sum": 1}}},
    ]).to_list(500)}
    course_out = []
    for c in courses:
        course_out.append({
            "id": c["_id"], "title": c["title"], "subject": c.get("subject"),
            "students": enroll_counts.get(c["_id"], 0),
            "published": c.get("published", True),
        })
    tests = await db.tests.find({"teacher_id": teacher_id}).to_list(200)
    test_ids = [t["_id"] for t in tests]
    attempt_counts = {r["_id"]: r["n"] for r in await db.test_attempts.aggregate([
        {"$match": {"test_id": {"$in": test_ids}}},
        {"$group": {"_id": "$test_id", "n": {"$sum": 1}}},
    ]).to_list(500)}
    tests_out = [{
        "id": t["_id"], "title": t["title"], "subject": t.get("subject"),
        "course_name": t.get("course_name"), "attempts": attempt_counts.get(t["_id"], 0),
    } for t in tests]
    classes = await db.live_classes.find({"teacher_id": teacher_id}).sort("start_time", -1).to_list(200)
    classes_out = [{
        "id": c["_id"], "title": c["title"], "subject": c.get("subject"),
        "start_time": c.get("start_time"), "course_name": c.get("course_name"),
        "batch_name": c.get("batch_name"),
    } for c in classes]
    assignments = await db.assignments.find({"teacher_id": teacher_id}).sort("created_at", -1).to_list(200)
    assignments_out = [{
        "id": a["_id"], "title": a["title"], "subject": a.get("subject"),
        "course_name": a.get("course_name"), "due_date": a.get("due_date"),
    } for a in assignments]
    return {
        "teacher": teacher,
        "courses": course_out,
        "tests": tests_out,
        "live_classes": classes_out,
        "assignments": assignments_out,
    }


@router.get("/top-performers")
async def admin_top_performers(limit: int = 5, user: dict = Depends(require_role("admin"))):
    """Top performers per batch and per course, ranked by average test %. Excludes demo users.
    First computes each student's overall avg_pct across all their test
    attempts (one aggregation), then for every course/batch, filters that
    global stats map down to its enrolled students and sorts."""
    demo_ids = await demo_user_ids()
    match = {"total": {"$gt": 0}}
    if demo_ids:
        match["student_id"] = {"$nin": demo_ids}
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$student_id",
            "avg_pct": {"$avg": {"$multiply": [{"$divide": ["$score", "$total"]}, 100]}},
            "attempts": {"$sum": 1},
            "student_name": {"$first": "$student_name"},
        }},
    ]
    stats = {r["_id"]: r for r in await db.test_attempts.aggregate(pipeline).to_list(5000)}

    # Per course (from enrollments) — skip demo-scoped courses
    courses = await db.courses.find({"demo_scope": {"$ne": True}}, {"_id": 1, "title": 1}).to_list(500)
    course_top = []
    for c in courses:
        enrolls = await db.enrollments.find({"course_id": c["_id"]}).to_list(2000)
        rows = []
        for e in enrolls:
            s = stats.get(e["student_id"])
            if s:
                rows.append({
                    "student_id": e["student_id"],
                    "student_name": s["student_name"],
                    "avg_pct": round(s["avg_pct"]),
                    "attempts": s["attempts"],
                })
        rows.sort(key=lambda r: (-r["avg_pct"], -r["attempts"]))
        course_top.append({
            "course_id": c["_id"],
            "course_title": c["title"],
            "top": rows[:limit],
        })

    # Per batch
    batches = await db.batches.find({}).to_list(500)
    course_titles = {c["_id"]: c["title"] for c in courses}
    batch_top = []
    for b in batches:
        enrolls = await db.enrollments.find({"batch_id": b["_id"]}).to_list(2000)
        rows = []
        for e in enrolls:
            s = stats.get(e["student_id"])
            if s:
                rows.append({
                    "student_id": e["student_id"],
                    "student_name": s["student_name"],
                    "avg_pct": round(s["avg_pct"]),
                    "attempts": s["attempts"],
                })
        rows.sort(key=lambda r: (-r["avg_pct"], -r["attempts"]))
        batch_top.append({
            "batch_id": b["_id"],
            "batch_name": b["name"],
            "course_title": course_titles.get(b.get("course_id"), ""),
            "top": rows[:limit],
        })

    return {"per_course": course_top, "per_batch": batch_top}
