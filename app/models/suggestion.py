"""Suggestion — the "suggest an idea" → admin inbox (Master Plan §5, §3.5).

Any member can drop an idea, bug report, or "please add this photo" request; it
lands in an admin inbox with a status lifecycle and an optional priority so the
admin can triage a queue instead of a pile. This is application data, not
genealogy — so no GEDCOM xref, no soft-delete/polymorphic machinery; a declined
suggestion just gets the ``declined`` status.

v2 mapping: a ``Suggestion`` @Entity + a ``SuggestionService``.
"""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


# Closed vocabularies, enforced in the service layer (portable VARCHARs, not DB
# enums — the §3 "standard SQL only" rule).
TOPICS = ("idea", "bug", "photo_request", "other")
STATUSES = ("new", "in_progress", "done", "declined")


class Suggestion(db.Model):
    __tablename__ = "suggestions"

    id = db.Column(db.Integer, primary_key=True)

    # SET NULL: a suggestion outlives the account that wrote it (the idea still
    # matters even if the member's login is later removed).
    author_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    topic = db.Column(db.String(20), nullable=False, default="idea")
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False,
                       default="new", server_default="new")

    # Nullable integer RANK the admin sets when accepting an item into the queue
    # (lower = higher priority). NULL = untriaged. An integer sorts cleanly for
    # the "prioritized queue" read; the UI can label it high/medium/low.
    priority = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow,
                           onupdate=_utcnow)

    author = db.relationship("User", foreign_keys=[author_user_id])

    def __repr__(self):
        return f"<Suggestion #{self.id} {self.topic} ({self.status})>"
