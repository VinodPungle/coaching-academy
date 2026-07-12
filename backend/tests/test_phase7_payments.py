"""Phase 7 + 8 - Payments (UPI QR + partial payments + admin grant) & Portal mode (demo/live)."""
import os, uuid, requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def _new_student():
    email = f"test_p7_{uuid.uuid4().hex[:6]}@rgpacademy.com"
    requests.post(f"{API}/auth/register", json={"name": "TEST_P7 S", "email": email, "password": "abcdef", "role": "student"}).raise_for_status()
    return _login(email, "abcdef"), email


def _make_paid_course():
    tt = _login("teacher@rgpacademy.com", "Teacher@123")
    r = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P7 {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 1000, "is_free": False,
    })
    return tt, r.json()["id"]


def _make_free_course():
    tt = _login("teacher@rgpacademy.com", "Teacher@123")
    r = requests.post(f"{API}/courses", headers=_hdr(tt), json={
        "title": f"TEST_P7f {uuid.uuid4().hex[:8]}", "subject": "Physics", "description": "d", "price": 0, "is_free": True,
    })
    return tt, r.json()["id"]


def _cleanup(cid, tt):
    requests.delete(f"{API}/courses/{cid}", headers=_hdr(tt))


def _cleanup_user(email):
    admin = _login("admin@rgpacademy.com", "Admin@123")
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    uid = next((u["id"] for u in users if u["email"] == email), None)
    if uid:
        requests.delete(f"{API}/admin/users/{uid}", headers=_hdr(admin))


def _set_portal_mode(mode):
    admin = _login("admin@rgpacademy.com", "Admin@123")
    requests.put(f"{API}/admin/settings", headers=_hdr(admin), json={"portal_mode": mode}).raise_for_status()


def test_paid_course_enrol_blocked_in_live_mode():
    _set_portal_mode("live")
    tt, cid = _make_paid_course()
    st_token, st_email = _new_student()
    try:
        r = requests.post(f"{API}/courses/{cid}/enroll", headers=_hdr(st_token), json={})
        assert r.status_code == 402
        assert "paid course" in r.json()["detail"].lower()
    finally:
        _cleanup(cid, tt)
        _cleanup_user(st_email)


def test_paid_course_enrol_allowed_in_demo_mode():
    _set_portal_mode("demo")
    tt, cid = _make_paid_course()
    st_token, st_email = _new_student()
    try:
        r = requests.post(f"{API}/courses/{cid}/enroll", headers=_hdr(st_token), json={})
        assert r.status_code == 200
    finally:
        _set_portal_mode("live")
        _cleanup(cid, tt)
        _cleanup_user(st_email)


def test_free_course_enrol_works_in_any_mode():
    for mode in ("live", "demo"):
        _set_portal_mode(mode)
        tt, cid = _make_free_course()
        st_token, st_email = _new_student()
        try:
            r = requests.post(f"{API}/courses/{cid}/enroll", headers=_hdr(st_token), json={})
            assert r.status_code == 200, f"free enrol failed in mode={mode}: {r.text}"
        finally:
            _cleanup(cid, tt)
            _cleanup_user(st_email)


def test_admin_settings_upi_vpa_validation():
    admin = _login("admin@rgpacademy.com", "Admin@123")
    # invalid VPA (no @)
    r = requests.put(f"{API}/admin/settings", headers=_hdr(admin), json={"upi_vpa": "notavpa"})
    assert r.status_code == 400
    # valid
    r = requests.put(f"{API}/admin/settings", headers=_hdr(admin), json={"upi_vpa": "rohini@upi", "upi_qr_url": "/api/files/xyz"})
    assert r.status_code == 200
    # public endpoint returns
    st = _login("student@rgpacademy.com", "Student@123")
    r = requests.get(f"{API}/settings/public", headers=_hdr(st)).json()
    assert r["upi_vpa"] == "rohini@upi"
    assert r["upi_qr_url"] == "/api/files/xyz"
    # invalid portal mode
    r = requests.put(f"{API}/admin/settings", headers=_hdr(admin), json={"portal_mode": "chaos"})
    assert r.status_code == 400


