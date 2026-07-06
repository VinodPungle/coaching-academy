"""
JAM Academy LMS — Iteration 3 backend tests.
Covers: leaderboard, notifications, forgot/reset password, batch-scoped live classes,
teacher analytics regression.
"""
import os
import re
import time
import uuid
import subprocess
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://educoach-platform.preview.emergentagent.com"
API = f"{BASE_URL}/api"

TEACHER_EMAIL = "teacher@jamacademy.com"
TEACHER_PASSWORD = "Teacher@123"
STUDENT_EMAIL = "student@jamacademy.com"
STUDENT_PASSWORD = "Student@123"


# ---------------------------- helpers ---------------------------- #

def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _register_student(prefix="test_it3"):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "name": "TEST_Student", "email": email, "password": "Passw0rd!", "role": "student"
    }, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "email": email, "user": d["user"], "password": "Passw0rd!"}


@pytest.fixture(scope="session")
def teacher_token():
    return _login(TEACHER_EMAIL, TEACHER_PASSWORD)


@pytest.fixture(scope="session")
def student_token():
    return _login(STUDENT_EMAIL, STUDENT_PASSWORD)


@pytest.fixture(scope="session")
def seed_course_id():
    r = requests.get(f"{API}/courses", timeout=15)
    assert r.status_code == 200
    return r.json()[0]["id"]


# ============================================================
# LEADERBOARD
# ============================================================

class TestLeaderboard:
    def test_leaderboard_ordering_and_my_rank(self, teacher_token):
        # create a test with 2 easy questions
        payload = {
            "title": "TEST_LB_" + uuid.uuid4().hex[:6],
            "subject": "Physics", "duration_min": 5, "published": True,
            "questions": [
                {"text": "2+2", "options": ["3", "4", "5", "6"], "correct_index": 1, "marks": 4},
                {"text": "3+3", "options": ["5", "6", "7", "8"], "correct_index": 1, "marks": 4},
            ],
        }
        cr = requests.post(f"{API}/tests", headers=_hdr(teacher_token), json=payload, timeout=15)
        assert cr.status_code == 200
        tid = cr.json()["id"]
        try:
            # 3 students with different scores
            s_high = _register_student()
            s_mid = _register_student()
            s_low = _register_student()

            def _get_qids(tok):
                gr = requests.get(f"{API}/tests/{tid}", headers=_hdr(tok), timeout=15).json()
                return [q["id"] for q in gr["questions"]]

            qids = _get_qids(s_high["token"])
            # high: both correct
            r1 = requests.post(f"{API}/tests/{tid}/attempt", headers=_hdr(s_high["token"]),
                               json={"answers": {qids[0]: 1, qids[1]: 1}}, timeout=15)
            assert r1.status_code == 200
            time.sleep(0.05)
            # mid: 1 correct
            r2 = requests.post(f"{API}/tests/{tid}/attempt", headers=_hdr(s_mid["token"]),
                               json={"answers": {qids[0]: 1, qids[1]: 0}}, timeout=15)
            assert r2.status_code == 200
            time.sleep(0.05)
            # low: 0 correct
            r3 = requests.post(f"{API}/tests/{tid}/attempt", headers=_hdr(s_low["token"]),
                               json={"answers": {qids[0]: 0, qids[1]: 0}}, timeout=15)
            assert r3.status_code == 200

            # fetch leaderboard as mid — verify ordering, rank, percentile
            lb = requests.get(f"{API}/tests/{tid}/leaderboard", headers=_hdr(s_mid["token"]), timeout=15)
            assert lb.status_code == 200
            body = lb.json()
            assert body["test_title"] == payload["title"]
            assert body["attempt_count"] == 3
            entries = body["entries"]
            assert len(entries) == 3
            # ordering: score desc
            scores = [e["score"] for e in entries]
            assert scores == sorted(scores, reverse=True), scores
            # rank 1 highest
            assert entries[0]["score"] == 8
            assert entries[2]["score"] == 0
            # my_rank for mid should be 2
            assert body["my_rank"] == 2
            # percentile = (3-2)/3 * 100 = 33
            assert body["my_percentile"] == 33
            # is_me flag
            me_entries = [e for e in entries if e["is_me"]]
            assert len(me_entries) == 1
            assert me_entries[0]["rank"] == 2

            # tie-break by submitted_at asc: create another test with two students getting same score
            # (already tested implicitly by sort order)
        finally:
            requests.delete(f"{API}/tests/{tid}", headers=_hdr(teacher_token), timeout=15)

    def test_leaderboard_no_attempts(self, teacher_token):
        payload = {"title": "TEST_LB_empty", "subject": "Physics", "duration_min": 5,
                   "published": True,
                   "questions": [{"text": "x", "options": ["a", "b"], "correct_index": 0, "marks": 4}]}
        cr = requests.post(f"{API}/tests", headers=_hdr(teacher_token), json=payload, timeout=15)
        tid = cr.json()["id"]
        try:
            lb = requests.get(f"{API}/tests/{tid}/leaderboard", headers=_hdr(teacher_token), timeout=15)
            assert lb.status_code == 200
            d = lb.json()
            assert d["entries"] == []
            assert d["attempt_count"] == 0
            assert d["my_rank"] is None
            assert d["my_percentile"] is None
        finally:
            requests.delete(f"{API}/tests/{tid}", headers=_hdr(teacher_token), timeout=15)

    def test_leaderboard_not_found(self, student_token):
        r = requests.get(f"{API}/tests/nope-xyz/leaderboard", headers=_hdr(student_token), timeout=15)
        assert r.status_code == 404


