"""stats_service — "On This Day" and the aggregate dashboard numbers.

Two read-only views that feed the Home page and the Admin dashboard (Master Plan
§4; design session 2026-07-03):
  * ``on_this_day`` — births, marriages, and deaths from the family's own history
    that share today's month-and-day. The little delight that makes a family site
    feel alive ("On this day in 1929, Grandpa was born").
  * ``aggregate_stats`` — how much is in the tree (people, families, sources,
    photos…) plus on-disk storage, for the dashboard cards and the admin's sense
    of scale/cost.

Everything here respects soft-delete (ADR-0001): deleted rows and events on
deleted subjects never surface.
"""

import os
from datetime import date

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Citation, Event, Family, Individual, MediaObject, Note, Place, Repository,
    Source, User,
)

# The GEDCOM tags "On This Day" cares about, mapped to the bucket they fill.
_ANNIVERSARY_TAGS = {"BIRT": "births", "MARR": "marriages", "DEAT": "deaths"}


def _subject_alive(subject_type, subject_id):
    """Is an event's polymorphic subject a live (non-soft-deleted) record?"""
    model = Individual if subject_type == "individual" else Family
    obj = db.session.get(model, subject_id)
    return obj is not None and obj.deleted_at is None


def _subject_label(subject_type, subject_id):
    if subject_type == "individual":
        ind = db.session.get(Individual, subject_id)
        primary = ind.primary_name if ind else None
        return primary.display if primary else None
    fam = db.session.get(Family, subject_id)
    if fam is None:
        return None
    partners = [p.primary_name.display for p in (fam.partner1, fam.partner2)
                if p is not None and p.primary_name is not None]
    return " & ".join(partners) if partners else None


def on_this_day(month=None, day=None):
    """Births/marriages/deaths whose month-and-day match today (or a given date).

    Matches on the normalized ``date_sort`` ("YYYY-MM-DD"), so fuzzy year-only
    dates ("1929-00-00") simply won't match a real day — correct, since we only
    celebrate anniversaries we can actually place on the calendar."""
    today = date.today()
    month = month or today.month
    day = day or today.day
    mmdd = f"{int(month):02d}-{int(day):02d}"

    events = (Event.query
              .filter(Event.deleted_at.is_(None),
                      Event.event_tag.in_(_ANNIVERSARY_TAGS.keys()),
                      func.substr(Event.date_sort, 6, 5) == mmdd)
              .order_by(Event.date_sort).all())

    buckets = {"births": [], "marriages": [], "deaths": []}
    for event in events:
        if not _subject_alive(event.subject_type, event.subject_id):
            continue
        buckets[_ANNIVERSARY_TAGS[event.event_tag]].append({
            "event_id": event.id,
            "subject_type": event.subject_type,
            "subject_id": event.subject_id,
            "who": _subject_label(event.subject_type, event.subject_id),
            "year": int(event.date_sort[:4]) if event.date_sort[:4].isdigit() else None,
            "date_original": event.date_original,
            "place": event.place.full_name if event.place else None,
        })
    return {"month": int(month), "day": int(day), **buckets}


def _storage_bytes():
    """Total bytes of the uploaded-media folder on disk. The admin's cost signal;
    the filesystem is the source of truth (the DB only stores paths)."""
    root = current_app.config.get("UPLOAD_FOLDER")
    if not root or not os.path.isdir(root):
        return 0
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def _live(model):
    """Count of live rows for a soft-deletable model."""
    return model.query.filter(model.deleted_at.is_(None)).count()


def aggregate_stats():
    """The dashboard counters + storage. One cheap call for Home and Admin."""
    return {
        "counts": {
            "people": _live(Individual),
            "families": _live(Family),
            "events": _live(Event),
            "sources": _live(Source),
            "citations": _live(Citation),
            "photos": _live(MediaObject),
            "notes": _live(Note),
            "places": Place.query.count(),          # reference data (no soft-delete)
            "repositories": Repository.query.count(),
            "users": User.query.count(),
        },
        "storage_bytes": _storage_bytes(),
    }
