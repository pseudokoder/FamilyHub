"""API tests: /api/individuals (+ names), and the API's auth/role wall.

This file also doubles as the proof that the JSON API's authorization works,
since individuals is the first resource: anonymous → 401, GUEST → 403 on writes,
a normal member → full CRUD.
"""


def test_reads_require_login(client):
    assert client.get("/api/individuals").status_code == 401
    assert client.get("/api/individuals/1").status_code == 401


def test_guest_can_read_but_not_write(guest_client):
    assert guest_client.get("/api/individuals").status_code == 200
    # A GUEST is below USER on the ladder → 403 on any write (§10).
    assert guest_client.post("/api/individuals", json={"sex": "M"}).status_code == 403


def test_create_get_and_list(member_client):
    created = member_client.post(
        "/api/individuals",
        json={"sex": "F", "living": False,
              "name": {"given": "Ada", "surname": "Lovelace"}},
    )
    assert created.status_code == 201
    data = created.get_json()
    assert data["sex"] == "F" and data["living"] is False
    assert data["primary_name"] == "Ada Lovelace"
    assert data["names"][0]["is_primary"] is True

    got = member_client.get(f"/api/individuals/{data['id']}").get_json()
    assert got["id"] == data["id"]

    listing = member_client.get("/api/individuals").get_json()
    assert any(i["id"] == data["id"] for i in listing["individuals"])


def test_invalid_sex_is_400_with_field(member_client):
    response = member_client.post("/api/individuals", json={"sex": "Z"})
    assert response.status_code == 400
    assert "sex" in response.get_json()["fields"]


def test_update_individual(member_client):
    ind = member_client.post("/api/individuals", json={"sex": "M"}).get_json()
    response = member_client.put(
        f"/api/individuals/{ind['id']}", json={"living": False, "sex": "U"}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["living"] is False and body["sex"] == "U"


def test_delete_individual(member_client):
    ind = member_client.post(
        "/api/individuals", json={"name": {"given": "Temp"}}
    ).get_json()
    assert member_client.delete(f"/api/individuals/{ind['id']}").status_code == 204
    assert member_client.get(f"/api/individuals/{ind['id']}").status_code == 404


def test_missing_individual_is_404(member_client):
    assert member_client.get("/api/individuals/9999").status_code == 404


def test_names_sub_resource(member_client):
    ind = member_client.post(
        "/api/individuals", json={"name": {"given": "Jane", "surname": "Doe"}}
    ).get_json()

    # Add a married name flagged primary — it should steal "primary" from the birth name.
    added = member_client.post(
        f"/api/individuals/{ind['id']}/names",
        json={"name_type": "married", "given": "Jane", "surname": "Smith",
              "is_primary": True},
    )
    assert added.status_code == 201
    name_id = added.get_json()["id"]

    got = member_client.get(f"/api/individuals/{ind['id']}").get_json()
    assert got["primary_name"] == "Jane Smith"
    assert got["names_count"] == 2
    assert sum(1 for n in got["names"] if n["is_primary"]) == 1  # exactly one primary

    assert member_client.put(
        f"/api/names/{name_id}", json={"surname": "Jones"}
    ).status_code == 200
    assert member_client.delete(f"/api/names/{name_id}").status_code == 204


def test_empty_name_rejected(member_client):
    ind = member_client.post("/api/individuals", json={}).get_json()
    response = member_client.post(
        f"/api/individuals/{ind['id']}/names", json={"name_type": "aka"}
    )
    assert response.status_code == 400  # a name needs a given or surname
