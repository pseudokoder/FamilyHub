"""WP3 admin Phase 3 — suggestions inbox + role-change requests."""

from app.extensions import db
from app.models import User


# --- Suggestions --------------------------------------------------------------

def test_member_submits_admin_triages(member_client, admin_client):
    created = member_client.post("/api/suggestions", json={
        "topic": "idea", "body": "Add a map of where everyone lived"})
    assert created.status_code == 201
    sid = created.get_json()["id"]

    # Members can't see the inbox; admins can.
    assert member_client.get("/api/suggestions").status_code == 403
    inbox = admin_client.get("/api/suggestions").get_json()["suggestions"]
    assert any(s["id"] == sid for s in inbox)

    # Triage: set status + priority, then read the prioritized queue.
    admin_client.put(f"/api/suggestions/{sid}",
                     json={"status": "in_progress", "priority": 1})
    queue = admin_client.get("/api/suggestions?prioritized=true").get_json()["suggestions"]
    assert queue[0]["id"] == sid and queue[0]["priority"] == 1


def test_suggestion_validation(member_client):
    assert member_client.post("/api/suggestions",
                              json={"topic": "idea", "body": "  "}).status_code == 400
    assert member_client.post("/api/suggestions",
                              json={"topic": "nonsense", "body": "x"}).status_code == 400


# --- Role-change requests -----------------------------------------------------

def test_role_request_approve_applies_role(member_client, admin_client, member):
    req = member_client.post("/api/role-requests", json={"requested_role": "curator"})
    assert req.status_code == 201
    rid = req.get_json()["id"]

    # A second pending request is refused.
    assert member_client.post("/api/role-requests",
                              json={"requested_role": "admin"}).status_code == 409

    approved = admin_client.post(f"/api/role-requests/{rid}/approve")
    assert approved.status_code == 200
    assert approved.get_json()["status"] == "approved"
    # The role change actually took effect (through the audited user_service).
    assert db.session.get(User, member.id).role == "curator"


def test_role_request_deny_leaves_role(member_client, admin_client, member):
    rid = member_client.post(
        "/api/role-requests", json={"requested_role": "admin"}).get_json()["id"]
    admin_client.post(f"/api/role-requests/{rid}/deny")
    assert db.session.get(User, member.id).role == "contributor"  # unchanged
    # A decided request can't be decided again.
    assert admin_client.post(f"/api/role-requests/{rid}/approve").status_code == 409


def test_role_request_rejects_noop_and_bad_role(member_client):
    # Requesting your current role is a no-op → 400.
    assert member_client.post("/api/role-requests",
                              json={"requested_role": "contributor"}).status_code == 400
    assert member_client.post("/api/role-requests",
                              json={"requested_role": "wizard"}).status_code == 400


def test_only_admin_lists_and_decides(member_client):
    assert member_client.get("/api/role-requests").status_code == 403
    assert member_client.post("/api/role-requests/1/approve").status_code == 403
