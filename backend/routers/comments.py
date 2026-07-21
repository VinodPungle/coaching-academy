"""Comments router: reusable threaded discussion for lessons and recordings."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter(tags=["comments"])


class CommentBody(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None


ContextType = Literal["lesson", "recording"]


async def _check_lesson_access(course_id: str, sub_topic_id: str, user: dict) -> dict:
    """Return the sub_topic dict if user can see it. Otherwise raise."""
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # find the sub topic
    sub_topic = None
    for section in course.get("sections", []):
        for st in section.get("sub_topics", []):
            if st["id"] == sub_topic_id:
                sub_topic = st
                break
    if not sub_topic:
        raise HTTPException(status_code=404, detail="Sub topic not found")
    if user["role"] == "student":
        enrollment = await db.enrollments.find_one({"course_id": course_id, "student_id": user["id"]})
        if not enrollment:
            raise HTTPException(status_code=403, detail="Enrol in this course to view comments")
    else:
        # teacher must own course; admin always allowed
        if user["role"] == "teacher" and course.get("teacher_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Not your course")
    return sub_topic


async def _check_live_class_access(class_id: str, user: dict) -> dict:
    live = await db.live_classes.find_one({"_id": class_id})
    if not live:
        raise HTTPException(status_code=404, detail="Live class not found")
    if user["role"] == "student":
        # student must be enrolled in one of the live class's target courses (if scoped)
        if live.get("course_id"):
            enrolled = await db.enrollments.find_one({"course_id": live["course_id"], "student_id": user["id"]})
            if not enrolled:
                raise HTTPException(status_code=403, detail="Enrol in this course to view the recording")
    elif user["role"] == "teacher" and live.get("teacher_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your live class")
    return live


@router.get("/lessons/{course_id}/{sub_topic_id}/{lesson_id}/comments")
async def list_lesson_comments(course_id: str, sub_topic_id: str, lesson_id: str, user: dict = Depends(get_current_user)):
    """Comments are threaded (parent_id) but flat-stored — the frontend
    reconstructs the tree client-side. Returns enabled=False (no comments
    payload needed) if the teacher toggled discussion off for this sub-topic."""
    sub_topic = await _check_lesson_access(course_id, sub_topic_id, user)
    if not sub_topic.get("comments_enabled", True):
        return {"enabled": False, "comments": []}
    docs = await db.comments.find({
        "context_type": "lesson",
        "context_id": lesson_id,
    }).sort("created_at", 1).to_list(2000)
    for d in docs:
        d["id"] = d.pop("_id")
    return {"enabled": True, "comments": docs}


@router.post("/lessons/{course_id}/{sub_topic_id}/{lesson_id}/comments")
async def post_lesson_comment(course_id: str, sub_topic_id: str, lesson_id: str, body: CommentBody, user: dict = Depends(get_current_user)):
    sub_topic = await _check_lesson_access(course_id, sub_topic_id, user)
    if not sub_topic.get("comments_enabled", True):
        raise HTTPException(status_code=403, detail="Comments are disabled by the teacher for this sub topic")
    doc = {
        "_id": str(uuid.uuid4()),
        "context_type": "lesson",
        "context_id": lesson_id,
        "course_id": course_id,
        "sub_topic_id": sub_topic_id,
        "parent_id": body.parent_id,
        "body": body.body.strip(),
        "author_id": user["id"],
        "author_name": user["name"],
        "author_role": user["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.comments.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/recordings/{class_id}/comments")
async def list_recording_comments(class_id: str, user: dict = Depends(get_current_user)):
    live = await _check_live_class_access(class_id, user)
    if not live.get("comments_enabled", True):
        return {"enabled": False, "comments": []}
    docs = await db.comments.find({
        "context_type": "recording",
        "context_id": class_id,
    }).sort("created_at", 1).to_list(2000)
    for d in docs:
        d["id"] = d.pop("_id")
    return {"enabled": True, "comments": docs}


@router.post("/recordings/{class_id}/comments")
async def post_recording_comment(class_id: str, body: CommentBody, user: dict = Depends(get_current_user)):
    live = await _check_live_class_access(class_id, user)
    if not live.get("comments_enabled", True):
        raise HTTPException(status_code=403, detail="Comments are disabled for this recording")
    doc = {
        "_id": str(uuid.uuid4()),
        "context_type": "recording",
        "context_id": class_id,
        "parent_id": body.parent_id,
        "body": body.body.strip(),
        "author_id": user["id"],
        "author_name": user["name"],
        "author_role": user["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.comments.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    """Three ways to be allowed to delete: you wrote it, you're an admin,
    or you're the teacher who owns the course/live-class the comment is on."""
    c = await db.comments.find_one({"_id": comment_id})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    is_author = c["author_id"] == user["id"]
    is_admin = user["role"] == "admin"
    is_owning_teacher = False
    if user["role"] == "teacher":
        if c["context_type"] == "lesson":
            course = await db.courses.find_one({"_id": c.get("course_id")})
            is_owning_teacher = course and course.get("teacher_id") == user["id"]
        elif c["context_type"] == "recording":
            live = await db.live_classes.find_one({"_id": c["context_id"]})
            is_owning_teacher = live and live.get("teacher_id") == user["id"]
    if not (is_author or is_admin or is_owning_teacher):
        raise HTTPException(status_code=403, detail="You can only delete your own comment")
    # cascade: delete replies
    await db.comments.delete_many({"parent_id": comment_id})
    await db.comments.delete_one({"_id": comment_id})
    return {"message": "Comment deleted"}


class RecordingCommentsToggleBody(BaseModel):
    comments_enabled: bool


@router.put("/live-classes/{class_id}/comments-toggle")
async def toggle_recording_comments(class_id: str, body: RecordingCommentsToggleBody, user: dict = Depends(require_role("teacher", "admin"))):
    query = {"_id": class_id} if user["role"] == "admin" else {"_id": class_id, "teacher_id": user["id"]}
    result = await db.live_classes.update_one(query, {"$set": {"comments_enabled": body.comments_enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Live class not found")
    return {"message": "Updated", "comments_enabled": body.comments_enabled}
