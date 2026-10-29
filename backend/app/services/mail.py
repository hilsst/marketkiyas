"""E-posta gönderimi (şifre sıfırlama kodu). SMTP ayarı yoksa geliştirme için sunucu günlüğüne yazar."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger(__name__)


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def send_mail(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        log.warning("SMTP ayarlı değil, e-posta gönderilmedi. Alıcı: %s | %s\n%s", to, subject, body)
        return
    await asyncio.to_thread(_send_sync, to, subject, body)
