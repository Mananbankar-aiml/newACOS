import asyncio
import logging

import resend

from core.config import settings
from core.db import db, new_id, utcnow_iso

logger = logging.getLogger(__name__)

if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY


def otp_email(title: str, body: str, code: str, expires: str) -> str:
    return f"""
    <div style='font-family:Arial,sans-serif;background:#09090b;color:#fafafa;padding:32px'>
      <h2 style='font-size:22px;margin:0 0 12px'>{title}</h2>
      <p style='color:#a1a1aa'>{body}</p>
      <div style='background:#18181b;border:1px solid #27272a;padding:24px;border-radius:8px;text-align:center;letter-spacing:8px;font-size:32px;font-weight:800;margin:16px 0'>{code}</div>
      <p style='color:#71717a;font-size:12px'>Expires in {expires}.</p>
    </div>"""


async def send_email(to: str, subject: str, html: str, purpose: str = "notification") -> str:
    msg_id = new_id()
    doc = {"id": msg_id, "to": to, "subject": subject, "html": html, "purpose": purpose,
           "sent_at": utcnow_iso(), "provider": "resend" if settings.RESEND_API_KEY else "console", "status": "queued"}
    if settings.RESEND_API_KEY:
        try:
            params = {"from": settings.SENDER_EMAIL, "to": [to], "subject": subject, "html": html}
            result = await asyncio.to_thread(resend.Emails.send, params)
            doc["status"] = "sent"
            doc["provider_id"] = result.get("id") if isinstance(result, dict) else None
        except Exception as exc:
            logger.exception("Resend failed")
            doc["status"] = "failed"
            doc["error"] = str(exc)
    else:
        logger.info("[EMAIL/console] to=%s subject=%r purpose=%s", to, subject, purpose)
        doc["status"] = "console"
    await db.emails.insert_one(doc)
    return msg_id
