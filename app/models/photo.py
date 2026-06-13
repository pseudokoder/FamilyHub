"""Photo album models: Album, Photo, PhotoComment.

THE GOLDEN RULE OF FILE UPLOADS (D426 Data Management): the database stores
*metadata about* files, never the files themselves. The actual image bytes
live on disk in UPLOAD_FOLDER (outside the web root, outside git); these
tables remember where each file is, who uploaded it, and what was said about
it. The nightly backup grabs both halves — DB and files — together.

Three tables, classic one-to-many chains:

    users 1--* albums 1--* photos 1--* photo_comments

v2 mapping: three @Entity classes with @OneToMany/@ManyToOne — this is the
exact relationship homework from D287/D288.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import LockableMixin


class Album(LockableMixin, db.Model):
    """A photo album — 'Thanksgiving 1987', 'The Las Vegas Trip', ...

    LockableMixin: once an admin locks an album, only an admin can delete
    it (see mixins.py for the whole Trial Period story)."""

    __tablename__ = "albums"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    # Foreign key = the relational glue (D426: this is how tables reference
    # each other without duplicating data). Every album knows its creator.
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # relationship() is the ORM's superpower: `album.photos` gives a Python
    # list, `photo.album` gives the parent — no SQL by hand.
    # cascade="all, delete-orphan": deleting an album deletes its photo ROWS
    # too (the service layer deletes the files — the DB can't reach the disk).
    photos = db.relationship(
        "Photo",
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="Photo.position, Photo.id",
    )
    # foreign_keys= is REQUIRED now: created_by and locked_by both point at
    # users, and SQLAlchemy won't guess which one "creator" means.
    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def cover_photo(self):
        """First photo doubles as the album cover. DESIGN DECISION (DEVDIARY):
        no cover_photo_id column — a computed property keeps the schema
        simpler and can become a real column later without data loss."""
        return self.photos[0] if self.photos else None

    def __repr__(self):
        return f"<Album {self.title!r}>"


class Photo(LockableMixin, db.Model):
    """One uploaded photo: where it lives on disk + everything about it."""

    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    # index=True: "show me this album's photos" is THE hot query here.
    album_id = db.Column(
        db.Integer, db.ForeignKey("albums.id"), nullable=False, index=True
    )

    # The name on disk — a random UUID like 3f2a...c9.jpg. NEVER the name the
    # user gave us: uploaded filenames can collide ("IMG_0001.jpg" x 50) or
    # carry path tricks like "..\..\evil". Random names kill both problems.
    filename = db.Column(db.String(255), nullable=False)

    # ...but we keep what they called it, for humans and for the v2 export.
    original_filename = db.Column(db.String(255), nullable=False)

    caption = db.Column(db.String(500), nullable=False, default="")

    # Sort order inside the album. The drag-to-rearrange UI is deferred, but
    # the column exists NOW — adding a column later means a migration plus
    # backfilling order for every existing photo. Cheap insurance.
    position = db.Column(db.Integer, nullable=False, default=0)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    album = db.relationship("Album", back_populates="photos")
    # Two FKs to users (uploaded_by + the mixin's locked_by) -> be explicit.
    uploader = db.relationship("User", foreign_keys=[uploaded_by])
    comments = db.relationship(
        "PhotoComment",
        back_populates="photo",
        cascade="all, delete-orphan",
        order_by="PhotoComment.created_at",
    )
    # Who's in this photo (see photo_tag.py). Deleting the photo deletes
    # its tags — a tag without its photo is meaningless.
    tags = db.relationship(
        "PhotoTag",
        back_populates="photo",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Photo {self.filename} in album {self.album_id}>"


class PhotoComment(db.Model):
    """A comment under a photo — 'Is that Aunt Ruth on the left?!'"""

    __tablename__ = "photo_comments"

    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(
        db.Integer, db.ForeignKey("photos.id"), nullable=False, index=True
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    photo = db.relationship("Photo", back_populates="comments")
    author = db.relationship("User")

    def __repr__(self):
        return f"<PhotoComment {self.id} on photo {self.photo_id}>"
