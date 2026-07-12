"""Shared test fixtures + helpers. Credentials come from env with sensible defaults."""
import os
import pytest

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
API = BACKEND_URL + "/api"

TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")
TEST_TEACHER_EMAIL = os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com")
TEST_TEACHER_PASSWORD = os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")
TEST_STUDENT_EMAIL = os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com")
TEST_STUDENT_PASSWORD = os.getenv("TEST_STUDENT_PASSWORD", "Student@123")
TEST_FRESH_USER_PASSWORD = os.getenv("TEST_FRESH_USER_PASSWORD", "abcdef")


@pytest.fixture
def creds():
    return {
        "admin": (TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD),
        "teacher": (TEST_TEACHER_EMAIL, TEST_TEACHER_PASSWORD),
        "student": (TEST_STUDENT_EMAIL, TEST_STUDENT_PASSWORD),
    }
