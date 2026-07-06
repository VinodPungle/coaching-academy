from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleBody(BaseModel):
    role: str


@router.get("/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    students = await db.users.count_documents({"role": "student"})
    teachers = await db.users.count_documents({"role": "teacher"})
    courses = await db.courses.count_documents({})
    enrollments = await db.enrollments.count_documents({})
    tests = await db.tests.count_documents({})
    attempts = await db.test_attempts.count_documents({})
    revenue_agg = await db.payments.aggregate([
        {"$match": {"status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]).to_list(1)
    revenue = revenue_agg[0]["total"] if revenue_agg else 0
    paid_count = revenue_agg[0]["count"] if revenue_agg else 0
    recent = await db.users.find({}, {"password_hash": 0}).sort("created_at", -1).to_list(6)
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
    query = {}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    if role in ("student", "teacher", "admin"):
        query["role"] = role
    docs = await db.users.find(query, {"password_hash": 0}).sort("created_at", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.put("/users/{user_id}/role")
async def change_role(user_id: str, body: RoleBody, user: dict = Depends(require_role("admin"))):
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
    docs = await db.payments.find({}).sort("created_at", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
    total = sum(d["amount"] for d in docs if d["status"] == "paid")
    return {"payments": docs, "total_revenue": total}
