"""Places — the GEDCOM PLAC record, reused across many events.

WHY A SEPARATE TABLE instead of a "place" text column on each event? Because
"Spring Hill, Maury, Tennessee, USA" gets typed into dozens of events — births,
marriages, burials. Storing it once and pointing every event at that single row
means: fix a spelling once and it's fixed everywhere; add map coordinates once;
and "show everything that happened in this town" becomes a simple query. That's
normalization removing duplication (WGU D426), and it's exactly why genealogy
software treats places as their own records.

v2 mapping: a `Place` `@Entity` referenced by `Event` via `@ManyToOne`.
"""

from app.extensions import db


class Place(db.Model):
    """A geographic location an event can point at — GEDCOM PLAC."""

    __tablename__ = "places"

    id = db.Column(db.Integer, primary_key=True)

    # The full, human-readable place string as a genealogist would write it,
    # most-specific-first: "Spring Hill, Maury, Tennessee, USA".
    full_name = db.Column(db.String(255))

    # The same place broken into its administrative pieces, so we can group
    # ("everyone born in Tennessee") and disambiguate (there are many
    # Springfields). Filled in when known; the full_name always works as a
    # fallback.
    city = db.Column(db.String(120))
    county = db.Column(db.String(120))
    state = db.Column(db.String(120))
    country = db.Column(db.String(120))

    # Coordinates for an eventual map view. DECIMAL(10,7) — NOT float — because
    # money and map coordinates are the classic cases where binary floating
    # point quietly loses precision; a fixed-point DECIMAL stores 7 places after
    # the point exactly (≈1 cm of latitude). Portable to MySQL's DECIMAL as-is.
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))

    def __repr__(self):
        return f"<Place #{self.id} {self.full_name!r}>"
