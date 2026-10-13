import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("uhr.mailer")


def send_mail(to: str, subject: str, body: str) -> None:
    if not to:
        return
    if not settings.smtp_host or not settings.smtp_from:
        log.warning("SMTP is not configured, email to %s skipped: %s", to, subject)
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    smtp_class = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    try:
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if not settings.smtp_ssl:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError):
        log.exception("Failed to send email to %s: %s", to, subject)
