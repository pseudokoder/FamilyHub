"""Notes — life stories and memories, GEDCOM NOTE/SNOTE.

This is the parents' main activity (CLAUDE.md): writing down family memories.
In the old build that was a standalone "blog." Here it's a GEDCOM NOTE — a
narrative attached to a record — so a memory about Grandpa shows up *on
Grandpa's page*, a memory about a wedding shows up *on that event*, and the
"memory blog" view is simply all the notes, newest first. One table, many views.

GEDCOM distinguishes an inline NOTE (belongs to one record) from a SHARED note,
SNOTE (one text reused by several records, e.g. a town's history attached to
everyone born there). We capture that with the `is_shared` flag; the same
note_links table attaches either kind.

CONTENT IS MARKDOWN (Master Plan §8 decision #4): authors write in a friendly
markup, we store the raw text, and rendering to safe HTML happens in the view
layer (WP2/WP3) — never store pre-rendered HTML, or you can't re-style it later.
"""

from app.extensions import db
from app.models.individual import _utcnow


class Note(db.Model):
    """A narrative — a memory, a bio, a life story. GEDCOM NOTE/SNOTE."""

    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    # @N1@ — only SHARED notes get an xref in GEDCOM; inline notes don't.
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)

    title = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), nullable=False, default="markdown")
    is_shared = db.Column(db.Boolean, nullable=False, default=False)

    # SET NULL: a memory outlives the author's *account*. The words stay even if
    # the login is removed.
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    author = db.relationship("User")
    links = db.relationship(
        "NoteLink", back_populates="note", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Note #{self.id} {self.title!r}>"


class NoteLink(db.Model):
    """Attaches one note to one record — individual, family, or event.

    Same polymorphic, composite-key pattern as MediaLink: it's the mechanism
    that lets a single memory appear on whichever page(s) it's about.
    """

    __tablename__ = "note_links"

    note_id = db.Column(
        db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 'individual' | 'family' | 'event'
    subject_type = db.Column(db.String(20), primary_key=True, nullable=False)
    subject_id = db.Column(db.Integer, primary_key=True, nullable=False)

    note = db.relationship("Note", back_populates="links")

    __table_args__ = (
        db.Index("ix_note_links_subject", "subject_type", "subject_id"),
    )

    def __repr__(self):
        return (f"<NoteLink note={self.note_id} "
                f"{self.subject_type}#{self.subject_id}>")
