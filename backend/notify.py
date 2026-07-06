import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
import resend
from database import db

logger = logging.getLogger(__name__)

ACADEMY_NAME = os.environ.get("ACADEMY_NAME", "Rohini's JAM Academy")


async def send_email(to: str, subject: str, html: str):
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
<tr><td style="padding:16px 32px;border-top:1px solid #e4e4e7;font-family:Arial,sans-serif;font-size:11px;color:#a1a1aa">{ACADEMY_NAME} · IIT-JAM Coaching · This is an automated message.</td></tr>
</table>
</td></tr>
</table>"""


async def notify(user_ids: list, title: str, body: str, link: str = "",
                 email_subject: str = None, email_html: str = None):
    user_ids = list(set(user_ids))
    if not user_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = [
        {"_id": str(uuid.uuid4()), "user_id": uid, "title": title, "body": body,
         "link": link, "read": False, "created_at": now}
        for uid in user_ids
    ]
    await db.notifications.insert_many(docs)
    if email_subject:
        users = await db.users.find({"_id": {"$in": user_ids}}).to_list(1000)
        for u in users:
            asyncio.create_task(send_email(u["email"], email_subject, email_html or email_template(title, body)))
