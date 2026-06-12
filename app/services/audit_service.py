"""Audit logging: one tiny function the other services call.

USAGE PATTERN (worth noticing): log_event() adds the row to the session
but does NOT commit. The calling service commits its own work, and the
audit row rides along **in the same transaction** — so an action and its
log entry land together or not at all. A log that can disagree with the
data it describes is worse than no log (D426: atomicity).

v2 mapping: AuditService.java, called from the other @Service classes.
"""

from app.extensions import db
from app.models import AuditLog


def log_event(user, action, target_type, target_id=None, detail=""):
    """Record who did what. `user` may be None for CLI actions."""
    db.session.add(AuditLog(
        user_id=user.id if user is not None else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=(detail or "")[:500],
    ))


def recent_events(limit=100):
    """Newest first, for the admin activity page."""
    return (AuditLog.query
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit).all())
