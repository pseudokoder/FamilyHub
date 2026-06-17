"""Genealogy service — the business logic that the polymorphic schema needs.

WHY THIS FILE EXISTS (Master Plan §3/§8): events, citations, media links, and
note links attach to a subject through a `subject_type` + `subject_id` pair
instead of a real foreign key. That's what lets one events table serve both
individuals and families — but it has a cost: **the database can't cascade
those deletes for us.** A normal FK would let SQLite/MySQL automatically remove
an individual's events when the individual is deleted; a polymorphic pseudo-FK
can't, because the database doesn't know `subject_id` points at `individuals`.

So the *application* takes responsibility. This is the single, central place
that knows "to delete an individual, also sweep up everything attached to them."
Routing every delete through here (instead of scattering the logic) is exactly
the §10 "one authorization/service layer" principle and the layered-architecture
rule in CLAUDE.md — and it maps straight to a Spring Boot `@Service` method in v2.

TEACHING NOTE on the trade-off: we *chose* polymorphic attachment because it's
the engine behind "everything is a view." The price is this manual cleanup. A
fair trade — and v2/Hibernate can formalize it with `@Any` if desired.
"""

from app.extensions import db
from app.models import (
    Citation, Event, Family, Individual, MediaLink, Name, NoteLink,
)

# --- Subject-type constants ---------------------------------------------------
# One spelling of each polymorphic type, defined ONCE. Every place that writes a
# subject_type imports these, so a typo ("indivdual") can't silently create an
# attachment nothing will ever find.
SUBJECT_INDIVIDUAL = "individual"
SUBJECT_FAMILY = "family"
SUBJECT_EVENT = "event"
SUBJECT_NAME = "name"

# Maps each polymorphic subject_type string to the model it points at — the
# lookup the database can't do for a polymorphic FK, so the app does (§8).
SUBJECT_MODELS = {
    SUBJECT_INDIVIDUAL: Individual,
    SUBJECT_FAMILY: Family,
    SUBJECT_EVENT: Event,
    SUBJECT_NAME: Name,
}


def subject_exists(subject_type, subject_id):
    """Does the polymorphic target actually exist? (The referential check the DB
    can't enforce for a subject_type/subject_id pair.)"""
    model = SUBJECT_MODELS.get(subject_type)
    return model is not None and db.session.get(model, subject_id) is not None


def subject_label(subject_type, subject_id):
    """A human-readable label for an attachment's subject, for serialization —
    so an event reads as 'John Hartwell', not just 'individual #5'."""
    model = SUBJECT_MODELS.get(subject_type)
    obj = db.session.get(model, subject_id) if model else None
    if obj is None:
        return None
    if subject_type == SUBJECT_INDIVIDUAL:
        return obj.primary_name.display if obj.primary_name else None
    if subject_type == SUBJECT_NAME:
        return obj.display
    if subject_type == SUBJECT_FAMILY:
        partners = [p.primary_name.display for p in (obj.partner1, obj.partner2)
                    if p is not None and p.primary_name is not None]
        return " & ".join(partners) if partners else None
    if subject_type == SUBJECT_EVENT:
        return obj.event_tag
    return None


def require_subject(subject_type, subject_id, allowed):
    """Validate a polymorphic attachment's target: the type must be allowed for
    THIS attachment, and the row it names must exist. Raises ApiError(400) with
    a precise field on any problem; returns the validated (type, id) pair. This
    is the one gate every polymorphic write goes through."""
    from app.services.api_errors import ApiError
    if subject_type not in allowed:
        raise ApiError(
            f"subject_type must be one of: {', '.join(sorted(allowed))}.",
            400, fields={"subject_type": "invalid"},
        )
    if subject_id is None:
        raise ApiError("subject_id is required.", 400,
                       fields={"subject_id": "required"})
    if not subject_exists(subject_type, subject_id):
        raise ApiError(f"No {subject_type} found with id {subject_id}.", 400,
                       fields={"subject_id": "no such record"})
    return subject_type, subject_id


