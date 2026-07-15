"""
Teacher profiles — public directory + edit endpoints.

Uses `db.teacher_profiles` collection keyed by teacher user_id. Missing profiles
are surfaced with an empty bio so admins can seed them from the CMS.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from database import db
from auth_utils import require_role, get_current_user, optional_user, DEMO_TEACHER_EMAIL

logger = logging.getLogger(__name__)
router = APIRouter(tags=["teacher-profiles"])


class ProfileBody(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=200)
    subtitle: Optional[str] = Field(default=None, max_length=300)
    bio: Optional[str] = Field(default=None, max_length=5000)
    photo_url: Optional[str] = Field(default=None, max_length=2000)


def _profile_out(user: dict, profile: dict | None) -> dict:
    p = profile or {}
    return {
        "id": user["_id"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "display_name": p.get("display_name") or user.get("name", ""),
        "subtitle": p.get("subtitle") or "",
        "bio": p.get("bio") or "",
        "photo_url": p.get("photo_url") or "",
        "updated_at": p.get("updated_at"),
    }


@router.get("/teacher-profiles")
async def list_profiles(user: dict | None = Depends(optional_user)):
    """Public — returns all teachers with their profiles for the public page.
    Demo teacher is hidden from everyone except admin (so admin can still edit
    the demo profile from the CMS)."""
    query = {"role": "teacher"}
    if not user or user.get("role") != "admin":
        query["email"] = {"$ne": DEMO_TEACHER_EMAIL}
    teachers = await db.users.find(query, {"name": 1, "email": 1}).to_list(1000)
    profiles = {p["_id"]: p async for p in db.teacher_profiles.find({})}
    result = []
    for t in sorted(teachers, key=lambda u: u.get("name") or u.get("email") or ""):
        result.append(_profile_out(t, profiles.get(t["_id"])))
    return result


@router.put("/teacher-profiles/{teacher_id}")
async def update_profile(teacher_id: str, body: ProfileBody, user: dict = Depends(get_current_user)):
    if user["role"] != "admin" and user["id"] != teacher_id:
        raise HTTPException(status_code=403, detail="You can only edit your own profile")
    teacher = await db.users.find_one({"_id": teacher_id, "role": "teacher"})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user["id"]}
    for field in ("display_name", "subtitle", "bio", "photo_url"):
        val = getattr(body, field)
        if val is not None:
            val = val.strip() if isinstance(val, str) else val
            # Validate URL: allow empty (removes photo), /api/files/... paths, or absolute http(s) URLs
            if field == "photo_url" and val:
                if not (val.startswith("/api/files/") or val.startswith("http://") or val.startswith("https://")):
                    raise HTTPException(status_code=400, detail="photo_url must be an http(s) URL or an /api/files/... path")
            update[field] = val
    await db.teacher_profiles.update_one({"_id": teacher_id}, {"$set": update}, upsert=True)
    profile = await db.teacher_profiles.find_one({"_id": teacher_id})
    return _profile_out(teacher, profile)


@router.get("/teacher-profiles/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers have profiles")
    teacher = await db.users.find_one({"_id": user["id"]})
    profile = await db.teacher_profiles.find_one({"_id": user["id"]})
    return _profile_out(teacher, profile)
