"""write_control — the one place genealogy MUTATIONS are audited and reversed.

WHY (ADR-0001, Master Plan v2.0.0 §9 Tier-1): FamilyHub uses *post-moderation*
write control. Anyone with the ``contribute`` permission may edit directly, but
every mutating operation is (a) captured in the ``audit_log`` with a full
before/after snapshot, (b) recoverable — "delete" is a SOFT delete, never a hard
one — and (c) reversible, so a Curator can undo any change with one click. That
trio (provenance + recoverability + revert) is this module's whole job.

HOW IT STAYS DRY: instead of a hand-written serializer per table, we snapshot a
row by INTROSPECTING its columns (the same trick export_service uses). So one
``snapshot`` + one generic ``_apply`` power audit, restore, and revert for every
soft-deletable entity — and adding a table later is a one-line entry in
``SUBJECT_MODELS``.

THE ACTOR: mutations happen inside a request, so we read ``current_user`` from
Flask-Login here rather than threading an ``actor`` argument through every service
signature. Outside a request (seed, CLI) there simply is no actor, and the audit
row records ``NULL`` — exactly like the existing backup/restore logging.

v2 mapping: a ``WriteControlService`` / Spring AOP ``@Around`` advice on the
service layer, backed by Hibernate Envers for the before/after history.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.extensions import db
from app.models import (
    Citation, Event, Family, Individual, MediaObject, Name, Note, Source,
)
from app.services import audit_service
from app.services.api_errors import ApiError

# subject_type string → model, for the id-keyed, soft-deletable entities a
# Curator can restore/revert. (Composite-key link rows — family_children,
# media_links, note_links — are soft-deleted with their parent, not reverted
# independently, so they're not listed here.)
SUBJECT_MODELS = {
    "individual": Individual,
    "name": Name,
    "family": Family,
    "event": Event,
    "source": Source,
    "citation": Citation,
    "media": MediaObject,
    "note": Note,
}

# Columns we never overwrite when reverting/restoring: identity and the auto
# timestamps the ORM maintains. Everything else (including deleted_at) is fair
# game, which is what makes reverting a delete = "put deleted_at back to NULL."
_PROTECTED_COLUMNS = {"id", "created_at", "updated_at"}


def _jsonable(value):
    """Coerce a column value into something json.dumps can hold (datetimes →
    ISO strings, Decimal → float). Mirrors export_service so a snapshot reads the
    same everywhere."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def snapshot(obj):
    """A plain dict of every column on ``obj`` — the before/after image stored in
    the audit trail and replayed on revert."""
    return {c.name: _jsonable(getattr(obj, c.name)) for c in obj.__table__.columns}


def _actor():
    """The logged-in user driving this mutation, or None (CLI/seed/tests without
    a request). Imported lazily so this module doesn't require a request context
    just to be imported."""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user
    except Exception:
        pass
    return None


# --- Audit hooks the CRUD services call (they add to the session; the service
#     commits, so the change and its audit row land in ONE transaction) ---------

def log_create(subject_type, obj, detail=""):
    """Record a create (before=NULL, after=the new row)."""
    audit_service.record_change(_actor(), "create", subject_type, obj.id,
                                before=None, after=snapshot(obj), detail=detail)


def log_update(subject_type, obj, before, detail=""):
    """Record an update. ``before`` is a snapshot taken BEFORE the mutation."""
    audit_service.record_change(_actor(), "update", subject_type, obj.id,
                                before=before, after=snapshot(obj), detail=detail)


def log_action(action, subject_type, subject_id=None, detail=""):
    """Record a mutation that isn't a full-row snapshot — e.g. adding/removing a
    parent/child link. Keeps the audit trail complete for relationship edits
    without pretending a composite-key link row is independently revertible."""
    audit_service.log_event(_actor(), action, subject_type, subject_id, detail)


# --- Soft delete / restore / revert (the recoverability guarantees) -----------

def soft_delete(subject_type, obj, detail=""):
    """Soft-delete a row: stamp ``deleted_at`` (reads filter it out) and audit it
    with the full prior state, so it's fully recoverable. Commits."""
    before = snapshot(obj)
    obj.deleted_at = datetime.now(timezone.utc)
    audit_service.record_change(_actor(), "delete", subject_type, obj.id,
                                before=before, after=None, detail=detail)
    db.session.commit()


def _get_any(subject_type, subject_id):
    """Fetch a row by id REGARDLESS of soft-delete state (restore/revert need to
    see deleted rows, unlike the normal read paths). Validates subject_type."""
    model = SUBJECT_MODELS.get(subject_type)
    if model is None:
        raise ApiError(
            f"subject_type must be one of: {', '.join(sorted(SUBJECT_MODELS))}.",
            400, fields={"subject_type": "invalid"})
    obj = db.session.get(model, subject_id)
    if obj is None:
        raise ApiError(f"No {subject_type} found with id {subject_id}.", 404)
    return obj


def _apply(obj, data):
    """Write a snapshot dict back onto a row, skipping identity/auto columns.
    This is what makes revert generic: replaying ``before_json`` restores every
    field, ``deleted_at`` included (so reverting a delete un-deletes the row)."""
    columns = {c.name for c in obj.__table__.columns}
    for key, value in data.items():
        if key in _PROTECTED_COLUMNS or key not in columns:
            continue
        if key == "deleted_at" and value is not None:
            value = _parse_dt(value)
        setattr(obj, key, value)


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def restore(subject_type, subject_id):
    """Un-delete a soft-deleted row (the "undelete from trash" action). Curator+.
    Returns the restored row's snapshot; audits the restore."""
    obj = _get_any(subject_type, subject_id)
    if not obj.is_deleted:
        raise ApiError(f"That {subject_type} is not deleted.", 400)
    obj.deleted_at = None
    after = snapshot(obj)
    audit_service.record_change(_actor(), "restore", subject_type, obj.id,
                                before=None, after=after)
    db.session.commit()
    return after


