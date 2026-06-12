"""AuditLog — who did what, to which thing, when.

WHY: with eight family members all able to create, edit, lock, and delete
things, "who deleted the Thanksgiving album?" needs a better answer than
shrugging. Every state-changing action writes one row here; the admin
panel shows the most recent ones. This is an append-only table — nothing
in the app ever updates or deletes an audit row.

DESIGN (D426): target_type + target_id instead of nine foreign keys.
A real FK per content type would mean a column per table and NULLs
everywhere — and the audit row must SURVIVE the thing it describes being
deleted, which an enforced FK would prevent. The trade-off (the database
can't validate the reference) is exactly right for a log.

v2 mapping: AuditLog @Entity + an AuditService — or Spring Boot Actuator's
audit events if you want the framework to do it.
"""

from datetime import datetime, timezone

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)

    # Nullable: actions from the command line (flask restore-backup) have
    # no logged-in user. The detail text says "CLI" in that case.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    action = db.Column(db.String(50), nullable=False)        # "delete", "lock", ...
    target_type = db.Column(db.String(50), nullable=False)   # "photo", "album", ...
    target_id = db.Column(db.Integer, nullable=True)          # NOT an FK on purpose
    detail = db.Column(db.String(500), nullable=False, default="", server_default="")

    # index=True: the admin page always asks "newest first".
    created_at = db.Column(
        db.DateTime, nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.target_type}#{self.target_id}>"
