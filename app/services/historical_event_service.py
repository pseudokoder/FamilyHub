"""historical_event_service — the timeline's almanac backdrop.

WHAT THIS IS (Master Plan v2.0.0 §4; design session 2026-07-03): a small, curated
list of world/US events the Timeline view blends in for CONTEXT — "Grandpa born
1929" reads richer beside "1929 — the Wall Street Crash." This is static
REFERENCE data, identical for every family, so it lives in its own table
(``historical_events``) seeded from the bundled ``DEFAULT_EVENTS`` list below —
never mixed into the private, per-person ``events`` table.

Layered architecture (CLAUDE.md): routes call these functions; the DATASET is the
one place the almanac is defined, so extending it is a one-list edit.

v2 mapping: a ``HistoricalEventService`` reading a table seeded by a Flyway
repeatable migration, or the Angular timeline merging a shipped JSON asset.
"""

from app.extensions import db
from app.models import HistoricalEvent

SCOPES = {"US", "world"}

# The bundled almanac. Kept deliberately short and high-signal — enough to give a
# multi-generation American family timeline texture without turning into a history
# textbook. ``date_sort`` is filled only where a to-the-day date helps interleave
# with dated family events. Extend this list to grow the backdrop; re-run
# ``flask seed-historical`` (idempotent) to load additions into an empty table.
DEFAULT_EVENTS = [
    (1861, "1861-04-12", "American Civil War begins", "Fort Sumter is fired upon.", "US"),
    (1865, "1865-04-09", "American Civil War ends", "Lee surrenders at Appomattox.", "US"),
    (1869, "1869-05-10", "Transcontinental Railroad completed", "The golden spike is driven at Promontory Summit.", "US"),
    (1876, None, "Telephone patented", "Alexander Graham Bell is granted the telephone patent.", "US"),
    (1886, "1886-10-28", "Statue of Liberty dedicated", "A gift from France is unveiled in New York Harbor.", "US"),
    (1898, None, "Spanish–American War", "The U.S. emerges as an overseas power.", "US"),
    (1901, None, "Queen Victoria dies", "The Victorian era ends after 63 years.", "world"),
    (1903, "1903-12-17", "First powered flight", "The Wright brothers fly at Kitty Hawk.", "US"),
    (1906, "1906-04-18", "San Francisco earthquake", "A quake and fire devastate the city.", "US"),
    (1912, "1912-04-15", "RMS Titanic sinks", "The liner goes down on its maiden voyage.", "world"),
    (1914, None, "World War I begins", "War breaks out across Europe.", "world"),
    (1918, "1918-11-11", "World War I ends", "The Armistice is signed.", "world"),
    (1918, None, "Influenza pandemic", "The 'Spanish flu' spreads worldwide.", "world"),
    (1920, "1920-08-18", "U.S. women win the vote", "The 19th Amendment is ratified.", "US"),
    (1929, "1929-10-29", "Wall Street Crash", "'Black Tuesday' begins the Great Depression.", "US"),
    (1933, None, "New Deal begins", "Roosevelt's recovery programs launch.", "US"),
    (1939, None, "World War II begins", "Germany invades Poland.", "world"),
    (1941, "1941-12-07", "Attack on Pearl Harbor", "The U.S. enters World War II.", "US"),
    (1945, "1945-09-02", "World War II ends", "Japan formally surrenders.", "world"),
    (1955, None, "Montgomery Bus Boycott", "The U.S. civil-rights movement gathers force.", "US"),
    (1963, "1963-11-22", "President Kennedy assassinated", "JFK is killed in Dallas.", "US"),
    (1969, "1969-07-20", "First Moon landing", "Apollo 11 lands; Armstrong walks on the Moon.", "US"),
    (1989, "1989-11-09", "Berlin Wall falls", "The divide between East and West Germany opens.", "world"),
    (1991, None, "Soviet Union dissolves", "The Cold War ends.", "world"),
    (2001, "2001-09-11", "September 11 attacks", "Coordinated attacks strike the United States.", "US"),
    (2008, None, "Global financial crisis", "A worldwide recession takes hold.", "world"),
    (2020, None, "COVID-19 pandemic", "A novel coronavirus spreads worldwide.", "world"),
]


def serialize(event):
    """The JSON shape of one almanac entry (the contract)."""
    return {
        "id": event.id,
        "year": event.year,
        "date_sort": event.date_sort,
        "title": event.title,
        "description": event.description,
        "scope": event.scope,
    }


def list_events(scope=None, year_from=None, year_to=None):
    """Almanac entries, oldest first, optionally filtered by scope and/or an
    inclusive year range — the shape the Timeline view blends in."""
    query = HistoricalEvent.query
    if scope:
        query = query.filter(HistoricalEvent.scope == scope)
    if year_from is not None:
        query = query.filter(HistoricalEvent.year >= year_from)
    if year_to is not None:
        query = query.filter(HistoricalEvent.year <= year_to)
    ordered = query.order_by(HistoricalEvent.year, HistoricalEvent.id).all()
    return [serialize(e) for e in ordered]


def seed_defaults():
    """Load the bundled almanac into an empty table. IDEMPOTENT: does nothing if
    any rows already exist, so it's safe to run on every deploy. Returns the
    number of rows inserted (0 if already populated)."""
    if HistoricalEvent.query.first() is not None:
        return 0
    db.session.add_all([
        HistoricalEvent(year=year, date_sort=date_sort, title=title,
                        description=description, scope=scope)
        for (year, date_sort, title, description, scope) in DEFAULT_EVENTS
    ])
    db.session.commit()
    return len(DEFAULT_EVENTS)
