"""Media objects and their links — the photo album, GEDCOM-style.

THE "EVERYTHING IS A VIEW" PAYOFF (Master Plan §2/§4): there is no separate
"photos" feature with its own tables. A photo is a GEDCOM OBJE record, and the
photo album is simply *all the media objects, grouped*. The clever part is
`media_links`: one photo can be attached to a person AND the family AND the
wedding event it shows — link it three times, and it appears in all three
views. No copying, one file.

WHY SEPARATE the object from the link? Because the FILE (its path, type,
caption, who uploaded it) is one thing; WHERE it's attached is another, and a
single file attaches in many places. Object = the noun, link = the verb.

SECURITY NOTE (CLAUDE.md): `file_path` points OUTSIDE the web root. Family
photos are never served by guessing a URL — they go through a login-walled
route, so PII in a photo can't leak. Actual upload handling (validation, EXIF
stripping) returns in WP2; this table is the data shape it will write to.
"""

from app.extensions import db
from app.models.individual import _utcnow


class MediaObject(db.Model):
    """One uploaded file — GEDCOM OBJE. Photos in v1; video deferred to v2."""

    __tablename__ = "media_objects"

    id = db.Column(db.Integer, primary_key=True)
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)  # @O1@

    # Stored outside the web root (see security note above). The random on-disk
    # filename — never the user's original name — is what lives here in WP2.
    file_path = db.Column(db.String(500))
    media_type = db.Column(db.String(50))   # MIME: image/jpeg, image/png
    title = db.Column(db.String(255))
    description = db.Column(db.Text)

    # SET NULL: if an uploader's account is deleted, keep the family photo but
    # forget who uploaded it. The picture matters more than the attribution.
    uploaded_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    uploader = db.relationship("User")
    links = db.relationship(
        "MediaLink", back_populates="media", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MediaObject #{self.id} {self.title!r}>"


class MediaLink(db.Model):
    """Attaches one media object to one record — individual, family, or event.

    Polymorphic, with a COMPOSITE primary key: the triple (media, subject_type,
    subject_id) is the identity, and it doubles as a uniqueness guarantee — you
    can't attach the same photo to the same record twice.
    """

    __tablename__ = "media_links"

    media_id = db.Column(
        db.Integer, db.ForeignKey("media_objects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 'individual' | 'family' | 'event'
    subject_type = db.Column(db.String(20), primary_key=True, nullable=False)
    subject_id = db.Column(db.Integer, primary_key=True, nullable=False)

    media = db.relationship("MediaObject", back_populates="links")

    __table_args__ = (
        db.Index("ix_media_links_subject", "subject_type", "subject_id"),
    )

    def __repr__(self):
        return (f"<MediaLink media={self.media_id} "
                f"{self.subject_type}#{self.subject_id}>")
