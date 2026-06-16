"""Events — births, deaths, marriages, occupations… the heart of the timeline.

This is where the "everything is a view" idea (Master Plan §2) really pays off.
An EVENT is anything that happened at a time and place: BIRT, DEAT, MARR, DIV,
BURI, plus GEDCOM *attributes* like OCCU (occupation) and RESI (residence).
Order every event by date and you have the timeline view, for free.

TWO DESIGN IDEAS WORTH STUDYING:

1. POLYMORPHIC ATTACHMENT (Master Plan §3/§8). An event can belong to an
   *individual* (a birth) OR a *family* (a marriage). Rather than two near-
   identical tables, we use a `subject_type` + `subject_id` pair: the type
   names which table, the id names the row. One events table serves both. The
   trade-off — the database can't enforce this with a real foreign key, so the
   app layer (genealogy_service) maintains it. v2/Hibernate can formalize it
   with `@Any`. We accept that trade-off because it's the mechanism that makes
   one shared database power many views.

2. DUAL DATES (Master Plan §3). Family history is full of fuzzy dates: "ABT
   1850", "BEF 1900", "March 1962". We keep BOTH the original GEDCOM string
   (`date_original`, shown to humans exactly as recorded) AND a normalized,
   sortable value (`date_sort`, e.g. "1850-00-00") so a timeline can ORDER BY
   it. Faithful display *and* correct sorting, neither sacrificed.
"""

from app.extensions import db
from app.models.individual import _utcnow


class Event(db.Model):
    """One dated, placed happening attached to an individual or a family."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)

    # --- The polymorphic link (see teaching note #1 above) -------------------
    # 'individual' or 'family'. Not a DB foreign key — that's the trade-off we
    # signed up for; the app keeps it honest.
    subject_type = db.Column(db.String(20), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)

    # --- What happened -------------------------------------------------------
    # The GEDCOM tag: BIRT, DEAT, MARR, OCCU, RESI… Short codes on purpose —
    # they're the genealogy standard, and keeping them lets us round-trip to a
    # .ged file in WP6 without a translation table.
    event_tag = db.Column(db.String(10), nullable=False)
    # For *attributes* (vs events): the value, e.g. the occupation "Blacksmith"
    # for an OCCU tag, or the residence text for RESI.
    event_value = db.Column(db.String(255))

    # --- When (see teaching note #2 above) -----------------------------------
    date_original = db.Column(db.String(100))   # "ABT 1850", "March 1962"
    date_sort = db.Column(db.String(20))        # "1850-00-00" — sortable

    # --- Where ---------------------------------------------------------------
    # SET NULL: deleting a place must not delete the birth that happened there;
    # the event simply loses its place pointer.
    place_id = db.Column(
        db.Integer, db.ForeignKey("places.id", ondelete="SET NULL"), nullable=True
    )

    # Extra GEDCOM detail some events carry.
    age = db.Column(db.String(30))      # "age at event", e.g. "72y"
    cause = db.Column(db.String(255))   # cause of death, etc.

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    place = db.relationship("Place")

    # --- Indexes (Master Plan §3.2) ------------------------------------------
    # Two queries dominate this table: "all events for this subject" (the person
    # page) and "all events in date order" (the timeline). A composite index on
    # the subject pair and one on date_sort turn both from full-table scans into
    # quick lookups (WGU D427 Data Management – Applications: index what you
    # filter and sort by). Explicit names so migrations can always refer to them.
    __table_args__ = (
        db.Index("ix_events_subject", "subject_type", "subject_id"),
        db.Index("ix_events_date_sort", "date_sort"),
    )

    def __repr__(self):
        return (f"<Event #{self.id} {self.event_tag} "
                f"{self.subject_type}#{self.subject_id} {self.date_original!r}>")
