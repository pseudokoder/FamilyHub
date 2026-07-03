"""Audit logging: one tiny function the other services call.

USAGE PATTERN (worth noticing): log_event() adds the row to the session
but does NOT commit. The calling service commits its own work, and the
audit row rides along **in the same transaction** — so an action and its
log entry land together or not at all. A log that can disagree with the
data it describes is worse than no log (D426: atomicity).

v2 mapping: AuditService.java, called from the other @Service classes.
"""

import json

from app.extensions import db
from app.models import AuditLog


def log_event(user, action, subject_type, subject_id=None, detail=""):
    """Record who did what (the security/admin trail). `user` may be None for
    CLI actions. For genealogy edits that also need before/after snapshots, use
    ``record_change`` below."""
    db.session.add(AuditLog(
        user_id=user.id if user is not None else None,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        detail=(detail or "")[:500],
    ))


def record_change(user, action, subject_type, subject_id,
                  before=None, after=None, detail=""):
    """Write one write-control audit row (ADR-0001) with before/after snapshots.

    ``before`` / ``after`` are plain dicts (a serialized row) or None; we JSON-
    encode them to TEXT. This is what ``revert`` reads back. Like ``log_event``
    it only ADDS to the session — the calling service commits, so the change and
    its audit row land in ONE transaction (atomicity, D426). Returns the pending
    AuditLog so a caller that needs the id can flush."""
    entry = AuditLog(
        user_id=user.id if user is not None else None,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        detail=(detail or "")[:500],
        before_json=json.dumps(before) if before is not None else None,
        after_json=json.dumps(after) if after is not None else None,
    )
    db.session.add(entry)
    return entry


def recent_events(limit=100):
    """Newest first, for the admin activity page."""
    return (AuditLog.query
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit).all())
