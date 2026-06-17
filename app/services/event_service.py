"""event_service — events & attributes (BIRT, DEAT, MARR, OCCU, RESI…).

Events are polymorphic: one attaches to an individual OR a family (see event.py).
This service validates that polymorphic target through the ONE gate
(genealogy_service.require_subject) and keeps both date fields — the faithful
``date_original`` and the sortable ``date_sort`` — exactly as the contract
promises (the §5A depth bar: every meaningful field is capturable).
"""

from app.extensions import db
from app.models import Event, Place
from app.services import genealogy_service as gs
from app.services.api_errors import ApiError

# Which records an event can belong to (NOT names/events — only people & families).
EVENT_SUBJECTS = {gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY}


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def _validate_place(place_id):
    if place_id is None:
        return None
    if db.session.get(Place, place_id) is None:
        raise ApiError(f"No place with id {place_id}.", 400,
                       fields={"place_id": "no such place"})
    return place_id


def serialize(event):
    return {
        "id": event.id,
        "subject_type": event.subject_type,
        "subject_id": event.subject_id,
        "subject_label": gs.subject_label(event.subject_type, event.subject_id),
        "event_tag": event.event_tag,
        "event_value": event.event_value,
        "date_original": event.date_original,
        "date_sort": event.date_sort,
        "place_id": event.place_id,
        "place": event.place.full_name if event.place else None,
        "age": event.age,
        "cause": event.cause,
        "created_at": _iso(event.created_at),
    }


def list_all(subject_type=None, subject_id=None):
    """All events, or just one subject's, ordered by the sortable date so the
    result is already timeline-ready (Master Plan §4)."""
    query = Event.query
    if subject_type and subject_id is not None:
        query = query.filter_by(subject_type=subject_type, subject_id=subject_id)
    return [serialize(e) for e in query.order_by(Event.date_sort).all()]


def get(event_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Event, event_id, "event"))


def create(data):
    from app.routes.api import require
    require(data, "event_tag")
    subject_type, subject_id = gs.require_subject(
        data.get("subject_type"), data.get("subject_id"), EVENT_SUBJECTS
    )
    event = Event(
        subject_type=subject_type, subject_id=subject_id,
        event_tag=data["event_tag"],
        event_value=data.get("event_value") or None,
        date_original=data.get("date_original") or None,
        date_sort=data.get("date_sort") or None,
        place_id=_validate_place(data.get("place_id")),
        age=data.get("age") or None,
        cause=data.get("cause") or None,
    )
    db.session.add(event)
    db.session.commit()
    return serialize(event)


def update(event_id, data):
    from app.routes.api import get_or_404
    event = get_or_404(Event, event_id, "event")
    if "subject_type" in data or "subject_id" in data:
        event.subject_type, event.subject_id = gs.require_subject(
            data.get("subject_type", event.subject_type),
            data.get("subject_id", event.subject_id), EVENT_SUBJECTS,
        )
    for field in ("event_tag", "event_value", "date_original", "date_sort",
                  "age", "cause"):
        if field in data:
            setattr(event, field, data.get(field) or None)
    if "event_tag" in data and not event.event_tag:
        raise ApiError("event_tag can't be blank.", 400,
                       fields={"event_tag": "required"})
    if "place_id" in data:
        event.place_id = _validate_place(data.get("place_id"))
    db.session.commit()
    return serialize(event)


def delete(event_id):
    from app.routes.api import get_or_404
    gs.delete_event(get_or_404(Event, event_id, "event"))
