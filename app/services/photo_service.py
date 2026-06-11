"""Photo business logic: albums, uploads, thumbnails, comments, deletion.

This is the most security-sensitive service in the app — file uploads are
the classic way web apps get hacked. The rules enforced here (D315):

  1. Extension allow-list  — only image types we expect, nothing else.
  2. Content verification  — Pillow must successfully parse the bytes as an
     image. Renaming virus.exe to virus.jpg fails this check.
  3. Random storage names  — a UUID, never the user's filename, so no path
     tricks ("..\\..\\windows\\...") and no collisions.
  4. Outside the web root  — UPLOAD_FOLDER is not in app/static; every view
     of a photo goes through a @login_required route.

v2 mapping: PhotoService.java (@Service) + a StorageService.
"""

import os
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError

from app.extensions import db
from app.models import Album, Photo, PhotoComment

# Formats Pillow handles well and browsers display natively. HEIC (newer
# iPhones) is deliberately NOT here yet — see "Decisions Made Without Wes".
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

# Gallery thumbnails: longest side capped at 400px. The gallery page then
# loads ~50 KB per photo instead of ~8 MB — the difference between "instant"
# and "is it broken?" on the parents' internet connection.
THUMBNAIL_MAX = (400, 400)


# --- Albums -----------------------------------------------------------------

def create_album(title, description, user):
    album = Album(
        title=title.strip(),
        description=(description or "").strip(),
        created_by=user.id,
    )
    db.session.add(album)
    db.session.commit()
    return album


def get_all_albums():
    """Newest first — the family will mostly look at recent uploads."""
    return Album.query.order_by(Album.created_at.desc()).all()


# --- Storage helpers ---------------------------------------------------------

def _album_dir(album_id):
    """uploads/photos/<album_id>/ — one folder per album keeps the disk
    browsable by a human during backup checks or disaster recovery."""
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "photos", str(album_id))
    os.makedirs(path, exist_ok=True)
    return path


def photo_paths(photo):
    """(full_path, thumb_path) on disk for a Photo row."""
    directory = _album_dir(photo.album_id)
    return (
        os.path.join(directory, photo.filename),
        os.path.join(directory, f"thumb_{photo.filename}"),
    )


# --- Uploading ----------------------------------------------------------------

def save_photos(album, files, user):
    """Save a batch of uploaded files into an album.

    Returns (saved_count, error_messages). FORGIVING by design: if Mom
    selects 10 photos and one is broken, the other 9 still make it and the
    message explains exactly which one didn't — never all-or-nothing.
    """
    saved, errors = 0, []
    # New photos go after existing ones (position column = album sort order).
    next_position = len(album.photos)

    for file in files:
        if not file or not file.filename:
            continue
        name = file.filename

        # Check 1: allowed extension. rsplit from the right so "trick.jpg.exe"
        # is judged by its REAL last extension ("exe" -> rejected).
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(
                f'"{name}" isn\'t a photo type we can use '
                f"(we accept: {', '.join(sorted(ALLOWED_EXTENSIONS))})."
            )
            continue

        # Check 2: are the BYTES really an image? Extensions are just names.
        try:
            Image.open(file.stream).verify()
        except (UnidentifiedImageError, OSError):
            errors.append(f'"{name}" doesn\'t look like a real photo file — it may be damaged.')
            continue
        # verify() consumes the stream; rewind before saving the actual bytes.
        file.stream.seek(0)

        # Random name on disk; the human name goes in the database.
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        full_path = os.path.join(_album_dir(album.id), stored_name)
        file.save(full_path)
        _make_thumbnail(full_path, ext)

        photo = Photo(
            album_id=album.id,
            filename=stored_name,
            original_filename=name[:255],
            position=next_position,
            uploaded_by=user.id,
        )
        db.session.add(photo)
        next_position += 1
        saved += 1

    # One commit for the whole batch: either the bookkeeping for all saved
    # photos lands, or none of it does (transactions, D427).
    db.session.commit()
    return saved, errors


def _make_thumbnail(full_path, ext):
    """Write thumb_<name> next to the original, longest side <= 400px."""
    directory, name = os.path.split(full_path)
    thumb_path = os.path.join(directory, f"thumb_{name}")
    try:
        img = Image.open(full_path)
        # thumbnail() keeps the aspect ratio — no squashed grandchildren.
        img.thumbnail(THUMBNAIL_MAX)
        if ext in ("jpg", "jpeg") and img.mode != "RGB":
            # JPEG can't store transparency; flatten exotic modes first.
            img = img.convert("RGB")
        img.save(thumb_path)
    except OSError:
        # No thumbnail is a cosmetic problem, not a lost photo: the serving
        # route falls back to the original if the thumb file is missing.
        current_app.logger.warning("Thumbnail failed for %s", full_path)


# --- Comments & deletion --------------------------------------------------------

def add_comment(photo, user, body):
    comment = PhotoComment(photo_id=photo.id, author_id=user.id, body=body.strip())
    db.session.add(comment)
    db.session.commit()
    return comment


def can_delete(photo, user):
    """Rule in ONE place: you can delete a photo if you uploaded it, or
    you're an admin. Routes ask this function — they don't re-invent it."""
    return user.is_admin or photo.uploaded_by == user.id


def delete_photo(photo):
    """Remove the photo's files AND its database row.

    Files first: if the disk delete fails we haven't lost the bookkeeping,
    and a re-run can finish the job. (Order matters in cleanup code.)
    """
    full_path, thumb_path = photo_paths(photo)
    for path in (full_path, thumb_path):
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(photo)  # cascade removes its comments too
    db.session.commit()
