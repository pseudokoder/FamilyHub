"""HistoricalEvent — a bundled almanac of world/US events for the timeline.

WHY THIS TABLE EXISTS (Master Plan v2.0.0, §4 timeline; design session
2026-07-03): a family timeline reads better with CONTEXT. "Grandpa was born in
1929" means more beside "1929 — the Wall Street Crash." These are NOT family
facts (they never attach to an individual), so they don't belong in ``events``.
They're static REFERENCE data — the same short almanac for every family — so they
get their own tiny table, seeded from a bundled dataset and re-seeded on demand.

DISTINCTION FROM ``events`` (the GEDCOM table): ``events`` are private, per-person
genealogy facts (a birth, a marriage) with polymorphic subjects and full evidence
citations. ``historical_events`` are public, global, subject-less backdrop the
timeline view BLENDS IN by date. Keeping them apart keeps the genealogy core clean
(one table per real-world concept — D426).

v2 mapping: a ``HistoricalEvent`` @Entity seeded by a Flyway ``R__`` repeatable
migration, or shipped as a static JSON asset the Angular timeline merges client-side.
"""

from app.extensions import db


class HistoricalEvent(db.Model):
    """One dated world/US event, for timeline context. Reference data, not
    family data — so no soft-delete, no polymorphic subject, no citations."""

    __tablename__ = "historical_events"

    id = db.Column(db.Integer, primary_key=True)

    # The plain year is what the timeline usually blends on ("things that happened
    # in 1929"). Required and indexed — every timeline query filters/sorts by it.
    year = db.Column(db.Integer, nullable=False, index=True)

    # An optional finer sortable date ("1929-10-29") for events we can place to
    # the day, so they interleave correctly with dated family events. Same
    # normalized-string shape as Event.date_sort, for one consistent sort key.
    date_sort = db.Column(db.String(20))

    title = db.Column(db.String(255), nullable=False)

    # REQUIRED one-liner (the design decision: an event with no description is
    # useless context). Kept short on purpose — it renders inline on the timeline.
    description = db.Column(db.String(255), nullable=False)

    # 'US' or 'world' — lets the UI filter the backdrop to what a given family
    # cares about. A short closed vocabulary, validated in the service layer.
    scope = db.Column(db.String(10), nullable=False, default="world")

    __table_args__ = (
        db.Index("ix_historical_events_scope_year", "scope", "year"),
    )

    def __repr__(self):
        return f"<HistoricalEvent {self.year} {self.title!r} ({self.scope})>"
