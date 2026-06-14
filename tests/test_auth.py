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
    "/about", "/site/hero", "/search", "/auth/change-password",
    "/apidocs", "/openapi.yaml", "/activity", "/plans", "/plans/new",
    "/admin/users", "/admin/settings", "/admin/backups",
]


def test_home_is_public_but_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log In" in response.data
    # The public landing page DESCRIBES features (a "what's inside" strip)
    # but exposes zero real family content — no albums, posts, names, or
    # the logged-in dashboard's navigation links.
    assert b"Welcome to FamilyHub" in response.data
    assert b"family only" in response.data  # the privacy reassurance footer
    # No actual family content / member-only nav for anonymous visitors.
    assert b"What's New" not in response.data
    assert b"Log Out" not in response.data


def test_skip_link_is_present(client):
    """Accessibility: the skip-to-content link and its target exist on
    every page (keyboard users jump past the navbar)."""
    response = client.get("/")
    assert b"Skip to main content" in response.data
    assert b'id="main-content"' in response.data


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


def test_change_own_password(client, admin):
    """Self-service: wrong current password changes nothing; the right one
    changes it for real (provable by logging in with the new password)."""
    client.post("/auth/login",
                data={"username": "admin", "password": ADMIN_PASSWORD})

    # Wrong current password -> rejected, old password still works.
    response = client.post(
        "/auth/change-password",
        data={"current_password": "not-my-password",
              "password": "BrandNewPass1", "confirm": "BrandNewPass1"},
        follow_redirects=True,
    )
    assert b"isn&#39;t right" in response.data

    # Right current password -> changed.
    response = client.post(
        "/auth/change-password",
        data={"current_password": ADMIN_PASSWORD,
              "password": "BrandNewPass1", "confirm": "BrandNewPass1"},
        follow_redirects=True,
    )
    assert b"password is changed" in response.data

    # The proof: log out, log back in with the NEW password.
    client.post("/auth/logout")
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "BrandNewPass1"},
        follow_redirects=True,
    )
    assert b"Welcome back" in response.data


def test_login_rate_limit_fires(tmp_path):
    """The one test that turns rate limiting back ON (same pattern as the
    CSRF test above): 10 rapid login attempts pass, the 11th gets a polite
    429 'please wait' page instead of another crack at the password."""
    from app import create_app
    from app.config import Config
    from app.extensions import db

    class RateLimitConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "rl.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "uploads_rl")
        BACKUP_FOLDER = str(tmp_path / "backups_rl")
        EXPORT_FOLDER = str(tmp_path / "export_rl")
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = True

    rl_app = create_app(RateLimitConfig)
    with rl_app.app_context():
        db.create_all()

    client = rl_app.test_client()
    bad_guess = {"username": "robot", "password": "guess-attempt"}
    statuses = [
        client.post("/auth/login", data=bad_guess).status_code
        for _ in range(11)
    ]
    assert statuses[:10] == [200] * 10, "a fumbling human is never blocked"
    assert statuses[10] == 429, "the robot's 11th try hits the brake"

    # And the brake page is friendly, not a bare error dump.
    response = client.post("/auth/login", data=bad_guess)
    assert b"wait" in response.data.lower()
