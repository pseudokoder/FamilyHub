"""Seed tests — the runnable proof that the whole schema holds together.

seed.py builds three generations of the (fictional) Hartwell family. If it runs
clean and populates every table — including every polymorphic link kind — the
GEDCOM-7 data foundation is sound. That's exactly the WP1 acceptance bar.
"""

from app.models import Citation, Event, MediaLink, NoteLink
from app.services import genealogy_service as gs
from seed import seed_all

# What a clean seed run should produce, table by table. Brittle on purpose: if a
# future edit to seed.py changes the data, this number changes with it — a
# deliberate tripwire that keeps the seed and its proof in lockstep.
EXPECTED_COUNTS = {
    "individuals": 9,
    "names": 12,
    "families": 3,
    "family_children": 5,
    "places": 4,
    "events": 12,
    "repositories": 1,
    "sources": 2,
    "citations": 4,
    "media_objects": 2,
    "media_links": 4,
    "notes": 3,
    "note_links": 4,
}


def test_seed_populates_every_table(app):
    counts = seed_all()
    assert counts == EXPECTED_COUNTS


def test_seed_exercises_every_polymorphic_subject_type(app):
    seed_all()
    # Events attach to individuals AND families.
    assert {e.subject_type for e in Event.query.all()} == {
        gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY,
    }
    # Citations cover all four kinds the schema allows.
    assert {c.subject_type for c in Citation.query.all()} == {
        gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY,
        gs.SUBJECT_EVENT, gs.SUBJECT_NAME,
    }
    # Media + note links each reach individuals, families, and events.
    assert {m.subject_type for m in MediaLink.query.all()} >= {
        gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY, gs.SUBJECT_EVENT,
    }
    assert {n.subject_type for n in NoteLink.query.all()} >= {
        gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY, gs.SUBJECT_EVENT,
    }


def test_seed_credits_an_existing_user_as_author(app, admin):
    """When an account exists (e.g. after `flask create-admin`), seed credits it
    as photo uploader / memory author — exercising those nullable FKs."""
    seed_all()
    from app.models import MediaObject, Note
    assert all(obj.uploaded_by == admin.id for obj in MediaObject.query.all())
    assert all(note.author_id == admin.id for note in Note.query.all())
