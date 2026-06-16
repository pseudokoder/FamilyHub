"""Model tests for the GEDCOM-7 core (WP1).

These prove the schema actually behaves: relationships connect, names reassemble,
cascade deletes clean up, and the polymorphic attachments (events, citations,
media links, note links) attach to any subject and get swept up on delete.

This is the WP1 phase-gate evidence — if these pass, the data foundation holds.
"""

from app.extensions import db
from app.models import (
    Citation, Event, Family, FamilyChild, Individual, MediaLink, MediaObject,
    Name, Note, NoteLink, Place, Repository, Source,
)
from app.services import genealogy_service as gs


def _person(given, surname, sex="M", living=False):
    """Create + persist an individual with one primary birth name."""
    person = Individual(sex=sex, living=living)
    db.session.add(person)
    db.session.flush()
    db.session.add(Name(individual_id=person.id, is_primary=True,
                        given=given, surname=surname))
    db.session.commit()
    return person


# --- Names & individuals ------------------------------------------------------

def test_individual_collects_multiple_names(app):
    person = _person("Wilhelmina", "Berg", sex="F")
    db.session.add(Name(individual_id=person.id, name_type="married",
                        given="Wilhelmina", surname="Hartwell", sort_order=1))
    db.session.commit()

    assert len(person.names) == 2
    # primary_name returns the flagged one; display reassembles the pieces.
    assert person.primary_name.is_primary
    assert person.primary_name.display == "Wilhelmina Berg"


def test_name_display_skips_blank_pieces(app):
    person = _person("Wilhelmina", "Berg", sex="F")
    name = person.primary_name
    name.name_prefix = "Dr."
    name.surname_prefix = "van der"
    db.session.commit()
    # Pieces join with single spaces, blanks omitted.
    assert name.display == "Dr. Wilhelmina van der Berg"


# --- Families & the parent/child graph ----------------------------------------

def test_family_links_partners_and_ordered_children(app):
    dad = _person("Thomas", "Hartwell")
    mom = _person("Margaret", "Hartwell", sex="F")
    kid_b = _person("Evelyn", "Hartwell", sex="F")
    kid_a = _person("Robert", "Hartwell")

    fam = Family(partner1_id=dad.id, partner2_id=mom.id)
    db.session.add(fam)
    db.session.flush()
    db.session.add_all([
        FamilyChild(family_id=fam.id, child_id=kid_a.id, child_order=0),
        FamilyChild(family_id=fam.id, child_id=kid_b.id,
                    pedigree_type="adopted", child_order=1),
    ])
    db.session.commit()

    assert fam.partner1.primary_name.display == "Thomas Hartwell"
    # children come back in child_order, and carry their pedigree payload.
    assert [c.child_id for c in fam.children] == [kid_a.id, kid_b.id]
    assert fam.children[1].pedigree_type == "adopted"


# --- Cascade deletes (ORM relationship cascade) -------------------------------

def test_deleting_individual_cascades_names(app):
    person = _person("Solo", "Person")
    name_id = person.primary_name.id
    db.session.delete(person)
    db.session.commit()
    assert db.session.get(Name, name_id) is None


def test_deleting_source_cascades_citations(app):
    src = Source(title="1880 Census")
    db.session.add(src)
    db.session.flush()
    cite = Citation(source_id=src.id, subject_type=gs.SUBJECT_INDIVIDUAL,
                    subject_id=999, page="p.1")
    db.session.add(cite)
    db.session.commit()
    cite_id = cite.id

    db.session.delete(src)
    db.session.commit()
    assert db.session.get(Citation, cite_id) is None


def test_deleting_media_object_cascades_links(app):
    obj = MediaObject(title="Portrait", file_path="media/p.jpg")
    db.session.add(obj)
    db.session.flush()
    db.session.add(MediaLink(media_id=obj.id,
                             subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=5))
    db.session.commit()

    db.session.delete(obj)
    db.session.commit()
    assert MediaLink.query.count() == 0


# --- Polymorphic attachment ---------------------------------------------------

