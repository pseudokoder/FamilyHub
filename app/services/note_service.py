"""note_service — Markdown memories/bios (NOTE/SNOTE) and where they attach.

A note is the "memory blog" and the "wiki text", depending on what it's linked
to (Master Plan §4). The content is stored as raw Markdown — rendering to safe
HTML is a VIEW concern (WP3), never stored pre-rendered, so it can be restyled
forever. Links are polymorphic, so one memory can appear on a person's page AND
the event it's about.
"""

from app.extensions import db
from app.models import Note, NoteLink
from app.services import genealogy_service as gs
from app.services import write_control
from app.services.api_errors import ApiError

# A note can be attached to a person, a family, or an event.
NOTE_SUBJECTS = {gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY, gs.SUBJECT_EVENT}
CONTENT_TYPES = {"markdown", "plain"}


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def serialize_link(link):
    return {
        "note_id": link.note_id,
        "subject_type": link.subject_type,
        "subject_id": link.subject_id,
        "subject_label": gs.subject_label(link.subject_type, link.subject_id),
    }


def serialize(note, with_links=True):
    links = [link for link in note.links if not link.is_deleted]
    data = {
        "id": note.id,
        "gedcom_xref": note.gedcom_xref,
        "title": note.title,
        "content": note.content,
        "content_type": note.content_type,
        "is_shared": note.is_shared,
        "author_id": note.author_id,
        "author": note.author.display_name if note.author else None,
        "created_at": _iso(note.created_at),
        "updated_at": _iso(note.updated_at),
        "links_count": len(links),
    }
    if with_links:
        data["links"] = [serialize_link(link) for link in links]
    return data


def _bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def _content_type(data):
    value = data.get("content_type")
    if value is None or value == "":
        return "markdown"
    if value not in CONTENT_TYPES:
        raise ApiError("content_type must be 'markdown' or 'plain'.", 400,
                       fields={"content_type": "invalid"})
    return value


def list_all(subject_type=None, subject_id=None):
    """All notes (newest first), or just those linked to one subject."""
    if subject_type and subject_id is not None:
        notes = (Note.query.join(NoteLink)
                 .filter(Note.deleted_at.is_(None),
                         NoteLink.deleted_at.is_(None),
                         NoteLink.subject_type == subject_type,
                         NoteLink.subject_id == subject_id)
                 .order_by(Note.updated_at.desc()).all())
    else:
        notes = (Note.query.filter(Note.deleted_at.is_(None))
                 .order_by(Note.updated_at.desc()).all())
    return [serialize(n, with_links=False) for n in notes]


def get(note_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Note, note_id, "note"))


def create(data, author=None):
    from app.routes.api import require
    require(data, "content")
    note = Note(
        title=data.get("title") or None,
        content=data["content"],
        content_type=_content_type(data),
        is_shared=_bool(data.get("is_shared")),
        author_id=author.id if author is not None else None,
        gedcom_xref=data.get("gedcom_xref") or None,
    )
    db.session.add(note)
    db.session.flush()
    # Convenience: attach to a subject inline when writing "a memory about X".
    if data.get("subject_type") or data.get("subject_id") is not None:
        st, sid = gs.require_subject(
            data.get("subject_type"), data.get("subject_id"), NOTE_SUBJECTS
        )
        db.session.add(NoteLink(note_id=note.id, subject_type=st, subject_id=sid))
    write_control.log_create("note", note)
    db.session.commit()
    return serialize(note)


def update(note_id, data):
    from app.routes.api import get_or_404
    note = get_or_404(Note, note_id, "note")
    before = write_control.snapshot(note)
    if "title" in data:
        note.title = data.get("title") or None
    if "content" in data:
        if not (data.get("content") or "").strip():
            raise ApiError("content can't be blank.", 400,
                           fields={"content": "required"})
        note.content = data["content"]
    if "content_type" in data:
        note.content_type = _content_type(data)
    if "is_shared" in data:
        note.is_shared = _bool(data.get("is_shared"), default=note.is_shared)
    write_control.log_update("note", note, before)
    db.session.commit()
    return serialize(note)


def delete(note_id):
    from app.routes.api import get_or_404
    note = get_or_404(Note, note_id, "note")
    # SOFT delete + audit (ADR-0001): its note_links stay so a restore is whole.
    write_control.soft_delete("note", note)


def add_link(note_id, data):
    from app.routes.api import get_or_404
    note = get_or_404(Note, note_id, "note")
    st, sid = gs.require_subject(
        data.get("subject_type"), data.get("subject_id"), NOTE_SUBJECTS
    )
    existing = db.session.get(NoteLink, (note.id, st, sid))
    if existing is not None and not existing.is_deleted:
        raise ApiError("This note is already attached there.", 409,
                       fields={"subject_id": "already linked"})
    if existing is not None:
        existing.deleted_at = None      # restore a previously-removed attachment
        link = existing
    else:
        link = NoteLink(note_id=note.id, subject_type=st, subject_id=sid)
        db.session.add(link)
    write_control.log_action("update", "note", note.id,
                             detail=f"attach {st} #{sid}")
    db.session.commit()
    return serialize_link(link)


def remove_link(note_id, subject_type, subject_id):
    from datetime import datetime, timezone
    link = db.session.get(NoteLink, (note_id, subject_type, subject_id))
    if link is None or link.is_deleted:
        raise ApiError("That attachment doesn't exist.", 404)
    link.deleted_at = datetime.now(timezone.utc)  # soft delete the attachment
    write_control.log_action("update", "note", note_id,
                             detail=f"detach {subject_type} #{subject_id}")
    db.session.commit()
