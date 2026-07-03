"""media_service — photo uploads (OBJE) and where they attach.

THE MOST SECURITY-SENSITIVE SERVICE in the app: file uploads are the classic way
web apps get hacked, and family photos carry the family's location in their EXIF.
The five rules (D315), carried forward from the first build's photo pipeline:

  1. Extension allow-list  — only image types we expect.
  2. Content verification  — Pillow must parse the bytes as a real image
     (renaming virus.exe → virus.jpg fails this).
  3. Random storage names  — a UUID, never the user's filename (no path tricks).
  4. Outside the web root   — files live in UPLOAD_FOLDER, served only through a
     @login_required route, never by guessable URL.
  5. Metadata STRIPPED      — every upload is re-encoded through Pillow, which
     drops the EXIF block (including GPS). A photo should show the family, not
     map their house. exif_transpose() bakes in rotation FIRST so portraits don't
     end up sideways once the orientation tag is thrown away.

v2 mapping: a MediaService + a StorageService (@Service beans).
"""

import os
import uuid

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.extensions import db
from app.models import MediaLink, MediaObject
from app.services import genealogy_service as gs
from app.services import write_control
from app.services.api_errors import ApiError

register_heif_opener()  # teach Pillow to read iPhone HEIC/HEIF

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
CONVERT_TO_JPEG = {"heic", "heif"}          # browsers can't show HEIC → JPEG at upload
THUMBNAIL_MAX = (400, 400)                  # gallery thumbnails: ~50 KB, not ~8 MB
MEDIA_SUBJECTS = {gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY, gs.SUBJECT_EVENT}
MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def _media_dir():
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "media")
    os.makedirs(path, exist_ok=True)
    return path


def _iso(dt):
    return dt.isoformat() if dt is not None else None


# --- The upload pipeline (rules 1–5) ------------------------------------------

def _store_image(file):
    """Validate, strip, and store one uploaded image. Returns (stored_name,
    mime). Raises ApiError(400) with a friendly message on any bad input."""
    name = file.filename or ""
    # rsplit from the right so "trick.jpg.exe" is judged by its REAL extension.
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ApiError(
            f'"{name}" isn\'t an image type we accept '
            f"({', '.join(sorted(ALLOWED_EXTENSIONS))}).",
            400, fields={"file": "bad type"},
        )
    # Are the BYTES really an image? (verify() consumes the stream — rewind after.)
    try:
        Image.open(file.stream).verify()
    except (UnidentifiedImageError, OSError):
        raise ApiError(f'"{name}" doesn\'t look like a real image file.',
                       400, fields={"file": "not an image"})
    file.stream.seek(0)

    directory = _media_dir()
    if ext == "gif":
        # The one passthrough: re-encoding would flatten an animated GIF, and
        # GIF predates camera metadata — there's no EXIF/GPS block to leak.
        stored_name = f"{uuid.uuid4().hex}.gif"
        file.save(os.path.join(directory, stored_name))
    else:
        if ext in CONVERT_TO_JPEG:
            ext = "jpg"
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        full_path = os.path.join(directory, stored_name)
        img = ImageOps.exif_transpose(Image.open(file.stream))  # bake in rotation
        for meta_key in ("exif", "xmp", "XML:com.adobe.xmp"):
            img.info.pop(meta_key, None)  # belt & suspenders: drop metadata
        if ext in ("jpg", "jpeg"):
            img.convert("RGB").save(full_path, "JPEG", quality=90)
        else:
            img.save(full_path, ext.upper())
    _make_thumbnail(stored_name, ext)
    return stored_name, MIME_TYPES.get(ext, "application/octet-stream")


def _make_thumbnail(stored_name, ext):
    directory = _media_dir()
    img = Image.open(os.path.join(directory, stored_name))
    img.thumbnail(THUMBNAIL_MAX)
    thumb_path = os.path.join(directory, f"thumb_{stored_name}")
    if ext in ("jpg", "jpeg"):
        img.convert("RGB").save(thumb_path, "JPEG", quality=80)
    elif ext == "gif":
        img.save(thumb_path)
    else:
        img.save(thumb_path, ext.upper())


def disk_path(media, thumb=False):
    """Absolute path of a media object's file (or its thumbnail) on disk."""
    name = os.path.basename(media.file_path)
    if thumb:
        name = f"thumb_{name}"
    return os.path.join(_media_dir(), name)


# --- Serialization ------------------------------------------------------------

def serialize_link(link):
    return {
        "media_id": link.media_id,
        "subject_type": link.subject_type,
        "subject_id": link.subject_id,
        "subject_label": gs.subject_label(link.subject_type, link.subject_id),
    }


