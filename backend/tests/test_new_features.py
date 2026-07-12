"""
JAM Academy LMS — Tests for NEW features (iteration 2).
Covers: payments (demo mode), batches (CRUD + capacity), file uploads, course-linked
tests/assignments visibility.
"""
import io
import os
import uuid
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://educoach-platform.preview.emergentagent.com"
API = f"{BASE_URL}/api"

TEACHER_EMAIL = os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com")
TEACHER_PASSWORD = os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123")


# ---------------------------- helpers ---------------------------- #

def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _register_student():
    email = f"test_new_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "name": "TEST New", "email": email, "password": "Passw0rd!", "role": "student"
    }, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "email": email, "user": d["user"]}


def _register_teacher():
    email = f"test_teach_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "name": "TEST Teacher", "email": email, "password": "Passw0rd!", "role": "teacher"
    }, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"]}


# Minimal valid PDF bytes (1-page blank PDF)
MINI_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"0000000010 00000 n \n0000000053 00000 n \n0000000100 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
)


@pytest.fixture(scope="session")
def teacher_token():
    return _login(TEACHER_EMAIL, TEACHER_PASSWORD)


@pytest.fixture(scope="session")
def seed_course_id():
    """First seeded course (owned by seed teacher)."""
    r = requests.get(f"{API}/courses", timeout=15)
    assert r.status_code == 200
    arr = r.json()
    assert len(arr) >= 1
    return arr[0]["id"]


# ---------------------------- payments ---------------------------- #

