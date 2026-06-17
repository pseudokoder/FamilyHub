"""place_service — reusable PLAC records.

Places are deliberately shared across many events (see place.py), so deleting one
must not leave events pointing at a ghost. The schema says ``ON DELETE SET NULL``,
but SQLite doesn't enforce foreign keys by default, so this service does the
null-out explicitly — the app owning the rule the database can't guarantee here.
"""

from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import Event, Place
from app.services.api_errors import ApiError

_FIELDS = ("full_name", "city", "county", "state", "country")


def _coord(data, field):
    """Parse a latitude/longitude into a Decimal, or None. Rejects non-numbers
    with a friendly 400 (a map can't plot 'somewhere nice')."""
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ApiError(f"{field} must be a number.", 400, fields={field: "invalid"})


def serialize(place):
    return {
        "id": place.id,
        "full_name": place.full_name,
        "city": place.city,
        "county": place.county,
        "state": place.state,
        "country": place.country,
        # DECIMAL -> float so it's valid JSON (and a double in v2).
        "latitude": float(place.latitude) if place.latitude is not None else None,
        "longitude": float(place.longitude) if place.longitude is not None else None,
    }


def list_all():
    return [serialize(p) for p in Place.query.order_by(Place.full_name).all()]


def get(place_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Place, place_id, "place"))


def create(data):
    from app.routes.api import require
    require(data, "full_name")  # a place needs at least a readable name
    place = Place(
        full_name=data.get("full_name"),
        city=data.get("city") or None,
        county=data.get("county") or None,
        state=data.get("state") or None,
        country=data.get("country") or None,
        latitude=_coord(data, "latitude"),
        longitude=_coord(data, "longitude"),
    )
    db.session.add(place)
    db.session.commit()
    return serialize(place)


def update(place_id, data):
    from app.routes.api import get_or_404
    place = get_or_404(Place, place_id, "place")
    for field in _FIELDS:
        if field in data:
            setattr(place, field, data.get(field) or None)
    if "latitude" in data:
        place.latitude = _coord(data, "latitude")
    if "longitude" in data:
        place.longitude = _coord(data, "longitude")
    db.session.commit()
    return serialize(place)


def delete(place_id):
    from app.routes.api import get_or_404
    place = get_or_404(Place, place_id, "place")
    # Detach the place from any events first (the SET NULL the DB won't do for us
    # on SQLite), so no event is left pointing at a deleted place.
    Event.query.filter_by(place_id=place.id).update({"place_id": None})
    db.session.delete(place)
    db.session.commit()
