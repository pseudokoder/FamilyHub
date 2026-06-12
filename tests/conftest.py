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
from app.services import user_service

register_heif_opener()  # lets tests CREATE .heic files to upload

ADMIN_PASSWORD = "AdminPass123"
MEMBER_PASSWORD = "MemberPass123"


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
    return user_service.create_user("admin", "Admin", ADMIN_PASSWORD, is_admin=True)


@pytest.fixture
def member(app):
    return user_service.create_user("member", "Member", MEMBER_PASSWORD)


@pytest.fixture
def admin_client(client, admin):
    """A test client already logged in as the admin."""
    client.post(
        "/auth/login", data={"username": "admin", "password": ADMIN_PASSWORD}
    )
    return client


@pytest.fixture
def member_client(app, member):
    """A SECOND client, logged in as a regular member — for permission
    tests ('member may not delete admin's photo')."""
    other = app.test_client()
    other.post(
        "/auth/login", data={"username": "member", "password": MEMBER_PASSWORD}
    )
    return other


# --- Sample upload files (generated, never checked into git) -------------------

def make_image(fmt="JPEG", size=(800, 600), color=(120, 80, 200), orientation=None):
    """An in-memory image file, ready to 'upload' through the test client.

    orientation=6 simulates a phone held sideways (EXIF rotation tag) —
    exactly what iPhones produce in portrait mode.
    """
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    kwargs = {}
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation  # 274 = the EXIF Orientation tag id
        kwargs["exif"] = exif
    img.save(buf, fmt, **kwargs)
    buf.seek(0)
    return buf


def make_fake_image():
    """Text bytes wearing a .jpg name — must be rejected by content checks."""
    return io.BytesIO(b"I am definitely not a photograph.")
