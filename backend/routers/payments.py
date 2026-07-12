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


@router.post("/payments/razorpay/create-order")
async def create_razorpay_order(body: RazorpayOrderBody, user: dict = Depends(require_role("student"))):
    course = await db.courses.find_one({"_id": body.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    fee = float(course.get("price", 0) or 0)
    if fee <= 0 or course.get("is_free"):
        raise HTTPException(status_code=400, detail="This course is free — enrol directly")
    already_paid = await _total_paid(user["id"], body.course_id)
    remaining = max(fee - already_paid, 0)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="No outstanding balance for this course")
    amount = float(body.amount) if body.amount else remaining
    if amount <= 0 or amount > remaining:
        raise HTTPException(status_code=400, detail=f"Amount must be between ₹1 and ₹{remaining:.0f}")
    client = _razorpay_client()
    receipt = f"c_{body.course_id[:8]}_{user['id'][:8]}_{int(datetime.now(timezone.utc).timestamp())}"[:40]
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
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {e}")
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
        "amount": order["amount"],   # paise
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
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_secret:
        raise HTTPException(status_code=400, detail="Razorpay not configured")
    expected = hmac.new(
        key_secret.encode(),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    order = await db.razorpay_orders.find_one({"_id": body.razorpay_order_id, "student_id": user["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "paid":
        return {"message": "Already recorded"}
    course = await db.courses.find_one({"_id": order["course_id"]})
    now = datetime.now(timezone.utc).isoformat()
    payment_id = str(uuid.uuid4())
    await db.payments.insert_one({
        "_id": payment_id,
        "student_id": user["id"],
        "student_name": user["name"],
        "course_id": order["course_id"],
        "course_title": (course or {}).get("title", ""),
        "batch_id": order.get("batch_id"),
        "amount": order["amount"],
        "currency": "INR",
        "method": "razorpay",
        "notes": f"Razorpay payment_id={body.razorpay_payment_id}",
        "razorpay_order_id": body.razorpay_order_id,
        "razorpay_payment_id": body.razorpay_payment_id,
        "recorded_by": "razorpay",
        "recorded_by_name": "Razorpay (online)",
        "status": "paid",
        "created_at": now,
        "paid_at": now,
    })
    await db.razorpay_orders.update_one({"_id": body.razorpay_order_id}, {"$set": {"status": "paid", "payment_id": payment_id, "paid_at": now}})
    # auto-enrol
    total_paid = await _total_paid(user["id"], order["course_id"])
    fee = float((course or {}).get("price", 0) or 0)
    existing = await db.enrollments.find_one({"course_id": order["course_id"], "student_id": user["id"]})
    granted = False
    if not existing:
        await db.enrollments.insert_one({
            "_id": str(uuid.uuid4()),
            "course_id": order["course_id"],
            "student_id": user["id"],
            "batch_id": order.get("batch_id"),
            "completed_lessons": [],
            "payment_id": payment_id,
            "grant_reason": "razorpay" if total_paid < fee else "fully_paid",
            "enrolled_at": now,
        })
        granted = True
    subject = f"Payment received — {(course or {}).get('title', 'course')}"
    html = email_template(subject,
        f"Hi {user['name']},<br/>We've received your online payment of ₹{order['amount']:.0f} for <b>{(course or {}).get('title','')}</b>."
        f"<br/>Razorpay payment id: <code>{body.razorpay_payment_id}</code>"
        f"<br/><br/>Outstanding: ₹{max(fee - total_paid, 0):.0f}"
    )
    await notify(
        [user["id"]], "Payment received", f"₹{order['amount']:.0f} received for {(course or {}).get('title','')}.",
        f"/app/courses/{order['course_id']}",
        email_subject=subject, email_html=html, cc_admin=True,
    )
    return {"message": "Payment verified", "payment_id": payment_id, "auto_enrolled": granted, "paid": total_paid, "outstanding": max(fee - total_paid, 0)}


class SettingsBody(BaseModel):
    portal_mode: Optional[str] = None       # "demo" | "live"
    upi_qr_url: Optional[str] = None        # image file URL uploaded via /files/upload
    upi_vpa: Optional[str] = None           # e.g. "rohini@upi"


@router.put("/admin/settings")
async def update_settings(body: SettingsBody, user: dict = Depends(require_role("admin"))):
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


@router.post("/admin/payments/record")
async def admin_record_payment(body: PaymentRecordBody, user: dict = Depends(require_role("admin"))):
    """Admin records an offline/UPI payment. Optionally grants course access even for partial amounts."""
    course = await db.courses.find_one({"_id": body.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    student = await db.users.find_one({"_id": body.student_id, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    course_fee = float(course.get("price", 0) or 0)
    # Reject over-payment (single record cannot exceed fee minus already-paid)
    prior_paid = await _total_paid(body.student_id, body.course_id)
    if course_fee > 0 and (prior_paid + body.amount) > course_fee:
        remaining = max(course_fee - prior_paid, 0)
        raise HTTPException(status_code=400, detail=f"Amount exceeds outstanding balance. Remaining: ₹{remaining:.2f}")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": str(uuid.uuid4()),
        "student_id": body.student_id,
        "student_name": student["name"],
        "course_id": body.course_id,
        "course_title": course["title"],
        "batch_id": body.batch_id,
        "amount": float(body.amount),
        "currency": "INR",
        "method": body.method,
        "notes": body.notes.strip(),
        "recorded_by": user["id"],
        "recorded_by_name": user["name"],
        "status": "paid",
        "created_at": now,
        "paid_at": now,
    }
    await db.payments.insert_one(doc)
    total_paid_after = prior_paid + float(body.amount)
    should_enroll = body.grant_access or (course_fee > 0 and total_paid_after >= course_fee)
    if should_enroll:
        existing = await db.enrollments.find_one({"course_id": body.course_id, "student_id": body.student_id})
        if not existing:
            reason = "fully_paid" if (course_fee > 0 and total_paid_after >= course_fee and not body.grant_access) else "admin_grant"
            await db.enrollments.insert_one({
                "_id": str(uuid.uuid4()),
                "course_id": body.course_id,
                "student_id": body.student_id,
                "batch_id": body.batch_id,
                "completed_lessons": [],
                "payment_id": doc["_id"],
                "granted_by_admin": True,
                "grant_reason": reason,
                "enrolled_at": now,
            })
            subject = f"Enrolled in {course['title']}"
            body_html = f"Hi {student['name']},<br/>You have been enrolled in <b>{course['title']}</b>."
            if reason == "fully_paid":
                body_html += f"<br/><br/>Your full payment of ₹{course_fee:.0f} has been received — access is now unlocked."
            else:
                body_html += f"<br/>Your payment of ₹{body.amount} has been recorded."
            await notify(
                [body.student_id], "Enrolled", body_html.replace("<b>", "").replace("</b>", "").replace("<br/>", " "),
                f"/app/courses/{body.course_id}",
                email_subject=subject, email_html=email_template(subject, body_html),
                cc_admin=True,
            )
    doc["id"] = doc.pop("_id")
    doc["auto_granted"] = bool(should_enroll and not body.grant_access)
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
    if fee > 0 and (other_paid + body.amount) > fee:
        remaining = max(fee - other_paid, 0)
        raise HTTPException(status_code=400, detail=f"Amount exceeds outstanding balance. Remaining: ₹{remaining:.2f}")
    update = {"amount": float(body.amount)}
    if body.notes is not None:
        update["notes"] = body.notes.strip()
    if body.method is not None:
        update["method"] = body.method
    await db.payments.update_one({"_id": payment_id}, {"$set": update})
    # Auto-enroll if this edit pushes total paid to full fee (and student wasn't enrolled)
    new_total = other_paid + float(body.amount)
    if fee > 0 and new_total >= fee:
        student_id = payment["student_id"]
        course_id = payment["course_id"]
        existing = await db.enrollments.find_one({"course_id": course_id, "student_id": student_id})
        if not existing:
            await db.enrollments.insert_one({
                "_id": str(uuid.uuid4()),
                "course_id": course_id,
                "student_id": student_id,
                "batch_id": payment.get("batch_id"),
                "completed_lessons": [],
                "payment_id": payment_id,
                "granted_by_admin": True,
                "grant_reason": "fully_paid",
                "enrolled_at": datetime.now(timezone.utc).isoformat(),
            })
            student = await db.users.find_one({"_id": student_id})
            await notify(
                [student_id], "Enrolled", f"Full payment received for {course['title']} — access unlocked.",
                f"/app/courses/{course_id}",
                email_subject=f"Enrolled in {course['title']}",
                email_html=email_template(
                    f"Enrolled in {course['title']}",
                    f"Hi {(student or {}).get('name','')},<br/>Your full payment of ₹{fee:.0f} has been received. Access to <b>{course['title']}</b> is now unlocked.",
                ),
                cc_admin=True,
            )
    return {"message": "Payment updated"}


@router.delete("/admin/payments/{payment_id}")
async def admin_delete_payment(payment_id: str, user: dict = Depends(require_role("admin"))):
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
    course = await db.courses.find_one({"_id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    paid = await _total_paid(user["id"], course_id)
    fee = float(course.get("price", 0) or 0)
    return {"fee": fee, "paid": paid, "outstanding": max(fee - paid, 0)}
