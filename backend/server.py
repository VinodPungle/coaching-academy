# App entry point: builds the FastAPI app, mounts every router under
# /api, configures CORS, and — on startup — runs one-time data migrations
# plus demo-data seeding. Run locally with:
#   uvicorn server:app --host 127.0.0.1 --port 8001
# In production this same module is what the Dockerfile's CMD launches
# inside the Azure Container App.
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')  # load backend/.env before anything reads os.environ

import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from database import db, client
from seed import seed
from notify import ACADEMY_NAME
from routers import auth, courses, tests, live_classes, assignments, announcements, dashboard, payments, batches, files, certificates, notifications, admin, comments, enquiries, site_config, teacher_profiles

app = FastAPI(title=f"{ACADEMY_NAME} LMS")

# Every route in every router below is actually mounted at /api/<router's path>
# (e.g. courses.router's "/courses" endpoint becomes GET /api/courses).
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    """Unauthenticated health-check / sanity endpoint — hitting /api/ confirms
    the backend is up and reachable."""
    return {"message": f"{ACADEMY_NAME} LMS API"}


# One include_router() per domain — see backend/routers/*.py. Adding a new
# router file requires both the import above and an include_router() call
# here, or its routes simply won't exist.
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
api_router.include_router(enquiries.router)
api_router.include_router(site_config.router)
api_router.include_router(teacher_profiles.router)

app.include_router(api_router)

