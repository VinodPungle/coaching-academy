"""Phase 6 - Test retakes toggle."""
import os, uuid, requests

API = os.environ.get("BACKEND_URL", "http://localhost:8001") + "/api"


def _login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _hdr(t): return {"Authorization": f"Bearer {t}"}


def _make_test(retakes=False):
    tt = _login(os.getenv("TEST_TEACHER_EMAIL", "teacher@rgpacademy.com"), os.getenv("TEST_TEACHER_PASSWORD", "Teacher@123"))
    r = requests.post(f"{API}/tests", headers=_hdr(tt), json={
        "title": f"TEST_P6 {uuid.uuid4().hex[:8]}", "subject": "Physics", "duration_min": 30, "published": True,
        "retakes_allowed": retakes,
        "questions": [{"text": "2+2?", "options": ["3", "4", "5", "6"], "correct_index": 1, "marks": 4}],
    })
    return tt, r.json()


def test_default_retakes_disabled():
    tt, test = _make_test(retakes=False)
    st = _login(os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))
    try:
        # attempt 1
        r = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {test["questions"][0]["id"]: 1}})
        assert r.status_code == 200
        # attempt 2 blocked
        r = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {test["questions"][0]["id"]: 0}})
        assert r.status_code == 400
        assert "retake" in r.json()["detail"].lower() or "already" in r.json()["detail"].lower()
    finally:
        # cleanup: force delete via admin (attempts prevent teacher delete)
        admin = _login(os.getenv("TEST_ADMIN_EMAIL", "admin@rgpacademy.com"), os.getenv("TEST_ADMIN_PASSWORD", "Admin@123"))
        r = requests.get(f"{API}/tests", headers=_hdr(admin)).json()
        # admin sees only own tests, so use direct DB via delete_many is out of scope. Skip test cleanup — will be cleaned by TEST_ cleanup.


def test_retakes_enabled_allows_reattempt_and_updates_score():
    tt, test = _make_test(retakes=True)
    st = _login(os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))
    try:
        qid = test["questions"][0]["id"]
        r1 = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {qid: 0}}).json()
        assert r1["score"] == 0
        # retake with correct answer
        r2 = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {qid: 1}}).json()
        assert r2["score"] == 4
        # leaderboard has exactly 1 entry (latest)
        lb = requests.get(f"{API}/tests/{test['id']}/leaderboard", headers=_hdr(st)).json()
        assert lb["attempt_count"] == 1
        assert lb["entries"][0]["score"] == 4
    finally:
        pass


def test_teacher_can_flip_retakes_mid_course():
    tt, test = _make_test(retakes=False)
    st = _login(os.getenv("TEST_STUDENT_EMAIL", "student@rgpacademy.com"), os.getenv("TEST_STUDENT_PASSWORD", "Student@123"))
    qid = test["questions"][0]["id"]
    try:
        # student attempts once
        requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {qid: 0}}).raise_for_status()
        # second blocked
        r = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {qid: 1}})
        assert r.status_code == 400
        # teacher flips retake ON
        requests.put(f"{API}/tests/{test['id']}", headers=_hdr(tt), json={
            "title": test["title"], "subject": "Physics", "duration_min": 30, "published": True,
            "retakes_allowed": True,
            "questions": [{"text": "2+2?", "options": ["3", "4", "5", "6"], "correct_index": 1, "marks": 4}],
        }).raise_for_status()
        # NOTE: PUT regenerates question ids per code — get new qid
        got = requests.get(f"{API}/tests/{test['id']}", headers=_hdr(tt)).json()
        new_qid = got["questions"][0]["id"]
        # now retake succeeds
        r = requests.post(f"{API}/tests/{test['id']}/attempt", headers=_hdr(st), json={"answers": {new_qid: 1}})
        assert r.status_code == 200
    finally:
        pass
