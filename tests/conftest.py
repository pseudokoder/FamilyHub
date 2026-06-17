"""Shared pytest fixtures — the test suite's foundation.

TEACHING NOTE (D480 Software Design and Quality Assurance): a FIXTURE is
reusable setup. Every test that takes an `app` argument gets a fresh,
fully-wired Flask app with its own throwaway database and upload folder in
a temp directory — so tests can't pollute the real database, the real
photos, or each other. Isolation is what makes a test trustworthy.

This is also the application-factory pattern paying off (Chapter 2 said
"testability" was reason #1): create_app(TestConfig) builds a complete app
with test settings, no monkey-patching required.

Run the suite:   pytest          (from the project root)
"""

import io

import pytest
from PIL import Image
from pillow_heif import register_heif_opener

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.role import Role
from app.services import user_service

register_heif_opener()  # lets tests CREATE .heic files to upload

# WP2: accounts log in by EMAIL (Master Plan §3.5). The fixtures below mint a
# known admin and member so tests can act as each role.
ADMIN_EMAIL = "admin@test.invalid"
ADMIN_PASSWORD = "AdminPass123"
MEMBER_EMAIL = "member@test.invalid"
MEMBER_PASSWORD = "MemberPass123"
GUEST_EMAIL = "guest@test.invalid"
GUEST_PASSWORD = "GuestPass123"


@pytest.fixture
def app(tmp_path):
    """A fresh app per test: temp DB, temp uploads, temp backups."""

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        # tmp_path is pytest's built-in per-test temp directory.
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "test.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        BACKUP_FOLDER = str(tmp_path / "backups")
        EXPORT_FOLDER = str(tmp_path / "export")
        # CSRF off in tests so every POST doesn't need token-scraping
        # boilerplate. test_auth.py has a dedicated test that turns it back
        # ON and proves the protection actually fires.
        WTF_CSRF_ENABLED = False
        # bcrypt's slowness is a FEATURE in production (it throttles
        # password-guessing) and a tax in tests. 4 rounds = fast tests,
        # same code paths.
        BCRYPT_LOG_ROUNDS = 4
        # Rate limiting off in tests (it would trip on rapid-fire requests);
        # test_auth.py re-enables it in one dedicated test, same pattern
        # as CSRF above.
        RATELIMIT_ENABLED = False
        # Mail "configured" so the forgot-password feature is ON in tests —
        # but MAIL_SUPPRESS_SEND means Flask-Mail never opens a real SMTP
        # connection; mail.record_messages() captures the would-be sends.
        MAIL_SERVER = "smtp.test.invalid"
        MAIL_SUPPRESS_SEND = True
        MAIL_DEFAULT_SENDER = "familyhub@test.invalid"

    app = create_app(TestConfig)
    with app.app_context():
        # Tests exercise app behavior, not migration history — create_all
        # builds the schema straight from the models. Migrations get their
        # workout on the real dev/prod databases.
        db.create_all()

        # TEACHING NOTE — Flask 3.x changed `g` to be app-context scoped
        # rather than request-scoped. Flask-Login caches the current user in
        # `g._login_user`, so when the pytest fixture holds one app_context
        # open for the whole test, a logged-in user from request N leaks
        # into request N+1 — making anonymous clients look authenticated and
        # member clients look like admins. This before_request hook is the
        # minimal surgical fix: wipe the cache before each request so
        # Flask-Login always reloads from the session cookie. In production,
        # each request has its own short-lived app context so this never
        # arises; it is a test-only concern.
        from flask import g

        @app.before_request
        def _clear_login_user_cache():
            g.pop("_login_user", None)

        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(app):
    return user_service.create_user(
        ADMIN_EMAIL, "Admin", ADMIN_PASSWORD, role=Role.ADMIN
    )


@pytest.fixture
def member(app):
    # No role given → defaults to USER, a normal family member.
    return user_service.create_user(MEMBER_EMAIL, "Member", MEMBER_PASSWORD)


@pytest.fixture
def admin_client(client, admin):
    """A test client already logged in as the admin."""
    client.post(
        "/auth/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    return client


@pytest.fixture
def member_client(app, member):
    """A SECOND client, logged in as a regular member — for permission
    tests ('a member may not do an admin-only thing')."""
    other = app.test_client()
    other.post(
        "/auth/login", data={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD}
    )
    return other


@pytest.fixture
def guest(app):
    """The lowest rung of the role ladder (§10) — can read, but not write."""
    return user_service.create_user(
        GUEST_EMAIL, "Guest", GUEST_PASSWORD, role=Role.GUEST
    )


@pytest.fixture
def guest_client(app, guest):
    other = app.test_client()
    other.post(
        "/auth/login", data={"email": GUEST_EMAIL, "password": GUEST_PASSWORD}
    )
    return other


# --- Sample upload files (generated, never checked into git) -------------------

def make_image(fmt="JPEG", size=(800, 600), color=(120, 80, 200), orientation=None,
               gps=False):
    """An in-memory image file, ready to 'upload' through the test client.

    orientation=6 simulates a phone held sideways (EXIF rotation tag) —
    exactly what iPhones produce in portrait mode. gps=True embeds GPS
    coordinates the way a real phone camera does, so tests can prove the
    upload pipeline strips them (the privacy rule in photo_service).
    """
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    kwargs = {}
    if orientation or gps:
        exif = Image.Exif()
        if orientation:
            exif[274] = orientation  # 274 = the EXIF Orientation tag id
        if gps:
            # 0x8825 is the GPS sub-directory pointer inside EXIF. These are
            # the exact tags a phone writes: hemisphere refs + lat/long as
            # (degrees, minutes, seconds) rationals.
            exif[0x8825] = {1: "N", 2: (40.0, 26.0, 46.3),
                            3: "W", 4: (79.0, 58.0, 56.0)}
        kwargs["exif"] = exif
    img.save(buf, fmt, **kwargs)
    buf.seek(0)
    return buf


def make_fake_image():
    """Text bytes wearing a .jpg name — must be rejected by content checks."""
    return io.BytesIO(b"I am definitely not a photograph.")
