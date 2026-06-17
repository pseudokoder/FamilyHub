"""seed.py — realistic mock data for the GEDCOM-7 schema (Master Plan WP1).

WHY A SEED SCRIPT? Two reasons, both about confidence:
  1. It lets Cowork (WP3) and Wes *see* the app full of believable data instead
     of a blank screen, so the views can be designed against something real.
  2. It is a working, runnable PROOF that the schema holds together — every
     table populated, every relationship wired, every polymorphic link kind
     exercised. If seed runs clean, the data model is sound. (WGU D426: a schema
     you can't populate with real-shaped data has a design flaw hiding in it.)

The data: the **Hartwell family**, three generations, entirely fictional. Fuzzy
dates ("ABT 1850", "March 1962") sit next to exact ones on purpose — that's what
real genealogy looks like, and it's what the dual date_original/date_sort design
is built to handle.

Run it:   flask seed         (wipes nothing; meant for a fresh dev database)
"""

from app.extensions import db
from app.models import (
    Citation, Event, Family, FamilyChild, Individual, MediaLink, MediaObject,
    Name, Note, NoteLink, Place, Repository, Role, Source, User,
)
from app.services import user_service
from app.services.genealogy_service import (
    SUBJECT_EVENT, SUBJECT_FAMILY, SUBJECT_INDIVIDUAL, SUBJECT_NAME,
)

# DEV-ONLY demo password. These are mock accounts for a fresh dev database so the
# API and the RBAC ladder have real users to exercise — never use this on a real
# server (real accounts are made with `flask create-admin` + the admin panel).
DEMO_PASSWORD = "FamilyHub123"
DEMO_USERS = [
    ("jo@example.com", "Grandma Jo", Role.USER),
    ("robert@example.com", "Robert Hartwell", Role.POWER_USER),
    ("pat@example.com", "Cousin Pat (by marriage)", Role.GUEST),
]


def seed_users():
    """Create the demo accounts (dev only). Skips any that already exist, so
    it's safe to re-run. Returns the users it created."""
    created = []
    for email, name, role in DEMO_USERS:
        if user_service.find_by_email(email) is None:
            created.append(
                user_service.create_user(email, name, DEMO_PASSWORD, role=role)
            )
    return created


def _individual(sex, living=False, **name_fields):
    """Create an individual with one primary birth name in one step — the
    common case. Extra names get added separately below."""
    person = Individual(sex=sex, living=living)
    db.session.add(person)
    db.session.flush()  # assign person.id so the Name can reference it
    db.session.add(Name(individual_id=person.id, is_primary=True, **name_fields))
    return person


