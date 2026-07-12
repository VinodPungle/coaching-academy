"""Phase 9 (enrollment mgmt) + Phase 10 (free courses on student dashboard)."""
import os, uuid, requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def _new_student():
    email = f"test_p9_{uuid.uuid4().hex[:6]}@rgpacademy.com"
    requests.post(f"{API}/auth/register", json={"name": "TEST_P9 S", "email": email, "password": os.getenv("TEST_FRESH_USER_PASSWORD", "abcdef"), "role": "student"}).raise_for_status()
    return _login(email, os.getenv("TEST_FRESH_USER_PASSWORD", "abcdef")), email


def _cleanup_user(email):
    admin = _login(os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin@123"))
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    uid = next((u["id"] for u in users if u["email"] == email), None)
    if uid: requests.delete(f"{API}/admin/users/{uid}", headers=_hdr(admin))


def test_teacher_moves_student_between_batches_and_selfpaced():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    admin = _login(os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin@123"))
    # Use a FREE course so the test doesn't depend on portal_mode (avoids parallel race with other tests toggling mode).
    course = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P9 {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True,
    }).json()
    b1 = requests.post(f"{API}/courses/{course['id']}/batches", headers=_hdr(tt), json={"name": "Morning", "schedule": "M-F 7am", "capacity": 10}).json()
    b2 = requests.post(f"{API}/courses/{course['id']}/batches", headers=_hdr(tt), json={"name": "Evening", "schedule": "M-F 6pm", "capacity": 10}).json()
    st_token, st_email = _new_student()
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    sid = next(u["id"] for u in users if u["email"] == st_email)
    try:
        requests.post(f"{API}/courses/{course['id']}/enroll", headers=_hdr(st_token), json={"batch_id": b1["id"]}).raise_for_status()
        # move to b2
        r = requests.put(f"{API}/courses/{course['id']}/students/{sid}/batch", headers=_hdr(tt), json={"batch_id": b2["id"]})
        assert r.status_code == 200
        # verify
        students = requests.get(f"{API}/courses/{course['id']}/students", headers=_hdr(tt)).json()
        row = next(s for s in students if s["id"] == sid)
        assert row["batch_id"] == b2["id"]
        assert row["batch_name"] == "Evening"
        # move to self-paced (batch_id=null)
        r = requests.put(f"{API}/courses/{course['id']}/students/{sid}/batch", headers=_hdr(tt), json={"batch_id": None})
        assert r.status_code == 200
        students = requests.get(f"{API}/courses/{course['id']}/students", headers=_hdr(tt)).json()
        row = next(s for s in students if s["id"] == sid)
        assert row["batch_id"] is None
    finally:
        requests.delete(f"{API}/courses/{course['id']}", headers=_hdr(tt))
        _cleanup_user(st_email)


def test_move_to_nonexistent_batch_rejected():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    admin = _login(os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin@123"))
    # Use a FREE course so this test doesn't depend on portal_mode (avoids parallel race with other tests toggling mode).
    course = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P9b {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True,
    }).json()
    st_token, st_email = _new_student()
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    sid = next(u["id"] for u in users if u["email"] == st_email)
    try:
        requests.post(f"{API}/courses/{course['id']}/enroll", headers=_hdr(st_token), json={}).raise_for_status()
        r = requests.put(f"{API}/courses/{course['id']}/students/{sid}/batch", headers=_hdr(tt), json={"batch_id": "does-not-exist"})
        assert r.status_code == 404
    finally:
        requests.delete(f"{API}/courses/{course['id']}", headers=_hdr(tt))
        _cleanup_user(st_email)


def test_dashboard_shows_free_courses():
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    free = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P10free {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True,
    }).json()
    paid = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P10paid {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 500, "is_free": False,
    }).json()
    st_token, st_email = _new_student()
    try:
        dash = requests.get(f"{API}/dashboard/student", headers=_hdr(st_token)).json()
        free_titles = [c["title"] for c in dash["free_courses"]]
        assert free["title"] in free_titles
        assert paid["title"] not in free_titles
        # enrol in free course from dashboard (should work in any mode)
        r = requests.post(f"{API}/courses/{free['id']}/enroll", headers=_hdr(st_token), json={})
        assert r.status_code == 200
        # should disappear from free list after enrolment
        dash = requests.get(f"{API}/dashboard/student", headers=_hdr(st_token)).json()
        free_titles_after = [c["title"] for c in dash["free_courses"]]
        assert free["title"] not in free_titles_after
    finally:
        requests.delete(f"{API}/courses/{free['id']}", headers=_hdr(tt))
        requests.delete(f"{API}/courses/{paid['id']}", headers=_hdr(tt))
        _cleanup_user(st_email)
