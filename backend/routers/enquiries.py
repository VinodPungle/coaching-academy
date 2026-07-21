# Public "Contact Us" lead-capture form on the landing page — no auth
# required, so this file leans on spam/abuse defenses instead: a honeypot
# field, per-IP rate limiting, and input validation. Submissions are
# stored (db.enquiries) and emailed to the admin inbox.
import os
import re
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator

from database import db
from notify import send_email, email_template, ACADEMY_NAME

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enquiries", tags=["enquiries"])

# Simple in-memory IP rate limiter: max 3 enquiries per IP per hour.
# In-memory (not persisted) is fine here — worst case a restart resets
# everyone's quota, which is an acceptable trade-off for a low-stakes form.
_ip_hits: dict = defaultdict(deque)
_RATE_LIMIT = 3
_WINDOW_SECONDS = 3600


class EnquiryBody(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=20)
    message: str = Field(min_length=10, max_length=2000)
    # Honeypot field: bots fill this; real users don't see it
    website: str = ""

    @field_validator("name", "message")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[+\d][\d\s\-()]{5,19}$", v):
            raise ValueError("Invalid phone number")
        return v


def _rate_limit_ok(ip: str) -> bool:
    """Sliding-window check: drop hit timestamps older than the window,
    then allow the request only if under the per-IP cap."""
    now = time.time()
    q = _ip_hits[ip]
    while q and q[0] < now - _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        return False
    q.append(now)
    return True


@router.post("")
async def submit_enquiry(body: EnquiryBody, request: Request):
    """Stores the enquiry and fire-and-forgets a notification email to the
    admin. Bots that fill the hidden `website` field get a fake success
    response instead of an error, so they don't learn the honeypot exists."""
    # Honeypot check
    if body.website.strip():
        logger.info(f"Enquiry rejected (honeypot triggered) from {request.client.host if request.client else 'unknown'}")
        # Return success to bots (don't reveal the trap)
        return {"success": True, "message": "Thank you. We'll get back to you shortly."}

    ip = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(ip):
        raise HTTPException(status_code=429, detail="Too many enquiries. Please try again later.")

    doc = {
        "_id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "message": body.message,
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "new",
    }
    await db.enquiries.insert_one(doc)

    # Fire-and-forget email to admin
    admin_email = os.environ.get("ADMIN_NOTIFY_EMAIL", "").strip() or "contact@bioexamprep.com"
    subject = f"New Enquiry from {body.name}"
    esc = lambda s: (s or "").replace("<", "&lt;").replace(">", "&gt;")
    body_html = (
        f"<p><strong>Name:</strong> {esc(body.name)}</p>"
        f"<p><strong>Email:</strong> {esc(body.email)}</p>"
        f"<p><strong>Phone:</strong> {esc(body.phone)}</p>"
        f"<p><strong>Message:</strong></p>"
        f"<p style=\"white-space:pre-wrap\">{esc(body.message)}</p>"
        f"<hr /><p style=\"color:#71717a;font-size:12px\">Received at {doc['created_at']} · IP: {esc(ip)}</p>"
    )
    html = email_template(f"New Enquiry — {ACADEMY_NAME}", body_html)
    asyncio.create_task(send_email(admin_email, subject, html))

    return {"success": True, "message": "Thank you. We'll get back to you shortly."}