# ============================================================
# NOTIFICATIONS
# ============================================================

class TestNotifications:
    def test_enroll_notifies_student_and_teacher(self, teacher_token, seed_course_id):
        stu = _register_student()
        # student initially has zero notifications
        n0 = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
        assert n0["items"] == []
        assert n0["unread"] == 0

        # baseline teacher unread
        tn0 = requests.get(f"{API}/notifications", headers=_hdr(teacher_token), timeout=15).json()
        base_teacher_unread = tn0["unread"]

        # enroll
        er = requests.post(f"{API}/courses/{seed_course_id}/enroll",
                           headers=_hdr(stu["token"]), json={}, timeout=15)
        assert er.status_code == 200

        # student sees "Enrollment confirmed"
        n1 = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
        assert n1["unread"] >= 1
        titles = [i["title"] for i in n1["items"]]
        assert any("Enrollment" in t or "enrolled" in t for t in titles), titles

        # teacher gets "New student enrolled"
        tn1 = requests.get(f"{API}/notifications", headers=_hdr(teacher_token), timeout=15).json()
        assert tn1["unread"] >= base_teacher_unread + 1
        teacher_titles = [i["title"] for i in tn1["items"][:5]]
        assert any("New student enrolled" in t for t in teacher_titles), teacher_titles

    def test_mark_all_read(self, teacher_token, seed_course_id):
        stu = _register_student()
        requests.post(f"{API}/courses/{seed_course_id}/enroll",
                      headers=_hdr(stu["token"]), json={}, timeout=15)
        n = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
        assert n["unread"] >= 1

        r = requests.post(f"{API}/notifications/read-all", headers=_hdr(stu["token"]), timeout=15)
        assert r.status_code == 200

        n2 = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
        assert n2["unread"] == 0

    def test_grading_notifies_student(self, teacher_token):
        # create assignment
        cr = requests.post(f"{API}/assignments", headers=_hdr(teacher_token),
                           json={"title": "TEST_gradeNotify", "subject": "Physics",
                                 "description": "d", "due_date": "2030-01-01",
                                 "max_marks": 10}, timeout=15)
        aid = cr.json()["id"]
        try:
            stu = _register_student()
            sr = requests.post(f"{API}/assignments/{aid}/submit", headers=_hdr(stu["token"]),
                               json={"content": "work"}, timeout=15)
            sub_id = sr.json()["id"]

            # snapshot student's notifications before grade
            before = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()["unread"]

            gr = requests.put(f"{API}/submissions/{sub_id}/grade",
                              headers=_hdr(teacher_token),
                              json={"grade": 9, "feedback": "great"}, timeout=15)
            assert gr.status_code == 200

            after = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
            assert after["unread"] >= before + 1
            titles = [i["title"] for i in after["items"]]
            assert any("graded" in t.lower() or "assignment" in t.lower() for t in titles), titles
        finally:
            requests.delete(f"{API}/assignments/{aid}", headers=_hdr(teacher_token), timeout=15)

    def test_announcement_notifies_all_students(self, teacher_token):
        stu = _register_student()
        # baseline
        before = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()["unread"]

        cr = requests.post(f"{API}/announcements", headers=_hdr(teacher_token),
                           json={"title": "TEST_ann_notif", "body": "hey"}, timeout=15)
        assert cr.status_code == 200
        aid = cr.json()["id"]
        try:
            after = requests.get(f"{API}/notifications", headers=_hdr(stu["token"]), timeout=15).json()
            assert after["unread"] >= before + 1
        finally:
            requests.delete(f"{API}/announcements/{aid}", headers=_hdr(teacher_token), timeout=15)

    def test_notifications_require_auth(self):
        r = requests.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 401


