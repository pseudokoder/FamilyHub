"""Security-header tests: every response carries the armor.

The interesting assertion is the strict CSP: script-src 'self' with NO
'unsafe-inline' — which only works because no template carries inline
JavaScript anymore (the data-confirm refactor). The second test pins that
refactor in place forever.
"""

from tests.conftest import ADMIN_PASSWORD


def test_headers_on_every_response(client):
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp, "the whole point of the refactor"
    assert "frame-ancestors 'none'" in csp
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_hsts_only_when_https_is_on(client, app, tmp_path):
    # Local/dev (SESSION_COOKIE_SECURE off): no HSTS — it would pin
    # browsers to https on a server that doesn't speak it.
    assert "Strict-Transport-Security" not in client.get("/").headers

    from app import create_app
    from app.config import Config

    class ProdishConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "hsts.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "uploads_hsts")
        BACKUP_FOLDER = str(tmp_path / "backups_hsts")
        EXPORT_FOLDER = str(tmp_path / "export_hsts")
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        SESSION_COOKIE_SECURE = True  # "production mode"

    prod_app = create_app(ProdishConfig)
    response = prod_app.test_client().get("/health")
    assert "max-age" in response.headers["Strict-Transport-Security"]


def test_no_inline_javascript_in_rendered_pages(client, admin):
    """The CSP bans inline handlers — so none may exist. This test walks the
    surviving authenticated pages and proves the dialogs hang off data-confirm
    attributes (handled in static/js/familyhub.js), never inline onsubmit=."""
    client.post("/auth/login",
                data={"username": "admin", "password": ADMIN_PASSWORD})

    for url in ("/", "/about", "/admin/users", "/admin/settings",
                "/admin/backups", "/admin/activity"):
        page = client.get(url).data
        assert b"onsubmit=" not in page, url
        assert b"onclick=" not in page, url
        assert b"javascript:" not in page, url
