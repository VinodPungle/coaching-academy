"""Course syllabus management tests.

Covers:
  Positive
    1. Teacher uploads a valid PDF and attaches it as the course syllabus.
    2. Student sees the syllabus on the course and can fetch the PDF.
    3. Teacher replaces the syllabus — course points at the new file, old file is gone.
    4. Teacher deletes the syllabus — association removed, file no longer accessible.
  Negative
    5. Uploading a disallowed file type is rejected.
    6. Attaching a non-PDF upload as syllabus is rejected.
    7. Oversized (>25 MB) document upload is rejected.
    8. Student cannot set or delete a syllabus (403).
    9. Another teacher cannot set/delete this course's syllabus (404 — not owner).
   10. Attaching a non-existent /api/files/ id is rejected (404).

Tests in this module share one course and run in file order (pytest-xdist
--dist loadscope keeps the module on a single worker).

All accounts are registered fresh so the suite is hermetic — no dependency on
seeded demo credentials.
"""
import os
import uuid as _uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE}/api"

PDF_V1 = b"%PDF-1.4\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF syllabus-v1\n"
PDF_V2 = b"%PDF-1.4\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF syllabus-v2\n"


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _register(role, tag):
    unique = f"TEST_syllabus_{tag}_{_uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": unique, "email": f"{unique}@example.com", "password": "Test@123", "role": role},
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["access_token"]


def _upload(token, filename, content, content_type="application/pdf"):
    return requests.post(
        f"{API}/files/upload",
        headers=_h(token),
        files={"file": (filename, content, content_type)},
        timeout=60,
    )


def _get_course(token, cid):
    r = requests.get(f"{API}/courses/{cid}", headers=_h(token), timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def teacher_token():
    return _register("teacher", "owner")


@pytest.fixture(scope="module")
def other_teacher_token():
    return _register("teacher", "other")


@pytest.fixture(scope="module")
def student_token():
    return _register("student", "stu")


@pytest.fixture(scope="module")
def course(teacher_token):
    unique = f"TEST_syllabus_course_{_uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{API}/courses",
        headers=_h(teacher_token),
        json={"title": unique, "subject": "General", "description": "Syllabus test course", "is_free": True, "price": 0},
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    yield cid
    requests.delete(f"{API}/courses/{cid}", headers=_h(teacher_token), timeout=15)


# ---------- 1. Teacher uploads a valid PDF and sets it as syllabus ----------
def test_upload_and_set_syllabus(teacher_token, course):
    up = _upload(teacher_token, "syllabus-v1.pdf", PDF_V1)
    assert up.status_code == 200, up.text
    payload = up.json()
    assert payload["url"].startswith("/api/files/"), payload

    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(teacher_token),
        json={"url": payload["url"], "filename": payload["filename"]},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["syllabus_url"] == payload["url"]

    doc = _get_course(teacher_token, course)
    assert doc.get("syllabus_url") == payload["url"]
    assert doc.get("syllabus_filename") == "syllabus-v1.pdf"

    # Teacher can view the uploaded PDF
    f = requests.get(f"{BASE}{payload['url']}", timeout=15)
    assert f.status_code == 200, f.text
    assert f.content == PDF_V1
    assert "pdf" in (f.headers.get("content-type") or "").lower()


# ---------- 2. Student sees and can view the syllabus ----------
def test_student_views_syllabus(student_token, course):
    doc = _get_course(student_token, course)
    assert doc.get("syllabus_url"), "student should see syllabus_url on the course"
    f = requests.get(f"{BASE}{doc['syllabus_url']}", timeout=15)
    assert f.status_code == 200, f.text
    assert f.content == PDF_V1


# ---------- 8. Student has read-only access ----------
def test_student_cannot_set_or_delete_syllabus(student_token, course):
    up = _upload(student_token, "sneaky.pdf", PDF_V2)
    assert up.status_code == 200, up.text  # generic upload is open to any authed user
    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(student_token),
        json={"url": up.json()["url"], "filename": "sneaky.pdf"},
        timeout=15,
    )
    assert r.status_code == 403, f"student PUT syllabus should 403, got {r.status_code}: {r.text}"
    r = requests.delete(f"{API}/courses/{course}/syllabus", headers=_h(student_token), timeout=15)
    assert r.status_code == 403, f"student DELETE syllabus should 403, got {r.status_code}: {r.text}"
    # course untouched
    assert _get_course(student_token, course).get("syllabus_filename") == "syllabus-v1.pdf"


