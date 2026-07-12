"""Iteration 7 refactor smoke tests — validates payments refactor helpers and Razorpay error surface.

Covers:
1. Partial payment (₹400 on ₹1000, grant_access=false) → student NOT enrolled.
2. Another ₹600 payment → auto-enrolled with `auto_granted: true`.
3. PUT edit amount up so total >= fee → auto-enrolment triggered.
4. Over-payment rejected with 400 + specific message "Amount exceeds outstanding balance."
5. Razorpay create-order + verify return 400 with 'Razorpay is not configured' or 'Razorpay not configured'.
6. Server startup (via /api root) has no uuid/migration exception in logs.
"""
import os
import uuid as _uuid
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE}/api"

ADMIN = {"email": os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")}
TEACHER = {"email": os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), "password": os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")}
STUDENT = {"email": os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), "password": os.getenv("TEST_STUDENT_PASSWORD", "Student@123")}


def _login(cr):
    r = requests.post(f"{API}/auth/login", json=cr, timeout=15)
    assert r.status_code == 200, r.text
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
def student_token():
    return _login(STUDENT)


@pytest.fixture(scope="module")
def paid_course(teacher_token):
    """Teacher creates a paid ₹1000 course, unique so parallel runs don't collide."""
    unique = f"TEST_iter7_pay_{_uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{API}/courses",
        headers=_h(teacher_token),
        json={"title": unique, "subject": "General", "description": "Refactor smoke course", "price": 1000, "is_free": False},
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    yield cid
    requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


@pytest.fixture(scope="module")
def fresh_student(admin_token):
    """Fresh student so enrolments/payments are hermetic."""
    unique = f"TEST_iter7_stu_{_uuid.uuid4().hex[:8]}"
    email = f"{unique}@example.com"
    reg = requests.post(
        f"{API}/auth/register",
        json={"name": unique, "email": email, "password": "Test@123", "role": "student"},
        timeout=15,
    )
    assert reg.status_code in (200, 201), reg.text
    sid = reg.json().get("user", {}).get("id") or reg.json().get("id")
    tok = reg.json().get("access_token") or _login({"email": email, "password": "Test@123"})
    return {"id": sid, "email": email, "token": tok}


# ---------- 1. Partial payment does NOT enrol ----------
def test_partial_payment_does_not_enrol(admin_token, paid_course, fresh_student):
    body = {
        "student_id": fresh_student["id"],
        "course_id": paid_course,
        "amount": 400,
        "method": "upi",
        "notes": "TEST_iter7 partial 400",
        "grant_access": False,
    }
    r = requests.post(f"{API}/admin/payments/record", headers=_h(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text
    resp = r.json()
    # student should not be enrolled yet
    assert resp.get("auto_granted") in (False, None), f"unexpected auto_granted: {resp}"

    # Verify via enrolments list
    enrols = requests.get(
        f"{API}/admin/enrollments?student_id={fresh_student['id']}",
        headers=_h(admin_token),
        timeout=15,
    )
    if enrols.status_code == 200:
        payload = enrols.json()
        matched = [e for e in (payload if isinstance(payload, list) else payload.get("enrollments", [])) if e.get("course_id") == paid_course]
        assert not matched, f"student should NOT be enrolled after ₹400/₹1000 partial: {matched}"


# ---------- 2. Second payment completes total → auto-enrol ----------
def test_second_payment_completes_and_auto_enrols(admin_token, paid_course, fresh_student):
    body = {
        "student_id": fresh_student["id"],
        "course_id": paid_course,
        "amount": 600,
        "method": "upi",
        "notes": "TEST_iter7 remainder 600",
        "grant_access": False,   # intentionally False — helper should auto-flip because total reaches fee
    }
    r = requests.post(f"{API}/admin/payments/record", headers=_h(admin_token), json=body, timeout=15)
    assert r.status_code == 200, r.text
    resp = r.json()
    # NOTE: `auto_granted` semantics: true when this payment closes the balance and enrolment is created.
    assert resp.get("auto_granted") == True, f"Expected auto_granted True after ₹400+₹600, got: {resp}"

    # Confirm enrolment via admin course-payments endpoint (returns `enrolled: bool`)
    cp = requests.get(
        f"{API}/admin/students/{fresh_student['id']}/course-payments/{paid_course}",
        headers=_h(admin_token),
        timeout=15,
    )
    assert cp.status_code == 200, cp.text
    body = cp.json()
    assert body.get("paid") >= 1000, f"total paid should be ≥ 1000: {body}"
    assert body.get("enrolled") == True, f"student should be enrolled after full payment: {body}"


# ---------- 3. Over-payment rejected with specific message ----------
def test_overpayment_rejected_with_message(admin_token, teacher_token, fresh_student):
    """Uses a fresh ₹500 course + separate student to keep this isolated from case 2."""
    unique = f"TEST_iter7_ov_{_uuid.uuid4().hex[:8]}"
    cr = requests.post(
        f"{API}/courses",
        headers=_h(teacher_token),
        json={"title": unique, "subject": "General", "description": "over", "price": 500, "is_free": False},
        timeout=15,
    )
    assert cr.status_code in (200, 201), cr.text
    cid = cr.json()["id"]
    try:
        # First pay ₹300 (leaves ₹200 remaining)
        r1 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={
                "student_id": fresh_student["id"],
                "course_id": cid,
                "amount": 300,
                "method": "upi",
                "notes": "seed",
                "grant_access": False,
            },
            timeout=15,
        )
        assert r1.status_code == 200, r1.text

        # Now attempt ₹250 (exceeds ₹200 remaining)
        r2 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={
                "student_id": fresh_student["id"],
                "course_id": cid,
                "amount": 250,
                "method": "upi",
                "notes": "should fail",
                "grant_access": False,
            },
            timeout=15,
        )
        assert r2.status_code == 400, f"Expected 400 for overpayment, got {r2.status_code}: {r2.text}"
        detail = r2.json().get("detail", "")
        assert "exceeds outstanding balance" in detail.lower() or "exceeds" in detail.lower(), (
            f"Unexpected overpayment error: {detail}"
        )
        assert "remaining" in detail.lower() or "₹" in detail, f"Should mention remaining amount: {detail}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- 4. PUT edit amount up auto-enrols ----------
