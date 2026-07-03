"""admin_service — the sensitive admin actions (Master Plan §9, §10).

These are the operations that need care: managing accounts, the secure
change-email dance, and backup/restore. Each routes through the existing audited
services (user_service, backup_service) rather than reimplementing them — the
"extend, don't duplicate" rule. The destructive ones (change-email, restore)
require **step-up re-auth**: the admin re-enters their OWN password, so a
walk-away-from-the-laptop attacker can't wield admin rights.
"""

import os
import secrets
import shutil
from datetime import datetime, timedelta, timezone

from flask import url_for

from app.models import User
from app.services import (
    audit_service, backup_service, mail_service, settings_service, user_service,
)
from app.services.api_errors import ApiError


def _step_up(admin, password):
    """Re-authenticate the acting admin before a sensitive action. Raises 403 on
    a wrong password — the last line before something irreversible."""
    if admin is None or user_service.authenticate(admin.email, password) is None:
        raise ApiError("Please re-enter your own password to continue.", 403,
                       fields={"current_password": "incorrect"})


def _get_user(user_id):
    from app.extensions import db
    obj = db.session.get(User, user_id)
    if obj is None:
        raise ApiError(f"No user found with id {user_id}.", 404)
    return obj


# --- Users list ---------------------------------------------------------------

def serialize_user(user):
    """Admin row: identity + role + verification + linked-person status."""
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "individual_id": user.individual_id,
        "linked": user.individual_id is not None,
        "locked": user.is_locked(),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def list_users():
    return [serialize_user(u) for u in user_service.get_all_users()]


# --- Admin reset password (email flow) ----------------------------------------

def send_password_reset_email(user):
    """Trigger the self-service reset flow FOR a user (admin action): email them a
    reset link rather than setting a password by hand."""
    if not mail_service.is_configured():
        raise ApiError("Email isn't set up on this server yet.", 503)
    token = user_service.generate_reset_token(user)
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    mail_service.send_password_reset(user, reset_url)
    audit_service.log_event(_actor(), "reset-email", "user", user.id,
                            f"reset link emailed to {user.email}")
    from app.extensions import db
    db.session.commit()


# --- Admin change-email (the secure dance) ------------------------------------

def change_user_email(admin, user_id, new_email, admin_password):
    """The secure change-email flow (§9):
      1. Step-up: the admin re-enters their own password.
      2. Notify BOTH the old and new addresses (no silent hijack).
      3. Apply the change (un-verifies the address).
      4. Verification link to the NEW address.
      5. FORCE a password reset — the old password is scrambled and a reset link
         is emailed, so an email change can't leave a stale credential usable.
      6. Audit it.
    Requires email to be configured (the whole flow is email-driven)."""
    if not mail_service.is_configured():
        raise ApiError("Email must be configured to change an address.", 503)
    _step_up(admin, admin_password)
    user = _get_user(user_id)
    old_email = user.email

    # 2. Notify both addresses BEFORE the change lands.
    mail_service.send_change_notice(old_email, user.display_name, new_email)
    mail_service.send_change_notice(new_email, user.display_name, new_email)

    # 3. Apply (set_email validates uniqueness + un-verifies + audits).
    user_service.set_email(user, new_email, actor=admin)

    # 4. Verification link to the new address.
    verify_token = user_service.generate_email_verify_token(user)
    verify_url = url_for("auth.verify_email", token=verify_token, _external=True)
    mail_service.send_email_verification(user, verify_url)

    # 5. Force a reset: scramble the password (so the old one is dead) + email a
    #    reset link. secrets.token_urlsafe(32) is unguessable and long enough to
    #    pass the baseline; the user MUST use the reset link to regain access.
    user_service.set_password(user, secrets.token_urlsafe(32), actor=admin)
    reset_url = url_for(
        "auth.reset_password",
        token=user_service.generate_reset_token(user), _external=True)
    mail_service.send_password_reset(user, reset_url)

    # 6. One clear audit line for the whole action.
    audit_service.log_event(admin, "admin change-email", "user", user.id,
                            f"{old_email} -> {new_email} (forced reset)")
    from app.extensions import db
    db.session.commit()
    return serialize_user(user)


# --- Backups: detail, schedule, run, guarded restore --------------------------

