"""Iteration 5 bug-fix pass tests.

Covers:
 1. GET /api/settings/public exposes razorpay_enabled + razorpay_key_id keys.
 2. POST /api/payments/razorpay/create-order without keys → 400 with 'Razorpay is not configured'.
 3. POST /api/payments/razorpay/verify without keys → 400 with 'Razorpay not configured'.
 4. Teacher can move a student's batch via PUT /api/courses/{cid}/students/{sid}/batch.
 5. Enrolment notify path exercises cc_admin (admin BCC email) — via backend logs.
 6. Landing page verified in frontend playwright script.
 7. No academy.vinodpungle references — checked via grep (report).
"""
import os
import time
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://educoach-platform.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")}
TEACHER = {"email": os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), "password": os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")}
STUDENT = {"email": os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), "password": os.getenv("TEST_STUDENT_PASSWORD", "Student@123")}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def teacher_token():
    return _login(TEACHER)


@pytest.fixture(scope="module")
def student_token():
    return _login(STUDENT)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------- 1. Public settings ----------------
def test_settings_public_exposes_razorpay(student_token):
    r = requests.get(f"{API}/settings/public", headers=_h(student_token), timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "razorpay_enabled" in data
    assert "razorpay_key_id" in data
    assert isinstance(data["razorpay_enabled"], bool)
    # env vars empty in preview
    assert data["razorpay_enabled"] == False
    assert data["razorpay_key_id"] == ""
    # UPI + portal_mode still there
    assert "portal_mode" in data
    assert "upi_qr_url" in data
    assert "upi_vpa" in data


# ---------------- 2 & 3. Razorpay endpoints when not configured ----------------
def test_razorpay_create_order_returns_400_when_not_configured(student_token):
    # Grab first paid course
    r = requests.get(f"{API}/courses", timeout=15)
    assert r.status_code == 200
    paid = [c for c in r.json() if float(c.get("price") or 0) > 0 and not c.get("is_free")]
    if not paid:
        pytest.skip("No paid course to test Razorpay against")
    course_id = paid[0]["id"]
    r2 = requests.post(
        f"{API}/payments/razorpay/create-order",
        headers=_h(student_token),
        json={"course_id": course_id},
        timeout=15,
    )
    assert r2.status_code == 400, r2.text
    assert "Razorpay is not configured" in r2.text


def test_razorpay_verify_returns_400_when_not_configured(student_token):
    r = requests.post(
        f"{API}/payments/razorpay/verify",
        headers=_h(student_token),
        json={
            "razorpay_order_id": "order_dummy",
            "razorpay_payment_id": "pay_dummy",
            "razorpay_signature": "deadbeef",
        },
        timeout=15,
    )
    assert r.status_code == 400, r.text
    assert "Razorpay not configured" in r.text


# ---------------- 4. Move student batch ----------------
def test_teacher_can_move_student_batch(teacher_token, student_token, admin_token):
    # Find a teacher course with at least one batch
    r = requests.get(f"{API}/teacher/courses", headers=_h(teacher_token), timeout=15)
    assert r.status_code == 200
    courses = r.json()
    assert len(courses) >= 1
    course = None
    batches = []
    for c in courses:
        b = requests.get(f"{API}/courses/{c['id']}/batches", headers=_h(teacher_token), timeout=15).json()
        if len(b) >= 1:
            course = c
            batches = b
            break
    if not course:
        pytest.skip("No teacher course with a batch — cannot test batch move")

    # Ensure at least one enrolled student — enrol via demo mode if needed
    students = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    if not students:
        # Try demo-mode enrol using student account
        # Switch to demo
        requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"portal_mode": "demo"}, timeout=15)
        try:
            requests.post(f"{API}/courses/{course['id']}/enroll", headers=_h(student_token), json={}, timeout=15)
        finally:
            requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"portal_mode": "live"}, timeout=15)
        students = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    if not students:
        pytest.skip("Could not create a student enrolment for batch move")

    student = students[0]
    target_batch = batches[0]["id"]

    # Move to batch 1
    r_move = requests.put(
        f"{API}/courses/{course['id']}/students/{student['id']}/batch",
        headers=_h(teacher_token),
        json={"batch_id": target_batch},
        timeout=15,
    )
    assert r_move.status_code == 200, r_move.text
    assert r_move.json().get("batch_id") == target_batch

    # Verify via GET
    students2 = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    row = next((s for s in students2 if s["id"] == student["id"]), None)
    assert row is not None
    assert row["batch_id"] == target_batch

    # Move back to self-paced (null)
    r_back = requests.put(
        f"{API}/courses/{course['id']}/students/{student['id']}/batch",
        headers=_h(teacher_token),
        json={"batch_id": None},
        timeout=15,
    )
    assert r_back.status_code == 200, r_back.text
    students3 = requests.get(f"{API}/courses/{course['id']}/students", headers=_h(teacher_token), timeout=15).json()
    row3 = next((s for s in students3 if s["id"] == student["id"]), None)
    assert row3["batch_id"] in (None, "")


