"""RoleRequest — a member asks for elevated access → admin approval (§5, §10).

A Contributor who wants to become a Curator (or a Viewer who wants to contribute)
files a request; an admin approves it — and approval applies the role change
THROUGH the audited user_service, so the elevation is as traceable as any other
change (ADR-0001). The request row is the paper trail: who asked, who decided, when.

v2 mapping: a ``RoleRequest`` @Entity + a ``RoleRequestService``.
"""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


STATUSES = ("pending", "approved", "denied")


class RoleRequest(db.Model):
    __tablename__ = "role_requests"

    id = db.Column(db.Integer, primary_key=True)

    # CASCADE: if the account is deleted, its pending requests go with it — a
    # request to promote a user who no longer exists is meaningless.
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requested_role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False,
                       default="pending", server_default="pending")

    # Who ruled on it (SET NULL so the decision record survives that admin's
    # account being removed) and when.
    decided_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    decided_by = db.relationship("User", foreign_keys=[decided_by_user_id])

    def __repr__(self):
        return f"<RoleRequest #{self.id} user={self.user_id} → {self.requested_role} ({self.status})>"