def backup_overview():
    """Everything the admin Backups panel shows: the list (with sizes), where
    they're stored, disk headroom, last/next run, and the schedule."""
    backups = backup_service.list_backups()
    folder = backup_service._backup_dir()
    try:
        usage = shutil.disk_usage(folder)
        disk_free, disk_total = usage.free, usage.total
    except OSError:
        disk_free = disk_total = None

    last_run = backups[0]["created"].isoformat() if backups else None
    schedule = settings_service.get("backup_schedule") or "off"
    return {
        "backups": [
            {"filename": b["filename"], "bytes": b["bytes"],
             "created_at": b["created"].isoformat()}
            for b in backups
        ],
        "storage_location": folder,
        "offsite_bucket": os.environ.get("BACKUP_S3_BUCKET", "").strip() or None,
        "disk_free_bytes": disk_free,
        "disk_total_bytes": disk_total,
        "last_run": last_run,
        "next_run": _next_run(schedule),
        "schedule": schedule,
        "schedule_hour": settings_service.get_int("backup_hour", 3),
    }


def _next_run(schedule):
    """A best-effort next-run timestamp from the schedule + hour (the real runner
    is OS cron; this is for the admin's display)."""
    if schedule not in ("daily", "weekly"):
        return None
    hour = settings_service.get_int("backup_hour", 3)
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    if schedule == "weekly":
        candidate += timedelta(days=(7 - candidate.weekday()) % 7)
    return candidate.isoformat()


def set_backup_schedule(data):
    """Update the schedule config (off|daily|weekly + hour 0-23)."""
    schedule = data.get("schedule")
    if schedule not in ("off", "daily", "weekly"):
        raise ApiError("schedule must be off, daily, or weekly.", 400,
                       fields={"schedule": "invalid"})
    settings_service.set_value("backup_schedule", schedule)
    if "hour" in data:
        try:
            hour = int(data["hour"])
        except (TypeError, ValueError):
            raise ApiError("hour must be 0-23.", 400, fields={"hour": "invalid"})
        if not 0 <= hour <= 23:
            raise ApiError("hour must be 0-23.", 400, fields={"hour": "invalid"})
        settings_service.set_value("backup_hour", str(hour))
    return backup_overview()


def run_backup_now(actor):
    """Create + verify + (if configured) ship a backup, audited. Returns the
    verification report the admin sees."""
    path = backup_service.create_backup()
    report = backup_service.verify_backup(path)
    uploaded, message = (False, None)
    if report["ok"]:
        uploaded, message = backup_service.upload_backup(path)
    audit_service.log_event(
        actor, "run backup", "backup",
        detail="verified" if report["ok"] else "FAILED verification")
    from app.extensions import db
    db.session.commit()
    return {"ok": report["ok"], "report": report,
            "uploaded": uploaded, "upload_message": message,
            "filename": os.path.basename(path)}


def restore_backup(admin, filename, admin_password, confirm):
    """GUARDED restore (§9): the scariest button in the app. Requires an explicit
    confirm flag AND step-up re-auth, only accepts a filename from our own backup
    list (no path tricks), and takes an AUTO SAFETY BACKUP first so a bad restore
    is itself recoverable."""
    if not confirm:
        raise ApiError("Restore must be explicitly confirmed.", 400,
                       fields={"confirm": "required"})
    _step_up(admin, admin_password)

    known = {b["filename"] for b in backup_service.list_backups()}
    if filename not in known:
        raise ApiError("No such backup.", 404, fields={"filename": "unknown"})

    # Safety net: snapshot the CURRENT state before overwriting it.
    safety = backup_service.create_backup()
    target = os.path.join(backup_service._backup_dir(), filename)
    report = backup_service.restore_backup(target)  # verifies before touching data

    audit_service.log_event(admin, "restore backup", "backup",
                            detail=f"restored {filename}; safety={os.path.basename(safety)}")
    from app.extensions import db
    db.session.commit()
    return {"ok": report["ok"], "restored": filename,
            "safety_backup": os.path.basename(safety)}


def _actor():
    """The current user, or None outside a request (mirrors write_control)."""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user
    except Exception:  # noqa: BLE001
        pass
    return None
