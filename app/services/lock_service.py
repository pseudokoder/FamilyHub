"""Locking: the admin's "this is part of the archive now" switch.

THE RULE (Wes's Trial Period, see models/mixins.py for the full story):
unlocked content can still be deleted by whoever created it; locked
content can only be deleted by an admin. Locking is itself admin-only —
the routes check that before calling in here.

One service handles all four lockable types, because the behavior is
identical — the mixin gave them the same shape, so one function fits all.
"""

from app.extensions import db
from app.models import Album, FamilyMember, Photo, TimelineEvent
from app.services import audit_service

# The human-readable name each type gets in the audit log and flash
# messages. Also doubles as the allow-list of what CAN be locked.
TYPE_NAMES = {
    Album: "album",
    Photo: "photo",
    FamilyMember: "wiki page",
    TimelineEvent: "timeline event",
}


def type_name(item):
    return TYPE_NAMES[type(item)]


def lock(item, admin):
    """Mark content as reviewed-and-preserved. Idempotent on purpose —
    locking twice is a no-op, not an error (admins double-click)."""
    if not item.is_locked:
        item.lock(admin)
        audit_service.log_event(admin, "lock", type_name(item), item.id)
        db.session.commit()
    return item


def unlock(item, admin):
    """Reopen the trial period (e.g. admin locked the wrong thing)."""
    if item.is_locked:
        item.unlock()
        audit_service.log_event(admin, "unlock", type_name(item), item.id)
        db.session.commit()
    return item