# ============================================================
# FORGOT / RESET PASSWORD
# ============================================================

def _extract_reset_token(email: str) -> str:
    """Grep backend logs for the reset link matching this email."""
    for path in ("/var/log/supervisor/backend.err.log", "/var/log/supervisor/backend.out.log"):
        try:
            out = subprocess.check_output(
                ["grep", "-a", f"Password reset link for {email}", path],
                stderr=subprocess.DEVNULL, timeout=10,
            ).decode()
        except Exception:
            continue
        if out:
            m = re.findall(r"token=([A-Za-z0-9_\-]+)", out)
            if m:
                return m[-1]
    raise AssertionError(f"reset token not found for {email}")


class TestForgotResetPassword:
    def test_forgot_password_flow_new_account(self):
        # Use a throwaway registered account
        stu = _register_student(prefix="test_forgot")
        email = stu["email"]

        # forgot-password
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=15)
        assert r.status_code == 200
        assert "reset link has been sent" in r.json()["message"].lower()

        # allow log flush
        time.sleep(1.0)
        token = _extract_reset_token(email)
        assert len(token) > 20

        # reset with new password
        new_pass = "NewP@ss_" + uuid.uuid4().hex[:6]
        rp = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "password": new_pass}, timeout=15)
        assert rp.status_code == 200, rp.text
        assert "reset successful" in rp.json()["message"].lower()

        # old password fails
        old = requests.post(f"{API}/auth/login",
                            json={"email": email, "password": "Passw0rd!"}, timeout=15)
        assert old.status_code == 401

        # new password works
        lg = requests.post(f"{API}/auth/login",
                           json={"email": email, "password": new_pass}, timeout=15)
        assert lg.status_code == 200

        # reused token rejected
        reuse = requests.post(f"{API}/auth/reset-password",
                              json={"token": token, "password": "AnotherP@ss1"}, timeout=15)
        assert reuse.status_code == 400
        assert "invalid" in reuse.json()["detail"].lower() or "expired" in reuse.json()["detail"].lower()

    def test_reset_invalid_token(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "totally-fake-token-xyz", "password": "Passw0rd!"}, timeout=15)
        assert r.status_code == 400

    def test_forgot_password_unknown_email_still_200(self):
        # Should NOT reveal whether an account exists
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"noone_{uuid.uuid4().hex[:8]}@example.com"}, timeout=15)
        assert r.status_code == 200

    def test_reset_short_password_rejected(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "whatever", "password": "abc"}, timeout=15)
        assert r.status_code == 400


# ============================================================
# BATCH-SCOPED LIVE CLASSES
# ============================================================

