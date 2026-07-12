from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from database import db, client
from seed import seed
from notify import ACADEMY_NAME
from routers import auth, courses, tests, live_classes, assignments, announcements, dashboard, payments, batches, files, certificates, notifications, admin, comments

app = FastAPI(title=f"{ACADEMY_NAME} LMS")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": f"{ACADEMY_NAME} LMS API"}


api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(tests.router)
api_router.include_router(live_classes.router)
api_router.include_router(assignments.router)
api_router.include_router(announcements.router)
api_router.include_router(dashboard.router)
api_router.include_router(payments.router)
api_router.include_router(batches.router)
api_router.include_router(files.router)
api_router.include_router(certificates.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(comments.router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.enrollments.create_index([("course_id", 1), ("student_id", 1)], unique=True)
    await db.test_attempts.create_index([("test_id", 1), ("student_id", 1)], unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    # One-time migration: rename @jamacademy.com emails to @rgpacademy.com (passwords unchanged)
    async for u in db.users.find({"email": {"$regex": "@jamacademy\\.com$", "$options": "i"}}):
        new_email = u["email"].split("@")[0] + "@rgpacademy.com"
        existing = await db.users.find_one({"email": new_email})
        if existing:
            # Duplicate collision: keep whichever has real content (courses/tests/enrollments/attempts).
            existing_content = (
                await db.courses.count_documents({"teacher_id": existing["_id"]})
                + await db.tests.count_documents({"teacher_id": existing["_id"]})
                + await db.enrollments.count_documents({"student_id": existing["_id"]})
                + await db.test_attempts.count_documents({"student_id": existing["_id"]})
            )
            old_content = (
                await db.courses.count_documents({"teacher_id": u["_id"]})
                + await db.tests.count_documents({"teacher_id": u["_id"]})
                + await db.enrollments.count_documents({"student_id": u["_id"]})
                + await db.test_attempts.count_documents({"student_id": u["_id"]})
            )
            if existing_content == 0 and old_content > 0:
                await db.users.delete_one({"_id": existing["_id"]})
                await db.users.update_one({"_id": u["_id"]}, {"$set": {"email": new_email}})
                logger.info(f"Migrated user email {u['email']} -> {new_email} (removed empty duplicate)")
            elif old_content == 0:
                # old is empty; delete it silently
                await db.users.delete_one({"_id": u["_id"]})
                logger.info(f"Removed empty duplicate {u['email']} (kept {new_email})")
            else:
                logger.warning(f"Cannot migrate {u['email']}: both accounts have content. Admin must resolve manually.")
        else:
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"email": new_email}})
            logger.info(f"Migrated user email {u['email']} -> {new_email}")
    # Phase 1: Backfill sub_topics for existing courses (Course → Section → Sub Topic → Lesson)
    async for c in db.courses.find({"sections": {"$exists": True}}):
        changed = False
        for sec in c.get("sections", []):
            if "sub_topics" not in sec:
                existing_lessons = sec.pop("lessons", []) if isinstance(sec.get("lessons"), list) else []
                sec["sub_topics"] = [{
                    "id": str(__import__("uuid").uuid4()),
                    "title": "Overview",
                    "order": 0,
                    "lessons": existing_lessons,
                    "comments_enabled": True,
                }]
                changed = True
            else:
                for st in sec["sub_topics"]:
                    st.setdefault("comments_enabled", True)
        if changed:
            await db.courses.update_one({"_id": c["_id"]}, {"$set": {"sections": c["sections"]}})
            logger.info(f"Backfilled sub_topics for course {c.get('title', c['_id'])}")
    await seed()
    logger.info("Startup complete: indexes ensured, seed data checked")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
