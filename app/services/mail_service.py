"""Outbound TRANSACTIONAL email (Master Plan §9): password reset, email
verification, and an admin send-test. No marketing/notification mail — that's a
separate v2 stream (§11).

CONFIG PRECEDENCE: the admin edits SMTP host/port/user/from in site_settings (so
no redeploy to change the mail server); the **password stays in .env**
(MAIL_PASSWORD) — the existing secrets mechanism, never the database. Env values
are the fallback when a setting is blank. Sending goes through Flask-Mail as
before (so the test suite's ``mail.record_messages()`` capture keeps working).

GRACEFUL DEGRADATION unchanged: if nothing is configured, ``is_configured()`` is
False, the feature hides itself, and nothing errors.
"""

from flask import current_app
from flask_mail import Message

from app.extensions import mail
from app.services import settings_service


def _settings_smtp():
    """The stored SMTP settings, or empty strings if the table isn't there yet
    (fresh install before migrations / a test app without create_all). Never lets
    a missing settings row break mail — env config is the reliable fallback."""
    try:
        return {
            "host": settings_service.get("smtp_host"),
            "port": settings_service.get_int("smtp_port", 0),
            "user": settings_service.get("smtp_user"),
            "sender": settings_service.get("smtp_from"),
        }
    except Exception:  # noqa: BLE001 — no settings table = use env only
        return {"host": "", "port": 0, "user": "", "sender": ""}


def _resolved_config():
    """SMTP config with site_settings taking precedence over env fallbacks."""
    s = _settings_smtp()
    return {
        "host": s["host"] or current_app.config.get("MAIL_SERVER") or "",
        "port": s["port"] or current_app.config.get("MAIL_PORT", 587),
        "user": s["user"] or current_app.config.get("MAIL_USERNAME"),
        "sender": s["sender"] or current_app.config.get("MAIL_DEFAULT_SENDER"),
    }


def is_configured():
    """True if we have somewhere to send mail (a settings host OR an env host)."""
    return bool(_resolved_config()["host"])


def _apply_settings():
    """Best-effort: push admin-set SMTP config onto the live Flask-Mail state so
    settings take effect without a redeploy. Wrapped defensively — a mail send
    must never crash because of an internals mismatch; the env config remains the
    reliable fallback."""
    cfg = _resolved_config()
    state = current_app.extensions.get("mail")
    if state is None or not _settings_smtp()["host"]:
        return
    try:
        state.server = cfg["host"]
        state.port = int(cfg["port"])
        if cfg["user"]:
            state.username = cfg["user"]
        if cfg["sender"]:
            state.default_sender = cfg["sender"]
    except Exception:  # noqa: BLE001 — never let config wiring break a send
        pass


def send(subject, recipient, body):
    """The one transactional-send primitive. Plain text on purpose (reliable in
    elderly users' mail apps; fewer spam flags — see the reset note below)."""
    _apply_settings()
    mail.send(Message(subject=subject, recipients=[recipient], body=body,
                      sender=_resolved_config()["sender"]))


def send_password_reset(user, reset_url):
    """Plain-text email, deliberately. HTML mail trips spam filters more often and
    renders unpredictably in elderly users' mail apps; a short plain message with
    one link is the most reliable thing on earth."""
    send(
        "FamilyHub — reset your password", user.email,
        f"Hi {user.display_name},\n\n"
        "Someone (hopefully you!) asked to reset your FamilyHub password. "
        "Click this link to choose a new one:\n\n"
        f"{reset_url}\n\n"
        "The link works for one hour. If you didn't ask for this, you can ignore "
        "this email — your password hasn't changed.\n\n— FamilyHub",
    )


def send_email_verification(user, verify_url, email=None):
    """Ask the owner of a new/changed address to confirm it's theirs (§9)."""
    send(
        "FamilyHub — confirm your email address", email or user.email,
        f"Hi {user.display_name},\n\n"
        "Please confirm this email address for your FamilyHub account by "
        "clicking the link below:\n\n"
        f"{verify_url}\n\n"
        "The link works for 24 hours. If you weren't expecting this, you can "
        "ignore it.\n\n— FamilyHub",
    )


def send_change_notice(recipient, display_name, new_email):
    """Tell an address that the account's login email is changing — sent to BOTH
    the old and new addresses so a hijacked-mailbox change can't happen silently."""
    send(
        "FamilyHub — your login email is changing", recipient,
        f"Hi {display_name},\n\n"
        f"An administrator is changing the login email on your FamilyHub account "
        f"to {new_email}. If you expected this, no action is needed. If you did "
        f"NOT, contact your family admin right away.\n\n— FamilyHub",
    )


def send_test(recipient):
    """The admin 'send a test email' action — proves the SMTP config works."""
    send(
        "FamilyHub — test email", recipient,
        "This is a test email from FamilyHub. If you received it, your email "
        "settings are working.\n\n— FamilyHub",
    )