class TestPayments:
    def test_payments_config_demo_mode(self):
        r = requests.get(f"{API}/payments/config", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["demo_mode"] == True, f"expected demo_mode true (empty stripe/razorpay keys), got {d}"
        assert d["stripe_configured"] == False
        assert d["razorpay_configured"] == False

    def test_full_checkout_confirm_creates_enrollment(self, seed_course_id, teacher_token):
        stu = _register_student()
        # get a batch id for this course
        br = requests.get(f"{API}/courses/{seed_course_id}/batches", headers=_hdr(stu["token"]), timeout=15)
        assert br.status_code == 200
        batches = br.json()
        assert len(batches) >= 2, "seed should provide 2 batches per course"
        batch_id = batches[0]["id"]
        initial_enrolled = batches[0]["enrolled_count"]

        # checkout
        co = requests.post(f"{API}/payments/checkout", headers=_hdr(stu["token"]),
                           json={"course_id": seed_course_id, "batch_id": batch_id, "method": "stripe"},
                           timeout=15)
        assert co.status_code == 200, co.text
        payload = co.json()
        assert payload["demo_mode"] == True
        payment = payload["payment"]
        assert payment["status"] == "pending"
        assert payment["gateway"] == "demo"
        assert payment["batch_id"] == batch_id
        pay_id = payment["id"]

        # confirm
        cf = requests.post(f"{API}/payments/{pay_id}/confirm", headers=_hdr(stu["token"]), timeout=15)
        assert cf.status_code == 200, cf.text
        assert cf.json()["status"] == "paid"

        # enrollment persists
        me = requests.get(f"{API}/student/enrollments", headers=_hdr(stu["token"]), timeout=15).json()
        assert any(c["id"] == seed_course_id for c in me)

        # my_batch is set on course detail
        cd = requests.get(f"{API}/courses/{seed_course_id}", headers=_hdr(stu["token"]), timeout=15).json()
        assert cd["enrolled"] == True
        assert cd["my_batch"] is not None
        assert cd["my_batch"]["id"] == batch_id

        # /api/student/payments lists it as paid
        pays = requests.get(f"{API}/student/payments", headers=_hdr(stu["token"]), timeout=15).json()
        assert any(p["id"] == pay_id and p["status"] == "paid" for p in pays)

        # batch enrolled_count incremented
        br2 = requests.get(f"{API}/courses/{seed_course_id}/batches",
                           headers=_hdr(teacher_token), timeout=15).json()
        target = [b for b in br2 if b["id"] == batch_id][0]
        assert target["enrolled_count"] == initial_enrolled + 1

        # /api/batches/{id}/students lists the new student (teacher only)
        bs = requests.get(f"{API}/batches/{batch_id}/students", headers=_hdr(teacher_token), timeout=15)
        assert bs.status_code == 200
        assert any(s["id"] == stu["user"]["id"] for s in bs.json())

        # duplicate checkout blocked
        co2 = requests.post(f"{API}/payments/checkout", headers=_hdr(stu["token"]),
                            json={"course_id": seed_course_id, "batch_id": batch_id, "method": "stripe"},
                            timeout=15)
        assert co2.status_code == 400
        assert "enrolled" in co2.json()["detail"].lower()

    def test_checkout_invalid_method(self, seed_course_id):
        stu = _register_student()
        r = requests.post(f"{API}/payments/checkout", headers=_hdr(stu["token"]),
                          json={"course_id": seed_course_id, "method": "bitcoin"}, timeout=15)
        assert r.status_code == 400

    def test_checkout_bad_course(self):
        stu = _register_student()
        r = requests.post(f"{API}/payments/checkout", headers=_hdr(stu["token"]),
                          json={"course_id": "nope-does-not-exist", "method": "stripe"}, timeout=15)
        assert r.status_code == 404

    def test_teacher_cannot_checkout(self, teacher_token, seed_course_id):
        r = requests.post(f"{API}/payments/checkout", headers=_hdr(teacher_token),
                          json={"course_id": seed_course_id, "method": "stripe"}, timeout=15)
        assert r.status_code == 403


# ---------------------------- batches ---------------------------- #

class TestBatches:
    def test_teacher_batch_crud_and_ownership(self, teacher_token, seed_course_id):
        # list initially
        r = requests.get(f"{API}/courses/{seed_course_id}/batches", headers=_hdr(teacher_token), timeout=15)
        assert r.status_code == 200
        initial = len(r.json())

        # create
        cr = requests.post(f"{API}/courses/{seed_course_id}/batches",
                           headers=_hdr(teacher_token),
                           json={"name": "TEST_Weekend Batch", "schedule": "Sat-Sun", "capacity": 10},
                           timeout=15)
        assert cr.status_code == 200, cr.text
        batch = cr.json()
        assert batch["name"] == "TEST_Weekend Batch"
        assert batch["capacity"] == 10
        assert batch["enrolled_count"] == 0
        bid = batch["id"]

        # verify list
        arr = requests.get(f"{API}/courses/{seed_course_id}/batches",
                           headers=_hdr(teacher_token), timeout=15).json()
        assert len(arr) == initial + 1
        assert any(b["id"] == bid for b in arr)

        # non-owner teacher cannot create batch on this course
        other = _register_teacher()
        nr = requests.post(f"{API}/courses/{seed_course_id}/batches",
                           headers=_hdr(other["token"]),
                           json={"name": "hack"}, timeout=15)
        assert nr.status_code == 404, "non-owner should not be able to create batch"

        # non-owner cannot delete either
        dnr = requests.delete(f"{API}/batches/{bid}", headers=_hdr(other["token"]), timeout=15)
        assert dnr.status_code == 404

        # owner can delete
        dr = requests.delete(f"{API}/batches/{bid}", headers=_hdr(teacher_token), timeout=15)
        assert dr.status_code == 200

    def test_batch_capacity_enforced(self, teacher_token, seed_course_id):
        # create a batch with capacity 1
        cr = requests.post(f"{API}/courses/{seed_course_id}/batches",
                           headers=_hdr(teacher_token),
                           json={"name": "TEST_TinyBatch", "capacity": 1}, timeout=15)
        assert cr.status_code == 200
        bid = cr.json()["id"]
        try:
            # student 1 fills it
            s1 = _register_student()
            co1 = requests.post(f"{API}/payments/checkout", headers=_hdr(s1["token"]),
                                json={"course_id": seed_course_id, "batch_id": bid, "method": "stripe"},
                                timeout=15)
            assert co1.status_code == 200, co1.text
            pid = co1.json()["payment"]["id"]
            cf1 = requests.post(f"{API}/payments/{pid}/confirm", headers=_hdr(s1["token"]), timeout=15)
            assert cf1.status_code == 200

            # student 2 checkout for same batch -> 400 batch full
            s2 = _register_student()
            co2 = requests.post(f"{API}/payments/checkout", headers=_hdr(s2["token"]),
                                json={"course_id": seed_course_id, "batch_id": bid, "method": "stripe"},
                                timeout=15)
            assert co2.status_code == 400
            assert "full" in co2.json()["detail"].lower()
        finally:
            requests.delete(f"{API}/batches/{bid}", headers=_hdr(teacher_token), timeout=15)


# ---------------------------- file uploads ---------------------------- #

class TestFiles:
    def test_upload_pdf_and_download(self, teacher_token):
        files = {"file": ("TEST_notes.pdf", io.BytesIO(MINI_PDF), "application/pdf")}
        r = requests.post(f"{API}/files/upload", headers=_hdr(teacher_token), files=files, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d
        assert d["filename"] == "TEST_notes.pdf"
        assert d["url"].startswith("/api/files/")
        assert d["size"] > 0

        # download
        dl = requests.get(f"{BASE_URL}{d['url']}", timeout=15)
        assert dl.status_code == 200
        assert dl.content.startswith(b"%PDF")

    def test_upload_disallowed_extension(self, teacher_token):
        files = {"file": ("virus.exe", io.BytesIO(b"MZ\x00\x00 fake exe"), "application/octet-stream")}
        r = requests.post(f"{API}/files/upload", headers=_hdr(teacher_token), files=files, timeout=15)
        assert r.status_code == 400
        assert "not allowed" in r.json()["detail"].lower()

    def test_upload_requires_auth(self):
        files = {"file": ("a.pdf", io.BytesIO(MINI_PDF), "application/pdf")}
        r = requests.post(f"{API}/files/upload", files=files, timeout=15)
        assert r.status_code == 401

    def test_get_file_not_found(self):
        r = requests.get(f"{API}/files/does-not-exist-xyz", timeout=15)
        assert r.status_code == 404


# ---------------------------- course-linked tests ---------------------------- #

class TestCourseLinkedContent:
    def test_course_linked_test_visibility(self, teacher_token, seed_course_id):
        # teacher creates a test linked to seed_course_id
        payload = {
            "title": "TEST_LinkedTest",
            "subject": "Physics",
            "duration_min": 5,
            "published": True,
            "course_id": seed_course_id,
            "questions": [{"text": "1+1", "options": ["1", "2", "3", "4"], "correct_index": 1, "marks": 4}],
        }
        cr = requests.post(f"{API}/tests", headers=_hdr(teacher_token), json=payload, timeout=15)
        assert cr.status_code == 200, cr.text
        test = cr.json()
        tid = test["id"]
        assert test["course_id"] == seed_course_id
        assert test["course_name"]  # not None

        try:
            # Fresh, non-enrolled student — should NOT see the linked test
            non_enrolled = _register_student()
            lr = requests.get(f"{API}/tests", headers=_hdr(non_enrolled["token"]), timeout=15)
            assert lr.status_code == 200
            ids = [t["id"] for t in lr.json()]
            assert tid not in ids, "non-enrolled student should NOT see course-linked test"

            # Enrolled student -> should see it
            enrolled = _register_student()
            # enroll via free enroll (course price doesn't matter for the enrollment record)
            er = requests.post(f"{API}/courses/{seed_course_id}/enroll",
                               headers=_hdr(enrolled["token"]), json={}, timeout=15)
            assert er.status_code == 200, er.text
            lr2 = requests.get(f"{API}/tests", headers=_hdr(enrolled["token"]), timeout=15).json()
            ids2 = [t["id"] for t in lr2]
            assert tid in ids2

            # unlinked test remains visible to non-enrolled
            un_payload = {**payload, "title": "TEST_Unlinked", "course_id": None}
            ur = requests.post(f"{API}/tests", headers=_hdr(teacher_token), json=un_payload, timeout=15)
            assert ur.status_code == 200
            un_tid = ur.json()["id"]
            try:
                lr3 = requests.get(f"{API}/tests", headers=_hdr(non_enrolled["token"]), timeout=15).json()
                assert un_tid in [t["id"] for t in lr3]
            finally:
                requests.delete(f"{API}/tests/{un_tid}", headers=_hdr(teacher_token), timeout=15)
        finally:
            requests.delete(f"{API}/tests/{tid}", headers=_hdr(teacher_token), timeout=15)

    def test_course_linked_assignment_visibility(self, teacher_token, seed_course_id):
        # linked assignment
        cr = requests.post(f"{API}/assignments", headers=_hdr(teacher_token),
                           json={"title": "TEST_LinkedAsgn", "subject": "Physics",
                                 "description": "test", "due_date": "2030-01-01",
                                 "max_marks": 10, "course_id": seed_course_id}, timeout=15)
        assert cr.status_code == 200, cr.text
        a = cr.json()
        aid = a["id"]
        assert a["course_name"], "course_name should be populated"

        try:
            non_enrolled = _register_student()
            lr = requests.get(f"{API}/assignments", headers=_hdr(non_enrolled["token"]), timeout=15).json()
            assert aid not in [x["id"] for x in lr], "non-enrolled student should NOT see linked assignment"

            enrolled = _register_student()
            er = requests.post(f"{API}/courses/{seed_course_id}/enroll",
                               headers=_hdr(enrolled["token"]), json={}, timeout=15)
            assert er.status_code == 200
            lr2 = requests.get(f"{API}/assignments", headers=_hdr(enrolled["token"]), timeout=15).json()
            assert aid in [x["id"] for x in lr2]
        finally:
            requests.delete(f"{API}/assignments/{aid}", headers=_hdr(teacher_token), timeout=15)

    def test_linked_test_bad_course_id_rejected(self, teacher_token):
        r = requests.post(f"{API}/tests", headers=_hdr(teacher_token),
                          json={"title": "TEST_BadLink", "subject": "Physics",
                                "duration_min": 5, "published": True,
                                "course_id": "no-such-course",
                                "questions": []}, timeout=15)
        assert r.status_code == 404

    def test_linked_assignment_bad_course_id_rejected(self, teacher_token):
        r = requests.post(f"{API}/assignments", headers=_hdr(teacher_token),
                          json={"title": "TEST_BadA", "subject": "Physics",
                                "course_id": "no-such-course"}, timeout=15)
        assert r.status_code == 404


# ---------------------------- assignment submission with file ---------------------------- #

class TestSubmissionWithFile:
    def test_student_submits_with_file_teacher_sees_link(self, teacher_token):
        # teacher creates unlinked assignment
        ar = requests.post(f"{API}/assignments", headers=_hdr(teacher_token),
                           json={"title": "TEST_FileAsgn", "subject": "Physics",
                                 "description": "upload pdf", "due_date": "2030-01-01",
                                 "max_marks": 10}, timeout=15)
        assert ar.status_code == 200
        aid = ar.json()["id"]

        try:
            stu = _register_student()
            # student uploads file
            up = requests.post(f"{API}/files/upload", headers=_hdr(stu["token"]),
                               files={"file": ("TEST_work.pdf", io.BytesIO(MINI_PDF), "application/pdf")},
                               timeout=30)
            assert up.status_code == 200
            f = up.json()
            file_url = f["url"]

            # submit
            sr = requests.post(f"{API}/assignments/{aid}/submit", headers=_hdr(stu["token"]),
                               json={"content": "my work", "file_url": file_url,
                                     "file_name": f["filename"]}, timeout=15)
            assert sr.status_code == 200, sr.text
            sub = sr.json()
            assert sub["file_url"] == file_url
            assert sub["file_name"] == "TEST_work.pdf"

            # teacher lists submissions and gets file_url
            subs = requests.get(f"{API}/assignments/{aid}/submissions",
                                headers=_hdr(teacher_token), timeout=15).json()
            match = [s for s in subs if s["id"] == sub["id"]][0]
            assert match["file_url"] == file_url
            assert match["file_name"] == "TEST_work.pdf"
        finally:
            requests.delete(f"{API}/assignments/{aid}", headers=_hdr(teacher_token), timeout=15)
