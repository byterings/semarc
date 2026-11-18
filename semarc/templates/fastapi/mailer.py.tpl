"""Plain-text email. MAIL_DRIVER selects smtp, log or memory (kept in `outbox` for tests).

Delivery failures are logged, not raised, so a mail outage never breaks registration or
password reset requests.
"""
import logging
import smtplib
from email.message import EmailMessage

from config.settings import settings

logger = logging.getLogger(__name__)
outbox: list[dict] = []


def send_mail(to: str, subject: str, body: str) -> None:
    try:
        if settings.mail_driver == "memory":
            outbox.append({"to": to, "subject": subject, "body": body})
        elif settings.mail_driver == "smtp":
            _smtp(to, subject, body)
        else:
            logger.warning("[mail] To: %s\nSubject: %s\n\n%s", to, subject, body)
    except Exception:
        logger.exception("Mail delivery failed")


def mail_body(intro: str, token: str, page: str, footer: str) -> str:
    lines = [intro, "", f"Token: {token}"]
    if settings.app_url:
        lines.append(f"Link: {settings.app_url.rstrip('/')}/{page}?token={token}")
    return "\n".join([*lines, "", footer]) + "\n"


def _smtp(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    client = smtplib.SMTP_SSL if settings.mail_encryption == "ssl" else smtplib.SMTP
    with client(settings.mail_host, settings.mail_port, timeout=10) as smtp:
        if settings.mail_encryption == "tls":
            smtp.starttls()
        if settings.mail_username:
            smtp.login(settings.mail_username, settings.mail_password)
        smtp.send_message(message)
