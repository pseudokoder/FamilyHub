"""WP3 admin Phase 4 — admin actions (users, email, settings, backups, matrix)."""

from app.extensions import db, mail
from app.models import User
from app.services import user_service
from tests.conftest import ADMIN_PASSWORD, MEMBER_EMAIL, MEMBER_PASSWORD


# --- Users list ---------------------------------------------------------------

def test_admin_users_list_shows_role_and_link(admin_client, member):
    rows = admin_client.get("/api/admin/users").get_json()["users"]
    me = next(r for r in rows if r["id"] == member.id)
    assert me["role"] == "contributor"
    assert me["linked"] is False and me["email_verified"] is False


def test_users_list_is_admin_only(member_client):
    assert member_client.get("/api/admin/users").status_code == 403


# --- Admin reset-password (email flow) ----------------------------------------

def test_admin_reset_password_emails_a_link(admin_client, member):
    with mail.record_messages() as outbox:
        resp = admin_client.post(f"/api/admin/users/{member.id}/reset-password")
    assert resp.get_json()["status"] == "reset_email_sent"
    assert len(outbox) == 1 and "reset" in outbox[0].subject.lower()


# --- Admin change-email (secure flow + step-up) -------------------------------

def test_change_email_requires_step_up(admin_client, member):
    resp = admin_client.post(
        f"/api/admin/users/{member.id}/change-email",
        json={"new_email": "new@test.invalid", "current_password": "WRONG"})
    assert resp.status_code == 403


def test_change_email_full_flow(admin_client, member):
    with mail.record_messages() as outbox:
        resp = admin_client.post(
            f"/api/admin/users/{member.id}/change-email",
            json={"new_email": "moved@test.invalid",
                  "current_password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    fresh = db.session.get(User, member.id)
    assert fresh.email == "moved@test.invalid"
    assert fresh.email_verified is False
    # BOTH addresses notified + verification + reset were sent.
    assert len(outbox) >= 4
    # Forced reset: the old password no longer works (it was scrambled).
    assert user_service.authenticate("moved@test.invalid", MEMBER_PASSWORD) is None


# --- Settings CRUD ------------------------------------------------------------

def test_settings_get_and_put(admin_client):
    grouped = admin_client.get("/api/settings").get_json()
    assert "security" in grouped and "branding" in grouped

    admin_client.put("/api/settings",
                     json={"site_name": "The Hartwells", "min_password_length": 10})
    after = admin_client.get("/api/settings").get_json()
    assert after["branding"]["site_name"] == "The Hartwells"
    assert after["security"]["min_password_length"] == 10
    # Validation: a too-short minimum is rejected.
    assert admin_client.put("/api/settings",
                            json={"min_password_length": 3}).status_code == 400


def test_settings_are_admin_only(member_client):
    assert member_client.get("/api/settings").status_code == 403


# --- Backups ------------------------------------------------------------------

def test_backup_overview_and_run(admin_client):
    admin_client.post("/api/admin/backups/run")
    overview = admin_client.get("/api/admin/backups").get_json()
    assert overview["backups"]  # at least the one we just made
    assert overview["disk_free_bytes"] is not None
    assert overview["schedule"] in ("off", "daily", "weekly")


def test_backup_schedule_update(admin_client):
    resp = admin_client.put("/api/admin/backups/schedule",
                            json={"schedule": "weekly", "hour": 4})
    body = resp.get_json()
    assert body["schedule"] == "weekly" and body["schedule_hour"] == 4
    assert body["next_run"] is not None
    assert admin_client.put("/api/admin/backups/schedule",
                            json={"schedule": "hourly"}).status_code == 400


def test_guarded_restore(admin_client):
    made = admin_client.post("/api/admin/backups/run").get_json()["filename"]
    # No confirm → refused.
    assert admin_client.post("/api/admin/backups/restore",
                             json={"filename": made, "current_password": ADMIN_PASSWORD,
                                   "confirm": False}).status_code == 400
    # Wrong step-up → refused.
    assert admin_client.post("/api/admin/backups/restore",
                             json={"filename": made, "current_password": "nope",
                                   "confirm": True}).status_code == 403
    # Confirmed + step-up → restores and reports the auto safety backup.
    ok = admin_client.post("/api/admin/backups/restore",
                           json={"filename": made, "current_password": ADMIN_PASSWORD,
                                 "confirm": True})
    assert ok.status_code == 200
    assert ok.get_json()["safety_backup"]


# --- Permission matrix --------------------------------------------------------

def test_permission_matrix(admin_client):
    body = admin_client.get("/api/permissions/matrix").get_json()
    assert set(body["matrix"]) == {"viewer", "contributor", "curator", "admin"}
    assert body["matrix"]["admin"]["administer"] is True
    assert body["matrix"]["viewer"]["contribute"] is False