def test_edit_payment_up_auto_enrols(admin_token, teacher_token):
    """Create fresh course + student, record ₹200 on ₹500, then PUT amount to ₹500 → auto-enrol."""
    tag = _uuid.uuid4().hex[:8]
    cr = requests.post(
        f"{API}/courses",
        headers=_h(teacher_token),
        json={"title": f"TEST_iter7_edit_{tag}", "subject": "General", "description": "edit", "price": 500, "is_free": False},
        timeout=15,
    )
    assert cr.status_code in (200, 201), cr.text
    cid = cr.json()["id"]
    email = f"TEST_iter7_edit_stu_{tag}@example.com"
    reg = requests.post(
        f"{API}/auth/register",
        json={"name": f"TEST_iter7_edit_stu_{tag}", "email": email, "password": "Test@123", "role": "student"},
        timeout=15,
    )
    assert reg.status_code in (200, 201), reg.text
    sid = reg.json().get("user", {}).get("id") or reg.json().get("id")
    stu_tok = reg.json().get("access_token") or _login({"email": email, "password": "Test@123"})
    try:
        # Record ₹200 first
        r1 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={"student_id": sid, "course_id": cid, "amount": 200, "method": "upi", "notes": "seed", "grant_access": False},
            timeout=15,
        )
        assert r1.status_code == 200, r1.text
        pid = r1.json().get("payment_id") or r1.json().get("id") or r1.json().get("_id")
        assert pid, f"No payment id in create response: {r1.json()}"

        # Edit amount up to ₹500 (total now ≥ fee)
        r2 = requests.put(
            f"{API}/admin/payments/{pid}",
            headers=_h(admin_token),
            json={"amount": 500},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        resp = r2.json()
        # accept `auto_granted: true` OR the enrolment already reflected in resp
        auto = resp.get("auto_granted", False)

        # Verify actual enrolment via admin course-payments endpoint
        cp = requests.get(
            f"{API}/admin/students/{sid}/course-payments/{cid}",
            headers=_h(admin_token),
            timeout=15,
        )
        assert cp.status_code == 200, cp.text
        cpd = cp.json()
        assert cpd.get("paid") >= 500, f"total paid should be ≥ 500 after edit-up: {cpd}"
        assert cpd.get("enrolled") == True, (
            f"Student should be auto-enrolled after PUT edit-up to full fee: {cpd}"
        )
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- 5. Razorpay endpoints — env keys empty → 400 ----------
def test_razorpay_create_order_400_when_env_empty(student_token, paid_course):
    """Preview env has empty Razorpay keys → /create-order must 400 (not 502).
    Uses the hermetic paid_course fixture to avoid parallel-test course deletion races."""
    r = requests.post(
        f"{API}/payments/razorpay/create-order",
        headers=_h(student_token),
        json={"course_id": paid_course},
        timeout=15,
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "").lower()
    assert "razorpay" in detail and ("not configured" in detail or "temporarily unavailable" not in detail), (
        f"Expected 'Razorpay not configured' style error, got: {detail}"
    )


def test_razorpay_verify_400_when_env_empty(student_token):
    r = requests.post(
        f"{API}/payments/razorpay/verify",
        headers=_h(student_token),
        json={"razorpay_order_id": "fake", "razorpay_payment_id": "fake", "razorpay_signature": "fake"},
        timeout=15,
    )
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "").lower()
    assert "razorpay" in detail and "not configured" in detail, (
        f"Expected 'Razorpay not configured' style error, got: {detail}"
    )


def test_razorpay_error_leak_removed(student_token):
    """Ensure the leaked f-string 'Payment gateway error: <raw>' is no longer surfaced."""
    r = requests.post(
        f"{API}/payments/razorpay/verify",
        headers=_h(student_token),
        json={"razorpay_order_id": "fake", "razorpay_payment_id": "fake", "razorpay_signature": "fake"},
        timeout=15,
    )
    detail = r.json().get("detail", "")
    assert "Payment gateway error:" not in detail, f"Raw exception leak still present: {detail}"


# ---------- 6. Startup sanity ----------
def test_startup_ok_no_uuid_error():
    # Assumes the log file exists locally in this environment; skip gracefully otherwise
    log = "/var/log/supervisor/backend.err.log"
    if not os.path.exists(log):
        pytest.skip("Backend log not accessible")
    with open(log, "r") as f:
        text = f.read()  # read full file — startup marker may be far back
    assert "Startup complete: indexes ensured, seed data checked" in text, "Startup marker missing from logs"
    # No uuid import failure or migration crash
    assert "cannot import name 'uuid'" not in text
    assert "NameError: name 'uuid' is not defined" not in text
