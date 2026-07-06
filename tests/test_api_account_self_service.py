"""Account self-service (FE-5 gap run): /api/me, /api/me/contributions,
/api/me/change-email, /api/me/delete.

Four member-facing capabilities the FE-5 "My Contributions" dashboard + Account
& Security page need — none of which existed before this session. See
BLOCKERS.md / DEVDIARY_BE.md for the brief.
"""

import re
from urllib.parse import urlparse

from app.extensions import db, mail
from app.models import User
from app.models.role import Role
from app.services import user_service
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, MEMBER_EMAIL, MEMBER_PASSWORD


def _verify_url_from(outbox):
    body = outbox[-1].body
    match = re.search(r"https?://\S+", body)
    assert match, f"no link found in email body: {body!r}"
    return urlparse(match.group(0)).path


# --- GET/PUT /api/me ------------------------------------------------------------

def test_me_snapshot_shape(member_client, member):
    data = member_client.get("/api/me").get_json()
    assert data["id"] == member.id
    assert data["email"] == MEMBER_EMAIL
    assert data["display_name"] == "Member"
    assert data["role"] == "contributor"
    assert data["email_verified_at"] is None
    assert data["timezone"] is None
    assert data["individual_id"] is None
    assert data["pending_email"] is None


def test_me_requires_login(client):
    assert client.get("/api/me").status_code == 401


