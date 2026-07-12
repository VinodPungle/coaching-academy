"""Iteration 6 bug-fix pass — narrow follow-up on two issues from iteration_5.

Covered:
1. move_student_batch to Self-paced (batch_id=null) must return 200 without
   UnboundLocalError, and set enrollment.batch_id -> None.
2. Repeated calls: batch -> self-paced -> batch -> self-paced (idempotency).
3. Regression: settings/public still exposes razorpay_enabled=False (env keys empty)
   so the frontend banner path is reachable.
"""
import os
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE}/api"

ADMIN = {"email": os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")}
TEACHER = {"email": os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), "password": os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def teacher_token():
    return _login(TEACHER)


@pytest.fixture(scope="module")
def new_student_token(admin_token):
    """Register a fresh student so tests are hermetic."""
    unique = f"TEST_iter6_{uuid.uuid4().hex[:8]}"
    email = f"{unique}@example.com"
    reg = requests.post(
        f"{API}/auth/register",
        json={"name": unique, "email": email, "password": "Test@123", "role": "student"},
        timeout=15,
    )
    assert reg.status_code in (200, 201), reg.text
    tok = reg.json().get("access_token") or _login({"email": email, "password": "Test@123"})
    return tok, reg.json().get("user", {}).get("id") or reg.json().get("id")


def _pick_teacher_course_with_batch(teacher_token):
    r = requests.get(f"{API}/teacher/courses", headers=_h(teacher_token), timeout=15)
    assert r.status_code == 200
    for c in r.json():
        b = requests.get(f"{API}/courses/{c['id']}/batches", headers=_h(teacher_token), timeout=15).json()
        if b:
            return c, b
    return None, []


def _enrol_in_demo(admin_token, student_token, course_id):
    requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"portal_mode": "demo"}, timeout=15)
    try:
        r = requests.post(f"{API}/courses/{course_id}/enroll", headers=_h(student_token), json={}, timeout=15)
    finally:
        requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"portal_mode": "live"}, timeout=15)
    return r


# ---------- 1. Move to self-paced from batched ----------
def test_move_from_batch_to_self_paced_returns_200(teacher_token, admin_token, new_student_token):
    course, batches = _pick_teacher_course_with_batch(teacher_token)
    if not course:
        pytest.skip("No teacher course with a batch available")
    student_tok, _ = new_student_token
    # Fetch student id via /auth/me
    me = requests.get(f"{API}/auth/me", headers=_h(student_tok), timeout=15).json()
    student_id = me["id"]

    # Enrol this fresh student in the course (demo mode toggle)
    enrol = _enrol_in_demo(admin_token, student_tok, course["id"])
    assert enrol.status_code in (200, 201), enrol.text

    # Move to first batch
    r1 = requests.put(
        f"{API}/courses/{course['id']}/students/{student_id}/batch",
        headers=_h(teacher_token),
        json={"batch_id": batches[0]["id"]},
        timeout=15,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json().get("batch_id") == batches[0]["id"]

    # Move back to self-paced (batch_id=null) — this is the fixed path
    r2 = requests.put(
        f"{API}/courses/{course['id']}/students/{student_id}/batch",
        headers=_h(teacher_token),
        json={"batch_id": None},
        timeout=15,
    )
    assert r2.status_code == 200, f"Self-paced move failed: {r2.status_code} {r2.text}"
    assert r2.json().get("batch_id") is None

    # Verify persistence
    students = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    row = next((s for s in students if s["id"] == student_id), None)
    assert row is not None, "enrolled student not returned"
    assert row["batch_id"] in (None, "")
    assert row.get("batch_name") in (None, "")


# ---------- 2. Move directly to self-paced when student is already self-paced ----------
def test_move_self_paced_to_self_paced_is_idempotent(teacher_token, admin_token, new_student_token):
    """Explicit UnboundLocalError guard — if `batch` variable was referenced when
    body.batch_id was None, this call would 500. It must return 200."""
    course, batches = _pick_teacher_course_with_batch(teacher_token)
    if not course:
        pytest.skip("No teacher course with a batch available")
    student_tok, _ = new_student_token
    me = requests.get(f"{API}/auth/me", headers=_h(student_tok), timeout=15).json()
    student_id = me["id"]

    # Already enrolled from previous test — otherwise enrol
    students = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    if not any(s["id"] == student_id for s in students):
        _enrol_in_demo(admin_token, student_tok, course["id"])

    # Ensure the student is currently self-paced
    requests.put(
        f"{API}/courses/{course['id']}/students/{student_id}/batch",
        headers=_h(teacher_token),
        json={"batch_id": None},
        timeout=15,
    )

    # Fire self-paced -> self-paced again (this is what triggered UnboundLocalError before)
    r = requests.put(
        f"{API}/courses/{course['id']}/students/{student_id}/batch",
        headers=_h(teacher_token),
        json={"batch_id": None},
        timeout=15,
    )
    assert r.status_code == 200, f"Idempotent self-paced move failed: {r.status_code} {r.text}"
    assert r.json().get("batch_id") is None


# ---------- 3. Settings/public still exposes razorpay disabled so banner path renders ----------
def test_settings_public_razorpay_disabled(teacher_token):
    r = requests.get(f"{API}/settings/public", headers=_h(teacher_token), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("razorpay_enabled") == False, (
        "Preview env should have empty Razorpay keys → razorpay_enabled must be False. "
        f"Got: {data.get('razorpay_enabled')}"
    )
