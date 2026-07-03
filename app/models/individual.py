"""Individuals and their names — the GEDCOM INDI record, split into two tables.

THE BIG PICTURE (Master Plan §1–§2): FamilyHub is, underneath every "feature,"
a GEDCOM 7 genealogy database. The single most important record type is the
**individual** — one human being in the family. The wiki person-page, the fan
chart, the timeline, the photo album: every one of them is just a *different
view* of these rows. Build this table right and the rest is queries.

WHY TWO TABLES (Individual + Name)?  Because a real person collects several
names over a lifetime: a birth name, a married name, an "also known as," an
immigrant's anglicized name. One column can't hold a list, and copying the
person's vitals onto every name would duplicate data. So we **normalize**: one
row per individual, many rows per name, joined by a foreign key. That's first
normal form in action (WGU D426 Data Management – Foundations).

v2 mapping: `Individual` becomes a Spring Boot `@Entity`; the `names`
relationship below becomes a `@OneToMany List<Name>`.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import SoftDeleteMixin


def _utcnow():
    """One clock for the whole schema. timezone-aware UTC so timestamps are
    unambiguous no matter where the server (or the family) happens to be."""
    return datetime.now(timezone.utc)


class Individual(SoftDeleteMixin, db.Model):
    """A single person in the family — GEDCOM's INDI record."""

    __tablename__ = "individuals"

    # DURABLE IDENTITY (Master Plan §3 design rule #1). This integer primary
    # key is the *real* identity of a person and never changes. GEDCOM's own
    # cross-reference ids (@I1@) are explicitly transient — they get reshuffled
    # every time a file is exported — so we keep them only in `gedcom_xref`
    # below, reserved for import/export, and NEVER use them as the key.
    id = db.Column(db.Integer, primary_key=True)

    # The GEDCOM @I1@ pointer. Nullable and unique: most individuals created in
    # the web UI won't have one until we export to a .ged file (that's WP6).
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)

    # GEDCOM SEX enum: M, F, X (intersex/other), U (unknown). One character,
    # because genealogy records biological sex as recorded historically — not
    # a free-text field. Nullable: we often simply don't know.
    sex = db.Column(db.String(1), nullable=True)

    # The privacy switch (Master Plan §5/§8): living people's PII (birth dates,
    # etc.) is hidden in public-facing views; the deceased can be shown. Defaults
    # to True — assume a new person is living and protect them until told
    # otherwise. Safer default = better privacy.
    living = db.Column(db.Boolean, nullable=False, default=True)

    # GEDCOM RESN (restriction notice): 'confidential', 'locked', 'privacy'.
    # A finer-grained override than `living` for sensitive records.
    restriction = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    # onupdate fires automatically whenever SQLAlchemy flushes a change to this
    # row, so "last touched" is always honest without the routes remembering to
    # set it.
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # RELATIONSHIP — the Python-side convenience that lets us write
    # `individual.names` and get a list of Name objects.
    #   cascade="all, delete-orphan": delete an individual and SQLAlchemy
    #   deletes their Name rows too (a name with no person is meaningless).
    #   That's the ORM enforcing the same rule the database FK does — belt and
    #   suspenders, and it works even on SQLite where FK enforcement is off by
    #   default in tests.
    names = db.relationship(
        "Name",
        back_populates="individual",
        cascade="all, delete-orphan",
        order_by="Name.sort_order",
    )

    @property
    def primary_name(self):
        """The name to show by default: the one flagged is_primary, else the
        first. A tiny read-helper so views don't repeat this logic."""
        for name in self.names:
            if name.is_primary:
                return name
        return self.names[0] if self.names else None

    def __repr__(self):
        name = self.primary_name
        return f"<Individual #{self.id} {name.display if name else '(unnamed)'}>"


class Name(SoftDeleteMixin, db.Model):
    """One name belonging to one individual — GEDCOM's INDI.NAME structure.

    GEDCOM breaks a name into PIECES (prefix, given, surname, suffix…) instead
    of one string, because "Dr. Wilhelmina van der Berg III" can't be sorted,
    searched, or alphabetized as a blob. Storing the pieces lets us sort by
    surname, search by given name, and reassemble the full name for display.
    """

    __tablename__ = "names"

    id = db.Column(db.Integer, primary_key=True)

    # ON DELETE CASCADE at the DATABASE level (the ondelete= argument) mirrors
    # the ORM cascade above: in MySQL (v2) or any direct SQL, removing the
    # parent individual removes their names automatically. index=True because
    # "give me this person's names" is the hottest query against this table.
    individual_id = db.Column(
        db.Integer,
        db.ForeignKey("individuals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # birth, married, aka, immigrant, maiden — which *kind* of name this is.
    name_type = db.Column(db.String(20), nullable=False, default="birth")

    name_prefix = db.Column(db.String(50))     # Dr., Capt., Rev.
    given = db.Column(db.String(150))           # "Wilhelmina Marie"
    nickname = db.Column(db.String(100))        # "Billie"
    surname_prefix = db.Column(db.String(50))   # van, de, von (sorts under "Berg")
    surname = db.Column(db.String(150))         # "van der Berg"
    name_suffix = db.Column(db.String(50))      # Jr., III

    # Exactly one name per person should be the primary (the app enforces "at
    # most one" in the service layer; the column just records the flag).
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    # Manual ordering when a person has several names of equal importance.
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    individual = db.relationship("Individual", back_populates="names")

    @property
    def display(self):
        """Reassemble the pieces into one human-readable string, skipping the
        blanks. This is presentation logic that genuinely belongs on the model
        (every view needs it the same way) rather than duplicated in templates."""
        parts = [
            self.name_prefix, self.given,
            self.surname_prefix, self.surname, self.name_suffix,
        ]
        return " ".join(p for p in parts if p).strip()

    def __repr__(self):
        return f"<Name #{self.id} {self.display!r} ({self.name_type})>"