def test_update_me_display_name_and_timezone(member_client, member):
    resp = member_client.put(
        "/api/me", json={"display_name": "Grandma Jo", "timezone": "America/Chicago"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["display_name"] == "Grandma Jo"
    assert body["timezone"] == "America/Chicago"
    fresh = db.session.get(User, member.id)
    assert fresh.display_name == "Grandma Jo"
    assert fresh.timezone == "America/Chicago"


def test_update_me_timezone_null_clears_override(member_client, member):
    member_client.put("/api/me", json={"timezone": "America/Chicago"})
    resp = member_client.put("/api/me", json={"timezone": None})
    assert resp.status_code == 200
    assert db.session.get(User, member.id).timezone is None


def test_update_me_rejects_invalid_timezone(member_client):
    resp = member_client.put("/api/me", json={"timezone": "Mars/OlympusMons"})
    assert resp.status_code == 400
    assert resp.get_json()["fields"]["timezone"] == "invalid"


def test_update_me_blank_display_name_rejected(member_client):
    resp = member_client.put("/api/me", json={"display_name": "   "})
    assert resp.status_code == 400


def test_update_me_ignores_role_and_email(member_client, member):
    resp = member_client.put(
        "/api/me", json={"role": "admin", "email": "hijack@test.invalid"})
    assert resp.status_code == 200
    fresh = db.session.get(User, member.id)
    assert fresh.role == "contributor"
    assert fresh.email == MEMBER_EMAIL


# --- GET /api/me/contributions ---------------------------------------------------

def test_contributions_own_rows_only(member_client, admin_client, member, admin):
    member_client.post("/api/individuals", json={"sex": "M"})
    admin_client.post("/api/individuals", json={"sex": "F"})

    mine = member_client.get("/api/me/contributions").get_json()
    assert mine["total"] == 1
    assert mine["activity"][0]["actor_id"] == member.id

    theirs = admin_client.get("/api/me/contributions").get_json()
    assert theirs["total"] >= 1
    assert all(row["actor_id"] == admin.id for row in theirs["activity"])


def test_contributions_ignores_actor_id_param_no_side_door(member_client, admin_client, member, admin):
    """No actor_id parameter is read here — passing one must NOT let a member
    see another member's rows. That would reopen the Curator-only trail."""
    admin_client.post("/api/individuals", json={"sex": "F"})
    resp = member_client.get(f"/api/me/contributions?actor_id={admin.id}").get_json()
    assert resp["total"] == 0


def test_contributions_filter_by_action_and_subject_type(member_client, member):
    ind = member_client.post("/api/individuals", json={"sex": "M"}).get_json()
    member_client.put(f"/api/individuals/{ind['id']}", json={"sex": "F"})

    creates = member_client.get(
        "/api/me/contributions?action=create&subject_type=individual").get_json()
    assert creates["total"] == 1
    assert creates["activity"][0]["action"] == "create"

    updates = member_client.get("/api/me/contributions?action=update").get_json()
    assert updates["total"] == 1
    assert updates["activity"][0]["action"] == "update"


def test_contributions_summary_counts(member_client, member):
    member_client.post("/api/individuals", json={"sex": "M"})
    member_client.post("/api/individuals", json={"sex": "F"})

    summary = member_client.get("/api/me/contributions").get_json()["summary"]
    assert summary["by_action"]["create"] == 2
    assert summary["by_subject_type"]["individual"] == 2


def test_contributions_requires_login(client):
    assert client.get("/api/me/contributions").status_code == 401


# --- POST /api/me/change-email --------------------------------------------------

def test_change_email_wrong_password(member_client):
    resp = member_client.post("/api/me/change-email", json={
        "new_email": "new@test.invalid", "current_password": "WRONG"})
    assert resp.status_code == 403


def test_change_email_duplicate_rejected(member_client, admin):
    resp = member_client.post("/api/me/change-email", json={
        "new_email": ADMIN_EMAIL, "current_password": MEMBER_PASSWORD})
    assert resp.status_code == 400
    assert resp.get_json()["fields"]["new_email"] == "in use"


def test_change_email_does_not_apply_until_verified(member_client, member):
    with mail.record_messages() as outbox:
        resp = member_client.post("/api/me/change-email", json={
            "new_email": "moved@test.invalid", "current_password": MEMBER_PASSWORD})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "verification_sent"
    assert body["pending_email"] == "moved@test.invalid"

    # The stored email is UNCHANGED until the link is clicked.
    fresh = db.session.get(User, member.id)
    assert fresh.email == MEMBER_EMAIL
    assert fresh.pending_email == "moved@test.invalid"
    assert len(outbox) == 1

    # GET /api/me surfaces the pending address server-side (FE-5/FE-6 sign-off
    # run: replaces FE's per-browser localStorage fallback).
    snapshot = member_client.get("/api/me").get_json()
    assert snapshot["pending_email"] == "moved@test.invalid"

    verify_path = _verify_url_from(outbox)
    member_client.get(verify_path)

    confirmed = db.session.get(User, member.id)
    assert confirmed.email == "moved@test.invalid"
    assert confirmed.pending_email is None
    assert confirmed.email_verified is True

    assert member_client.get("/api/me").get_json()["pending_email"] is None


def test_change_email_requires_mail_configured(tmp_path):
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
        BCRYPT_LOG_ROUNDS = 4
        MAIL_SERVER = None

    nomail_app = create_app(NoMailConfig)
    with nomail_app.app_context():
        db.create_all()
        m = user_service.create_user(MEMBER_EMAIL, "Member", MEMBER_PASSWORD)
        nomail_client = nomail_app.test_client()
        nomail_client.post(
            "/auth/login", data={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD})
        resp = nomail_client.post("/api/me/change-email", json={
            "new_email": "new@test.invalid", "current_password": MEMBER_PASSWORD})
        assert resp.status_code == 503
        db.session.remove()


# --- POST /api/me/delete ---------------------------------------------------------

def test_delete_wrong_password(member_client):
    assert member_client.post(
        "/api/me/delete", json={"current_password": "WRONG"}).status_code == 403


def test_delete_anonymizes_but_preserves_contributions(member_client, member):
    ind = member_client.post("/api/individuals", json={"sex": "M"}).get_json()

    resp = member_client.post(
        "/api/me/delete", json={"current_password": MEMBER_PASSWORD})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "anonymized"

    fresh = db.session.get(User, member.id)
    assert fresh.is_active is False
    assert fresh.display_name == "Former member"
    assert fresh.email != MEMBER_EMAIL
    assert fresh.individual_id is None

    # Genealogy data + the write it made are untouched.
    from app.models import Individual
    still_there = db.session.get(Individual, ind["id"])
    assert still_there is not None and still_there.deleted_at is None

    # Login is dead.
    assert user_service.authenticate(MEMBER_EMAIL, MEMBER_PASSWORD) is None

    # The audit trail still names the (now-anonymized) actor via the live
    # relationship — attributed to the neutral placeholder, never dropped.
    from app.models import AuditLog
    rows = AuditLog.query.filter_by(user_id=member.id).all()
    assert len(rows) >= 2  # the "create individual" + the "self-delete" entry
    assert all(r.user.display_name == "Former member" for r in rows)


def test_delete_blocked_for_last_active_admin(admin_client):
    resp = admin_client.post(
        "/api/me/delete", json={"current_password": ADMIN_PASSWORD})
    assert resp.status_code == 409


def test_delete_allowed_when_another_active_admin_exists(app, admin_client, admin):
    user_service.create_user(
        "second-admin@test.invalid", "Other Admin", "OtherPass123", role=Role.ADMIN)
    resp = admin_client.post(
        "/api/me/delete", json={"current_password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    assert db.session.get(User, admin.id).is_active is False


def test_delete_requires_login(client):
    assert client.post("/api/me/delete", json={}).status_code == 401
