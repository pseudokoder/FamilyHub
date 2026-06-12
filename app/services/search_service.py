"""Site-wide search: one query box, every kind of family content.

TEACHING NOTE (D426 Data Management): this is plain SQL LIKE matching —
`WHERE title LIKE '%ruth%'` — wrapped by SQLAlchemy's `ilike()` so it's
case-insensitive on SQLite today AND MySQL in v2. At family scale
(hundreds of rows, not millions) a LIKE scan returns instantly, so a
search engine would be pure overkill. The scale-up path is documented
right here for v2: MySQL FULLTEXT indexes (or Elasticsearch beyond that)
would swap in *inside this service* — the route and template above it
wouldn't change a line. That's the payoff of the service layer.

v2 mapping: SearchService.java (@Service) with Spring Data JPA
`findByTitleContainingIgnoreCase(...)` query methods.
"""

from sqlalchemy import or_

from app.models import Album, FamilyMember, Photo, Post, TimelineEvent

# Cap each section so one wildly common word can't render a 500-row page.
PER_SECTION_CAP = 25


def _escape_like(term):
    """LIKE treats % and _ as wildcards. If Dad searches for "100%", he
    means the characters 1-0-0-percent, not "anything starting with 100".
    Escaping user text before it goes into the pattern keeps searches
    literal — and doubles as good injection hygiene thinking (D315), even
    though the ORM already parameterizes the query itself."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_all(query):
    """Search every content type; returns a dict of result lists.

    One function, five queries — deliberately simple. Each query says
    "any of these columns contains the term, case-insensitively".
    """
    like = f"%{_escape_like(query.strip())}%"

    def matches(*columns):
        # or_() builds "col1 LIKE x OR col2 LIKE x ..." — a match in ANY
        # searched column counts.
        return or_(*[column.ilike(like, escape="\\") for column in columns])

    return {
        "posts": (
            Post.query.filter(matches(Post.title, Post.body))
            .order_by(Post.created_at.desc()).limit(PER_SECTION_CAP).all()
        ),
        "members": (
            FamilyMember.query
            .filter(matches(FamilyMember.name, FamilyMember.location,
                            FamilyMember.bio))
            .order_by(FamilyMember.name).limit(PER_SECTION_CAP).all()
        ),
        "albums": (
            Album.query.filter(matches(Album.title, Album.description))
            .order_by(Album.created_at.desc()).limit(PER_SECTION_CAP).all()
        ),
        "photos": (
            # Captions plus the photo's ORIGINAL filename — "IMG_0042" is
            # often the only text a photo has, and people do remember it.
            Photo.query.filter(matches(Photo.caption, Photo.original_filename))
            .order_by(Photo.uploaded_at.desc()).limit(PER_SECTION_CAP).all()
        ),
        "events": (
            TimelineEvent.query
            .filter(matches(TimelineEvent.title, TimelineEvent.description))
            .order_by(TimelineEvent.year).limit(PER_SECTION_CAP).all()
        ),
    }
