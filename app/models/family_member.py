from datetime import datetime, timezone

from app.models import db


class FamilyMember(db.Model):
    """A person in the family tree. Starter model for Day 3 setup."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<FamilyMember {self.name}>"