def test_move_batch_invalid_returns_error(teacher_token):
    """Hermetic: create a throwaway TEST_ course so parallel runs don't collide with tests that delete courses."""
    course = requests.post(
        f"{API}/courses", headers=_h(teacher_token),
        json={"title": f"TEST_iter5_movebad_{uuid.uuid4().hex[:6]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True},
        timeout=15,
    ).json()
    try:
        r_bad = requests.put(
            f"{API}/courses/{course['id']}/students/non-existent-student/batch",
            headers=_h(teacher_token),
            json={"batch_id": "non-existent-batch"},
            timeout=15,
        )
        assert r_bad.status_code in (404, 400)
    finally:
        requests.delete(f"{API}/courses/{course['id']}", headers=_h(teacher_token), timeout=15)


# ---------------- 5. Admin BCC on enrolment notifications ----------------
def test_enrolment_triggers_admin_bcc_email(admin_token, student_token, teacher_token):
    """After enrolling in a course, backend should attempt two email sends
    (one to student, one to ADMIN_NOTIFY_EMAIL with [Admin] prefix — demo mode logs).
    Hermetic: creates its own TEST_ course to avoid shared-state pollution with other tests."""
    # Create a fresh throwaway paid course (portal will be in demo mode so enrol still succeeds)
    course = requests.post(
        f"{API}/courses", headers=_h(teacher_token),
        json={"title": f"TEST_iter5_bcc_{uuid.uuid4().hex[:6]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True},
        timeout=15,
    ).json()

    # Create a fresh student
    unique = f"TEST_bcc_{uuid.uuid4().hex[:8]}"
    reg = requests.post(
        f"{API}/auth/register",
        json={"name": unique, "email": f"{unique}@example.com", "password": "Test@123", "role": "student"},
        timeout=15,
    )
    if reg.status_code not in (200, 201):
        requests.delete(f"{API}/courses/{course['id']}", headers=_h(teacher_token), timeout=15)
        pytest.skip(f"register failed: {reg.text}")
    new_tok = reg.json().get("access_token") or _login({"email": f"{unique}@example.com", "password": "Test@123"})

    # Free course — enrolment works regardless of portal_mode (no parallel race).
    try:
        enrol = requests.post(
            f"{API}/courses/{course['id']}/enroll",
            headers=_h(new_tok),
            json={},
            timeout=15,
        )
    finally:
        requests.delete(f"{API}/courses/{course['id']}", headers=_h(teacher_token), timeout=15)

    assert enrol.status_code == 200, f"enrol failed: {enrol.text}"

    # Give async tasks time to schedule
    time.sleep(3)

    log_paths = [
        "/var/log/supervisor/backend.err.log",
        "/var/log/supervisor/backend.out.log",
    ]
    log_text = ""
    for p in log_paths:
        try:
            with open(p, "r") as f:
                log_text += f.read()[-40000:]
        except FileNotFoundError:
            pass

    student_email = f"{unique}@example.com".lower()
    # Look for both email addresses in logs (success or failure lines both include recipient email)
    assert student_email in log_text.lower(), (
        f"Expected student email {student_email} in backend logs — not found"
    )
    assert "contact@bioexamprep.com" in log_text, (
        "Expected admin BCC email to contact@bioexamprep.com — not found in backend logs. "
        "This means notify() cc_admin=True path did NOT fire."
    )
    # [Admin] subject prefix is code-verified in notify.py (line ~113). We cannot check in logs
    # because Resend send-failure lines don't include the subject.


# ---------------- 7. No stale references ----------------
def test_no_academy_vinodpungle_references():
    import subprocess
    result = subprocess.run(
        [
            "grep", "-r", "academy" + ".vinodpungle" + ".com",  # split to avoid self-match
            "/app/backend", "/app/frontend/src", "/app/memory",
            "--include=*.py", "--include=*.js", "--include=*.jsx",
            "--include=*.ts", "--include=*.tsx", "--include=*.md", "--include=*.json",
        ],
        capture_output=True, text=True,
    )
    assert result.stdout.strip() == "", f"Found stale academy.vinodpungle refs: {result.stdout}"
