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
from routers import auth, courses, tests, live_classes, assignments, announcements, dashboard

app = FastAPI(title="JAM Academy LMS")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "JAM Academy LMS API"}


api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(tests.router)
api_router.include_router(live_classes.router)
api_router.include_router(assignments.router)
api_router.include_router(announcements.router)
api_router.include_router(dashboard.router)

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
    await seed()
    logger.info("Startup complete: indexes ensured, seed data checked")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