def test_event_attaches_to_both_individuals_and_families(app):
    person = _person("John", "Hartwell")
    fam = Family(partner1_id=person.id)
    db.session.add(fam)
    db.session.flush()
    db.session.add_all([
        Event(subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=person.id,
              event_tag="BIRT", date_original="ABT 1850", date_sort="1850-00-00"),
        Event(subject_type=gs.SUBJECT_FAMILY, subject_id=fam.id,
              event_tag="MARR", date_original="1870", date_sort="1870-00-00"),
    ])
    db.session.commit()

    by_subject = {(e.subject_type, e.subject_id) for e in Event.query.all()}
    assert (gs.SUBJECT_INDIVIDUAL, person.id) in by_subject
    assert (gs.SUBJECT_FAMILY, fam.id) in by_subject


def test_place_is_reused_across_events(app):
    person = _person("John", "Hartwell")
    place = Place(full_name="Spring Hill, Maury, Tennessee, USA")
    db.session.add(place)
    db.session.flush()
    db.session.add_all([
        Event(subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=person.id,
              event_tag="BIRT", place_id=place.id),
        Event(subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=person.id,
              event_tag="DEAT", place_id=place.id),
    ])
    db.session.commit()
    # One place row, pointed at by two events — the whole reason places are
    # their own table.
    assert Place.query.count() == 1
    assert Event.query.filter_by(place_id=place.id).count() == 2


# --- genealogy_service: polymorphic-cascade delete helpers --------------------

def test_delete_individual_sweeps_up_polymorphic_attachments(app):
    person = _person("Doomed", "Person")
    pid = person.id
    name_id = person.primary_name.id

    event = Event(subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=pid,
                  event_tag="OCCU", event_value="Blacksmith")
    db.session.add(event)
    db.session.flush()
    obj = MediaObject(title="Photo", file_path="media/x.jpg")
    note = Note(title="Memory", content="A story.")
    src = Source(title="A source")
    db.session.add_all([obj, note, src])
    db.session.flush()
    db.session.add_all([
        # links to the individual...
        MediaLink(media_id=obj.id, subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=pid),
        NoteLink(note_id=note.id, subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=pid),
        Citation(source_id=src.id, subject_type=gs.SUBJECT_INDIVIDUAL, subject_id=pid),
        # ...a citation on the individual's NAME...
        Citation(source_id=src.id, subject_type=gs.SUBJECT_NAME, subject_id=name_id),
        # ...and a note link on their EVENT.
        NoteLink(note_id=note.id, subject_type=gs.SUBJECT_EVENT, subject_id=event.id),
    ])
    db.session.commit()

    gs.delete_individual(person)

    # Individual + name (ORM cascade) gone...
    assert db.session.get(Individual, pid) is None
    assert db.session.get(Name, name_id) is None
    # ...and every polymorphic attachment swept up by the service.
    assert Event.query.count() == 0
    assert MediaLink.query.count() == 0
    assert NoteLink.query.count() == 0
    assert Citation.query.count() == 0
    # The shared objects themselves survive (only the LINKS were removed).
    assert MediaObject.query.count() == 1
    assert Note.query.count() == 1
    assert Source.query.count() == 1


def test_delete_family_sweeps_up_polymorphic_attachments(app):
    dad = _person("Dad", "Smith")
    kid = _person("Kid", "Smith")
    fam = Family(partner1_id=dad.id)
    db.session.add(fam)
    db.session.flush()
    fid = fam.id
    db.session.add(FamilyChild(family_id=fid, child_id=kid.id))
    event = Event(subject_type=gs.SUBJECT_FAMILY, subject_id=fid, event_tag="MARR")
    note = Note(title="Wedding", content="They married.")
    db.session.add_all([event, note])
    db.session.flush()
    db.session.add(NoteLink(note_id=note.id, subject_type=gs.SUBJECT_FAMILY, subject_id=fid))
    db.session.commit()

    gs.delete_family(fam)

    assert db.session.get(Family, fid) is None
    assert FamilyChild.query.count() == 0   # ORM cascade
    assert Event.query.count() == 0         # swept up
    assert NoteLink.query.count() == 0      # swept up
    # The two people and the note object are untouched.
    assert Individual.query.count() == 2
    assert Note.query.count() == 1
