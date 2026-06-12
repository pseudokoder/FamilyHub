"""Authentication tests: the login wall, session security, CSRF.

These encode the security PROMISES from CLAUDE.md as executable checks —
if a future change accidentally exposes family content to anonymous
visitors, this file fails the build before the family ever sees it.
"""

import pytest

from tests.conftest import ADMIN_PASSWORD

# Every family-content URL in the app. New features should add theirs here.
PROTECTED_ROUTES = [
    "/albums", "/albums/new", "/posts", "/posts/new",
    "/family", "/family/new", "/timeline", "/timeline/new",
    "/about", "/site/hero",
    "/admin/users", "/admin/settings", "/admin/backups",
]


def test_home_is_public_but_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log In" in response.data
    # No family content or navigation for anonymous visitors.
    assert b"Photo Albums" not in response.data
    assert b"Memories" not in response.data


@pytest.mark.parametrize("route", PROTECTED_ROUTES)
def test_login_wall(client, route):
    """THE PII rule: every family page bounces anonymous visitors to login."""
    response = client.get(route, follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_success(client, admin):
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": ADMIN_PASSWORD},
        follow_redirects=True,
    )
    assert b"Welcome back, Admin!" in response.data


def test_login_is_case_insensitive_on_username(client, admin):
    response = client.post(
        "/auth/login",
        data={"username": "  ADMIN ", "password": ADMIN_PASSWORD},
        follow_redirects=True,
    )
    assert b"Welcome back" in response.data


def test_login_wrong_password_is_vague(client, admin):
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=True,
    )
    # One vague message for bad user OR bad password — no username harvesting.
    assert b"don&#39;t match" in response.data
    assert b"Welcome back" not in response.data


def test_login_unknown_user_same_message(client):
    response = client.post(
        "/auth/login",
        data={"username": "nobody", "password": "whatever123"},
        follow_redirects=True,
    )
    assert b"don&#39;t match" in response.data


def test_logout_requires_post(admin_client):
    # GET /auth/logout must NOT log anyone out (state changes are POST-only).
    assert admin_client.get("/auth/logout").status_code == 405
    response = admin_client.post("/auth/logout", follow_redirects=True)
    assert b"logged out" in response.data


def test_open_redirect_blocked(client, admin):
    """?next= may only point at OUR pages — never at evil.example."""
    for evil in ("https://evil.example", "//evil.example"):
        response = client.post(
            f"/auth/login?next={evil}",
            data={"username": "admin", "password": ADMIN_PASSWORD},
            follow_redirects=False,
        )
        assert response.headers["Location"] in ("/", "http://localhost/")
        client.post("/auth/logout")


def test_safe_next_is_honored(client, admin):
    response = client.post(
        "/auth/login?next=/albums",
        data={"username": "admin", "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert response.headers["Location"].endswith("/albums")


def test_csrf_actually_fires(tmp_path, admin):
    """The one test that turns CSRF back ON: a POST without a token must be
    rejected. Proves the protection the other tests switch off for
    convenience genuinely exists."""
    from app import create_app
    from app.config import Config

    class CsrfConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "csrf.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "uploads_csrf")
        BACKUP_FOLDER = str(tmp_path / "backups_csrf")
        EXPORT_FOLDER = str(tmp_path / "export_csrf")
        WTF_CSRF_ENABLED = True

    csrf_app = create_app(CsrfConfig)
    response = csrf_app.test_client().post(
        "/auth/login", data={"username": "admin", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 400  # rejected: no CSRF token
