"""API read/update/list coverage + a CSRF check on the /api write surface.

The happy-path create/delete flows are covered per-resource elsewhere; this file
exercises the remaining GET/PUT/list branches and the polymorphic subject_label
variants (family/event/name) in one place.
"""

from tests.conftest import make_image


def _ind(client, given="Person"):
    return client.post(
        "/api/individuals", json={"name": {"given": given}}).get_json()["id"]


def test_all_list_endpoints_reachable(member_client):
    for url in ("/api/individuals", "/api/families", "/api/events", "/api/places",
                "/api/repositories", "/api/sources", "/api/citations",
                "/api/notes", "/api/media"):
        assert member_client.get(url).status_code == 200, url


def test_family_get_update_and_child_404(member_client):
    dad = _ind(member_client, "Dad")
    fam = member_client.post("/api/families", json={}).get_json()
    member_client.put(f"/api/families/{fam['id']}",
                      json={"partner1_id": dad, "gedcom_xref": "@F9@"})
    got = member_client.get(f"/api/families/{fam['id']}").get_json()
    assert got["partner1_id"] == dad and got["gedcom_xref"] == "@F9@"
    assert member_client.delete(
        f"/api/families/{fam['id']}/children/9999").status_code == 404


def test_event_get_and_subject_switch(member_client):
    person = _ind(member_client)
    fam = member_client.post("/api/families", json={}).get_json()
    event = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": person,
        "event_tag": "BIRT"}).get_json()
    assert member_client.get(f"/api/events/{event['id']}").status_code == 200
    switched = member_client.put(f"/api/events/{event['id']}", json={
        "subject_type": "family", "subject_id": fam["id"]}).get_json()
    assert switched["subject_type"] == "family"


def test_place_and_source_get_update(member_client):
    place_id = member_client.post("/api/places", json={"full_name": "X"}).get_json()["id"]
    assert member_client.get(f"/api/places/{place_id}").status_code == 200

    repo = member_client.post("/api/repositories", json={"name": "Archive"}).get_json()
    assert member_client.get(f"/api/repositories/{repo['id']}").status_code == 200
    member_client.put(f"/api/repositories/{repo['id']}", json={"website": "https://y"})

    src = member_client.post("/api/sources", json={"title": "S"}).get_json()
    member_client.put(f"/api/sources/{src['id']}",
                      json={"author": "A", "repository_id": repo["id"]})
    assert member_client.get(f"/api/sources/{src['id']}").get_json()["author"] == "A"


def test_citation_lifecycle_and_subject_labels(member_client):
    person = _ind(member_client, "Ada")
    name_id = member_client.get(
        f"/api/individuals/{person}").get_json()["names"][0]["id"]
    fam = member_client.post("/api/families", json={"partner1_id": person}).get_json()
    event = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": person,
        "event_tag": "BIRT"}).get_json()
    src = member_client.post("/api/sources", json={"title": "Bible"}).get_json()

    # subject_label resolves for family, event, and name subjects.
    on_family = member_client.post("/api/citations", json={
        "source_id": src["id"], "subject_type": "family",
        "subject_id": fam["id"]}).get_json()
    assert on_family["subject_label"] == "Ada"  # the family's one partner
    on_event = member_client.post("/api/citations", json={
        "source_id": src["id"], "subject_type": "event",
        "subject_id": event["id"]}).get_json()
    assert on_event["subject_label"] == "BIRT"
    on_name = member_client.post("/api/citations", json={
        "source_id": src["id"], "subject_type": "name",
        "subject_id": name_id}).get_json()
    assert on_name["subject_label"] == "Ada"

    assert member_client.get(f"/api/citations/{on_family['id']}").status_code == 200
    member_client.put(f"/api/citations/{on_family['id']}",
                      json={"page": "p. 5", "quality": 2, "notes": "n"})
    listed = member_client.get(
        f"/api/citations?subject_type=event&subject_id={event['id']}").get_json()
    assert len(listed["citations"]) == 1
    assert member_client.delete(f"/api/citations/{on_family['id']}").status_code == 204


def test_note_get_update_and_remove_link_404(member_client):
    note = member_client.post("/api/notes", json={"content": "x"}).get_json()
    assert member_client.get(f"/api/notes/{note['id']}").status_code == 200
    member_client.put(f"/api/notes/{note['id']}", json={
        "title": "T", "content": "y", "content_type": "plain", "is_shared": True})
    got = member_client.get(f"/api/notes/{note['id']}").get_json()
    assert got["title"] == "T" and got["is_shared"] is True
    assert member_client.put(
        f"/api/notes/{note['id']}", json={"content": "  "}).status_code == 400
    assert member_client.delete(
        f"/api/notes/{note['id']}/links/individual/9999").status_code == 404


def test_media_get_update(member_client):
    media_id = member_client.post(
        "/api/media", data={"file": (make_image(), "p.jpg")},
        content_type="multipart/form-data").get_json()["id"]
    assert member_client.get(f"/api/media/{media_id}").status_code == 200
    member_client.put(f"/api/media/{media_id}", json={"title": "T", "description": "D"})
    assert member_client.get(f"/api/media/{media_id}").get_json()["title"] == "T"


def test_name_reorder_and_primary_switch(member_client):
    person = _ind(member_client, "Jane")
    first = member_client.get(
        f"/api/individuals/{person}").get_json()["names"][0]["id"]
    member_client.put(f"/api/names/{first}", json={"sort_order": 5, "name_type": "aka"})
    second = member_client.post(
        f"/api/individuals/{person}/names", json={"given": "Janet"}).get_json()["id"]
    member_client.put(f"/api/names/{second}", json={"is_primary": True})
    got = member_client.get(f"/api/individuals/{person}").get_json()
    assert sum(1 for n in got["names"] if n["is_primary"]) == 1


def test_api_write_requires_csrf_token(tmp_path):
    """With CSRF on, an /api write WITHOUT the token is rejected (400) — the
    same protection the web forms get, now proven for the JSON surface."""
    from app import create_app
    from app.config import Config
    from app.extensions import db

    class CsrfApiConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "capi.db").as_posix()
        UPLOAD_FOLDER = str(tmp_path / "u")
        BACKUP_FOLDER = str(tmp_path / "b")
        EXPORT_FOLDER = str(tmp_path / "e")
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfApiConfig)
    with app.app_context():
        db.create_all()
    # CSRF fires in before_request, ahead of the auth check, so no token = 400.
    response = app.test_client().post("/api/individuals", json={"sex": "M"})
    assert response.status_code == 400