class TestBatchScopedClasses:
    def test_scoped_visibility(self, teacher_token, seed_course_id):
        # Fetch the two seed batches for the course
        br = requests.get(f"{API}/courses/{seed_course_id}/batches",
                          headers=_hdr(teacher_token), timeout=15).json()
        assert len(br) >= 2
        batch_a = br[0]
        batch_b = br[1]

        # Teacher schedules class scoped to batch_a
        payload_a = {
            "title": "TEST_BatchClass_A_" + uuid.uuid4().hex[:6],
            "subject": "Physics",
            "start_time": "2030-01-01T10:00:00Z",
            "duration_min": 60,
            "meeting_link": "https://meet.example.com/a",
            "course_id": seed_course_id,
            "batch_id": batch_a["id"],
        }
        ca = requests.post(f"{API}/live-classes", headers=_hdr(teacher_token),
                           json=payload_a, timeout=15)
        assert ca.status_code == 200, ca.text
        cls_a = ca.json()
        assert cls_a["batch_id"] == batch_a["id"]
        assert cls_a["batch_name"] == batch_a["name"]
        assert cls_a["course_id"] == seed_course_id
        cls_a_id = cls_a["id"]

        # class scoped to batch_b
        payload_b = {**payload_a, "title": "TEST_BatchClass_B_" + uuid.uuid4().hex[:6],
                     "batch_id": batch_b["id"], "meeting_link": "https://meet.example.com/b"}
        cb = requests.post(f"{API}/live-classes", headers=_hdr(teacher_token),
                           json=payload_b, timeout=15)
        assert cb.status_code == 200
        cls_b_id = cb.json()["id"]

        # Course-scoped class (no batch) — visible to any student enrolled in course
        payload_course = {"title": "TEST_CourseClass_" + uuid.uuid4().hex[:6],
                          "subject": "Physics",
                          "start_time": "2030-01-02T10:00:00Z",
                          "duration_min": 60, "meeting_link": "https://ex.com/c",
                          "course_id": seed_course_id, "batch_id": None}
        cc = requests.post(f"{API}/live-classes", headers=_hdr(teacher_token),
                           json=payload_course, timeout=15)
        assert cc.status_code == 200
        cls_course_id = cc.json()["id"]

        # Global class (no course)
        payload_global = {"title": "TEST_GlobalClass_" + uuid.uuid4().hex[:6],
                          "subject": "Physics",
                          "start_time": "2030-01-03T10:00:00Z",
                          "duration_min": 60, "meeting_link": "https://ex.com/g"}
        cg = requests.post(f"{API}/live-classes", headers=_hdr(teacher_token),
                           json=payload_global, timeout=15)
        assert cg.status_code == 200
        cls_global_id = cg.json()["id"]

        try:
            # Fresh students: one in batch_a, one in batch_b, one enrolled in DIFFERENT course
            stu_a = _register_student()
            requests.post(f"{API}/courses/{seed_course_id}/enroll",
                          headers=_hdr(stu_a["token"]),
                          json={"batch_id": batch_a["id"]}, timeout=15).raise_for_status()

            stu_b = _register_student()
            requests.post(f"{API}/courses/{seed_course_id}/enroll",
                          headers=_hdr(stu_b["token"]),
                          json={"batch_id": batch_b["id"]}, timeout=15).raise_for_status()

            # student not enrolled in this course
            stu_none = _register_student()
            # (do not enroll)

            def _class_ids(tok):
                r = requests.get(f"{API}/live-classes", headers=_hdr(tok), timeout=15)
                assert r.status_code == 200
                return {c["id"] for c in r.json()}

            ids_a = _class_ids(stu_a["token"])
            ids_b = _class_ids(stu_b["token"])
            ids_none = _class_ids(stu_none["token"])

            # student A: sees A + course-scoped + global; NOT B
            assert cls_a_id in ids_a, "batch A student should see batch A class"
            assert cls_b_id not in ids_a, "batch A student should NOT see batch B class"
            assert cls_course_id in ids_a, "batch A student should see course-scoped class"
            assert cls_global_id in ids_a

            # student B: sees B + course-scoped + global; NOT A
            assert cls_b_id in ids_b
            assert cls_a_id not in ids_b
            assert cls_course_id in ids_b
            assert cls_global_id in ids_b

            # student not enrolled: sees ONLY global
            assert cls_global_id in ids_none
            assert cls_a_id not in ids_none
            assert cls_b_id not in ids_none
            assert cls_course_id not in ids_none

            # student dashboard 'upcoming_classes' respects same filter
            dash_a = requests.get(f"{API}/dashboard/student",
                                  headers=_hdr(stu_a["token"]), timeout=15).json()
            dash_upcoming_ids_a = {c["id"] for c in dash_a["upcoming_classes"]}
            assert cls_b_id not in dash_upcoming_ids_a
            # a or global should be there
            assert cls_a_id in dash_upcoming_ids_a or cls_course_id in dash_upcoming_ids_a or cls_global_id in dash_upcoming_ids_a
        finally:
            for cid in (cls_a_id, cls_b_id, cls_course_id, cls_global_id):
                requests.delete(f"{API}/live-classes/{cid}", headers=_hdr(teacher_token), timeout=15)

    def test_scoped_class_notifies_only_scoped_students(self, teacher_token, seed_course_id):
        # Set up: student enrolled in batch_a, student enrolled in batch_b, student not enrolled
        br = requests.get(f"{API}/courses/{seed_course_id}/batches",
                          headers=_hdr(teacher_token), timeout=15).json()
        batch_a = br[0]
        batch_b = br[1]

        stu_a = _register_student()
        requests.post(f"{API}/courses/{seed_course_id}/enroll",
                      headers=_hdr(stu_a["token"]),
                      json={"batch_id": batch_a["id"]}, timeout=15).raise_for_status()
        stu_b = _register_student()
        requests.post(f"{API}/courses/{seed_course_id}/enroll",
                      headers=_hdr(stu_b["token"]),
                      json={"batch_id": batch_b["id"]}, timeout=15).raise_for_status()

        # Read + clear existing notifications
        requests.post(f"{API}/notifications/read-all", headers=_hdr(stu_a["token"]), timeout=15)
        requests.post(f"{API}/notifications/read-all", headers=_hdr(stu_b["token"]), timeout=15)

        # schedule class scoped to batch_a
        payload = {"title": "TEST_ScopedNotify_" + uuid.uuid4().hex[:6],
                   "subject": "Physics",
                   "start_time": "2030-05-01T10:00:00Z",
                   "duration_min": 60, "meeting_link": "https://ex.com",
                   "course_id": seed_course_id, "batch_id": batch_a["id"]}
        cr = requests.post(f"{API}/live-classes", headers=_hdr(teacher_token),
                           json=payload, timeout=15)
        assert cr.status_code == 200
        cid = cr.json()["id"]
        try:
            time.sleep(0.5)
            na = requests.get(f"{API}/notifications", headers=_hdr(stu_a["token"]), timeout=15).json()
            nb = requests.get(f"{API}/notifications", headers=_hdr(stu_b["token"]), timeout=15).json()
            # A should have +1 unread with the class title
            titles_a = [i["title"] for i in na["items"]]
            assert na["unread"] >= 1, na
            assert any("live class" in t.lower() for t in titles_a), titles_a
            # B should NOT be notified about this scoped class
            titles_b = [i["title"] + ":" + i["body"] for i in nb["items"]]
            assert not any(payload["title"] in t for t in titles_b), titles_b
        finally:
            requests.delete(f"{API}/live-classes/{cid}", headers=_hdr(teacher_token), timeout=15)


