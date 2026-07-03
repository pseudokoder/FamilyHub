"""AuditLog — who did what, to which thing, when, and what changed.

WHY: with a family all able to create, edit, and delete things, "who changed
Grandpa's birth date?" needs a better answer than shrugging. Every state-changing
action writes one row here. This is an append-only table — nothing in the app
ever updates or deletes an audit row.

Two jobs, one table:
  * The **security/admin trail** (logins, backups, user management) uses the
    human-readable ``detail`` string.
  * The **write-control trail** (ADR-0001) for genealogy edits additionally
    captures ``before_json`` / ``after_json`` — the full prior and new state of
    the row — which is what powers one-click **revert** (Master Plan v2.0.0, §9
    Tier-1). Reverting is just "write ``before_json`` back."

DESIGN (D426): ``subject_type`` + ``subject_id`` (the same polymorphic pair the
rest of the schema uses on events/citations/media/notes) instead of one FK per
content type. A real FK would need a column per table AND would forbid the audit
row from OUTLIVING the thing it describes being deleted — exactly backwards for a
log. The trade-off (the database can't validate the reference) is right here.

v2 mapping: AuditLog @Entity + an AuditService — or Spring Boot Actuator's
audit events / Hibernate Envers if you want the framework to do it.
"""

from datetime import datetime, timezone

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)

    # Nullable: actions from the command line (flask restore-backup) have
    # no logged-in user. The detail text says "CLI" in that case.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # create | update | delete | restore | revert (genealogy write-control),
    # plus the security/admin verbs (login, backup, edit, set password, …).
    action = db.Column(db.String(50), nullable=False)
    # The polymorphic subject: 'individual', 'family', 'user', 'site settings'…
    # Renamed from target_type/target_id (2026-07-03) to match the schema-wide
    # subject_type/subject_id convention. NOT a foreign key, on purpose.
    subject_type = db.Column(db.String(50), nullable=False)
    subject_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.String(500), nullable=False, default="", server_default="")

    # Before/after snapshots for revert (ADR-0001). JSON serialized as TEXT —
    # portable to MySQL as-is. NULL where they don't apply: before_json is NULL
    # on a create, after_json is NULL on a delete, and both are NULL for the
    # security/admin events that only carry a ``detail`` string.
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)

    # index=True: the admin page always asks "newest first".
    created_at = db.Column(
        db.DateTime, nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.subject_type}#{self.subject_id}>"
