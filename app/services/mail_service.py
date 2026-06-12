"""Outbound email. One job: password-reset links.

GRACEFUL DEGRADATION: if MAIL_SERVER isn't configured in .env, the
feature simply isn't there — is_configured() gates both the route and the
login-page link, and nothing errors. A half-configured feature that
crashes is worse than an absent one.

v2 mapping: a MailService @Service wrapping Spring's JavaMailSender.
"""

from flask import current_app
from flask_mail import Message

from app.extensions import mail


def is_configured():
    return bool(current_app.config.get("MAIL_SERVER"))


def send_password_reset(user, reset_url):
    """Plain-text email, deliberately. HTML mail trips spam filters more
    often and renders unpredictably in elderly users' mail apps; a short
    plain message with one link is the most reliable thing on earth."""
    message = Message(
        subject="FamilyHub — reset your password",
        recipients=[user.email],
        body=(
            f"Hi {user.display_name},\n\n"
            "Someone (hopefully you!) asked to reset your FamilyHub "
            "password. Click this link to choose a new one:\n\n"
            f"{reset_url}\n\n"
            "The link works for one hour. If you didn't ask for this, "
            "you can ignore this email — your password hasn't changed.\n\n"
            "— FamilyHub"
        ),
    )
    mail.send(message)
