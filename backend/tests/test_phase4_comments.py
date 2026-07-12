"""Phase 4 - Comments (reusable threaded)."""
import os
import uuid
import requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def _make_course_with_lesson():
    tt = _login("teacher@rgpacademy.com", "Teacher@123")
    r = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P4 {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0,
    })
    cid = r.json()["id"]
    sec = requests.post(f"{API}/courses/{cid}/sections", headers=_hdr(tt), json={"title": "S"}).json()
    stid = sec["sub_topics"][0]["id"]
    lesson = requests.post(
        f"{API}/courses/{cid}/sections/{sec['id']}/sub-topics/{stid}/lessons",
        headers=_hdr(tt), json={"title": "L", "url": "https://y/x"},
    ).json()
    return tt, cid, sec["id"], stid, lesson["id"]


def _enroll_student(cid):
    st = _login("student@rgpacademy.com", "Student@123")
    requests.post(f"{API}/courses/{cid}/enroll", headers=_hdr(st), json={})
    return st


def _cleanup(cid, tt):
    requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def test_student_and_teacher_can_post_and_reply():
    tt, cid, sid, stid, lid = _make_course_with_lesson()
    st = _enroll_student(cid)
    try:
        url = f"{API}/lessons/{cid}/{stid}/{lid}/comments"
        # student posts
        r = requests.post(url, headers=_hdr(st), json={"body": "How to solve Q3?"}).json()
        cid_root = r["id"]
        # teacher replies
        rep = requests.post(url, headers=_hdr(tt), json={"body": "Use energy conservation.", "parent_id": cid_root}).json()
        # list
        data = requests.get(url, headers=_hdr(st)).json()
        assert data["enabled"] is True
        assert len(data["comments"]) == 2
        parents = [c for c in data["comments"] if not c["parent_id"]]
        assert len(parents) == 1
        assert parents[0]["body"] == "How to solve Q3?"
        replies = [c for c in data["comments"] if c["parent_id"] == cid_root]
        assert len(replies) == 1
        assert replies[0]["author_role"] == "teacher"
    finally:
        _cleanup(cid, tt)


def test_teacher_disable_blocks_new_comments():
    tt, cid, sid, stid, lid = _make_course_with_lesson()
    st = _enroll_student(cid)
    try:
        # disable
        requests.put(
            f"{API}/courses/{cid}/sections/{sid}/sub-topics/{stid}/comments-toggle",
            headers=_hdr(tt), json={"comments_enabled": False},
        ).raise_for_status()
        # list returns enabled=false
        url = f"{API}/lessons/{cid}/{stid}/{lid}/comments"
        data = requests.get(url, headers=_hdr(st)).json()
        assert data["enabled"] is False
        # student post blocked
        r = requests.post(url, headers=_hdr(st), json={"body": "hi"})
        assert r.status_code == 403
    finally:
        _cleanup(cid, tt)


def test_non_enrolled_student_denied():
    tt, cid, sid, stid, lid = _make_course_with_lesson()
    st = _login("student@rgpacademy.com", "Student@123")
    # ensure not enrolled: use fresh registration
    fresh_email = f"test_p4_{uuid.uuid4().hex[:6]}@rgpacademy.com"
    requests.post(f"{API}/auth/register", json={"name": "TEST_P4 U", "email": fresh_email, "password": "abcdef", "role": "student"})
    fresh = _login(fresh_email, "abcdef")
    try:
        url = f"{API}/lessons/{cid}/{stid}/{lid}/comments"
        r = requests.get(url, headers=_hdr(fresh))
        assert r.status_code == 403
        r2 = requests.post(url, headers=_hdr(fresh), json={"body": "hi"})
        assert r2.status_code == 403
    finally:
        _cleanup(cid, tt)
        # cleanup fresh user
        admin = _login("admin@rgpacademy.com", "Admin@123")
        users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
        uid = next((u["id"] for u in users if u["email"] == fresh_email), None)
        if uid:
            requests.delete(f"{API}/admin/users/{uid}", headers=_hdr(admin))


def test_delete_own_and_teacher_can_delete_any():
    tt, cid, sid, stid, lid = _make_course_with_lesson()
    st = _enroll_student(cid)
    try:
        url = f"{API}/lessons/{cid}/{stid}/{lid}/comments"
        c1 = requests.post(url, headers=_hdr(st), json={"body": "student1"}).json()
        c2 = requests.post(url, headers=_hdr(tt), json={"body": "teacher msg"}).json()
        # student cannot delete teacher's
        r = requests.delete(f"{API}/comments/{c2['id']}", headers=_hdr(st))
        assert r.status_code == 403
        # student can delete own
        r = requests.delete(f"{API}/comments/{c1['id']}", headers=_hdr(st))
        assert r.status_code == 200
        # teacher can delete anyone's including own
        c3 = requests.post(url, headers=_hdr(st), json={"body": "student2"}).json()
        r = requests.delete(f"{API}/comments/{c3['id']}", headers=_hdr(tt))
        assert r.status_code == 200
    finally:
        _cleanup(cid, tt)


def test_delete_root_cascades_replies():
    tt, cid, sid, stid, lid = _make_course_with_lesson()
    st = _enroll_student(cid)
    try:
        url = f"{API}/lessons/{cid}/{stid}/{lid}/comments"
        root = requests.post(url, headers=_hdr(st), json={"body": "root"}).json()
        for i in range(3):
            requests.post(url, headers=_hdr(tt), json={"body": f"reply {i}", "parent_id": root["id"]}).json()
        assert len(requests.get(url, headers=_hdr(st)).json()["comments"]) == 4
        requests.delete(f"{API}/comments/{root['id']}", headers=_hdr(st)).raise_for_status()
        assert len(requests.get(url, headers=_hdr(st)).json()["comments"]) == 0
    finally:
        _cleanup(cid, tt)


def test_recording_comments_teacher_toggle():
    tt = _login("teacher@rgpacademy.com", "Teacher@123")
    # create a live class
    r = requests.post(f"{API}/live-classes", headers=_hdr(tt), json={
        "title": "TEST_P4 class", "subject": "Physics",
        "start_time": "2025-01-01T10:00:00+00:00", "duration_min": 60,
        "meeting_link": "https://meet.google.com/abc-defg-hij",
    })
    class_id = r.json()["id"]
    try:
        # post recording comment as teacher
        url = f"{API}/recordings/{class_id}/comments"
        r = requests.post(url, headers=_hdr(tt), json={"body": "welcome"}).json()
        assert r["context_type"] == "recording"
        # disable
        requests.put(f"{API}/live-classes/{class_id}/comments-toggle", headers=_hdr(tt), json={"comments_enabled": False}).raise_for_status()
        data = requests.get(url, headers=_hdr(tt)).json()
        assert data["enabled"] is False
        r = requests.post(url, headers=_hdr(tt), json={"body": "hi"})
        assert r.status_code == 403
    finally:
        requests.delete(f"{API}/live-classes/{class_id}", headers=_hdr(tt))
