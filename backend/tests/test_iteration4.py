"""
Iteration 4 tests — Rohini's Academy rename, scope filtering, admin breakdowns,
course cross-linking, delete-test guard, teacher modify.

Focus:
  - Auth with new @rgpacademy.com emails
  - Teacher scope (tests, live_classes, assignments, announcements)
  - Student scope
  - Delete test with attempts -> 400 with clear message
  - Delete test without attempts -> ok
  - Update test (PUT) works
  - Course-linked filter (?course_id=)
  - Admin /admin/teachers per-teacher breakdown
  - Admin /admin/teachers/{id}/detail
  - Admin /admin/top-performers per_course + per_batch
"""

import os
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN = (os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin@123"))
TEACHER = (os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
STUDENT = (os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"], data["user"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------- Auth ------------------------------- #

class TestAuthRename:
    def test_admin_login_rgp(self):
        token, u = login(*ADMIN)
        assert u["role"] == "admin"
        assert u["email"].endswith("@rgpacademy.com")

    def test_teacher_login_rgp(self):
        token, u = login(*TEACHER)
        assert u["role"] == "teacher"
        assert u["email"].endswith("@rgpacademy.com")

    def test_student_login_rgp(self):
        token, u = login(*STUDENT)
        assert u["role"] == "student"
        assert u["email"].endswith("@rgpacademy.com")

    def test_jam_email_login_gone(self):
        """After migration, old @jamacademy.com login should fail."""
        r = requests.post(f"{API}/auth/login", json={"email": "admin@jamacademy.com", "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")}, timeout=15)
        assert r.status_code in (400, 401, 404), f"Old jam admin should not login, got {r.status_code}"


# ------------------------------ Fixtures ---------------------------- #

@pytest.fixture(scope="module")
def teacher_ctx():
    token, u = login(*TEACHER)
    return {"token": token, "user": u, "h": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def admin_ctx():
    token, u = login(*ADMIN)
    return {"token": token, "user": u, "h": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def student_ctx():
    token, u = login(*STUDENT)
    return {"token": token, "user": u, "h": {"Authorization": f"Bearer {token}"}}


# ---------------------------- Teacher scope ------------------------- #

class TestTeacherScope:
    def test_teacher_courses_own_only(self, teacher_ctx):
        r = requests.get(f"{API}/teacher/courses", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        tid = teacher_ctx["user"]["id"]
        for c in data:
            assert c.get("teacher_id") == tid, f"teacher/courses returned foreign course: {c}"

    def test_teacher_tests_own_with_attempt_count(self, teacher_ctx):
        r = requests.get(f"{API}/tests", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        tid = teacher_ctx["user"]["id"]
        for t in data:
            assert t.get("teacher_id") == tid
            assert "attempt_count" in t
            assert isinstance(t["attempt_count"], int)

    def test_teacher_live_classes_own_only(self, teacher_ctx):
        r = requests.get(f"{API}/live-classes", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        tid = teacher_ctx["user"]["id"]
        for c in r.json():
            assert c.get("teacher_id") == tid

    def test_teacher_assignments_own_only(self, teacher_ctx):
        r = requests.get(f"{API}/assignments", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        tid = teacher_ctx["user"]["id"]
        for a in r.json():
            assert a.get("teacher_id") == tid

    def test_teacher_announcements_own_plus_admin(self, teacher_ctx):
        r = requests.get(f"{API}/announcements", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        tid = teacher_ctx["user"]["id"]
        for a in r.json():
            # either own or admin-posted
            assert a.get("teacher_id") == tid or a.get("posted_by_role") == "admin", f"unexpected announcement: {a}"


# ---------------------------- Student scope ------------------------- #

class TestStudentScope:
    def _enrolled_ids(self, student_ctx):
        r = requests.get(f"{API}/student/enrollments", headers=student_ctx["h"], timeout=15)
        assert r.status_code == 200, r.text
        return {c["id"] for c in r.json()}

    def test_student_tests_scope(self, student_ctx):
        enrolled_ids = self._enrolled_ids(student_ctx)
        r = requests.get(f"{API}/tests", headers=student_ctx["h"], timeout=15)
        assert r.status_code == 200
        for t in r.json():
            cid = t.get("course_id")
            assert cid is None or cid in enrolled_ids, f"student saw non-enrolled test course_id={cid}"

    def test_student_assignments_scope(self, student_ctx):
        enrolled_ids = self._enrolled_ids(student_ctx)
        r = requests.get(f"{API}/assignments", headers=student_ctx["h"], timeout=15)
        assert r.status_code == 200
        for a in r.json():
            cid = a.get("course_id")
            assert cid is None or cid in enrolled_ids

    def test_student_live_classes_scope(self, student_ctx):
        enrolled_ids = self._enrolled_ids(student_ctx)
        r = requests.get(f"{API}/live-classes", headers=student_ctx["h"], timeout=15)
        assert r.status_code == 200
        for c in r.json():
            cid = c.get("course_id")
            assert cid is None or cid in enrolled_ids

    def test_student_announcements_scope(self, student_ctx):
        enrolled_ids = self._enrolled_ids(student_ctx)
        r = requests.get(f"{API}/announcements", headers=student_ctx["h"], timeout=15)
        assert r.status_code == 200
        for a in r.json():
            cid = a.get("course_id")
            assert cid is None or cid in enrolled_ids


# ------------------------ Delete test guard ------------------------- #

class TestDeleteTestGuard:
    def test_delete_test_without_attempts_ok(self, teacher_ctx):
        # Create a test without attempts and delete
        payload = {
            "title": f"TEST_delete_{uuid.uuid4().hex[:6]}",
            "subject": "Physics",
            "duration_min": 30,
            "published": False,
            "questions": [
                {"text": "Q1?", "options": ["a", "b", "c", "d"], "correct_index": 0, "marks": 4}
            ],
        }
        r = requests.post(f"{API}/tests", json=payload, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200, r.text
        test_id = r.json()["id"]

        r = requests.delete(f"{API}/tests/{test_id}", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200, r.text

        # Confirm gone
        r = requests.get(f"{API}/tests/{test_id}", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 404

    def test_delete_test_with_attempts_blocked_400(self, teacher_ctx, student_ctx):
        # Create linked test on a course teacher owns (find or create)
        r = requests.get(f"{API}/teacher/courses", headers=teacher_ctx["h"], timeout=15)
        courses = r.json()
        assert courses, "Teacher should have at least one course from seed"
        course_id = courses[0]["id"]

        # Ensure student enrolled — try enroll (idempotent-ish)
        r = requests.post(
            f"{API}/courses/{course_id}/enroll",
            json={},
            headers=student_ctx["h"],
            timeout=15,
        )
        # 200 or 400 (already enrolled) both fine
        assert r.status_code in (200, 400), r.text

        payload = {
            "title": f"TEST_attempted_{uuid.uuid4().hex[:6]}",
            "subject": "Physics",
            "duration_min": 30,
            "published": True,
            "course_id": course_id,
            "questions": [
                {"text": "Q1?", "options": ["a", "b", "c", "d"], "correct_index": 0, "marks": 4}
            ],
        }
        r = requests.post(f"{API}/tests", json=payload, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200, r.text
        test_id = r.json()["id"]
        qid = r.json()["questions"][0]["id"]

        # Student attempts
        r = requests.post(
            f"{API}/tests/{test_id}/attempt",
            json={"answers": {qid: 0}},
            headers=student_ctx["h"],
            timeout=15,
        )
        assert r.status_code == 200, r.text

        # Now delete should fail 400 with clear message
        r = requests.delete(f"{API}/tests/{test_id}", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 400, f"Expected 400 for deleting attempted test, got {r.status_code}: {r.text}"
        msg = r.json().get("detail", "")
        assert "Cannot delete" in msg and "attempt" in msg.lower(), f"Message not matching: {msg}"

        # cleanup: remove attempt then delete
        # (Best-effort — leave test in place; test data has TEST_ prefix.)


# ---------------------------- Update test --------------------------- #

class TestUpdateTest:
    def test_put_test_updates_fields(self, teacher_ctx):
        payload = {
            "title": f"TEST_edit_{uuid.uuid4().hex[:6]}",
            "subject": "Chem",
            "duration_min": 45,
            "published": False,
            "questions": [
                {"text": "Q?", "options": ["a", "b"], "correct_index": 0, "marks": 2}
            ],
        }
        r = requests.post(f"{API}/tests", json=payload, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        test_id = r.json()["id"]

        new_body = dict(payload)
        new_body["title"] = payload["title"] + "_edited"
        new_body["duration_min"] = 90
        r = requests.put(f"{API}/tests/{test_id}", json=new_body, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["title"] == new_body["title"]
        assert updated["duration_min"] == 90

        # verify persisted via GET
        r = requests.get(f"{API}/tests/{test_id}", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        assert r.json()["title"] == new_body["title"]
        # cleanup
        requests.delete(f"{API}/tests/{test_id}", headers=teacher_ctx["h"], timeout=15)


# --------------------- Course cross-linking filter ------------------ #

class TestCourseLinkedFilter:
    def test_live_classes_course_id_filter(self, teacher_ctx):
        courses = requests.get(f"{API}/teacher/courses", headers=teacher_ctx["h"]).json()
        if not courses:
            pytest.skip("teacher has no courses")
        cid = courses[0]["id"]
        r = requests.get(f"{API}/live-classes?course_id={cid}", headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        for c in r.json():
            assert c.get("course_id") == cid


# ----------------------------- Admin -------------------------------- #

class TestAdminBreakdowns:
    def test_admin_teachers_summary(self, admin_ctx):
        r = requests.get(f"{API}/admin/teachers", headers=admin_ctx["h"], timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for t in data:
            for key in ("id", "name", "email", "courses", "students", "tests",
                        "assignments", "upcoming_classes", "past_classes"):
                assert key in t, f"missing {key} in teacher summary: {t}"
            assert t["email"].endswith("@rgpacademy.com") or "@" in t["email"]

    def test_admin_teacher_detail(self, admin_ctx):
        r = requests.get(f"{API}/admin/teachers", headers=admin_ctx["h"], timeout=15)
        tid = r.json()[0]["id"]
        r = requests.get(f"{API}/admin/teachers/{tid}/detail", headers=admin_ctx["h"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        for key in ("teacher", "courses", "tests", "live_classes", "assignments"):
            assert key in d
        assert d["teacher"]["id"] == tid

    def test_admin_top_performers(self, admin_ctx):
        r = requests.get(f"{API}/admin/top-performers", headers=admin_ctx["h"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "per_course" in d and "per_batch" in d
        assert isinstance(d["per_course"], list)
        assert isinstance(d["per_batch"], list)
        # If any course has top entries, verify fields
        for course in d["per_course"]:
            assert "course_id" in course and "course_title" in course and "top" in course
            for row in course["top"]:
                for k in ("student_id", "student_name", "avg_pct", "attempts"):
                    assert k in row


# --------------------- Announcement course_id ---------------------- #

class TestAnnouncementCourseId:
    def test_teacher_post_announcement_global(self, teacher_ctx):
        payload = {"title": f"TEST_ann_{uuid.uuid4().hex[:6]}", "body": "Global test", "course_id": None}
        r = requests.post(f"{API}/announcements", json=payload, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        aid = r.json()["id"]
        assert r.json().get("course_id") is None
        # cleanup
        requests.delete(f"{API}/announcements/{aid}", headers=teacher_ctx["h"], timeout=15)

    def test_teacher_post_announcement_course(self, teacher_ctx):
        courses = requests.get(f"{API}/teacher/courses", headers=teacher_ctx["h"]).json()
        if not courses:
            pytest.skip("no teacher courses")
        cid = courses[0]["id"]
        payload = {"title": f"TEST_ann_{uuid.uuid4().hex[:6]}", "body": "Course-linked", "course_id": cid}
        r = requests.post(f"{API}/announcements", json=payload, headers=teacher_ctx["h"], timeout=15)
        assert r.status_code == 200
        assert r.json()["course_id"] == cid
        assert r.json().get("course_name")
        aid = r.json()["id"]
        # cleanup
        requests.delete(f"{API}/announcements/{aid}", headers=teacher_ctx["h"], timeout=15)
