"""WP3 Phase 2 — write-control: soft-delete, audit, restore, revert (ADR-0001).

Proves the post-moderation guarantees end to end through the JSON API: deletes are
soft and audited, a Curator can restore or revert, and the activity feed is walled
to Curator+ with working filters.
"""


def _make_person(client, given="Alma", sex="F"):
    return client.post("/api/individuals",
                       json={"sex": sex, "name": {"given": given}}).get_json()


# --- Soft delete + restore ----------------------------------------------------

def test_delete_is_soft_and_restorable(curator_client):
    person = _make_person(curator_client)
    assert curator_client.delete(f"/api/individuals/{person['id']}").status_code == 204
    # Gone from reads...
    assert curator_client.get(f"/api/individuals/{person['id']}").status_code == 404
    assert all(i["id"] != person["id"]
               for i in curator_client.get("/api/individuals").get_json()["individuals"])
    # ...but restorable.
    restored = curator_client.post(
        "/api/restore",
        json={"subject_type": "individual", "subject_id": person["id"]})
    assert restored.status_code == 200
    assert curator_client.get(f"/api/individuals/{person['id']}").status_code == 200


def test_restore_of_live_row_is_400(curator_client):
    person = _make_person(curator_client)
    resp = curator_client.post(
        "/api/restore",
        json={"subject_type": "individual", "subject_id": person["id"]})
    assert resp.status_code == 400


# --- Revert -------------------------------------------------------------------

def _latest_audit(client, action=None, subject_type=None):
    params = "?per_page=200"
    if action:
        params += f"&action={action}"
    if subject_type:
        params += f"&subject_type={subject_type}"
    return client.get(f"/api/activity{params}").get_json()["activity"]


def test_revert_an_update_restores_prior_value(curator_client):
    person = _make_person(curator_client, sex="M")
    curator_client.put(f"/api/individuals/{person['id']}", json={"sex": "F"})
    assert curator_client.get(f"/api/individuals/{person['id']}").get_json()["sex"] == "F"

    update_entry = _latest_audit(curator_client, action="update",
                                 subject_type="individual")[0]
    resp = curator_client.post(f"/api/audit/{update_entry['id']}/revert")
    assert resp.status_code == 200
    assert curator_client.get(f"/api/individuals/{person['id']}").get_json()["sex"] == "M"


def test_revert_a_create_soft_deletes_the_row(curator_client):
    person = _make_person(curator_client)
    create_entry = _latest_audit(curator_client, action="create",
                                 subject_type="individual")[0]
    assert create_entry["subject_id"] == person["id"]
    curator_client.post(f"/api/audit/{create_entry['id']}/revert")
    # Reverting a creation removes the row.
    assert curator_client.get(f"/api/individuals/{person['id']}").status_code == 404


def test_revert_missing_audit_is_404(curator_client):
    assert curator_client.post("/api/audit/999999/revert").status_code == 404


# --- The activity feed --------------------------------------------------------

def test_activity_records_create_update_delete(curator_client):
    person = _make_person(curator_client)
    curator_client.put(f"/api/individuals/{person['id']}", json={"sex": "M"})
    curator_client.delete(f"/api/individuals/{person['id']}")
    actions = {e["action"] for e in _latest_audit(curator_client,
                                                   subject_type="individual")}
    assert {"create", "update", "delete"} <= actions


def test_activity_pagination_and_filter(curator_client):
    for _ in range(3):
        _make_person(curator_client)
    page = curator_client.get("/api/activity?action=create&per_page=2").get_json()
    assert page["per_page"] == 2
    assert len(page["activity"]) == 2
    assert page["total"] >= 3
    assert all(e["action"] == "create" for e in page["activity"])


# --- Authorization walls ------------------------------------------------------

def test_activity_needs_curator(member_client, client):
    # A Contributor is below Curator → 403; anonymous → 401.
    assert member_client.get("/api/activity").status_code == 403
    assert client.get("/api/activity").status_code == 401


def test_restore_and_revert_need_revert_permission(member_client, curator_client):
    person = _make_person(curator_client)
    curator_client.delete(f"/api/individuals/{person['id']}")
    # A Contributor lacks the `revert` permission → 403 on both.
    assert member_client.post(
        "/api/restore",
        json={"subject_type": "individual", "subject_id": person["id"]}
    ).status_code == 403
    assert member_client.post("/api/audit/1/revert").status_code == 403
