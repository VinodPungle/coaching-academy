# Multi-channel notification helper: writes an in-app notification, and
# (best-effort, fire-and-forget) sends an email via Resend and/or a
# WhatsApp message via Twilio. Every "notify this user" call in the app
# routes through `notify()` at the bottom of this file.
import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
import resend
from twilio.rest import Client as TwilioClient
from database import db

logger = logging.getLogger(__name__)

ACADEMY_NAME = os.environ.get("ACADEMY_NAME", "Academy for Life Science Exams Preparation")


async def send_email(to: str, subject: str, html: str):
    """Send one email via Resend. If RESEND_API_KEY isn't set, logs instead
    of sending — this is the "demo mode" used in local dev / preview envs
    so nothing breaks without real email credentials."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.info(f"[EMAIL demo mode] to={to} subject={subject}")
        return None
    resend.api_key = api_key
    params = {
        "from": f"{ACADEMY_NAME} <{os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    reply_to = os.environ.get("REPLY_TO_EMAIL", "").strip()
    if reply_to:
        params["reply_to"] = [reply_to]
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to}: {result.get('id') if isinstance(result, dict) else result}")
        return result
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return None


def email_template(title: str, body: str, cta_label: str = "", cta_url: str = "") -> str:
    """Wrap a title/body (and optional call-to-action button) in a shared
    inline-styled HTML email layout so every notification email looks the
    same. `body` is inserted as raw HTML — callers are responsible for
    escaping any untrusted content before passing it in."""
    button = (
        f'<tr><td style="padding-top:20px"><a href="{cta_url}" style="display:inline-block;background:#1d4ed8;color:#ffffff;padding:12px 24px;font-weight:bold;text-decoration:none;font-family:Arial,sans-serif;font-size:14px">{cta_label}</a></td></tr>'
        if cta_url else ""
    )
    return f"""<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:32px 0">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e4e4e7">
<tr><td style="background:#09090b;padding:20px 32px"><span style="color:#ffffff;font-family:Arial,sans-serif;font-weight:bold;font-size:18px">{ACADEMY_NAME}</span></td></tr>
<tr><td style="padding:32px">
<table cellpadding="0" cellspacing="0" width="100%">
<tr><td style="font-family:Arial,sans-serif;font-size:20px;font-weight:bold;color:#09090b">{title}</td></tr>
<tr><td style="padding-top:12px;font-family:Arial,sans-serif;font-size:14px;line-height:22px;color:#52525b">{body}</td></tr>
{button}
</table>
</td></tr>
<tr><td style="padding:16px 32px;border-top:1px solid #e4e4e7;font-family:Arial,sans-serif;font-size:11px;color:#a1a1aa">{ACADEMY_NAME} · Entrance Exam Coaching · This is an automated message.</td></tr>
</table>
</td></tr>
</table>"""


def whatsapp_configured() -> bool:
    return all(os.environ.get(k, "").strip() for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"))


async def send_whatsapp(phone: str, text: str):
    """Send one WhatsApp message via Twilio. Requires an E.164 phone number
    (leading '+'); silently no-ops for missing/malformed numbers or when
    Twilio isn't configured (demo mode, same pattern as send_email)."""
    if not phone or not phone.strip().startswith("+"):
        return None
    if not whatsapp_configured():
        logger.info(f"[WHATSAPP demo mode] to={phone} text={text[:60]}")
        return None

    def _send():
        client = TwilioClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        return client.messages.create(
            from_=os.environ["TWILIO_WHATSAPP_FROM"],
            to=f"whatsapp:{phone.strip()}",
            body=text,
        )

    try:
        result = await asyncio.to_thread(_send)
        logger.info(f"WhatsApp sent to {phone}: {result.sid}")
        return result
    except Exception as e:
        logger.error(f"WhatsApp send failed to {phone}: {e}")
        return None


async def notify(user_ids: list, title: str, body: str, link: str = "",
                 email_subject: str = None, email_html: str = None,
                 cc_admin: bool = False):
    """Main entry point routers call to notify one or more users.
    Always writes an in-app `notifications` doc per user (shown in the bell
    icon / NotificationsBell.jsx). Email is only sent if `email_subject` is
    passed; WhatsApp is sent to any recipient with a phone number on file.
    Both external sends are fired via `asyncio.create_task` — the caller
    (an API request) does not wait for them, so a slow/failed email/WhatsApp
    send never delays or breaks the HTTP response."""
    user_ids = list(set(user_ids))  # de-dupe in case the same user appears twice
    if not user_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = [
        {"_id": str(uuid.uuid4()), "user_id": uid, "title": title, "body": body,
         "link": link, "read": False, "created_at": now}
        for uid in user_ids
    ]
    await db.notifications.insert_many(docs)
    users = await db.users.find({"_id": {"$in": user_ids}}).to_list(2000)
    wa_text = f"*{ACADEMY_NAME}*\n\n*{title}*\n{body}"
    for u in users:
        if email_subject:
            asyncio.create_task(send_email(u["email"], email_subject, email_html or email_template(title, body)))
        if u.get("phone"):
            asyncio.create_task(send_whatsapp(u["phone"], wa_text))
    # Admin BCC on important events (new enrolment / payment received)
    if cc_admin and email_subject:
        admin_email = os.environ.get("ADMIN_NOTIFY_EMAIL", "").strip()
        if admin_email:
            asyncio.create_task(send_email(admin_email, f"[Admin] {email_subject}", email_html or email_template(title, body)))
