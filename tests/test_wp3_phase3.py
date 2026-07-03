"""WP3 Phase 3 — Account↔Person link, self-edit, and the tree root (ADR-0002)."""


def _person(client, given, birth_year=None, sex="U"):
    pid = client.post("/api/individuals",
                      json={"sex": sex, "name": {"given": given}}).get_json()["id"]
    if birth_year is not None:
        client.post("/api/events", json={
            "subject_type": "individual", "subject_id": pid,
            "event_tag": "BIRT", "date_sort": f"{birth_year}-00-00"})
    return pid


# --- Admin link / unlink ------------------------------------------------------

def test_admin_links_then_unlinks(admin_client, member_client, member):
    pid = _person(admin_client, "Member Person")
    link = admin_client.put(f"/api/users/{member.id}/individual",
                            json={"individual_id": pid})
    assert link.status_code == 200
    assert link.get_json()["individual_id"] == pid

    # The linked member now sees their person via /api/me/person.
    mine = member_client.get("/api/me/person").get_json()["individual"]
    assert mine["id"] == pid

    admin_client.delete(f"/api/users/{member.id}/individual")
    assert member_client.get("/api/me/person").get_json()["individual"] is None


def test_link_requires_link_account_permission(curator_client, member, admin_client):
    pid = _person(admin_client, "P")
    # A Curator can revert, but linking accounts is Admin-only (link_account).
    assert curator_client.put(f"/api/users/{member.id}/individual",
                              json={"individual_id": pid}).status_code == 403


def test_link_nonexistent_individual_is_400(admin_client, member):
    assert admin_client.put(f"/api/users/{member.id}/individual",
                            json={"individual_id": 99999}).status_code == 400


def test_cannot_link_one_person_to_two_accounts(admin_client, member, viewer):
    pid = _person(admin_client, "Shared")
    assert admin_client.put(f"/api/users/{member.id}/individual",
                            json={"individual_id": pid}).status_code == 200
    # Same person, different account → 409.
    assert admin_client.put(f"/api/users/{viewer.id}/individual",
                            json={"individual_id": pid}).status_code == 409


# --- Self-edit (self-authoring) ----------------------------------------------

def test_linked_viewer_may_edit_own_record(admin_client, viewer, viewer_client):
    pid = _person(admin_client, "Selfie", sex="U")
    admin_client.put(f"/api/users/{viewer.id}/individual", json={"individual_id": pid})

    # A Viewer normally can't write to an individual at all...
    assert viewer_client.put(f"/api/individuals/{pid}",
                             json={"sex": "F"}).status_code == 403
    # ...but MAY edit their OWN linked record via /api/me/person (ADR-0002).
    resp = viewer_client.put("/api/me/person", json={"sex": "F"})
    assert resp.status_code == 200
    assert resp.get_json()["sex"] == "F"


def test_self_edit_requires_a_link(member_client):
    assert member_client.put("/api/me/person", json={"sex": "M"}).status_code == 400


# --- The tree root resolver ---------------------------------------------------

def test_tree_root_falls_back_to_oldest_ancestor(admin_client, member_client, member):
    grandparent = _person(admin_client, "Ada", birth_year=1901)
    child = _person(admin_client, "Ben", birth_year=1935)
    fam = admin_client.post("/api/families",
                            json={"partner1_id": grandparent}).get_json()["id"]
    admin_client.post(f"/api/families/{fam}/children", json={"child_id": child})

    # An UNLINKED member gets the oldest ancestor (the earliest-born root).
    root = member_client.get("/api/tree/root").get_json()
    assert root["source"] == "oldest_ancestor"
    assert root["individual_id"] == grandparent

    # Once linked, the tree opens on the member's own person instead.
    admin_client.put(f"/api/users/{member.id}/individual", json={"individual_id": child})
    root = member_client.get("/api/tree/root").get_json()
    assert root["source"] == "linked"
    assert root["individual_id"] == child
