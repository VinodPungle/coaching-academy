"""Iteration 8 followup — validates the 3 refactor cleanups from iteration_7:

1. PUT /api/admin/payments/{payment_id} response contains {message, auto_granted: true}
   when edit-up causes student to be enrolled (and student is enrolled in DB).
2. PUT /api/admin/payments/{payment_id} response has auto_granted: false when editing
   an already-fully-paid record downward (no new enrolment; student was already enrolled).
3. POST /api/admin/payments/record over-amount error uses `.2f` precision on ₹.
4. POST /api/payments/razorpay/create-order over-amount error uses `.2f` precision on ₹.
5. Refactor confirmation: admin_edit_payment source no longer contains
   `db.enrollments.insert_one` (delegates entirely to _maybe_enroll_and_notify).
"""
import os
import re
import uuid as _uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE}/api"

ADMIN = {"email": os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin@123")}
TEACHER = {"email": os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), "password": os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")}


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


def _create_paid_course(teacher_token, price=1000):
    unique = f"TEST_iter8_{_uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{API}/courses",
        headers=_h(teacher_token),
        json={"title": unique, "subject": "General", "description": "iter8", "price": price, "is_free": False},
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _register_student(tag):
    email = f"TEST_iter8_stu_{tag}@example.com"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": f"TEST_iter8_stu_{tag}", "email": email, "password": "Test@123", "role": "student"},
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    sid = r.json().get("user", {}).get("id") or r.json().get("id")
    tok = r.json().get("access_token") or _login({"email": email, "password": "Test@123"})
    return {"id": sid, "email": email, "token": tok}


# ---------- Case 1: Edit-up on partial → auto_granted:true + student enrolled ----------
def test_put_edit_up_returns_auto_granted_true_and_enrolls(admin_token, teacher_token):
    tag = _uuid.uuid4().hex[:8]
    cid = _create_paid_course(teacher_token, price=1000)
    stu = _register_student(tag)
    try:
        # Seed partial ₹400 (grant_access=False so student is NOT yet enrolled)
        r1 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={
                "student_id": stu["id"], "course_id": cid, "amount": 400,
                "method": "upi", "notes": "seed 400", "grant_access": False,
            },
            timeout=15,
        )
        assert r1.status_code == 200, r1.text
        pid = r1.json().get("payment_id") or r1.json().get("id") or r1.json().get("_id")
        assert pid, r1.json()

        # Baseline: student should NOT be enrolled
        # Note: /api/student/enrollments returns joined course objects (course_id is under `id`)
        el = requests.get(f"{API}/student/enrollments", headers=_h(stu["token"]), timeout=15)
        assert el.status_code == 200, el.text
        el_list = el.json() if isinstance(el.json(), list) else []
        assert not any((e.get("id") == cid or e.get("course_id") == cid) for e in el_list), \
            f"student should not be enrolled after ₹400/₹1000 partial: {el_list}"

        # Edit the payment amount UP to ₹1000 → total_paid == fee → auto-enrol
        r2 = requests.put(
            f"{API}/admin/payments/{pid}",
            headers=_h(admin_token),
            json={"amount": 1000},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        resp = r2.json()
        assert "message" in resp, f"Response missing `message`: {resp}"
        assert "auto_granted" in resp, f"Response missing `auto_granted`: {resp}"
        assert resp["auto_granted"] is True, f"Expected auto_granted=True, got: {resp}"

        # Verify via student GET /api/student/enrollments as that student
        el2 = requests.get(f"{API}/student/enrollments", headers=_h(stu["token"]), timeout=15)
        assert el2.status_code == 200, el2.text
        enrols = el2.json() if isinstance(el2.json(), list) else []
        assert any((e.get("id") == cid or e.get("course_id") == cid) for e in enrols), \
            f"student must now be enrolled in course {cid}: {enrols}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- Case 2: Edit an already-fully-paid record DOWN → auto_granted:false ----------
def test_put_edit_down_on_already_paid_returns_auto_granted_false(admin_token, teacher_token):
    tag = _uuid.uuid4().hex[:8]
    cid = _create_paid_course(teacher_token, price=1000)
    stu = _register_student(tag)
    try:
        # Full payment with grant_access=True → student is enrolled from the start
        r1 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={
                "student_id": stu["id"], "course_id": cid, "amount": 1000,
                "method": "upi", "notes": "full 1000", "grant_access": True,
            },
            timeout=15,
        )
        assert r1.status_code == 200, r1.text
        pid = r1.json().get("payment_id") or r1.json().get("id") or r1.json().get("_id")
        assert pid, r1.json()

        # Confirm student is enrolled
        el = requests.get(f"{API}/student/enrollments", headers=_h(stu["token"]), timeout=15)
        assert el.status_code == 200
        el_list = el.json() if isinstance(el.json(), list) else []
        assert any((e.get("id") == cid or e.get("course_id") == cid) for e in el_list), \
            f"student should be enrolled after full payment: {el_list}"

        # Edit DOWN to ₹800 — student already enrolled → auto_granted must be False
        r2 = requests.put(
            f"{API}/admin/payments/{pid}",
            headers=_h(admin_token),
            json={"amount": 800},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        resp = r2.json()
        assert "message" in resp and "auto_granted" in resp, f"Missing keys: {resp}"
        assert resp["auto_granted"] is False, f"Expected auto_granted=False (already enrolled), got: {resp}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- Case 3: Over-amount record → .2f precision ----------
def test_record_overpayment_error_uses_2f_precision(admin_token, teacher_token):
    tag = _uuid.uuid4().hex[:8]
    cid = _create_paid_course(teacher_token, price=1000)
    stu = _register_student(tag)
    try:
        # Seed ₹400 → remaining ₹600
        r1 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={"student_id": stu["id"], "course_id": cid, "amount": 400,
                  "method": "upi", "notes": "seed", "grant_access": False},
            timeout=15,
        )
        assert r1.status_code == 200, r1.text

        # Attempt ₹700 → should 400
        r2 = requests.post(
            f"{API}/admin/payments/record",
            headers=_h(admin_token),
            json={"student_id": stu["id"], "course_id": cid, "amount": 700,
                  "method": "upi", "notes": "over", "grant_access": False},
            timeout=15,
        )
        assert r2.status_code == 400, r2.text
        detail = r2.json().get("detail", "")
        assert "₹" in detail, f"Missing ₹ in error: {detail}"
        # Must be .2f (e.g. ₹600.00) — must have `.dd` decimal portion
        m = re.search(r"₹(\d+\.\d{2})", detail)
        assert m, f"Expected ₹NNN.NN (.2f) format, got: {detail}"
        assert m.group(1) == "600.00", f"Expected ₹600.00 remaining, got: {detail}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- Case 4: Razorpay create-order over-amount error uses .2f ----------
