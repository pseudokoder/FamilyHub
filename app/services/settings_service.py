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

KNOWN_KEYS = ("tagline", "about_text", "contact_text")

# --- WP3 admin: the config-as-data settings (Master Plan §3.5 / §5 / §9) -------
#
# site_settings is key/value (see the model), so every new admin/security/branding
# knob is just a ROW with a sensible default — no migration, no new column. Each
# spec says which GROUP it belongs to, its TYPE (for coercion + validation), and
# whether it is a SECRET (secrets live in .env, never here — the SMTP *password*
# is MAIL_PASSWORD in the environment; only non-secret SMTP config lives here).
DEFAULTS = {
    # Branding / white-label — feeds the header, page titles, Chronicle masthead.
    "site_name": "FamilyHub",
    "family_name": "",
    "logo_path": "",
    # Security baseline (§9) — enforced by user_service / auth / the app factory.
    "min_password_length": "8",
    "breach_check_enabled": "false",
    "login_lockout_threshold": "10",
    "session_timeout_days": "30",
    # Email config (non-secret; the password is the MAIL_PASSWORD env secret).
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_from": "",
    # Timezone + record defaults.
    "default_timezone": "UTC",
    "tree_orientation": "vertical",     # v1 default; horizontal is a v2 toggle
    "date_format": "original",          # original | iso
    "place_format": "full",             # full | short
    "new_record_privacy": "living",     # living | public
    # Backup schedule (the actual runner is OS cron/deploy; these drive it + the
    # admin "next run" display).
    "backup_schedule": "daily",         # off | daily | weekly
    "backup_hour": "3",                 # 0-23, server local hour
}

# Type per key, so the CRUD endpoint coerces + validates instead of storing junk.
_INT_KEYS = {"min_password_length", "login_lockout_threshold",
             "session_timeout_days", "smtp_port", "backup_hour"}
_BOOL_KEYS = {"breach_check_enabled"}

# Grouping for the admin Settings UI (the FE renders one card per group).
SETTING_GROUPS = {
    "branding": ["site_name", "family_name", "logo_path"],
    "security": ["min_password_length", "breach_check_enabled",
                 "login_lockout_threshold", "session_timeout_days"],
    "email": ["smtp_host", "smtp_port", "smtp_user", "smtp_from"],
    "defaults": ["default_timezone", "tree_orientation", "date_format",
                 "place_format", "new_record_privacy"],
}

# The image types we accept for the dashboard hero banner. Defined HERE rather
# than borrowed from a photo-upload module so this preserved settings feature
# has no dependency on the (rebuilt-in-WP2) media layer — a small "depend on
# nothing you don't need" win that keeps the home page booting during the
# WP1 re-foundation.
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}

# One fixed name: a new upload simply replaces the old hero. No gallery,
# no history — it's a banner, not an archive.
HERO_FILENAME = "hero.jpg"


def get(key, default=""):
    setting = db.session.get(SiteSetting, key)
    return setting.setting_value if setting else default


def set_value(key, value):
    """Insert-or-update ("upsert") one setting."""
    setting = db.session.get(SiteSetting, key)
    if setting is None:
        setting = SiteSetting(setting_key=key)
        db.session.add(setting)
    setting.setting_value = (value or "").strip()
    db.session.commit()


def get_all():
    return {key: get(key) for key in KNOWN_KEYS}


# --- Typed accessors + defaults (WP3 admin) -----------------------------------

def _get_or_default(key):
    """The stored value, or the DEFAULTS fallback if the row was never seeded —
    so a caller always gets a usable value even before ``ensure_defaults`` runs."""
    setting = db.session.get(SiteSetting, key)
    if setting is not None and setting.setting_value != "":
        return setting.setting_value
    return DEFAULTS.get(key, "")


def get_int(key, default=0):
    try:
        return int(_get_or_default(key))
    except (TypeError, ValueError):
        return default


def get_bool(key):
    return str(_get_or_default(key)).strip().lower() in {"true", "1", "yes", "on"}


def ensure_defaults():
    """Idempotently seed every DEFAULTS key that doesn't exist yet. Safe to run on
    every deploy / first request. Returns the number of rows inserted."""
    inserted = 0
    for key, value in DEFAULTS.items():
        if db.session.get(SiteSetting, key) is None:
            db.session.add(SiteSetting(setting_key=key, setting_value=value))
            inserted += 1
    if inserted:
        db.session.commit()
    return inserted


def security_config():
    """The security baseline as live values (§9) — read by password validation,
    login lockout, and the session-timeout wiring."""
    return {
        "min_password_length": get_int("min_password_length", 8),
        "breach_check_enabled": get_bool("breach_check_enabled"),
        "login_lockout_threshold": get_int("login_lockout_threshold", 10),
        "session_timeout_days": get_int("session_timeout_days", 30),
    }


def branding():
    return {k: _get_or_default(k) for k in SETTING_GROUPS["branding"]}


def editable_settings():
    """Every admin-editable setting, grouped, as current values — for the Settings
    UI (GET). Coerces ints/bools to real JSON types so the form renders correctly."""
    out = {}
    for group, keys in SETTING_GROUPS.items():
        out[group] = {}
        for key in keys:
            if key in _INT_KEYS:
                out[group][key] = get_int(key, int(DEFAULTS.get(key, 0) or 0))
            elif key in _BOOL_KEYS:
                out[group][key] = get_bool(key)
            else:
                out[group][key] = _get_or_default(key)
    return out


def update_settings(data):
    """Apply a flat {key: value} patch of admin-editable settings (PUT). Ignores
    unknown keys, coerces + range-checks the typed ones, and returns the new
    editable view. Raises ValueError (→ 400 at the route) on a bad value."""
    editable = {k for keys in SETTING_GROUPS.values() for k in keys}
    for key, value in data.items():
        if key not in editable:
            continue
        if key in _INT_KEYS:
            try:
                num = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be a whole number.")
            if num < 0:
                raise ValueError(f"{key} can't be negative.")
            if key == "min_password_length" and num < 6:
                raise ValueError("min_password_length must be at least 6.")
            set_value(key, str(num))
        elif key in _BOOL_KEYS:
            set_value(key, "true" if str(value).strip().lower()
                      in {"true", "1", "yes", "on"} else "false")
        else:
            set_value(key, value)
    return editable_settings()


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
