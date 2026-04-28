import logging
import smtplib
from email.message import EmailMessage

from src.api.config import (
    AUTH_EMAIL_DELIVERY_MODE,
    AUTH_EMAIL_FROM,
    IS_PRODUCTION,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
)

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when an auth email cannot be delivered safely."""


def _ensure_email_configuration() -> None:
    if AUTH_EMAIL_DELIVERY_MODE not in {"console", "smtp"}:
        raise EmailDeliveryError("AUTH_EMAIL_DELIVERY_MODE must be either 'console' or 'smtp'.")
    if AUTH_EMAIL_DELIVERY_MODE == "console" and IS_PRODUCTION:
        raise EmailDeliveryError("Console email delivery is not allowed in production.")
    if AUTH_EMAIL_DELIVERY_MODE == "smtp":
        if not AUTH_EMAIL_FROM:
            raise EmailDeliveryError("AUTH_EMAIL_FROM must be configured for SMTP auth email delivery.")
        if not SMTP_HOST:
            raise EmailDeliveryError("SMTP_HOST must be configured for SMTP auth email delivery.")


def send_auth_code_email(email: str, subject: str, body: str) -> None:
    _ensure_email_configuration()

    if AUTH_EMAIL_DELIVERY_MODE == "console":
        logger.warning("[AUTH EMAIL][DEV ONLY] to=%s subject=%s body=%s", email, subject, body)
        return

    message = EmailMessage()
    message["From"] = AUTH_EMAIL_FROM
    message["To"] = email
    message["Subject"] = subject
    message.set_content(body)

    smtp_cls = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
    with smtp_cls(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if not SMTP_USE_SSL and SMTP_USE_TLS:
            server.starttls()
        if SMTP_USERNAME:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
