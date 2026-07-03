"""API tests: /api/notes (Markdown memories + polymorphic note links)."""


def _individual(client, given="Jo"):
    return client.post(
        "/api/individuals", json={"name": {"given": given}}
    ).get_json()["id"]


def test_note_create_with_inline_link(member_client):
    pid = _individual(member_client)
    response = member_client.post("/api/notes", json={
        "title": "The crossing", "content": "## Story",
        "subject_type": "individual", "subject_id": pid,
    })
    assert response.status_code == 201
    data = response.get_json()
    # Author is stamped from the logged-in member, never the request body.
    assert data["author"] == "Member"
    assert data["links"][0]["subject_label"] == "Jo"


def test_note_validation(member_client):
    assert member_client.post("/api/notes", json={"title": "x"}).status_code == 400
    assert member_client.post(
        "/api/notes", json={"content": "x", "content_type": "html"}
    ).status_code == 400


def test_note_links_management_and_filter(member_client):
    pid = _individual(member_client)
    note = member_client.post("/api/notes", json={"content": "memory"}).get_json()

    member_client.post(f"/api/notes/{note['id']}/links",
                       json={"subject_type": "individual", "subject_id": pid})
    # Same attachment twice → 409.
    dup = member_client.post(f"/api/notes/{note['id']}/links",
                             json={"subject_type": "individual", "subject_id": pid})
    assert dup.status_code == 409

    filtered = member_client.get(
        f"/api/notes?subject_type=individual&subject_id={pid}"
    ).get_json()
    assert len(filtered["notes"]) == 1

    assert member_client.delete(
        f"/api/notes/{note['id']}/links/individual/{pid}"
    ).status_code == 204


def test_note_delete_is_soft_and_preserves_links(member_client):
    from app.models import NoteLink
    pid = _individual(member_client)
    note = member_client.post("/api/notes", json={
        "content": "x", "subject_type": "individual", "subject_id": pid}).get_json()
    assert NoteLink.query.count() == 1
    member_client.delete(f"/api/notes/{note['id']}")
    # Soft delete (ADR-0001): the note reads as gone...
    assert member_client.get(f"/api/notes/{note['id']}").status_code == 404
    # ...but the physical link row is kept so a restore brings the note back whole.
    assert NoteLink.query.count() == 1