def serialize(media, with_links=True):
    links = [link for link in media.links if not link.is_deleted]
    data = {
        "id": media.id,
        "gedcom_xref": media.gedcom_xref,
        "file_path": media.file_path,
        "media_type": media.media_type,
        "title": media.title,
        "description": media.description,
        # When the photo was TAKEN (distinct from created_at = when uploaded).
        "capture_date": media.capture_date,
        "capture_date_sort": media.capture_date_sort,
        "uploaded_by": media.uploaded_by,
        "uploader": media.uploader.display_name if media.uploader else None,
        "created_at": _iso(media.created_at),
        # Login-walled URLs the front-end uses in <img> tags — never the raw path.
        "file_url": f"/api/media/{media.id}/file",
        "thumb_url": f"/api/media/{media.id}/thumb",
        "links_count": len(links),
    }
    if with_links:
        data["links"] = [serialize_link(link) for link in links]
    return data


# --- CRUD ---------------------------------------------------------------------

def list_all(subject_type=None, subject_id=None, order_by="uploaded"):
    """Media, newest upload first by default. Pass ``order_by="capture"`` to order
    by when the photo was TAKEN (capture_date_sort) — the album/timeline view
    (Master Plan §4). Soft-deleted objects and links are excluded (ADR-0001)."""
    if order_by == "capture":
        # NULLs (undated photos) sort last; then oldest capture first.
        ordering = (MediaObject.capture_date_sort.is_(None),
                    MediaObject.capture_date_sort.asc())
    else:
        ordering = (MediaObject.created_at.desc(),)

    query = MediaObject.query.filter(MediaObject.deleted_at.is_(None))
    if subject_type and subject_id is not None:
        query = (query.join(MediaLink)
                 .filter(MediaLink.deleted_at.is_(None),
                         MediaLink.subject_type == subject_type,
                         MediaLink.subject_id == subject_id))
    objects = query.order_by(*ordering).all()
    return [serialize(m, with_links=False) for m in objects]


def get(media_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(MediaObject, media_id, "media object"))


def create_from_upload(file, form, uploader):
    """Process an uploaded image (multipart) and create its MediaObject row.
    Title/description come from the form fields alongside the file."""
    if file is None or not file.filename:
        raise ApiError("An image file is required.", 400, fields={"file": "required"})
    stored_name, mime = _store_image(file)
    media = MediaObject(
        file_path=f"media/{stored_name}",
        media_type=mime,
        title=(form.get("title") or None),
        description=(form.get("description") or None),
        capture_date=(form.get("capture_date") or None),
        capture_date_sort=(form.get("capture_date_sort") or None),
        uploaded_by=uploader.id if uploader is not None else None,
        gedcom_xref=(form.get("gedcom_xref") or None),
    )
    db.session.add(media)
    db.session.flush()
    # Optional inline attachment, like notes ("a photo OF this person").
    if form.get("subject_type") or form.get("subject_id"):
        st, sid = gs.require_subject(
            form.get("subject_type"),
            int(form.get("subject_id")) if form.get("subject_id") else None,
            MEDIA_SUBJECTS,
        )
        db.session.add(MediaLink(media_id=media.id, subject_type=st, subject_id=sid))
    write_control.log_create("media", media)
    db.session.commit()
    return serialize(media)


def update(media_id, data):
    """Update the metadata only — the image bytes are immutable once stored
    (re-uploading is a new object). Keeps the strip-on-upload guarantee simple."""
    from app.routes.api import get_or_404
    media = get_or_404(MediaObject, media_id, "media object")
    before = write_control.snapshot(media)
    for field in ("title", "description", "gedcom_xref",
                  "capture_date", "capture_date_sort"):
        if field in data:
            setattr(media, field, data.get(field) or None)
    write_control.log_update("media", media, before)
    db.session.commit()
    return serialize(media)


def delete(media_id):
    from app.routes.api import get_or_404
    media = get_or_404(MediaObject, media_id, "media object")
    # SOFT delete + audit (ADR-0001). We deliberately DO NOT remove the files from
    # disk — a soft delete must be recoverable, so the bytes stay put (hidden from
    # reads) until a restore/revert, or a future hard-purge task reclaims space.
    write_control.soft_delete("media", media)


def add_link(media_id, data):
    from app.routes.api import get_or_404
    media = get_or_404(MediaObject, media_id, "media object")
    st, sid = gs.require_subject(
        data.get("subject_type"), data.get("subject_id"), MEDIA_SUBJECTS
    )
    existing = db.session.get(MediaLink, (media.id, st, sid))
    if existing is not None and not existing.is_deleted:
        raise ApiError("This photo is already attached there.", 409,
                       fields={"subject_id": "already linked"})
    if existing is not None:
        existing.deleted_at = None      # restore a previously-removed attachment
        link = existing
    else:
        link = MediaLink(media_id=media.id, subject_type=st, subject_id=sid)
        db.session.add(link)
    write_control.log_action("update", "media", media.id,
                             detail=f"attach {st} #{sid}")
    db.session.commit()
    return serialize_link(link)


def remove_link(media_id, subject_type, subject_id):
    from datetime import datetime, timezone
    link = db.session.get(MediaLink, (media_id, subject_type, subject_id))
    if link is None or link.is_deleted:
        raise ApiError("That attachment doesn't exist.", 404)
    link.deleted_at = datetime.now(timezone.utc)  # soft delete the attachment
    write_control.log_action("update", "media", media_id,
                             detail=f"detach {subject_type} #{subject_id}")
    db.session.commit()