# ============================================================
# REGRESSION
# ============================================================

class TestRegression:
    def test_teacher_analytics(self, teacher_token):
        r = requests.get(f"{API}/dashboard/teacher/analytics",
                         headers=_hdr(teacher_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "courses" in d and "tests" in d and "assignments" in d
        assert isinstance(d["courses"], list)

    def test_login_both_roles(self):
        assert _login(TEACHER_EMAIL, TEACHER_PASSWORD)
        assert _login(STUDENT_EMAIL, STUDENT_PASSWORD)

    def test_payments_demo_checkout_still_enrolls(self, teacher_token):
        # fresh student — enroll via payments/checkout+confirm
        r = requests.get(f"{API}/courses", timeout=15)
        cid = r.json()[1]["id"]  # 2nd course to reduce collision with other tests
        stu = _register_student()
        co = requests.post(f"{API}/payments/checkout", headers=_hdr(stu["token"]),
                           json={"course_id": cid, "method": "stripe"}, timeout=15)
        assert co.status_code == 200
        pid = co.json()["payment"]["id"]
        cf = requests.post(f"{API}/payments/{pid}/confirm", headers=_hdr(stu["token"]), timeout=15)
        assert cf.status_code == 200
        # verify enrolled
        me = requests.get(f"{API}/student/enrollments", headers=_hdr(stu["token"]), timeout=15).json()
        assert any(c["id"] == cid for c in me)
