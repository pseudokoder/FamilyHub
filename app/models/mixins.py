"""Model mixins — reusable column bundles shared across tables.

SOFT DELETE (Master Plan v2.0.0 §3, ADR-0001). FamilyHub never *hard*-deletes a
family record. A wrong birth date, an accidental "delete person" — these must be
recoverable, and every change must be traceable (the Genealogical Proof Standard
in miniature). So "delete" just stamps ``deleted_at`` with the current time;
reads filter those rows out by default, and a Curator can restore or revert.

WHY A MIXIN (WGU D426/D480): the ``deleted_at`` column is identical on eleven
tables. Defining it once here and mixing it in keeps the schema DRY — the single
source of truth for "what a soft-deletable row looks like." Add the behaviour to
a new table later by inheriting one class, not by copy-pasting a column.

TEACHING NOTE (why a plain Column works in a mixin): SQLAlchemy's declarative
mapper copies a simple, self-contained ``Column`` onto each subclass, so every
table gets its OWN ``deleted_at`` column and index — they are not shared. (A
column that referenced another table via ``ForeignKey`` would need
``@declared_attr`` instead; ours doesn't, so the plain form is correct here.)

v2 mapping: a ``@MappedSuperclass`` in JPA carrying the same field, or Hibernate's
``@SQLDelete`` + ``@Where(clause = "deleted_at is null")`` to filter automatically.
"""

from app.extensions import db


class SoftDeleteMixin:
    """Adds a nullable ``deleted_at`` timestamp + soft-delete helpers to a model.

    NULL ``deleted_at`` = the row is live. A non-NULL value = the moment it was
    soft-deleted. Indexed because the hottest filter on every soft-deletable
    table is ``WHERE deleted_at IS NULL`` (show me the live rows)."""

    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    @property
    def is_deleted(self):
        """True if this row has been soft-deleted (``deleted_at`` is set)."""
        return self.deleted_at is not None
