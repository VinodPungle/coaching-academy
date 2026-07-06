import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["assignments"])


class AssignmentBody(BaseModel):
    title: str
    subject: str
    description: str = ""
    due_date: str = ""
    max_marks: int = 10
    course_id: Optional[str] = None


class SubmissionBody(BaseModel):
    content: str
    link: str = ""
    file_url: str = ""
    file_name: str = ""


class GradeBody(BaseModel):
    grade: float
    feedback: str = ""


@router.get("/assignments")
async def list_assignments(user: dict = Depends(get_current_user)):
    if user["role"] in ("teacher", "admin"):
        docs = await db.assignments.find({"teacher_id": user["id"]}).sort("created_at", -1).to_list(200)
        result = []
        for d in docs:
            d["id"] = d.pop("_id")
            d["submission_count"] = await db.submissions.count_documents({"assignment_id": d["id"]})
            result.append(d)
        return result
    enrollments = await db.enrollments.find({"student_id": user["id"]}).to_list(500)
    my_courses = [e["course_id"] for e in enrollments]
    docs = await db.assignments.find({"course_id": {"$in": [None, *my_courses]}}).sort("created_at", -1).to_list(200)
    result = []
    for d in docs:
        d["id"] = d.pop("_id")
        sub = await db.submissions.find_one({"assignment_id": d["id"], "student_id": user["id"]})
        if sub:
            sub["id"] = sub.pop("_id")
        d["my_submission"] = sub
        result.append(d)
    return result


@router.post("/assignments")
async def create_assignment(body: AssignmentBody, user: dict = Depends(require_role("teacher", "admin"))):
    doc = body.model_dump()
    course_name = None
    if body.course_id:
        course = await db.courses.find_one({"_id": body.course_id})
        if not course:
            raise HTTPException(status_code=404, detail="Linked course not found")
        course_name = course["title"]
    doc["course_name"] = course_name
    doc.update({
        "_id": str(uuid.uuid4()),
        "teacher_id": user["id"],
        "teacher_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.assignments.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.assignments.delete_one({"_id": assignment_id, "teacher_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.submissions.delete_many({"assignment_id": assignment_id})
    return {"message": "Assignment deleted"}


@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: str, body: SubmissionBody, user: dict = Depends(require_role("student"))):
    assignment = await db.assignments.find_one({"_id": assignment_id})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    existing = await db.submissions.find_one({"assignment_id": assignment_id, "student_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted this assignment")
    doc = {
        "_id": str(uuid.uuid4()),
        "assignment_id": assignment_id,
        "student_id": user["id"],
        "student_name": user["name"],
        "content": body.content,
        "link": body.link,
        "file_url": body.file_url,
        "file_name": body.file_name,
        "grade": None,
        "feedback": "",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.submissions.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/assignments/{assignment_id}/submissions")
async def list_submissions(assignment_id: str, user: dict = Depends(require_role("teacher", "admin"))):
    docs = await db.submissions.find({"assignment_id": assignment_id}).sort("submitted_at", -1).to_list(500)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.put("/submissions/{submission_id}/grade")
async def grade_submission(submission_id: str, body: GradeBody, user: dict = Depends(require_role("teacher", "admin"))):
    result = await db.submissions.update_one(
        {"_id": submission_id}, {"$set": {"grade": body.grade, "feedback": body.feedback}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Graded"}
