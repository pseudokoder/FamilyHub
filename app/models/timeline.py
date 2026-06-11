"""TimelineEvent — one moment in the family's history.

DATE-MODELING DECISION (a classic data-design puzzle, D426): family history
is full of partial dates. "Grandpa was born June 12, 1947" — but also
"the family came over from Germany in 1890" (year only) and "the house
fire was March 1962" (no day). A single DATE column can't store "unknown
month". So: three integer columns — year (required), month and day
(optional). Honest data beats fake precision (storing 1890 as Jan 1, 1890
would LOOK exact and LIE).
"""

import calendar
from datetime import datetime, timezone

from app.extensions import db


class TimelineEvent(db.Model):
    __tablename__ = "timeline_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="", server_default="")

    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=True)  # 1-12, None = unknown
    day = db.Column(db.Integer, nullable=True)    # 1-31, None = unknown

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    creator = db.relationship("User")

    @property
    def display_date(self):
        """'1890', 'March 1962', or 'June 12, 1947' — exactly as much as
        we actually know, no more."""
        if self.month:
            if self.day:
                return f"{calendar.month_name[self.month]} {self.day}, {self.year}"
            return f"{calendar.month_name[self.month]} {self.year}"
        return str(self.year)

    @property
    def decade(self):
        """1962 -> 1960, for the decade headers on the timeline page."""
        return (self.year // 10) * 10

    def __repr__(self):
        return f"<TimelineEvent {self.year}: {self.title!r}>"
