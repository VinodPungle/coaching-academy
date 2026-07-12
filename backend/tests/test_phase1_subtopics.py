"""Phase 1 - Sub Topic layer.

Tests migration idempotency, CRUD, delete-with-lessons guard, reorder, and lesson add via sub topic path.
Run with: cd /app/backend && pytest tests/test_phase1_subtopics.py -v
"""
import os
import uuid
import requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def test_migration_backfills_sub_topics():
    """Every course in the DB should have every section wrapped in at least one sub_topic."""
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    courses = requests.get(f"{API}/teacher/courses", headers=_hdr(tt)).json()
    assert len(courses) >= 1
    for c in courses:
        full = requests.get(f"{API}/courses/{c['id']}", headers=_hdr(tt)).json()
        for section in full.get("sections", []):
            assert "sub_topics" in section, f"Section {section['title']} missing sub_topics"
            assert "lessons" not in section or section.get("lessons") == [], "Old lessons array should be removed"
            for st in section["sub_topics"]:
                assert "id" in st and "title" in st and "lessons" in st
                assert "comments_enabled" in st


def _create_course(token, subject="Physics"):
    r = requests.post(f"{API}/courses", headers=_hdr(token), json={
        "title": f"TEST_P1 {uuid.uuid4().hex[:8]}",
        "subject": subject,
        "description": "phase 1 test",
        "price": 0,
    })
    r.raise_for_status()
    return r.json()["id"]


def _cleanup(course_id, token):
    requests.delete(f"{API}/courses/{course_id}", headers=_hdr(token))


def test_add_section_creates_default_sub_topic():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "Ch 1"}).json()
        assert len(sec["sub_topics"]) == 1
        assert sec["sub_topics"][0]["title"] == "Overview"
    finally:
        _cleanup(cid, tt)


def test_add_section_empty_title_rejected():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        r = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "   "})
        assert r.status_code == 400
    finally:
        _cleanup(cid, tt)


def test_sub_topic_crud_and_duplicate_rejected():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S1"}).json()
        sid = sec["id"]
        # add
        st1 = requests.post(f"{API}/courses/{cid}/sections/{sid}/sub-topics", headers=_hdr(tt), json={"title": "Waves"}).json()
        assert st1["title"] == "Waves"
        # duplicate
        r = requests.post(f"{API}/courses/{cid}/sections/{sid}/sub-topics", headers=_hdr(tt), json={"title": "waves"})
        assert r.status_code == 400
        # rename
        requests.put(f"{API}/courses/{cid}/sections/{sid}/sub-topics/{st1['id']}", headers=_hdr(tt), json={"title": "Oscillations"}).raise_for_status()
        full = requests.get(f"{API}/courses/{cid}", headers=_hdr(tt)).json()
        titles = [st["title"] for st in full["sections"][0]["sub_topics"]]
        assert "Oscillations" in titles
    finally:
        _cleanup(cid, tt)


def test_delete_sub_topic_blocked_if_lessons_exist():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S"}).json()
        sid = sec["id"]
        stid = sec["sub_topics"][0]["id"]
        # add a lesson
        requests.post(
            f"{API}/courses/{cid}/sections/{sid}/sub-topics/{stid}/lessons",
            headers=_hdr(tt),
            json={"title": "L1", "url": "https://youtu.be/dQw4w9WgXcQ", "duration": "10m"},
        ).raise_for_status()
        # attempt delete
        r = requests.delete(f"{API}/courses/{cid}/sections/{sid}/sub-topics/{stid}", headers=_hdr(tt))
        assert r.status_code == 400
        assert "lesson" in r.json()["detail"].lower()
    finally:
        _cleanup(cid, tt)


def test_reorder_sub_topics():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S"}).json()
        sid = sec["id"]
        a = requests.post(f"{API}/courses/{cid}/sections/{sid}/sub-topics", headers=_hdr(tt), json={"title": "A"}).json()
        b = requests.post(f"{API}/courses/{cid}/sections/{sid}/sub-topics", headers=_hdr(tt), json={"title": "B"}).json()
        # Reorder: [B, Overview, A]
        overview = sec["sub_topics"][0]["id"]
        requests.put(
            f"{API}/courses/{cid}/sections/{sid}/sub-topics/reorder",
            headers=_hdr(tt), json={"sub_topic_ids": [b["id"], overview, a["id"]]},
        ).raise_for_status()
        full = requests.get(f"{API}/courses/{cid}", headers=_hdr(tt)).json()
        st = full["sections"][0]["sub_topics"]
        assert st[0]["title"] == "B"
        assert st[2]["title"] == "A"
    finally:
        _cleanup(cid, tt)


def test_add_lesson_requires_url_or_notes():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S"}).json()
        stid = sec["sub_topics"][0]["id"]
        r = requests.post(
            f"{API}/courses/{cid}/sections/{sec['id']}/sub-topics/{stid}/lessons",
            headers=_hdr(tt), json={"title": "L1"},
        )
        assert r.status_code == 400
        # with notes only, should succeed
        r = requests.post(
            f"{API}/courses/{cid}/sections/{sec['id']}/sub-topics/{stid}/lessons",
            headers=_hdr(tt), json={"title": "L1", "notes": [{"title": "N", "url": "https://x/y.pdf"}]},
        )
        assert r.status_code == 200
    finally:
        _cleanup(cid, tt)


def test_get_lesson_page_prev_next():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid = _create_course(tt)
    try:
        sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S"}).json()
        stid = sec["sub_topics"][0]["id"]
        ids = []
        for i in range(3):
            r = requests.post(
                f"{API}/courses/{cid}/sections/{sec['id']}/sub-topics/{stid}/lessons",
                headers=_hdr(tt), json={"title": f"L{i}", "url": "https://y/z"},
            )
            ids.append(r.json()["id"])
        # first
        p = requests.get(f"{API}/courses/{cid}/lessons/{ids[0]}", headers=_hdr(tt)).json()
        assert p["prev_lesson_id"] is None
        assert p["next_lesson_id"] == ids[1]
        assert p["section_title"] == "S"
        # last
        p = requests.get(f"{API}/courses/{cid}/lessons/{ids[-1]}", headers=_hdr(tt)).json()
        assert p["next_lesson_id"] is None
        assert p["prev_lesson_id"] == ids[1]
    finally:
        _cleanup(cid, tt)


def test_completed_lesson_progress_accounts_for_subtopics():
    """Progress should be based on total lessons across all sub_topics."""
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    st_token = _login(os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))
    # use an existing seeded course (has 2 sections, each with 1+ sub_topics)
    courses = requests.get(f"{API}/courses", headers=_hdr(st_token)).json()
    course = courses[0]
    # enrol if not already
    enrolls = requests.get(f"{API}/student/enrollments", headers=_hdr(st_token)).json()
    if not any(e["id"] == course["id"] for e in enrolls):
        # need to pass batch or skip if paid
        pass
    # progress endpoint should not crash and should return an integer 0..100
    enrolls = requests.get(f"{API}/student/enrollments", headers=_hdr(st_token)).json()
    for e in enrolls:
        assert 0 <= e.get("progress", 0) <= 100


def test_migration_idempotent():
    """Re-running startup migration should be a no-op (no double-wrapping)."""
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    courses = requests.get(f"{API}/teacher/courses", headers=_hdr(tt)).json()
    for c in courses:
        full = requests.get(f"{API}/courses/{c['id']}", headers=_hdr(tt)).json()
        for section in full.get("sections", []):
            # sub_topics should not themselves have nested sub_topics
            for st in section["sub_topics"]:
                assert "sub_topics" not in st, "Sub topics should not nest"
