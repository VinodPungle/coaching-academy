"""Phase 3 - Lesson detail page navigation tests (server-side response contract)."""
import os
import uuid
import requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _create_course_with_lessons(teacher_token, n_lessons=3):
    r = requests.post(f"{API}/courses", headers=_hdr(teacher_token), json={
        "title": f"TEST_P3 {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0,
    })
    cid = r.json()["id"]
    sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(teacher_token), json={"title": "S"}).json()
    stid = sec["sub_topics"][0]["id"]
    lids = []
    for i in range(n_lessons):
        r = requests.post(
            f"{API}/courses/{cid}/sections/{sec['id']}/sub-topics/{stid}/lessons",
            headers=_hdr(teacher_token), json={"title": f"L{i}", "url": "https://youtu.be/dQw4w9WgXcQ"},
        )
        lids.append(r.json()["id"])
    return cid, lids


def test_first_lesson_no_prev():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid, lids = _create_course_with_lessons(tt)
    try:
        r = requests.get(f"{API}/courses/{cid}/lessons/{lids[0]}", headers=_hdr(tt)).json()
        assert r["prev_lesson_id"] is None
        assert r["next_lesson_id"] == lids[1]
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def test_final_lesson_no_next():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid, lids = _create_course_with_lessons(tt)
    try:
        r = requests.get(f"{API}/courses/{cid}/lessons/{lids[-1]}", headers=_hdr(tt)).json()
        assert r["next_lesson_id"] is None
        assert r["prev_lesson_id"] == lids[-2]
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def test_lesson_navigation_across_sections_and_sub_topics():
    """Navigation should flow: section1[st1[l0,l1]] → section1[st2[l2]] → section2[st1[l3]] """
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    r = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P3nav {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0,
    })
    cid = r.json()["id"]
    try:
        s1 = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S1"}).json()
        s2 = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S2"}).json()
        # Add a 2nd sub_topic in S1
        st12 = requests.post(f"{API}/courses/{cid}/sections/{s1['id']}/sub-topics", headers=_hdr(tt), json={"title": "St2"}).json()
        lids = []
        # 2 lessons in S1/Overview
        for i in range(2):
            r = requests.post(
                f"{API}/courses/{cid}/sections/{s1['id']}/sub-topics/{s1['sub_topics'][0]['id']}/lessons",
                headers=_hdr(tt), json={"title": f"S1a-L{i}", "url": "https://y/x"},
            )
            lids.append(r.json()["id"])
        # 1 lesson in S1/St2
        r = requests.post(
            f"{API}/courses/{cid}/sections/{s1['id']}/sub-topics/{st12['id']}/lessons",
            headers=_hdr(tt), json={"title": "S1b-L0", "url": "https://y/x"},
        )
        lids.append(r.json()["id"])
        # 1 lesson in S2/Overview
        r = requests.post(
            f"{API}/courses/{cid}/sections/{s2['id']}/sub-topics/{s2['sub_topics'][0]['id']}/lessons",
            headers=_hdr(tt), json={"title": "S2-L0", "url": "https://y/x"},
        )
        lids.append(r.json()["id"])
        # walk
        for i, lid in enumerate(lids):
            r = requests.get(f"{API}/courses/{cid}/lessons/{lid}", headers=_hdr(tt)).json()
            expected_next = lids[i + 1] if i < len(lids) - 1 else None
            expected_prev = lids[i - 1] if i > 0 else None
            assert r["next_lesson_id"] == expected_next, f"lesson {i}: expected next {expected_next} got {r['next_lesson_id']}"
            assert r["prev_lesson_id"] == expected_prev, f"lesson {i}: expected prev {expected_prev} got {r['prev_lesson_id']}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def test_lesson_page_requires_enrollment_for_student():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    st = _login(os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))
    cid, lids = _create_course_with_lessons(tt, 1)
    try:
        r = requests.get(f"{API}/courses/{cid}/lessons/{lids[0]}", headers=_hdr(st))
        assert r.status_code == 403
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def test_single_lesson_first_and_last_at_once():
    """A course with 1 lesson: prev and next both None."""
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    cid, lids = _create_course_with_lessons(tt, 1)
    try:
        r = requests.get(f"{API}/courses/{cid}/lessons/{lids[0]}", headers=_hdr(tt)).json()
        assert r["prev_lesson_id"] is None
        assert r["next_lesson_id"] is None
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))