def test_admin_records_partial_payment_and_grants_access():
    _set_portal_mode("live")
    tt, cid = _make_paid_course()  # fee = 1000
    st_token, st_email = _new_student()
    admin = _login("admin@rgpacademy.com", "Admin@123")
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    sid = next(u["id"] for u in users if u["email"] == st_email)
    try:
        r = requests.post(f"{API}/admin/payments/record", headers=_hdr(admin), json={
            "student_id": sid, "course_id": cid, "amount": 400, "method": "upi", "grant_access": True,
        })
        assert r.status_code == 200
        # enrolment created
        enrolls = requests.get(f"{API}/student/enrollments", headers=_hdr(st_token)).json()
        assert any(e["id"] == cid for e in enrolls)
        # outstanding = 600
        dues = requests.get(f"{API}/student/courses/{cid}/dues", headers=_hdr(st_token)).json()
        assert dues["fee"] == 1000
        assert dues["paid"] == 400
        assert dues["outstanding"] == 600
        # admin view
        detail = requests.get(f"{API}/admin/students/{sid}/course-payments/{cid}", headers=_hdr(admin)).json()
        assert detail["outstanding"] == 600
        assert len(detail["payments"]) == 1
    finally:
        _cleanup(cid, tt)
        _cleanup_user(st_email)


def test_reject_overpayment_and_edit():
    _set_portal_mode("live")
    tt, cid = _make_paid_course()  # fee = 1000
    st_token, st_email = _new_student()
    admin = _login("admin@rgpacademy.com", "Admin@123")
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    sid = next(u["id"] for u in users if u["email"] == st_email)
    try:
        # record 400
        p1 = requests.post(f"{API}/admin/payments/record", headers=_hdr(admin), json={
            "student_id": sid, "course_id": cid, "amount": 400, "method": "upi", "grant_access": True,
        }).json()
        # try to add 700 (over by 100)
        r = requests.post(f"{API}/admin/payments/record", headers=_hdr(admin), json={
            "student_id": sid, "course_id": cid, "amount": 700, "method": "upi", "grant_access": False,
        })
        assert r.status_code == 400
        assert "exceeds" in r.json()["detail"].lower() or "remaining" in r.json()["detail"].lower()
        # edit p1 upward to 600 -> outstanding 400
        r = requests.put(f"{API}/admin/payments/{p1['id']}", headers=_hdr(admin), json={"amount": 600})
        assert r.status_code == 200
        dues = requests.get(f"{API}/student/courses/{cid}/dues", headers=_hdr(st_token)).json()
        assert dues["paid"] == 600 and dues["outstanding"] == 400
        # edit downward too
        r = requests.put(f"{API}/admin/payments/{p1['id']}", headers=_hdr(admin), json={"amount": 200})
        assert r.status_code == 200
        dues = requests.get(f"{API}/student/courses/{cid}/dues", headers=_hdr(st_token)).json()
        assert dues["paid"] == 200 and dues["outstanding"] == 800
        # negative rejected via schema
        r = requests.post(f"{API}/admin/payments/record", headers=_hdr(admin), json={
            "student_id": sid, "course_id": cid, "amount": -100, "method": "upi",
        })
        assert r.status_code == 422
    finally:
        _cleanup(cid, tt)
        _cleanup_user(st_email)


def test_admin_grant_enrollment_without_payment():
    _set_portal_mode("live")
    tt, cid = _make_paid_course()
    st_token, st_email = _new_student()
    admin = _login("admin@rgpacademy.com", "Admin@123")
    users = requests.get(f"{API}/admin/users", headers=_hdr(admin)).json()
    sid = next(u["id"] for u in users if u["email"] == st_email)
    try:
        r = requests.post(f"{API}/admin/enrollments/grant", headers=_hdr(admin), json={"student_id": sid, "course_id": cid})
        assert r.status_code == 200
        # duplicate grant rejected
        r = requests.post(f"{API}/admin/enrollments/grant", headers=_hdr(admin), json={"student_id": sid, "course_id": cid})
        assert r.status_code == 400
        enrolls = requests.get(f"{API}/student/enrollments", headers=_hdr(st_token)).json()
        assert any(e["id"] == cid for e in enrolls)
    finally:
        _cleanup(cid, tt)
        _cleanup_user(st_email)
