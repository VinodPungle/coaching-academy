"""
Runtime site configuration — brand name + landing page copy stored in MongoDB,
editable by admins, cached in memory with an invalidation on write.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import db
from auth_utils import require_role

logger = logging.getLogger(__name__)
router = APIRouter(tags=["site-config"])

_SETTINGS_ID = "site"


DEFAULT_LANDING = {
    "hero_badge": "New Batches Open",
    "hero_heading": "Crack Exams with the most experienced faculties.",
    "hero_subheading": "Live classes, structured courses, mock tests and personal mentorship for CSIR-NET, GATE, IIT-JAM, and other Life Sciences entrance exams.",
    "hero_cta_student": "Start learning free",
    "hero_cta_teacher": "I'm a teacher",
    "stat_1_number": "Self paced",
    "stat_1_label": "Live classes",
    "stat_2_number": "Personal",
    "stat_2_label": "Attention",
    "stat_3_number": "Past Questions",
    "stat_3_label": "Covered",
    "features_heading": "Everything a serious aspirant needs. Nothing they don't.",
    "contact_eyebrow": "Get in touch",
    "contact_heading": "Have a question? We'd love to hear from you.",
    "contact_description": "Reach out about courses, batches, or personalised mentorship. Our team usually replies within one business day.",
    "cta_heading": "Your entrance exam success is one decision away.",
    "cta_description": "Join the new batch today. First course module is free.",
    "cta_button": "Create free account",
    "footer_tagline": "Built for entrance exam aspirants",
    "teachers_menu_label": "Teachers Profile",
    "contact_email": "contact@bioexamprep.com",
    "contact_phone": "+91 9403888372",
    "contact_website": "bioexamprep.com",
    "next_class_empty_state": "No live classes scheduled yet",
}


class SiteConfigBody(BaseModel):
    brand_name: Optional[str] = Field(default=None, max_length=200)
    landing: Optional[dict] = None


def _default_brand() -> str:
    return os.environ.get("ACADEMY_NAME") or "Rohini's Academy for Bio Exams"


async def _current_settings() -> dict:
    doc = await db.site_settings.find_one({"_id": _SETTINGS_ID})
    if not doc:
        doc = {
            "_id": _SETTINGS_ID,
            "brand_name": _default_brand(),
            "landing": DEFAULT_LANDING.copy(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.site_settings.insert_one(doc)
    landing = {**DEFAULT_LANDING, **(doc.get("landing") or {})}
    return {
        "brand_name": doc.get("brand_name") or _default_brand(),
        "landing": landing,
        "updated_at": doc.get("updated_at"),
    }


@router.get("/site-config")
async def get_site_config():
    """Public — used by every page to render brand + landing copy at runtime."""
    return await _current_settings()


@router.put("/site-config")
async def update_site_config(body: SiteConfigBody, user: dict = Depends(require_role("admin"))):
    # Ensure doc exists with defaults so we can $set landing.<key> without conflict
    await _current_settings()
    update = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.brand_name is not None:
        brand = (body.brand_name or "").strip()
        if not brand:
            raise HTTPException(status_code=400, detail="Brand name cannot be empty")
        if len(brand) > 200:
            raise HTTPException(status_code=400, detail="Brand name too long (max 200 chars)")
        update["brand_name"] = brand
    if body.landing is not None:
        if not isinstance(body.landing, dict):
            raise HTTPException(status_code=400, detail="landing must be an object")
        for k, v in body.landing.items():
            if k not in DEFAULT_LANDING:
                continue
            if v is None:
                continue
            if not isinstance(v, str):
                raise HTTPException(status_code=400, detail=f"landing.{k} must be a string")
            v = v.strip()
            if len(v) > 5000:
                raise HTTPException(status_code=400, detail=f"landing.{k} too long (max 5000 chars)")
            update[f"landing.{k}"] = v
    await db.site_settings.update_one({"_id": _SETTINGS_ID}, {"$set": update})
    return await _current_settings()
