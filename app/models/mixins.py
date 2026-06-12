"""Model mixins — small reusable pieces of table, written once.

THE LOCKING MODEL (Wes's "Trial Period" rule, June 12 2026):
content that's hard to recreate — photos, albums, wiki pages, timeline
events — starts life UNLOCKED. While unlocked ("the trial period"), the
person who created it may still delete it: you can take back an upload
you regret. Once an admin has reviewed it and **locked** it, it's part of
the family archive: only an admin can delete it from then on.

Posts and comments are deliberately NOT lockable — they're personal words,
always deletable by their author (or an admin).

TEACHING NOTE (D286/D287): a MIXIN adds the same columns + behavior to
several models without repeating the code — composition instead of
copy-paste. SQLAlchemy wrinkle worth knowing: a plain column can live on
the mixin directly, but a column with a ForeignKey must be wrapped in
@declared_attr so each model gets its OWN copy of the FK (they can't
share one object). v2 equivalent: a JPA @MappedSuperclass.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import declared_attr

from app.extensions import db


class LockableMixin:
    """Adds locked_at / locked_by and the is_locked question."""

    locked_at = db.Column(db.DateTime, nullable=True)

    @declared_attr
    def locked_by(cls):
        return db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    @property
    def is_locked(self):
        """Locked = an admin reviewed this and preserved it. The timestamp
        doubles as the fact — no separate boolean column to drift out of
        sync with it."""
        return self.locked_at is not None

    def lock(self, user):
        self.locked_at = datetime.now(timezone.utc)
        self.locked_by = user.id

    def unlock(self):
        self.locked_at = None
        self.locked_by = None