def test_razorpay_create_order_overamount_uses_2f_precision(admin_token, teacher_token):
    """Razorpay's `_resolve_razorpay_amount` now uses .2f (was .0f).
    Trigger the over-amount branch: request amount > remaining balance.
    Note: env keys are empty so the request may hit the Razorpay-not-configured error
    BEFORE amount validation. Order of checks in create-order:
      1. Course exists (404) → 2. is_free (400) → 3. amount validation (400)
      → 4. _razorpay_client (400 not configured).
    Amount validation happens BEFORE client init, so this test should trigger .2f."""
    tag = _uuid.uuid4().hex[:8]
    cid = _create_paid_course(teacher_token, price=1000)
    stu = _register_student(tag)
    try:
        # Attempt to create Razorpay order for ₹1500 on ₹1000 course → over
        r = requests.post(
            f"{API}/payments/razorpay/create-order",
            headers=_h(stu["token"]),
            json={"course_id": cid, "amount": 1500},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "")
        # Should hit the amount check with .2f (₹1000.00), NOT the "not configured" path
        if "not configured" in detail.lower():
            pytest.skip(f"Amount validation short-circuited by Razorpay config check: {detail}")
        assert "₹" in detail, f"Missing ₹ in error: {detail}"
        m = re.search(r"₹(\d+\.\d{2})", detail)
        assert m, f"Expected ₹NNN.NN (.2f) format, got: {detail}"
        assert m.group(1) == "1000.00", f"Expected ₹1000.00, got: {detail}"
    finally:
        requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- Case 5: Refactor confirmation via source grep ----------
def test_admin_edit_payment_no_longer_inlines_enrollment_insert():
    """admin_edit_payment must delegate to _maybe_enroll_and_notify — no `db.enrollments.insert_one` in its body."""
    src = open("/app/backend/routers/payments.py", "r").read()
    # Find the function body between `async def admin_edit_payment` and the next `async def` or `@router`
    m = re.search(
        r"async def admin_edit_payment\(.*?\n(.*?)(?=\n@router\.|\nasync def )",
        src,
        re.DOTALL,
    )
    assert m, "Could not locate admin_edit_payment in payments.py"
    body = m.group(1)
    assert "db.enrollments.insert_one" not in body, (
        f"admin_edit_payment still inlines `db.enrollments.insert_one` — refactor incomplete. Body:\n{body}"
    )
    # Positive check: must delegate to _maybe_enroll_and_notify
    assert "_maybe_enroll_and_notify" in body, (
        "admin_edit_payment should call _maybe_enroll_and_notify"
    )