def seed_all(author=None):
    """Populate a fresh database with the Hartwell family. Returns a dict of
    {table_name: row_count} so callers (and the test) can prove what landed.

    `author` is the User credited as uploader of photos / author of memories.
    If omitted we borrow the first existing account (e.g. the admin created by
    `flask create-admin`), or leave it NULL — both are valid (those FKs are
    deliberately nullable so content outlives accounts).
    """
    if author is None:
        author = User.query.first()
    author_id = author.id if author is not None else None

    # ------------------------------------------------------------------ PLACES
    # Created once, pointed at by many events — the whole reason places are
    # their own table (see place.py).
    amsterdam = Place(
        full_name="Amsterdam, Noord-Holland, Netherlands",
        city="Amsterdam", state="Noord-Holland", country="Netherlands",
        latitude=52.3702157, longitude=4.8951679,
    )
    spring_hill = Place(
        full_name="Spring Hill, Maury, Tennessee, USA",
        city="Spring Hill", county="Maury", state="Tennessee", country="USA",
        latitude=35.7512000, longitude=-86.9300000,
    )
    nashville = Place(
        full_name="Nashville, Davidson, Tennessee, USA",
        city="Nashville", county="Davidson", state="Tennessee", country="USA",
    )
    chicago = Place(
        full_name="Chicago, Cook, Illinois, USA",
        city="Chicago", county="Cook", state="Illinois", country="USA",
    )
    db.session.add_all([amsterdam, spring_hill, nashville, chicago])
    db.session.flush()

    # ------------------------------------------------------- GENERATION 1
    wilhelmina = _individual(
        "F", given="Wilhelmina Marie",
        surname_prefix="van der", surname="Berg", nickname="Billie",
    )
    # A second name: her married name. A person collects names over a lifetime —
    # exactly why names are their own table.
    db.session.add(Name(
        individual_id=wilhelmina.id, name_type="married",
        given="Wilhelmina", surname="Hartwell", sort_order=1,
    ))
    thomas = _individual("M", given="Thomas Earl", surname="Hartwell")

    # ------------------------------------------------------- GENERATION 2
    john = _individual("M", given="John Thomas", surname="Hartwell")
    db.session.add(Name(  # nickname-style AKA
        individual_id=john.id, name_type="aka",
        given="Jack", surname="Hartwell", sort_order=1,
    ))
    margaret = _individual("F", given="Margaret", surname="O'Sullivan")
    db.session.add(Name(
        individual_id=margaret.id, name_type="married",
        given="Margaret", surname="Hartwell", sort_order=1,
    ))

    # ------------------------------------------------------- GENERATION 3
    robert = _individual("M", living=True, given="Robert James", surname="Hartwell")
    evelyn = _individual("F", living=True, given="Evelyn Rose", surname="Hartwell")
    samuel = _individual("M", living=True, given="Samuel", surname="Hartwell")
    linda = _individual("F", living=True, given="Linda", surname="Carter")
    maya = _individual("F", living=True, given="Maya Jane", surname="Hartwell")
    db.session.flush()

    # ------------------------------------------------------------------ FAMILIES
    # F1: the immigrant grandparents.
    fam1 = Family(partner1_id=thomas.id, partner2_id=wilhelmina.id)
    # F2: their son John and Margaret — note the varied pedigree types below.
    fam2 = Family(partner1_id=john.id, partner2_id=margaret.id)
    # F3: grandson Robert and Linda.
    fam3 = Family(partner1_id=robert.id, partner2_id=linda.id)
    db.session.add_all([fam1, fam2, fam3])
    db.session.flush()

    db.session.add_all([
        FamilyChild(family_id=fam1.id, child_id=john.id,
                    pedigree_type="birth", child_order=0),
        # F2's three children show off pedigree_type: a birth child, another
        # birth child, and an adopted child — all equally real children.
        FamilyChild(family_id=fam2.id, child_id=robert.id,
                    pedigree_type="birth", child_order=0),
        FamilyChild(family_id=fam2.id, child_id=evelyn.id,
                    pedigree_type="birth", child_order=1),
        FamilyChild(family_id=fam2.id, child_id=samuel.id,
                    pedigree_type="adopted", child_order=2),
        FamilyChild(family_id=fam3.id, child_id=maya.id,
                    pedigree_type="birth", child_order=0),
    ])

    # ------------------------------------------------------------------ EVENTS
    # date_original is shown to humans EXACTLY as recorded; date_sort is the
    # normalized, sortable shadow (unknown month/day -> "00"). Both stored.
    events = [
        # Individual events (subject_type = 'individual')
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=wilhelmina.id,
              event_tag="BIRT", date_original="ABT 1850", date_sort="1850-00-00",
              place_id=amsterdam.id),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=wilhelmina.id,
              event_tag="IMMI", date_original="1871", date_sort="1871-00-00",
              place_id=spring_hill.id),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=wilhelmina.id,
              event_tag="DEAT", date_original="3 FEB 1923", date_sort="1923-02-03",
              place_id=spring_hill.id, age="72y", cause="Pneumonia"),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=thomas.id,
              event_tag="BIRT", date_original="1848", date_sort="1848-00-00"),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=john.id,
              event_tag="BIRT", date_original="14 MAR 1872", date_sort="1872-03-14",
              place_id=spring_hill.id),
        # An ATTRIBUTE (occupation) — same table, value in event_value.
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=john.id,
              event_tag="OCCU", event_value="Blacksmith", date_original="1900",
              date_sort="1900-00-00", place_id=spring_hill.id),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=robert.id,
              event_tag="BIRT", date_original="March 1962", date_sort="1962-03-00",
              place_id=nashville.id),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=evelyn.id,
              event_tag="BIRT", date_original="10 APR 1965", date_sort="1965-04-10",
              place_id=nashville.id),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=samuel.id,
              event_tag="BIRT", date_original="ABT 1968", date_sort="1968-00-00"),
        Event(subject_type=SUBJECT_INDIVIDUAL, subject_id=maya.id,
              event_tag="BIRT", date_original="22 JUL 2014", date_sort="2014-07-22",
              place_id=chicago.id),
        # Family events (subject_type = 'family') — marriages.
        Event(subject_type=SUBJECT_FAMILY, subject_id=fam1.id,
              event_tag="MARR", date_original="ABT 1870", date_sort="1870-00-00",
              place_id=spring_hill.id),
        Event(subject_type=SUBJECT_FAMILY, subject_id=fam2.id,
              event_tag="MARR", date_original="June 1895", date_sort="1895-06-00",
              place_id=nashville.id),
    ]
    db.session.add_all(events)
    db.session.flush()
    john_birth = events[4]   # referenced by a citation below
    john_occu = events[5]    # referenced by a note below

    # ----------------------------------------------------- SOURCES & CITATIONS
    archive = Repository(
        name="Tennessee State Library and Archives",
        address="1001 Rep. John Lewis Way N, Nashville, TN",
        website="https://sos.tn.gov/tsla",
    )
    db.session.add(archive)
    db.session.flush()
    census = Source(
        title="1880 United States Federal Census",
        author="U.S. Census Bureau", publication="NARA microfilm",
        repository_id=archive.id,
    )
    bible = Source(title="Hartwell Family Bible", author="Hartwell family")
    db.session.add_all([census, bible])
    db.session.flush()

    # Citations exercise ALL FOUR polymorphic subject kinds: event, individual,
    # name, family.
    margaret_maiden = next(n for n in margaret.names if n.name_type == "birth")
    db.session.add_all([
        Citation(source_id=census.id, subject_type=SUBJECT_EVENT,
                 subject_id=john_birth.id, page="p. 42, dwelling 17",
                 quality=3, notes="Birth year confirmed by census age."),
        Citation(source_id=census.id, subject_type=SUBJECT_INDIVIDUAL,
                 subject_id=wilhelmina.id, page="p. 42, line 3", quality=2),
        Citation(source_id=bible.id, subject_type=SUBJECT_NAME,
                 subject_id=margaret_maiden.id,
                 page="flyleaf", quality=2,
                 notes="Maiden-name spelling 'O'Sullivan' per the family bible."),
        Citation(source_id=bible.id, subject_type=SUBJECT_FAMILY,
                 subject_id=fam2.id, page="marriages page", quality=2),
    ])

    # ------------------------------------------------------- MEDIA + LINKS
    # Placeholder photos (file_path points where WP2's upload pipeline will put
    # the real bytes — outside the web root). Linked to people, a family, and an
    # event, so all three media-link subject kinds are exercised.
    portrait = MediaObject(
        title="Hartwell family portrait", description="Studio portrait, Nashville.",
        file_path="media/placeholder/hartwell-portrait-1905.jpg",
        media_type="image/jpeg", uploaded_by=author_id,
    )
    farm = MediaObject(
        title="Robert at the Spring Hill farm",
        file_path="media/placeholder/robert-farm.jpg",
        media_type="image/jpeg", uploaded_by=author_id,
    )
    db.session.add_all([portrait, farm])
    db.session.flush()
    db.session.add_all([
        MediaLink(media_id=portrait.id, subject_type=SUBJECT_INDIVIDUAL, subject_id=john.id),
        MediaLink(media_id=portrait.id, subject_type=SUBJECT_FAMILY, subject_id=fam2.id),
        MediaLink(media_id=farm.id, subject_type=SUBJECT_INDIVIDUAL, subject_id=robert.id),
        MediaLink(media_id=farm.id, subject_type=SUBJECT_EVENT, subject_id=john_occu.id),
    ])

    # ------------------------------------------------------- NOTES + LINKS
    # Markdown bios/memories. Linked to an individual, a family, and an event —
    # the third polymorphic link kind, all three subject types covered.
    crossing = Note(
        title="The crossing",
        content=("## The crossing\n\n**Wilhelmina** sailed from Amsterdam in "
                 "1871, nineteen years old, with a single trunk and her mother's "
                 "thimble. Family lore says she could already mend a sail."),
        content_type="markdown", author_id=author_id,
    )
    blacksmith = Note(
        title="The blacksmith of Spring Hill",
        content=("John — *Jack* to everyone — kept the only forge in town for "
                 "forty years. Half the gates in Maury County still swing on his "
                 "hinges."),
        content_type="markdown", author_id=author_id,
    )
    town = Note(
        title="Spring Hill, Tennessee",
        content="A shared note about the town where the family put down roots.",
        content_type="markdown", is_shared=True, author_id=author_id,
    )
    db.session.add_all([crossing, blacksmith, town])
    db.session.flush()
    db.session.add_all([
        NoteLink(note_id=crossing.id, subject_type=SUBJECT_INDIVIDUAL, subject_id=wilhelmina.id),
        NoteLink(note_id=blacksmith.id, subject_type=SUBJECT_INDIVIDUAL, subject_id=john.id),
        NoteLink(note_id=blacksmith.id, subject_type=SUBJECT_EVENT, subject_id=john_occu.id),
        NoteLink(note_id=town.id, subject_type=SUBJECT_FAMILY, subject_id=fam1.id),
    ])

    db.session.commit()

    # Counts prove what landed — the test asserts against these.
    return {
        "individuals": Individual.query.count(),
        "names": Name.query.count(),
        "families": Family.query.count(),
        "family_children": FamilyChild.query.count(),
        "places": Place.query.count(),
        "events": Event.query.count(),
        "repositories": Repository.query.count(),
        "sources": Source.query.count(),
        "citations": Citation.query.count(),
        "media_objects": MediaObject.query.count(),
        "media_links": MediaLink.query.count(),
        "notes": Note.query.count(),
        "note_links": NoteLink.query.count(),
    }