# CORS_ORIGINS is a comma-separated allowlist (e.g.
# "https://bioexamprep.com,https://www.bioexamprep.com") — set per
# environment via the Container App's env vars; defaults to "*" (allow all)
# only if the env var is entirely unset, which should never happen in prod.
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
    """Runs once when the backend process boots (every deploy/restart).
    Two kinds of work happen here:
      1. Index creation — safe to repeat every time, MongoDB no-ops if the
         index already exists.
      2. One-time data migrations — each guarded by either a natural
         "already migrated?" check or a db.system_flags document, so they
         don't redo work (or damage data) on every subsequent restart.
    Order matters: migrations run before seed() so seeded demo data lands
    in its final, already-migrated shape."""
    # Uniqueness/lookup indexes the app's query patterns rely on.
    await db.users.create_index("email", unique=True)
    await db.enrollments.create_index([("course_id", 1), ("student_id", 1)], unique=True)  # one enrollment per student per course
    await db.test_attempts.create_index([("test_id", 1), ("student_id", 1)], unique=True)  # one attempt record per student per test
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)  # MongoDB TTL index — Atlas auto-deletes expired reset tokens
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])  # fast "my recent notifications" lookups
    # One-time email domain migration: @jamacademy.com and @rgpacademy.com -> @bioexamprep.com
    async for u in db.users.find({"email": {"$regex": "@(jamacademy|rgpacademy)\\.com$", "$options": "i"}}):
        new_email = u["email"].split("@")[0] + "@bioexamprep.com"
        existing = await db.users.find_one({"email": new_email})
        if existing and existing["_id"] != u["_id"]:
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
                await db.users.delete_one({"_id": u["_id"]})
                logger.info(f"Removed empty duplicate {u['email']} (kept {new_email})")
            else:
                logger.warning(f"Cannot migrate {u['email']}: both accounts have content. Admin must resolve manually.")
        else:
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"email": new_email}})
            logger.info(f"Migrated user email {u['email']} -> {new_email}")

    # One-time purge of non-demo accounts (guarded by system_flags to prevent re-runs).
    # This was a historical cleanup (the app used to have real test-signup data
    # mixed in with the seeded demo accounts); it deletes every user that isn't
    # one of the three fixed demo logins, cascading their owned content.
    DEMO_EMAILS = {"admin@bioexamprep.com", "teacher@bioexamprep.com", "student@bioexamprep.com"}
    purge_flag = await db.system_flags.find_one({"_id": "purge_non_demo_v1"})
    if not purge_flag:
        victims = await db.users.find({"email": {"$nin": list(DEMO_EMAILS)}}, {"_id": 1, "email": 1, "role": 1}).to_list(10000)
        victim_ids = [v["_id"] for v in victims]
        teacher_ids = [v["_id"] for v in victims if v.get("role") == "teacher"]
        if victim_ids:
            # Cascade: teacher-owned content
            their_courses = await db.courses.find({"teacher_id": {"$in": teacher_ids}}, {"_id": 1}).to_list(10000)
            their_course_ids = [c["_id"] for c in their_courses]
            their_tests = await db.tests.find({"teacher_id": {"$in": teacher_ids}}, {"_id": 1}).to_list(10000)
            their_test_ids = [t["_id"] for t in their_tests]
            their_assignments = await db.assignments.find({"teacher_id": {"$in": teacher_ids}}, {"_id": 1}).to_list(10000)
            their_assignment_ids = [a["_id"] for a in their_assignments]
            if their_course_ids:
                await db.enrollments.delete_many({"course_id": {"$in": their_course_ids}})
                await db.batches.delete_many({"course_id": {"$in": their_course_ids}})
            await db.courses.delete_many({"teacher_id": {"$in": teacher_ids}})
            if their_test_ids:
                await db.test_attempts.delete_many({"test_id": {"$in": their_test_ids}})
            await db.tests.delete_many({"teacher_id": {"$in": teacher_ids}})
            if their_assignment_ids:
                await db.submissions.delete_many({"assignment_id": {"$in": their_assignment_ids}})
            await db.assignments.delete_many({"teacher_id": {"$in": teacher_ids}})
            await db.live_classes.delete_many({"teacher_id": {"$in": teacher_ids}})
            await db.announcements.delete_many({"teacher_id": {"$in": teacher_ids}})
            # Cascade: student-owned content
            await db.enrollments.delete_many({"student_id": {"$in": victim_ids}})
            await db.test_attempts.delete_many({"student_id": {"$in": victim_ids}})
            await db.submissions.delete_many({"student_id": {"$in": victim_ids}})
            await db.notifications.delete_many({"user_id": {"$in": victim_ids}})
            await db.certificates.delete_many({"student_id": {"$in": victim_ids}})
            await db.payments.delete_many({"student_id": {"$in": victim_ids}})
            await db.users.delete_many({"_id": {"$in": victim_ids}})
            logger.info(f"Purged {len(victim_ids)} non-demo users and cascaded their data")
        await db.system_flags.insert_one({"_id": "purge_non_demo_v1", "at": datetime.now(timezone.utc).isoformat()})
    # Phase 1: Backfill sub_topics for existing courses (Course → Section → Sub Topic → Lesson)
    async for c in db.courses.find({"sections": {"$exists": True}}):
        changed = False
        for sec in c.get("sections", []):
            if "sub_topics" not in sec:
                existing_lessons = sec.pop("lessons", []) if isinstance(sec.get("lessons"), list) else []
                sec["sub_topics"] = [{
                    "id": str(uuid.uuid4()),
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
    # One-time: mark demo accounts with is_demo flag + delete their historical payment records
    from auth_utils import DEMO_EMAILS
    demo_users = await db.users.find({"email": {"$in": list(DEMO_EMAILS)}}, {"_id": 1, "is_demo": 1}).to_list(10)
    for du in demo_users:
        if not du.get("is_demo"):
            await db.users.update_one({"_id": du["_id"]}, {"$set": {"is_demo": True}})
            logger.info(f"Marked user {du['_id']} as is_demo=True")
    # One-time payments purge (idempotent flag)
    if not await db.system_flags.find_one({"_id": "demo_payments_purge_v1"}):
        demo_ids = [u["_id"] for u in demo_users]
        if demo_ids:
            r = await db.payments.delete_many({"$or": [{"student_id": {"$in": demo_ids}}, {"user_id": {"$in": demo_ids}}]})
            logger.info(f"Purged {r.deleted_count} demo payment records")
        await db.system_flags.insert_one({"_id": "demo_payments_purge_v1", "at": datetime.now(timezone.utc).isoformat()})
    # One-time: backfill demo_scope on announcements from demo teacher (courses/tests/etc handled elsewhere)
    if not await db.system_flags.find_one({"_id": "demo_announcements_tag_v1"}):
        demo_teacher_ids = [u["_id"] for u in demo_users if u.get("_id")]
        # Actually filter by role too
        demo_teacher_ids = [u["_id"] async for u in db.users.find({"role": "teacher", "is_demo": True}, {"_id": 1})]
        if demo_teacher_ids:
            r = await db.announcements.update_many({"teacher_id": {"$in": demo_teacher_ids}}, {"$set": {"demo_scope": True}})
            logger.info(f"Tagged {r.modified_count} demo announcements")
        await db.system_flags.insert_one({"_id": "demo_announcements_tag_v1", "at": datetime.now(timezone.utc).isoformat()})
    # One-time: retroactively tag demo_scope on courses/tests/assignments/live_classes created by demo teachers
    # (needed for content that existed before the demo-isolation deploy)
    if not await db.system_flags.find_one({"_id": "demo_content_tag_v2"}):
        demo_teacher_ids = [u["_id"] async for u in db.users.find({"role": "teacher", "is_demo": True}, {"_id": 1})]
        if demo_teacher_ids:
            for coll_name in ("courses", "tests", "assignments", "live_classes"):
                r = await db[coll_name].update_many(
                    {"teacher_id": {"$in": demo_teacher_ids}, "demo_scope": {"$ne": True}},
                    {"$set": {"demo_scope": True}},
                )
                logger.info(f"Backfilled demo_scope on {r.modified_count} {coll_name}")
        await db.system_flags.insert_one({"_id": "demo_content_tag_v2", "at": datetime.now(timezone.utc).isoformat()})
    # Object storage (Azure Blob when AZURE_STORAGE_CONNECTION_STRING is set, else local disk) needs no init step.
    # Warn loudly if running without Blob configured — local-disk uploads don't
    # survive a container restart/redeploy, so this is a real production risk.
    import storage_service
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — uploads will be stored on local container disk (not persistent across deploys)")

    # One-time backfill: copy any legacy files still on disk to object storage
    try:
        await _backfill_legacy_files_to_object_storage()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Legacy files backfill failed: {exc}")
    logger.info("Startup complete: indexes ensured, seed data checked")


async def _backfill_legacy_files_to_object_storage():
    """Copy files still present on the container disk into object storage.
    Idempotent — guarded by db.system_flags flag; updates each file record with
    storage_path so subsequent reads go through object storage.
    """
    import storage_service
    from pathlib import Path
    flag = await db.system_flags.find_one({"_id": "files_to_objstore_v1"})
    if flag:
        return
    if not storage_service.is_configured():
        logger.warning("Skipping legacy files backfill — object storage not configured")
        return
    LEGACY_DIR = Path(__file__).parent / "uploads"
    copied, missing, failed = 0, 0, 0
    async for meta in db.files.find({"storage_path": {"$in": [None, ""]}}):
        file_id = meta["_id"]
        ext = meta.get("ext", "")
        local = LEGACY_DIR / f"{file_id}{ext}"
        if not local.exists():
            missing += 1
            continue
        try:
            path = storage_service.build_path(meta.get("uploader_id") or "system", file_id, ext)
            result = storage_service.put_object(path, local.read_bytes(), meta.get("content_type") or "application/octet-stream")
            await db.files.update_one({"_id": file_id}, {"$set": {"storage_path": result.get("path", path)}})
            copied += 1
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to migrate {file_id}: {exc}")
            failed += 1
    logger.info(f"Legacy file backfill: copied={copied} missing={missing} failed={failed}")
    await db.system_flags.insert_one({"_id": "files_to_objstore_v1", "at": datetime.now(timezone.utc).isoformat(), "stats": {"copied": copied, "missing": missing, "failed": failed}})


@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanly close the MongoDB connection pool when the process exits."""
    client.close()
