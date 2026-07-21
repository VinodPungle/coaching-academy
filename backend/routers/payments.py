"""Phase 7 payments + Phase 8 portal mode + Razorpay online payments.

- UPI: admin uploads QR + VPA; students pay offline; admin records payments.
- Razorpay: online instant payments; auto-records payment + enrols student on signature verify.
"""
import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from database import db
from auth_utils import require_role, get_current_user
from notify import notify, email_template

logger = logging.getLogger(__name__)
try:
    import razorpay  # type: ignore
except ImportError:  # graceful fallback if package not installed
    razorpay = None

router = APIRouter(tags=["payments"])


SETTINGS_ID = "portal_settings"


async def get_settings() -> dict:
    doc = await db.settings.find_one({"_id": SETTINGS_ID}) or {}
    doc.setdefault("portal_mode", "live")   # live | demo
    doc.setdefault("upi_qr_url", "")
    doc.setdefault("upi_vpa", "")
    return doc


@router.get("/settings/public")
async def public_settings():
    """Endpoint any authenticated user can read (portal mode + UPI details + Razorpay key)."""
    s = await get_settings()
    return {
        "portal_mode": s["portal_mode"],
        "upi_qr_url": s.get("upi_qr_url", ""),
        "upi_vpa": s.get("upi_vpa", ""),
        "razorpay_enabled": bool(os.environ.get("RAZORPAY_KEY_ID", "").strip() and os.environ.get("RAZORPAY_KEY_SECRET", "").strip()),
        "razorpay_key_id": os.environ.get("RAZORPAY_KEY_ID", "").strip(),
    }


def _razorpay_client():
    if razorpay is None:
        raise HTTPException(status_code=500, detail="Razorpay SDK not installed on server")
    key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        raise HTTPException(status_code=400, detail="Razorpay is not configured. Ask the admin to add API keys.")
    return razorpay.Client(auth=(key_id, key_secret))


class RazorpayOrderBody(BaseModel):
    course_id: str
    batch_id: Optional[str] = None
    amount: Optional[float] = None   # if None, uses full remaining balance


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> None:
    """Validate Razorpay HMAC-SHA256 signature. Raises 400 on mismatch or missing secret."""
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_secret:
        raise HTTPException(status_code=400, detail="Razorpay not configured")
    expected = hmac.new(
        key_secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")


def _resolve_razorpay_amount(remaining: float, requested: Optional[float]) -> float:
    """Determine payment amount from remaining balance + optional user override. Raise if invalid."""
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="No outstanding balance for this course")
    amount = float(requested) if requested else remaining
    if amount <= 0 or amount > remaining:
        raise HTTPException(status_code=400, detail=f"Amount must be between ₹1 and ₹{remaining:.2f}")
    return amount


def _new_razorpay_receipt(course_id: str, student_id: str) -> str:
    ts = int(datetime.now(timezone.utc).timestamp())
    return f"c_{course_id[:8]}_{student_id[:8]}_{ts}"[:40]


