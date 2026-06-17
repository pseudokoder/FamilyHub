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


def test_delete_family(member_client):
    fam = member_client.post("/api/families", json={}).get_json()
    assert member_client.delete(f"/api/families/{fam['id']}").status_code == 204
    assert member_client.get(f"/api/families/{fam['id']}").status_code == 404
