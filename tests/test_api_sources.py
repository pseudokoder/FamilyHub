"""API tests: /api/repositories, /api/sources, /api/citations (evidence layer)."""


def _individual(client, given="Ada"):
    return client.post(
        "/api/individuals", json={"name": {"given": given}}
    ).get_json()["id"]


def test_repository_and_source(member_client):
    repo = member_client.post(
        "/api/repositories", json={"name": "State Archive", "website": "https://x"}
    ).get_json()
    assert repo["name"] == "State Archive"

    source = member_client.post(
        "/api/sources", json={"title": "1880 Census", "repository_id": repo["id"]}
    ).get_json()
    assert source["repository"] == "State Archive"

    assert member_client.post("/api/sources", json={"author": "x"}).status_code == 400
    assert member_client.post(
        "/api/sources", json={"title": "X", "repository_id": 99999}
    ).status_code == 400


def test_deleting_repository_detaches_sources(member_client):
    repo = member_client.post("/api/repositories", json={"name": "R"}).get_json()
    source = member_client.post(
        "/api/sources", json={"title": "S", "repository_id": repo["id"]}
    ).get_json()
    member_client.delete(f"/api/repositories/{repo['id']}")
    assert member_client.get(
        f"/api/sources/{source['id']}"
    ).get_json()["repository_id"] is None


def test_citation_polymorphic_and_quality(member_client):
    pid = _individual(member_client)
    source = member_client.post("/api/sources", json={"title": "Bible"}).get_json()

    citation = member_client.post("/api/citations", json={
        "source_id": source["id"], "subject_type": "individual",
        "subject_id": pid, "page": "p. 1", "quality": 3,
    }).get_json()
    assert citation["quality"] == 3
    assert citation["subject_label"] == "Ada"

    # QUAY out of range, and a nonexistent source — both 400.
    assert member_client.post("/api/citations", json={
        "source_id": source["id"], "subject_type": "individual",
        "subject_id": pid, "quality": 9}).status_code == 400
    assert member_client.post("/api/citations", json={
        "source_id": 99999, "subject_type": "individual",
        "subject_id": pid}).status_code == 400


def test_deleting_source_cascades_citations(member_client):
    pid = _individual(member_client)
    source = member_client.post("/api/sources", json={"title": "S"}).get_json()
    citation = member_client.post("/api/citations", json={
        "source_id": source["id"], "subject_type": "individual",
        "subject_id": pid}).get_json()

    member_client.delete(f"/api/sources/{source['id']}")
    assert member_client.get(f"/api/citations/{citation['id']}").status_code == 404
