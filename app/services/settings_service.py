"""Site settings business logic: the admin-editable text + the hero image.

The known keys (one place, so typos can't invent settings):
    tagline       — one line under the welcome heading on the dashboard
    about_text    — the About page body
    contact_text  — how to reach the admin (shown on the About page)
"""

import os

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from app.extensions import db
from app.models import SiteSetting
from app.services.photo_service import ALLOWED_EXTENSIONS

KNOWN_KEYS = ("tagline", "about_text", "contact_text")

# One fixed name: a new upload simply replaces the old hero. No gallery,
# no history — it's a banner, not an archive.
HERO_FILENAME = "hero.jpg"


def get(key, default=""):
    setting = db.session.get(SiteSetting, key)
    return setting.value if setting else default


def set_value(key, value):
    """Insert-or-update ("upsert") one setting."""
    setting = db.session.get(SiteSetting, key)
    if setting is None:
        setting = SiteSetting(key=key)
        db.session.add(setting)
    setting.value = (value or "").strip()
    db.session.commit()


def get_all():
    return {key: get(key) for key in KNOWN_KEYS}


# --- Hero image ---------------------------------------------------------------

def _site_dir():
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], "site")
    os.makedirs(path, exist_ok=True)
    return path


def hero_path():
    return os.path.join(_site_dir(), HERO_FILENAME)


def hero_exists():
    return os.path.exists(hero_path())


def save_hero_image(file):
    """Validate + store the dashboard hero image. Returns an error message,
    or None on success.

    Same defense-in-depth as photo uploads (see photo_service for the full
    lesson): extension allow-list, Pillow content verification, EXIF
    rotation baked in, always re-encoded to JPEG. Re-encoding also caps the
    size: a hero loads on EVERY dashboard visit, so we shrink it to
    1600px — plenty for a banner, tiny on the wire.
    """
    name = file.filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return (
            f'"{name}" isn\'t an image type we can use '
            f"(we accept: {', '.join(sorted(ALLOWED_EXTENSIONS))})."
        )
    try:
        Image.open(file.stream).verify()
    except (UnidentifiedImageError, OSError):
        return f'"{name}" doesn\'t look like a real image file.'
    file.stream.seek(0)

    img = ImageOps.exif_transpose(Image.open(file.stream))
    img.thumbnail((1600, 1600))
    img.convert("RGB").save(hero_path(), "JPEG", quality=88)
    return None
