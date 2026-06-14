"""Family Plans — the lean collaborative pillar.

WHAT IT IS: a shared space to plan things together (a reunion, a trip, a
"neat ideas" board). Deliberately built by REUSING patterns already in
the app rather than inventing architecture:

  - a Plan is shaped like a blog Post (title + description),
  - it's LOCKABLE like photos/wiki/timeline (the Trial Period rule),
  - its checklist items echo the parent→child pattern (album→photos),
  - its attachments reuse the photo upload SECURITY model (validate,
    random names, stored outside the web root, served login-walled).

THREE small tables, one feature:
    family_plans → plan_items   (the shared checklist)
    family_plans → plan_attachments (images + PDFs only)

v2 mapping: a FamilyPlan @Entity with @OneToMany item/attachment
collections — the same homework as the album→photo relationship.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import LockableMixin


class FamilyPlan(LockableMixin, db.Model):
    """One shared plan. Editable by any member (collaborative, like the
    wiki); deletable by its creator until an admin locks it (Trial Period,
    like every other content pillar)."""

    __tablename__ = "family_plans"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="", server_default="")

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # created_by AND the mixin's locked_by both point at users — so the
    # relationship must say which FK it follows (learned the hard way in
    # Ch. 18 when the lock columns landed).
    creator = db.relationship("User", foreign_keys=[created_by])
    items = db.relationship(
        "PlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanItem.id",
    )
    attachments = db.relationship(
        "PlanAttachment",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanAttachment.uploaded_at",
    )

    @property
    def open_item_count(self):
        """How many checklist items aren't done yet — for the list badge."""
        return sum(1 for item in self.items if not item.is_done)

    def __repr__(self):
        return f"<FamilyPlan {self.title!r}>"


class PlanItem(db.Model):
    """One checklist line — 'Book the cabin', 'Bring the canoe'. Any member
    may add items and tick them off; that shared ticking IS the
    collaboration."""

    __tablename__ = "plan_items"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("family_plans.id"), nullable=False, index=True
    )
    text = db.Column(db.String(300), nullable=False)
    is_done = db.Column(db.Boolean, nullable=False, default=False)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    plan = db.relationship("FamilyPlan", back_populates="items")
    creator = db.relationship("User")

    def __repr__(self):
        return f"<PlanItem {self.id} done={self.is_done}>"


class PlanAttachment(db.Model):
    """A shared file on a plan — an itinerary PDF, a map screenshot. Limited
    to images + PDFs (see plan_service for WHY arbitrary files are unsafe);
    stored outside the web root and served only through a login-walled
    route, exactly like family photos."""

    __tablename__ = "plan_attachments"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("family_plans.id"), nullable=False, index=True
    )

    # Random UUID on disk; the human name kept for display + download.
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    # "image" or "pdf" — lets the template show a preview vs. a file link.
    kind = db.Column(db.String(10), nullable=False)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    plan = db.relationship("FamilyPlan", back_populates="attachments")
    uploader = db.relationship("User")

    def __repr__(self):
        return f"<PlanAttachment {self.filename} ({self.kind})>"
