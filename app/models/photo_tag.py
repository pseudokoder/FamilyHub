"""PhotoTag — "this person is in this photo."

THE BRIDGE TABLE: photos and wiki pages were islands; this table is the
bridge. One row = one face named in one photo. From it, two features
fall out for free: chips under a photo answering "who IS that?", and a
"Photos featuring X" gallery on every wiki page.

DESIGN (D426): this is a classic many-to-many join table (a photo holds
many people; a person appears in many photos) — but written as a real
model class instead of SQLAlchemy's bare `db.Table`, because the
relationship itself has facts to remember (who tagged, when). The
UniqueConstraint is the data integrity rule: the same person can't be
tagged into the same photo twice, and the DATABASE enforces it even if
app code slips.

v2 mapping: @Entity with a composite unique constraint — the join-table-
with-payload pattern from D287's data modeling unit.
"""

from datetime import datetime, timezone

from app.extensions import db


class PhotoTag(db.Model):
    __tablename__ = "photo_tags"
    __table_args__ = (
        db.UniqueConstraint("photo_id", "member_id",
                            name="uq_photo_tags_photo_id_member_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(
        db.Integer, db.ForeignKey("photos.id"), nullable=False, index=True
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey("family_member.id"), nullable=False, index=True
    )

    # Who named the face, and when — the payload that justifies a real model.
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    photo = db.relationship("Photo", back_populates="tags")
    member = db.relationship("FamilyMember", back_populates="photo_tags")
    tagger = db.relationship("User")

    def __repr__(self):
        return f"<PhotoTag member {self.member_id} in photo {self.photo_id}>"
