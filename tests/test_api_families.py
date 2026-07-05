"""API tests: /api/families (+ the children sub-resource)."""


def _individual(client, given):
    return client.post(
        "/api/individuals", json={"name": {"given": given}}
    ).get_json()["id"]


def test_create_family_with_partners(member_client):
    p1 = _individual(member_client, "Thomas")
    p2 = _individual(member_client, "Wilhelmina")
    response = member_client.post(
        "/api/families", json={"partner1_id": p1, "partner2_id": p2}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["partner1"] == "Thomas" and data["partner2"] == "Wilhelmina"


def test_family_rejects_nonexistent_partner(member_client):
    response = member_client.post("/api/families", json={"partner1_id": 99999})
    assert response.status_code == 400
    assert "partner1_id" in response.get_json()["fields"]


def test_children_sub_resource(member_client):
    dad = _individual(member_client, "John")
    kid = _individual(member_client, "Robert")
    fam = member_client.post("/api/families", json={"partner1_id": dad}).get_json()

    added = member_client.post(
        f"/api/families/{fam['id']}/children",
        json={"child_id": kid, "pedigree_type": "adopted", "child_order": 1},
    )
    assert added.status_code == 201
    assert added.get_json()["pedigree_type"] == "adopted"

    got = member_client.get(f"/api/families/{fam['id']}").get_json()
    assert got["children_count"] == 1
    assert got["children"][0]["child_name"] == "Robert"

    # Same child twice → 409 Conflict (the composite PK won't allow it).
    dup = member_client.post(
        f"/api/families/{fam['id']}/children", json={"child_id": kid}
    )
    assert dup.status_code == 409

    # A bad pedigree type → 400.
    bad = member_client.post(
        f"/api/families/{fam['id']}/children",
        json={"child_id": dad, "pedigree_type": "clone"},
    )
    assert bad.status_code == 400

    assert member_client.delete(
        f"/api/families/{fam['id']}/children/{kid}"
    ).status_code == 204


def test_update_child_link(member_client):
    """PUT edits pedigree_type/child_order on an active link in place — ONE
    'update' audit entry (before -> after), not a delete + re-POST pair
    (BLOCKERS.md forward note, 2026-07-04)."""
    dad = _individual(member_client, "John")
    kid = _individual(member_client, "Robert")
    fam = member_client.post("/api/families", json={"partner1_id": dad}).get_json()
    member_client.post(
        f"/api/families/{fam['id']}/children",
        json={"child_id": kid, "pedigree_type": "birth", "child_order": 0},
    )

    from app.services import write_control
    before_count = len(write_control.list_activity(
        subject_type="family_child")["activity"])

    updated = member_client.put(
        f"/api/families/{fam['id']}/children/{kid}",
        json={"pedigree_type": "adopted", "child_order": 2},
    )
    assert updated.status_code == 200
    body = updated.get_json()
    assert body["pedigree_type"] == "adopted"
    assert body["child_order"] == 2

    got = member_client.get(f"/api/families/{fam['id']}").get_json()
    assert got["children"][0]["pedigree_type"] == "adopted"
    assert got["children"][0]["child_order"] == 2

    # Exactly one new audit row, and it's a single 'update' with a before/after
    # snapshot — not a delete + create pair.
    activity = write_control.list_activity(subject_type="family_child")["activity"]
    assert len(activity) == before_count + 1
    newest = activity[0]
    assert newest["action"] == "update"

    from app.models import AuditLog
    entry = AuditLog.query.filter_by(id=newest["id"]).first()
    import json
    before = json.loads(entry.before_json)
    after = json.loads(entry.after_json)
    assert before["pedigree_type"] == "birth" and before["child_order"] == 0
    assert after["pedigree_type"] == "adopted" and after["child_order"] == 2


def test_update_child_link_404_when_missing_or_deleted(member_client):
    dad = _individual(member_client, "John")
    kid = _individual(member_client, "Robert")
    fam = member_client.post("/api/families", json={"partner1_id": dad}).get_json()

    # Never linked at all.
    never_linked = member_client.put(
        f"/api/families/{fam['id']}/children/{kid}", json={"child_order": 1}
    )
    assert never_linked.status_code == 404

    # Linked, then removed (soft-deleted) — still 404.
    member_client.post(
        f"/api/families/{fam['id']}/children", json={"child_id": kid}
    )
    member_client.delete(f"/api/families/{fam['id']}/children/{kid}")
    after_delete = member_client.put(
        f"/api/families/{fam['id']}/children/{kid}", json={"child_order": 1}
    )
    assert after_delete.status_code == 404


def test_update_child_link_rbac_denies_viewer(member_client, viewer_client):
    dad = _individual(member_client, "John")
    kid = _individual(member_client, "Robert")
    fam = member_client.post("/api/families", json={"partner1_id": dad}).get_json()
    member_client.post(
        f"/api/families/{fam['id']}/children", json={"child_id": kid}
    )

    denied = viewer_client.put(
        f"/api/families/{fam['id']}/children/{kid}", json={"child_order": 1}
    )
    assert denied.status_code == 403


def test_delete_family(member_client):
    fam = member_client.post("/api/families", json={}).get_json()
    assert member_client.delete(f"/api/families/{fam['id']}").status_code == 204
    assert member_client.get(f"/api/families/{fam['id']}").status_code == 404