@router.post("/payments/razorpay/create-order")
async def create_razorpay_order(body: RazorpayOrderBody, user: dict = Depends(require_role("student"))):
    """Step 1 of the online-payment flow: creates a Razorpay order (server
    to server) for the outstanding balance (or a partial amount) and
    records it as "created" so verify_razorpay() can later confirm it
    actually belongs to this student/course."""
    course = await db.courses.find_one({"_id": body.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    fee = float(course.get("price", 0) or 0)
    if fee <= 0 or course.get("is_free"):
        raise HTTPException(status_code=400, detail="This course is free — enrol directly")
    remaining = max(fee - await _total_paid(user["id"], body.course_id), 0)
    amount = _resolve_razorpay_amount(remaining, body.amount)
    client = _razorpay_client()
    receipt = _new_razorpay_receipt(body.course_id, user["id"])
    try:
        order = client.order.create({
            "amount": int(round(amount * 100)),
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "course_id": body.course_id,
                "student_id": user["id"],
                "batch_id": body.batch_id or "",
            },
        })
    except Exception as e:
        logger.error(f"Razorpay order create failed: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway is temporarily unavailable. Please retry.")
    await db.razorpay_orders.insert_one({
        "_id": order["id"],
        "student_id": user["id"],
        "course_id": body.course_id,
        "batch_id": body.batch_id,
        "amount": amount,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "razorpay_key_id": os.environ.get("RAZORPAY_KEY_ID", "").strip(),
        "prefill": {"name": user["name"], "email": user["email"], "contact": user.get("phone") or ""},
    }


class RazorpayVerifyBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/payments/razorpay/verify")
async def verify_razorpay(body: RazorpayVerifyBody, user: dict = Depends(require_role("student"))):
    """Step 2: called by the frontend after Razorpay's checkout widget
    succeeds. Verifies the HMAC signature (proves the payment is genuine,
    not spoofed by the client), records it as a normal payment doc via the
    same _build_payment_doc/_maybe_enroll_and_notify helpers admin-recorded
    payments use, and marks the order "paid" so re-verification is a no-op."""
    _verify_razorpay_signature(body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature)
    order = await db.razorpay_orders.find_one({"_id": body.razorpay_order_id, "student_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "paid":
        return {"message": "Already recorded"}
    course = await db.courses.find_one({"_id": order["course_id"]})
    payment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    fake_body = type("Body", (), {
        "amount": order["amount"],
        "method": "razorpay",
        "notes": f"Razorpay payment_id={body.razorpay_payment_id}",
        "batch_id": order.get("batch_id"),
    })()
    doc = _build_payment_doc(
        student={"_id": user["id"], "name": user["name"]},
        course=course or {"_id": order["course_id"], "title": ""},
        body=fake_body,
        recorded_by_id="razorpay",
        recorded_by_name="Razorpay (online)",
        extras={
            "_id": payment_id,
            "razorpay_order_id": body.razorpay_order_id,
            "razorpay_payment_id": body.razorpay_payment_id,
        },
        is_test=bool(user.get("is_demo")),
    )
    await db.payments.insert_one(doc)
    await db.razorpay_orders.update_one(
        {"_id": body.razorpay_order_id},
        {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}},
    )
    total_paid = await _total_paid(user["id"], order["course_id"])
    fee = float((course or {}).get("price", 0) or 0)
    reason = "fully_paid" if total_paid >= fee else "razorpay"
    granted = await _maybe_enroll_and_notify(
        {"_id": user["id"], "name": user["name"]}, course or {"_id": order["course_id"], "title": ""},
        payment_id, order.get("batch_id"), fee, total_paid, reason,
    )
    return {
        "message": "Payment verified",
        "payment_id": payment_id,
        "auto_enrolled": granted,
        "paid": total_paid,
        "outstanding": max(fee - total_paid, 0),
    }


class SettingsBody(BaseModel):
    portal_mode: Optional[str] = None       # "demo" | "live"
    upi_qr_url: Optional[str] = None        # image file URL uploaded via /files/upload
    upi_vpa: Optional[str] = None           # e.g. "rohini@upi"


@router.put("/admin/settings")
async def update_settings(body: SettingsBody, user: dict = Depends(require_role("admin"))):
    """Admin-only, partial update of portal-wide payment settings — demo
    mode (bypasses paid-enrollment gating platform-wide) and the UPI QR/VPA
    students see when paying offline."""
    update = {}
    if body.portal_mode is not None:
        if body.portal_mode not in ("demo", "live"):
            raise HTTPException(status_code=400, detail="portal_mode must be 'demo' or 'live'")
        update["portal_mode"] = body.portal_mode
    if body.upi_qr_url is not None:
        update["upi_qr_url"] = body.upi_qr_url.strip()
    if body.upi_vpa is not None:
        # basic UPI VPA validation: contains @
        vpa = body.upi_vpa.strip()
        if vpa and "@" not in vpa:
            raise HTTPException(status_code=400, detail="UPI VPA must contain '@', e.g. 'name@bank'")
        update["upi_vpa"] = vpa
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.settings.update_one({"_id": SETTINGS_ID}, {"$set": update}, upsert=True)
    return await get_settings()


class PaymentRecordBody(BaseModel):
    student_id: str
    course_id: str
    amount: float = Field(..., ge=0)
    method: str = "upi"                    # upi | cash | bank | other
    notes: str = ""
    batch_id: Optional[str] = None
    grant_access: bool = True              # grant enrolment on record


async def _fetch_course_and_student(course_id: str, student_id: str):
    """Load course + student; raise 404 if either missing. Returns (course, student)."""
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    student = await db.users.find_one({"_id": student_id, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return course, student


def _assert_amount_within_outstanding(amount: float, fee: float, prior_paid: float):
    """Reject over-payment. No-op for free courses (fee=0)."""
    if fee > 0 and (prior_paid + amount) > fee:
        remaining = max(fee - prior_paid, 0)
        raise HTTPException(status_code=400, detail=f"Amount exceeds outstanding balance. Remaining: ₹{remaining:.2f}")


def _build_payment_doc(student, course, body, recorded_by_id: str, recorded_by_name: str, extras: Optional[dict] = None, is_test: bool = False) -> dict:
    """Build a `db.payments` insert doc from a request body + student/course context."""
    now = datetime.now(timezone.utc).isoformat()
    if isinstance(student, dict) and student.get("is_demo"):
        is_test = True
    doc = {
        "_id": str(uuid.uuid4()),
        "student_id": student["_id"],
        "student_name": student["name"],
        "course_id": course["_id"],
        "course_title": course["title"],
        "batch_id": getattr(body, "batch_id", None),
        "amount": float(body.amount),
        "currency": "INR",
        "method": getattr(body, "method", "upi"),
        "notes": (getattr(body, "notes", "") or "").strip(),
        "recorded_by": recorded_by_id,
        "recorded_by_name": recorded_by_name,
        "status": "paid",
        "is_test_txn": is_test,
        "created_at": now,
        "paid_at": now,
    }
    if extras:
        doc.update(extras)
    return doc


async def _maybe_enroll_and_notify(student, course, payment_id: str, batch_id: Optional[str],
                                   fee: float, total_paid_after: float, grant_reason: str) -> bool:
    """Create enrolment if student is not already enrolled. Send notifications. Returns True if newly enrolled."""
    existing = await db.enrollments.find_one({"course_id": course["_id"], "student_id": student["_id"]})
    if existing:
        return False
    now = datetime.now(timezone.utc).isoformat()
    await db.enrollments.insert_one({
        "_id": str(uuid.uuid4()),
        "course_id": course["_id"],
        "student_id": student["_id"],
        "batch_id": batch_id,
        "completed_lessons": [],
        "payment_id": payment_id,
        "granted_by_admin": grant_reason != "razorpay",
        "grant_reason": grant_reason,
        "enrolled_at": now,
    })
    subject = f"Enrolled in {course['title']}"
    body_html = f"Hi {student['name']},<br/>You have been enrolled in <b>{course['title']}</b>."
    if grant_reason == "fully_paid":
        body_html += f"<br/><br/>Your full payment of ₹{fee:.0f} has been received — access is now unlocked."
    elif grant_reason == "razorpay":
        outstanding = max(fee - total_paid_after, 0)
        body_html += f"<br/><br/>Online payment received.<br/>Outstanding: ₹{outstanding:.0f}"
    else:
        body_html += "<br/>Payment recorded and access granted."
    await notify(
        [student["_id"]], "Enrolled", f"Enrolled in {course['title']}.",
        f"/app/courses/{course['_id']}",
        email_subject=subject, email_html=email_template(subject, body_html),
        cc_admin=True,
    )
    return True


@router.post("/admin/payments/record")
async def admin_record_payment(body: PaymentRecordBody, user: dict = Depends(require_role("admin"))):
    """Admin records an offline/UPI payment. Auto-enrols on full payment; can also grant on partial at admin discretion."""
    course, student = await _fetch_course_and_student(body.course_id, body.student_id)
    fee = float(course.get("price", 0) or 0)
    prior_paid = await _total_paid(body.student_id, body.course_id)
    _assert_amount_within_outstanding(body.amount, fee, prior_paid)
    doc = _build_payment_doc(student, course, body, user["id"], user["name"])
    await db.payments.insert_one(doc)
    total_paid_after = prior_paid + float(body.amount)
    fully_paid = fee > 0 and total_paid_after >= fee
    should_enroll = body.grant_access or fully_paid
    auto_granted = False
    if should_enroll:
        reason = "fully_paid" if (fully_paid and not body.grant_access) else "admin_grant"
        auto_granted = await _maybe_enroll_and_notify(
            student, course, doc["_id"], body.batch_id, fee, total_paid_after, reason,
        )
    doc["id"] = doc.pop("_id")
    doc["auto_granted"] = bool(auto_granted and not body.grant_access)
    return doc


class PaymentEditBody(BaseModel):
    amount: float = Field(..., ge=0)
    notes: Optional[str] = None
    method: Optional[str] = None


@router.put("/admin/payments/{payment_id}")
async def admin_edit_payment(payment_id: str, body: PaymentEditBody, user: dict = Depends(require_role("admin"))):
    payment = await db.payments.find_one({"_id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    course = await db.courses.find_one({"_id": payment["course_id"]})
    fee = float((course or {}).get("price", 0) or 0)
    other_paid = await _total_paid(payment["student_id"], payment["course_id"], exclude_id=payment_id)
    _assert_amount_within_outstanding(body.amount, fee, other_paid)
    update = {"amount": float(body.amount)}
    if body.notes is not None:
        update["notes"] = body.notes.strip()
    if body.method is not None:
        update["method"] = body.method
    await db.payments.update_one({"_id": payment_id}, {"$set": update})
    # Auto-enroll if this edit pushes total paid to full fee (and student wasn't enrolled)
    new_total = other_paid + float(body.amount)
    auto_granted = False
    if fee > 0 and new_total >= fee:
        student = await db.users.find_one({"_id": payment["student_id"]})
        if student:
            auto_granted = await _maybe_enroll_and_notify(
                student, course, payment_id, payment.get("batch_id"),
                fee, new_total, "fully_paid",
            )
    return {"message": "Payment updated", "auto_granted": auto_granted}


@router.delete("/admin/payments/{payment_id}")
async def admin_delete_payment(payment_id: str, user: dict = Depends(require_role("admin"))):
    """Removes a (usually erroneous) payment record. Does NOT un-enroll the
    student even if this was the payment that unlocked access — enrollment
    and payment records are intentionally not linked for deletion."""
    payment = await db.payments.find_one({"_id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    await db.payments.delete_one({"_id": payment_id})
    return {"message": "Payment removed"}


class ManualEnrolBody(BaseModel):
    student_id: str
    course_id: str
    batch_id: Optional[str] = None


@router.post("/admin/enrollments/grant")
async def admin_grant_enrollment(body: ManualEnrolBody, user: dict = Depends(require_role("admin"))):
    """Grant course access without any payment record (useful for scholarships / demos)."""
    course = await db.courses.find_one({"_id": body.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    student = await db.users.find_one({"_id": body.student_id, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    existing = await db.enrollments.find_one({"course_id": body.course_id, "student_id": body.student_id})
    if existing:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this course")
    await db.enrollments.insert_one({
        "_id": str(uuid.uuid4()),
        "course_id": body.course_id,
        "student_id": body.student_id,
        "batch_id": body.batch_id,
        "completed_lessons": [],
        "granted_by_admin": True,
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
    })
    await notify(
        [body.student_id],
        "Enrolled by admin",
        f"You have been enrolled in {course['title']}.",
        f"/app/courses/{body.course_id}",
    )
    return {"message": "Enrolment granted"}


async def _total_paid(student_id: str, course_id: str, exclude_id: Optional[str] = None) -> float:
    q = {"student_id": student_id, "course_id": course_id, "status": "paid"}
    if exclude_id:
        q["_id"] = {"$ne": exclude_id}
    docs = await db.payments.find(q).to_list(500)
    return sum(float(d.get("amount", 0)) for d in docs)


@router.get("/admin/students/{student_id}/course-payments/{course_id}")
async def admin_course_payments(student_id: str, course_id: str, user: dict = Depends(require_role("admin"))):
    """Full payment ledger for one student+course pair: every payment,
    fee/paid/outstanding totals, and whether they're actually enrolled —
    the admin-facing "how much has this student paid" screen."""
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    payments = await db.payments.find({"student_id": student_id, "course_id": course_id, "status": "paid"}).sort("created_at", -1).to_list(500)
    for p in payments:
        p["id"] = p.pop("_id")
    total = sum(float(p.get("amount", 0)) for p in payments)
    fee = float(course.get("price", 0) or 0)
    outstanding = max(fee - total, 0)
    enrolled = await db.enrollments.find_one({"student_id": student_id, "course_id": course_id})
    return {
        "student_id": student_id,
        "course_id": course_id,
        "course_title": course["title"],
        "fee": fee,
        "paid": total,
        "outstanding": outstanding,
        "enrolled": enrolled is not None,
        "payments": payments,
    }


@router.get("/student/payments")
async def my_payments(user: dict = Depends(require_role("student"))):
    docs = await db.payments.find({"student_id": user["id"]}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs


@router.get("/student/courses/{course_id}/dues")
async def my_course_dues(course_id: str, user: dict = Depends(require_role("student"))):
    """How much the current student still owes for one course — powers the
    "pay remaining balance" UI."""
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    paid = await _total_paid(user["id"], course_id)
    fee = float(course.get("price", 0) or 0)
    return {"fee": fee, "paid": paid, "outstanding": max(fee - paid, 0)}
