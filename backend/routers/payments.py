import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from auth_utils import require_role
from notify import notify, email_template

router = APIRouter(tags=["payments"])


class CheckoutBody(BaseModel):
    course_id: str
    batch_id: Optional[str] = None
    method: str = "stripe"


def gateway_config():
    stripe = bool(os.environ.get("STRIPE_API_KEY", "").strip())
    razorpay = bool(os.environ.get("RAZORPAY_KEY_ID", "").strip() and os.environ.get("RAZORPAY_KEY_SECRET", "").strip())
    return {"stripe_configured": stripe, "razorpay_configured": razorpay, "demo_mode": not (stripe or razorpay)}


@router.get("/payments/config")
async def payments_config():
    return gateway_config()


@router.post("/payments/checkout")
async def checkout(body: CheckoutBody, user: dict = Depends(require_role("student"))):
    if body.method not in ("stripe", "razorpay"):
        raise HTTPException(status_code=400, detail="Invalid payment method")
    course = await db.courses.find_one({"_id": body.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = await db.enrollments.find_one({"course_id": body.course_id, "student_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    if body.batch_id:
        batch = await db.batches.find_one({"_id": body.batch_id, "course_id": body.course_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.get("capacity"):
            count = await db.enrollments.count_documents({"batch_id": body.batch_id})
            if count >= batch["capacity"]:
                raise HTTPException(status_code=400, detail="This batch is full")
    config = gateway_config()
    doc = {
        "_id": str(uuid.uuid4()),
        "student_id": user["id"],
        "student_name": user["name"],
        "course_id": body.course_id,
        "course_title": course["title"],
        "batch_id": body.batch_id,
        "amount": course.get("price", 0),
        "currency": "INR",
        "method": body.method,
        "gateway": "demo" if config["demo_mode"] else body.method,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payments.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return {"payment": doc, **config}


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(payment_id: str, user: dict = Depends(require_role("student"))):
    payment = await db.payments.find_one({"_id": payment_id, "student_id": user["id"]})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment["status"] == "paid":
        raise HTTPException(status_code=400, detail="Payment already completed")
    config = gateway_config()
    if not config["demo_mode"]:
        raise HTTPException(status_code=501, detail="Gateway verification pending setup. Add Stripe/Razorpay keys and implement webhook verification.")
    now = datetime.now(timezone.utc).isoformat()
    await db.payments.update_one({"_id": payment_id}, {"$set": {"status": "paid", "paid_at": now}})
    existing = await db.enrollments.find_one({"course_id": payment["course_id"], "student_id": user["id"]})
    if not existing:
        await db.enrollments.insert_one({
            "_id": str(uuid.uuid4()),
            "course_id": payment["course_id"],
            "student_id": user["id"],
            "batch_id": payment.get("batch_id"),
            "completed_lessons": [],
            "payment_id": payment_id,
            "enrolled_at": now,
        })
    course = await db.courses.find_one({"_id": payment["course_id"]})
    await notify(
        [user["id"]],
        "Payment successful",
        f"₹{payment['amount']} paid for {payment['course_title']}. You are enrolled!",
        f"/app/courses/{payment['course_id']}",
        email_subject=f"Payment received — {payment['course_title']}",
        email_html=email_template("Payment successful", f"Hi {user['name']},<br/><br/>We received your payment of <b>₹{payment['amount']}</b> for <b>{payment['course_title']}</b>. You are now enrolled — happy learning!"),
    )
    if course:
        await notify([course["teacher_id"]], "New student enrolled", f"{user['name']} enrolled in {payment['course_title']} (paid ₹{payment['amount']}).", f"/app/courses/{payment['course_id']}")
    return {"message": "Payment successful. You are now enrolled.", "status": "paid"}


@router.get("/student/payments")
async def my_payments(user: dict = Depends(require_role("student"))):
    docs = await db.payments.find({"student_id": user["id"]}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["id"] = d.pop("_id")
    return docs