# ---------- 9. Another teacher cannot touch this course's syllabus ----------
def test_other_teacher_cannot_modify_syllabus(other_teacher_token, course):
    up = _upload(other_teacher_token, "intruder.pdf", PDF_V2)
    assert up.status_code == 200, up.text
    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(other_teacher_token),
        json={"url": up.json()["url"], "filename": "intruder.pdf"},
        timeout=15,
    )
    assert r.status_code == 404, f"non-owner PUT should 404, got {r.status_code}: {r.text}"
    r = requests.delete(f"{API}/courses/{course}/syllabus", headers=_h(other_teacher_token), timeout=15)
    assert r.status_code == 404, f"non-owner DELETE should 404, got {r.status_code}: {r.text}"
    assert _get_course(other_teacher_token, course).get("syllabus_filename") == "syllabus-v1.pdf"


# ---------- 5. Disallowed file type rejected at upload ----------
def test_disallowed_extension_rejected(teacher_token):
    r = _upload(teacher_token, "malware.exe", b"MZ fake", "application/octet-stream")
    assert r.status_code == 400, f"expected 400 for .exe upload, got {r.status_code}: {r.text}"
    assert "not allowed" in r.json().get("detail", "").lower()


# ---------- 6. Non-PDF upload cannot become a syllabus ----------
def test_non_pdf_syllabus_rejected(teacher_token, course):
    up = _upload(teacher_token, "notes.txt", b"plain text notes", "text/plain")
    assert up.status_code == 200, up.text  # .txt is fine for the generic uploader…
    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(teacher_token),
        json={"url": up.json()["url"], "filename": "notes.txt"},
        timeout=15,
    )
    assert r.status_code == 400, f"expected 400 for non-PDF syllabus, got {r.status_code}: {r.text}"
    assert "pdf" in r.json().get("detail", "").lower()
    assert _get_course(teacher_token, course).get("syllabus_filename") == "syllabus-v1.pdf"


# ---------- 10. Dangling file reference rejected ----------
def test_missing_file_reference_rejected(teacher_token, course):
    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(teacher_token),
        json={"url": f"/api/files/{_uuid.uuid4()}", "filename": "ghost.pdf"},
        timeout=15,
    )
    assert r.status_code == 404, f"expected 404 for missing file id, got {r.status_code}: {r.text}"


# ---------- 7. Oversized document rejected ----------
def test_oversized_pdf_rejected(teacher_token):
    big = b"%PDF-1.4\n" + b"0" * (25 * 1024 * 1024 + 1)
    r = _upload(teacher_token, "huge.pdf", big)
    assert r.status_code == 400, f"expected 400 for >25MB upload, got {r.status_code}: {r.text}"
    assert "too large" in r.json().get("detail", "").lower()


# ---------- 3. Replace: course points at new file, old file removed ----------
def test_replace_syllabus(teacher_token, course):
    old_url = _get_course(teacher_token, course)["syllabus_url"]

    up = _upload(teacher_token, "syllabus-v2.pdf", PDF_V2)
    assert up.status_code == 200, up.text
    new_url = up.json()["url"]

    r = requests.put(
        f"{API}/courses/{course}/syllabus",
        headers=_h(teacher_token),
        json={"url": new_url, "filename": "syllabus-v2.pdf"},
        timeout=15,
    )
    assert r.status_code == 200, r.text

    doc = _get_course(teacher_token, course)
    assert doc["syllabus_url"] == new_url
    assert doc["syllabus_filename"] == "syllabus-v2.pdf"

    # New file serves, previous syllabus file is gone
    assert requests.get(f"{BASE}{new_url}", timeout=15).content == PDF_V2
    old = requests.get(f"{BASE}{old_url}", timeout=15)
    assert old.status_code == 404, f"replaced syllabus file should be deleted, got {old.status_code}"


# ---------- 4. Delete: association + file removed; students lose access ----------
def test_delete_syllabus(teacher_token, student_token, course):
    url = _get_course(teacher_token, course)["syllabus_url"]

    r = requests.delete(f"{API}/courses/{course}/syllabus", headers=_h(teacher_token), timeout=15)
    assert r.status_code == 200, r.text

    doc = _get_course(student_token, course)
    assert not doc.get("syllabus_url"), f"syllabus_url should be gone: {doc.get('syllabus_url')}"
    assert not doc.get("syllabus_filename")

    # Viewing after deletion fails — file is really gone
    gone = requests.get(f"{BASE}{url}", timeout=15)
    assert gone.status_code == 404, f"deleted syllabus file should 404, got {gone.status_code}"

    # Deleting again reports there is nothing to remove
    again = requests.delete(f"{API}/courses/{course}/syllabus", headers=_h(teacher_token), timeout=15)
    assert again.status_code == 404, f"second delete should 404, got {again.status_code}: {again.text}"