def revert(audit_id):
    """Undo the change described by one audit entry (ADR-0001). Curator+.

    The logic is delightfully uniform because ``before_json`` is a full row image:
      * update / delete / restore  → replay ``before_json`` (restores prior state,
        deleted_at and all).
      * create (no before)         → soft-delete the row (undo the creation).
    A fresh ``revert`` audit row records the reversal itself. Returns the new
    snapshot (or None if the row is now soft-deleted)."""
    from app.models import AuditLog
    import json

    entry = db.session.get(AuditLog, audit_id)
    if entry is None:
        raise ApiError(f"No audit entry found with id {audit_id}.", 404)
    if entry.subject_type not in SUBJECT_MODELS:
        raise ApiError("That change isn't revertible.", 400,
                       fields={"subject_type": "not revertible"})

    obj = _get_any(entry.subject_type, entry.subject_id)
    current = snapshot(obj)
    before = json.loads(entry.before_json) if entry.before_json else None

    if before is not None:
        _apply(obj, before)
        after = snapshot(obj)
    else:
        # The audited action created the row → reverting means removing it.
        obj.deleted_at = datetime.now(timezone.utc)
        after = None

    audit_service.record_change(
        _actor(), "revert", entry.subject_type, entry.subject_id,
        before=current, after=after,
        detail=f"revert of audit #{audit_id} ({entry.action})")
    db.session.commit()
    return after


# --- The activity feed (paginated, filtered audit log) ------------------------

def _iso(dt):
    return dt.isoformat() if dt is not None else None


def serialize_entry(entry):
    """One audit row as JSON — the activity-feed contract shape."""
    return {
        "id": entry.id,
        "action": entry.action,
        "actor_id": entry.user_id,
        "actor": entry.user.display_name if entry.user else None,
        "subject_type": entry.subject_type,
        "subject_id": entry.subject_id,
        "detail": entry.detail,
        "created_at": _iso(entry.created_at),
    }


def list_activity(action=None, actor_id=None, subject_type=None,
                  date_from=None, date_to=None, page=1, per_page=50):
    """Newest-first, paginated audit feed with optional filters (Master Plan §9;
    powers the admin Activity tab). Returns a dict with the rows + page metadata."""
    from app.models import AuditLog

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if actor_id is not None:
        query = query.filter(AuditLog.user_id == actor_id)
    if subject_type:
        query = query.filter(AuditLog.subject_type == subject_type)
    if date_from is not None:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to is not None:
        query = query.filter(AuditLog.created_at <= date_to)

    query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    per_page = max(1, min(int(per_page), 200))  # clamp so a client can't ask for all
    page = max(1, int(page))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "activity": [serialize_entry(e) for e in pagination.items],
        "page": pagination.page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }


# --- Member-safe "recent activity" feed for Home (BLOCKERS.md, 2026-07-03) -----
#
# The full audit trail above is Curator+ ONLY by design (ADR-0001) — it carries
# deletes, reverts, and account/security actions that a Viewer or Contributor
# shouldn't see. But Home wants a friendly "Jane added a photo" feed for EVERY
# logged-in member. Rather than loosen the Curator-only trail, this is a
# DIFFERENT, narrower view over the SAME table (one database, many views): only
# ``create`` events, only on new-content subject types, rendered as a plain
# sentence. Deletes/updates/reverts/user/backup actions never appear here.

MEMBER_SAFE_SUBJECTS = ("individual", "media", "note")

# Friendly noun per subject type, for the sentence below.
_FRIENDLY_NOUN = {
    "individual": "a new person",
    "media": "a photo",
    "note": "a story",
}


def _member_friendly_entry(entry):
    """One safe feed row, or None if the subject has since been (soft-)deleted —
    a friendly feed shouldn't point at content that's no longer there."""
    model = SUBJECT_MODELS.get(entry.subject_type)
    obj = db.session.get(model, entry.subject_id) if model else None
    if obj is None or getattr(obj, "is_deleted", False):
        return None

    actor = entry.user.display_name if entry.user else "Someone"
    if entry.subject_type == "individual":
        name = obj.primary_name.display if obj.primary_name else None
        what = f"a new person: {name}" if name else _FRIENDLY_NOUN["individual"]
    elif entry.subject_type == "media":
        what = f"a photo: {obj.title}" if obj.title else _FRIENDLY_NOUN["media"]
    else:  # note
        what = f"a story: {obj.title}" if obj.title else _FRIENDLY_NOUN["note"]

    verb = "added" if entry.subject_type != "note" else "wrote"
    return {
        "id": entry.id,
        "text": f"{actor} {verb} {what}",
        "subject_type": entry.subject_type,
        "subject_id": entry.subject_id,
        "created_at": _iso(entry.created_at),
    }


def member_feed(limit=20):
    """Friendly, ALL-MEMBERS recent-activity feed for Home. Only ``create``
    events on new genealogy content (people/photos/stories) — never deletes,
    reverts, edits, or account/security actions. Over-fetches a little so
    since-deleted subjects (silently skipped) don't shrink the visible feed."""
    from app.models import AuditLog

    limit = max(1, min(int(limit), 100))
    entries = (AuditLog.query
               .filter(AuditLog.action == "create",
                       AuditLog.subject_type.in_(MEMBER_SAFE_SUBJECTS))
               .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
               .limit(limit * 2)
               .all())

    feed = []
    for entry in entries:
        row = _member_friendly_entry(entry)
        if row is not None:
            feed.append(row)
        if len(feed) >= limit:
            break
    return feed
