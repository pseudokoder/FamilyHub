"""Forgot-password flow tests: the emailed link round-trip, the privacy of the
responses, and the three ways a token must die (forged, expired — covered by
max_age, and already-used).

WP2 note: email is now the login key, so every account always has one — the old
"account without an email" case no longer exists and its test is retired.
"""

import re

from app.extensions import mail
from app.services import user_service


def test_full_reset_round_trip(app, member):
    """Request link -> email arrives -> link opens the form -> new password
    works at the login page. The whole story, driven by an anonymous visitor
    (a logged-in browser gets bounced off these pages by design)."""
    anon = app.test_client()

    with mail.record_messages() as outbox:
        anon.post("/auth/forgot-password", data={"email": member.email},
                  follow_redirects=True)
    assert len(outbox) == 1
    assert outbox[0].recipients == [member.email]

    # Pull the link out of the plain-text body, exactly like a human would.
    link = re.search(r"/auth/reset-password/\S+", outbox[0].body).group(0)

    assert b"Choose a new password" in anon.get(link).data
    anon.post(link, data={"password": "FreshNewPass1",
                          "confirm": "FreshNewPass1"})

    response = anon.post(
        "/auth/login",
        data={"email": member.email, "password": "FreshNewPass1"},
        follow_redirects=True,
    )
    assert b"Welcome back" in response.data


def test_unknown_email_gets_same_message_and_no_mail(client, member):
    with mail.record_messages() as outbox:
        response = client.post(
            "/auth/forgot-password", data={"email": "not-a-real@nowhere.invalid"},
            follow_redirects=True,
        )
    assert b"on its way" in response.data, "identical message — no harvesting"
    assert len(outbox) == 0


def test_forged_token_rejected(client, member):
    response = client.get("/auth/reset-password/totally-made-up-token",
                          follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_token_is_single_use(app, member):
    """Using the link changes the password — which invalidates the hash
    fragment inside the token. The same link a second time: dead."""
    anon = app.test_client()
    with app.test_request_context():
        token = user_service.generate_reset_token(member)

    anon.post(f"/auth/reset-password/{token}",
              data={"password": "FirstReset123", "confirm": "FirstReset123"})

    response = anon.get(f"/auth/reset-password/{token}",
                        follow_redirects=True)
    assert b"invalid or has expired" in response.data


def test_feature_hides_itself_without_mail_config(tmp_path, client):
    from app import create_app
    from app.config import Config

    class NoMailConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "nm.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "uploads_nm")
        BACKUP_FOLDER = str(tmp_path / "backups_nm")
        EXPORT_FOLDER = str(tmp_path / "export_nm")
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        MAIL_SERVER = None  # email NOT set up on this server

    nomail_app = create_app(NoMailConfig)
    nomail_client = nomail_app.test_client()

    # The login page points at a generic administrator, not at a dead feature
    # or a hardcoded personal name (ADR-0003)...
    assert b"Contact your family administrator" in nomail_client.get("/auth/login").data
    # ...and the route itself declines politely.
    response = nomail_client.get("/auth/forgot-password", follow_redirects=True)
    assert b"ask your family administrator" in response.data
