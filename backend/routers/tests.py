import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["tests"])


async def resolve_course(course_id):
    if not course_id:
        return None, None
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Linked course not found")
    return course_id, course["title"]


async def enrolled_course_ids(student_id: str):
    enrollments = await db.enrollments.find({"student_id": student_id}).to_list(500)
    return [e["course_id"] for e in enrollments]


class QuestionBody(BaseModel):
    text: str
    options: List[str]
    correct_index: int
    marks: int = 4


class TestBody(BaseModel):
    title: str
    subject: str
    duration_min: int = 60
    published: bool = True
    course_id: Optional[str] = None
    questions: List[QuestionBody] = []


class AttemptBody(BaseModel):
    answers: Dict[str, int]


def test_out(doc: dict, hide_answers: bool = False) -> dict:
    doc["id"] = doc.pop("_id")
    if hide_answers:
        for q in doc.get("questions", []):
            q.pop("correct_index", None)
    return doc


@router.get("/tests")
async def list_tests(user: dict = Depends(get_current_user)):
    if user["role"] in ("teacher", "admin"):
        docs = await db.tests.find({"teacher_id": user["id"]}).sort("created_at", -1).to_list(200)
        result = []
        for d in docs:
            d = test_out(d)
            d["attempt_count"] = await db.test_attempts.count_documents({"test_id": d["id"]})
            result.append(d)
        return result
    my_courses = await enrolled_course_ids(user["id"])
    docs = await db.tests.find({"published": True, "course_id": {"$in": [None, *my_courses]}}).sort("created_at", -1).to_list(200)
    result = []
    for d in docs:
        d = test_out(d, hide_answers=True)
        attempt = await db.test_attempts.find_one({"test_id": d["id"], "student_id": user["id"]})
        d["my_attempt"] = {"score": attempt["score"], "total": attempt["total"]} if attempt else None
        result.append(d)
    return result


@router.get("/tests/{test_id}")
async def get_test(test_id: str, user: dict = Depends(get_current_user)):
    doc = await db.tests.find_one({"_id": test_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Test not found")
    hide = user["role"] == "student"
    doc = test_out(doc, hide_answers=hide)
    if user["role"] == "student":
        attempt = await db.test_attempts.find_one({"test_id": test_id, "student_id": user["id"]})
        doc["my_attempt"] = None
        if attempt:
            attempt["id"] = attempt.pop("_id")
            doc["my_attempt"] = attempt
    return doc


@router.post("/tests")
async def create_test(body: TestBody, user: dict = Depends(require_role("teacher", "admin"))):
    questions = [{"id": str(uuid.uuid4()), **q.model_dump()} for q in body.questions]
    course_id, course_name = await resolve_course(body.course_id)
    doc = {
        "_id": str(uuid.uuid4()),
        "title": body.title,
        "subject": body.subject,
        "duration_min": body.duration_min,
        "published": body.published,
        "course_id": course_id,
        "course_name": course_name,
        "questions": questions,
        "total_marks": sum(q["marks"] for q in questions),
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tests.insert_one(doc)
    return test_out(doc)


@router.put("/tests/{test_id}")
async def update_test(test_id: str, body: TestBody, user: dict = Depends(require_role("teacher", "admin"))):
    existing = await db.tests.find_one({"_id": test_id, "teacher_id": user["id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Test not found")
    questions = [{"id": str(uuid.uuid4()), **q.model_dump()} for q in body.questions]
    course_id, course_name = await resolve_course(body.course_id)
    update = {
        "title": body.title,
        "subject": body.subject,
        "duration_min": body.duration_min,
        "published": body.published,
        "course_id": course_id,
        "course_name": course_name,
        "questions": questions,
        "total_marks": sum(q["marks"] for q in questions),
    }
    await db.tests.update_one({"_id": test_id}, {"$set": update})
    existing.update(update)
    return test_out(existing)


@router.delete("/tests/{test_id}")
async def delete_test(test_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.tests.delete_one({"_id": test_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Test not found")
    await db.test_attempts.delete_many({"test_id": test_id})
    return {"message": "Test deleted"}


@router.post("/tests/{test_id}/attempt")
async def submit_attempt(test_id: str, body: AttemptBody, user: dict = Depends(require_role("student"))):
    test = await db.tests.find_one({"_id": test_id})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    existing = await db.test_attempts.find_one({"test_id": test_id, "student_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You have already attempted this test")
    score = 0
    correct = 0
    for q in test.get("questions", []):
        if body.answers.get(q["id"]) == q["correct_index"]:
            score += q.get("marks", 4)
            correct += 1
    doc = {
        "_id": str(uuid.uuid4()),
        "test_id": test_id,
        "test_title": test["title"],
        "student_id": user["id"],
        "student_name": user["name"],
        "answers": body.answers,
        "score": score,
        "total": test.get("total_marks", 0),
        "correct_count": correct,
        "question_count": len(test.get("questions", [])),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.test_attempts.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/tests/{test_id}/attempts")
async def test_attempts(test_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    docs = await db.test_attempts.find({"test_id": test_id}).sort("score", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.get("/student/attempts")
async def my_attempts(user: dict = Depends(require_role("student"))):
    docs = await db.test_attempts.find({"student_id": user["id"]}).sort("submitted_at", -1).to_list(200)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs
