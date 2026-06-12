"""FamilyMember — one wiki page per person in the family tree.

DESIGN NOTE: this is a different table from User on purpose (see the note
in user.py). A great-grandmother born in 1903 gets a rich wiki page here;
she will never have a login. The ~8 Users are people; not all people are
Users. One table per real-world concept (D426).

This model started life on "Day 3" as just (name, location). The wiki
feature grew it — go read the migration in migrations/versions/ to see
exactly how a live table gains columns without losing data. That's the
whole point of migrations.

PII WARNING: birth dates and family history are exactly the PII CLAUDE.md
protects. Every route that shows this data is @login_required.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import LockableMixin


class FamilyMember(LockableMixin, db.Model):
    __tablename__ = "family_member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))

    # The wiki page body. server_default="" tells the DATABASE the default
    # too — needed so the migration can add this NOT NULL column to a table
    # that already has rows (existing rows get "" instead of an error).
    bio = db.Column(db.Text, nullable=False, default="", server_default="")

    # Real Date columns, not strings: they sort correctly, validate
    # themselves, and map straight to MySQL DATE / Java LocalDate in v2.
    # Nullable because family history is full of unknowns.
    birth_date = db.Column(db.Date, nullable=True)
    death_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # Wikipedia-style accountability: who touched this page last, and when.
    # Nullable FKs — pages created before this feature have no recorded author.
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Two FKs to the same table need explicit foreign_keys= so SQLAlchemy
    # knows which column each relationship follows.
    creator = db.relationship("User", foreign_keys=[created_by])
    last_editor = db.relationship("User", foreign_keys=[updated_by])

    # Page history, newest first (see wiki_revision.py for the WHY).
    # delete-orphan: removing a person removes their page history with them.
    revisions = db.relationship(
        "WikiRevision",
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="desc(WikiRevision.id)",
    )

    @property
    def lifespan(self):
        """'1947 – 2020', '1947 – ', or '' — for the page header."""
        if not self.birth_date and not self.death_date:
            return ""
        born = str(self.birth_date.year) if self.birth_date else "?"
        if self.death_date:
            return f"{born} – {self.death_date.year}"
        return f"born {born}"

    def __repr__(self):
        return f"<FamilyMember {self.name}>"