def _purge_links(model, subject_type, subject_ids):
    """Bulk-delete polymorphic rows of `model` for a set of subject ids.

    `synchronize_session=False` tells SQLAlchemy "don't bother updating objects
    already loaded in memory" — correct and fast here, because the caller
    commits and moves on rather than re-reading these rows."""
    subject_ids = [s for s in subject_ids if s is not None]
    if not subject_ids:
        return
    (model.query
     .filter(model.subject_type == subject_type,
             model.subject_id.in_(subject_ids))
     .delete(synchronize_session=False))


def delete_individual(individual):
    """Delete one individual and everything attached to them, then commit.

    The order matters: clear the polymorphic attachments FIRST (the database
    won't), then delete the individual — whose Name rows the ORM cascade removes
    automatically (see Individual.names). We also sweep up citations and event-
    level attachments so nothing is left pointing at a person who no longer
    exists.
    """
    ind_id = individual.id
    name_ids = [n.id for n in individual.names]
    event_ids = [
        e.id for e in Event.query
        .filter_by(subject_type=SUBJECT_INDIVIDUAL, subject_id=ind_id).all()
    ]

    # Citations can back the individual, any of their names, or their events.
    _purge_links(Citation, SUBJECT_INDIVIDUAL, [ind_id])
    _purge_links(Citation, SUBJECT_NAME, name_ids)
    _purge_links(Citation, SUBJECT_EVENT, event_ids)

    # Media and note links can hang off the individual or their events.
    for link_model in (MediaLink, NoteLink):
        _purge_links(link_model, SUBJECT_INDIVIDUAL, [ind_id])
        _purge_links(link_model, SUBJECT_EVENT, event_ids)

    # Now the events themselves, then the individual (names cascade via ORM).
    Event.query.filter_by(
        subject_type=SUBJECT_INDIVIDUAL, subject_id=ind_id
    ).delete(synchronize_session=False)
    db.session.delete(individual)
    db.session.commit()


def delete_family(family):
    """Delete one family and everything attached to it, then commit.

    The family's `family_children` link rows cascade via the ORM (see
    Family.children); we clear the polymorphic attachments the database can't,
    exactly as for an individual.
    """
    fam_id = family.id
    event_ids = [
        e.id for e in Event.query
        .filter_by(subject_type=SUBJECT_FAMILY, subject_id=fam_id).all()
    ]

    _purge_links(Citation, SUBJECT_FAMILY, [fam_id])
    _purge_links(Citation, SUBJECT_EVENT, event_ids)
    for link_model in (MediaLink, NoteLink):
        _purge_links(link_model, SUBJECT_FAMILY, [fam_id])
        _purge_links(link_model, SUBJECT_EVENT, event_ids)

    Event.query.filter_by(
        subject_type=SUBJECT_FAMILY, subject_id=fam_id
    ).delete(synchronize_session=False)
    db.session.delete(family)
    db.session.commit()


def delete_event(event):
    """Delete one event and the polymorphic attachments hanging off IT (a photo
    of the wedding, a citation for the birth). Same DB-can't-cascade reason as
    deleting a person."""
    eid = event.id
    _purge_links(Citation, SUBJECT_EVENT, [eid])
    _purge_links(MediaLink, SUBJECT_EVENT, [eid])
    _purge_links(NoteLink, SUBJECT_EVENT, [eid])
    db.session.delete(event)
    db.session.commit()


def individual_events(individual):
    """All of an individual's events, oldest first by the sortable date.

    A read-helper the person-page and timeline views (WP4) will lean on. Sorting
    on `date_sort` is why we store that normalized string alongside the fuzzy
    original (see Event)."""
    return (Event.query
            .filter_by(subject_type=SUBJECT_INDIVIDUAL, subject_id=individual.id)
            .order_by(Event.date_sort).all())
