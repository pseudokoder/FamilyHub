"""search_service — find a person by any fragment you remember (Master Plan §12).

A genealogy site is useless without search. WP2 delivers the BACKEND of it — a
stable endpoint the WP4 search UI will build on — covering people by name +
filters, plus a text search across notes/memories.

SCOPE DECISION (documented): the notes text search here uses portable SQL
``LIKE``. Master Plan §12 schedules **SQLite FTS5** full-text for WP4; doing it
now would pull a SQLite-only virtual table into the schema, breaking the §3
"standard SQL only / MySQL-ready" rule. The endpoint's SHAPE is the contract —
WP4 swaps the LIKE for FTS5 behind it without changing a single caller.

SECURITY NOTE (D315): user text goes into a LIKE pattern, so the wildcard
characters % and _ are escaped — otherwise a search for "50%" would match
everything. (SQLAlchemy still parameterizes the value, so this is about correct
matching, not injection.)
"""

from sqlalchemy import Integer, cast, func, or_

from app.models import Event, Individual, Name, Note, Place


def _like(term):
    """A safe ``LIKE`` pattern: escape the wildcards, then wrap in %…%."""
    safe = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{safe}%"


def _event_year(individual_id, tag):
    event = (Event.query
             .filter_by(subject_type="individual", subject_id=individual_id,
                        event_tag=tag)
             .first())
    if event and event.date_sort and event.date_sort[:4].isdigit():
        return int(event.date_sort[:4])
    return None


def _person_result(individual):
    primary = individual.primary_name
    return {
        "id": individual.id,
        "name": primary.display if primary else None,
        "sex": individual.sex,
        "living": individual.living,
        "birth_year": _event_year(individual.id, "BIRT"),
        "death_year": _event_year(individual.id, "DEAT"),
    }


def _snippet(text, length=160):
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= length else text[:length].rstrip() + "…"


def _search_people(args, q):
    query = Individual.query
    given, surname = args.get("given"), args.get("surname")

    # Name matching: q hits given/surname/nickname; given/surname hit their field.
    if q or given or surname:
        query = query.join(Name)
        if q:
            like = _like(q)
            query = query.filter(or_(
                Name.given.ilike(like, escape="\\"),
                Name.surname.ilike(like, escape="\\"),
                Name.nickname.ilike(like, escape="\\"),
            ))
        if given:
            query = query.filter(Name.given.ilike(_like(given), escape="\\"))
        if surname:
            query = query.filter(Name.surname.ilike(_like(surname), escape="\\"))

    if args.get("sex"):
        query = query.filter(Individual.sex == args.get("sex"))

    living = args.get("living")
    if living not in (None, ""):
        query = query.filter(
            Individual.living == (str(living).lower() in {"true", "1", "yes"}))

    # Birth-year range and/or place filter via the events table.
    birth_from = args.get("birth_from", type=int)
    birth_to = args.get("birth_to", type=int)
    place = args.get("place")
    if birth_from is not None or birth_to is not None or place:
        events = Event.query.filter(Event.subject_type == "individual")
        if birth_from is not None or birth_to is not None:
            events = events.filter(Event.event_tag == "BIRT")
            year = cast(func.substr(Event.date_sort, 1, 4), Integer)
            if birth_from is not None:
                events = events.filter(year >= birth_from)
            if birth_to is not None:
                events = events.filter(year <= birth_to)
        if place:
            events = (events.join(Place, Event.place_id == Place.id)
                      .filter(Place.full_name.ilike(_like(place), escape="\\")))
        matching_ids = [e.subject_id for e in events.all()] or [-1]
        query = query.filter(Individual.id.in_(matching_ids))

    # distinct() because the Name join can return a person once per matching name.
    people = query.distinct().order_by(Individual.id).all()
    return [_person_result(p) for p in people]


def _search_notes(q):
    like = _like(q)
    notes = (Note.query
             .filter(or_(Note.content.ilike(like, escape="\\"),
                         Note.title.ilike(like, escape="\\")))
             .order_by(Note.updated_at.desc()).all())
    return [
        {"id": n.id, "title": n.title, "snippet": _snippet(n.content),
         "author": n.author.display_name if n.author else None}
        for n in notes
    ]


def search(args):
    """Run a search from the request args; returns grouped JSON-ready results."""
    q = (args.get("q") or "").strip()
    people = _search_people(args, q)
    # Notes are text-only: a free-text query is required to search them.
    notes = _search_notes(q) if q else []
    return {
        "query": q,
        "people": people,
        "notes": notes,
        "counts": {"people": len(people), "notes": len(notes)},
    }
