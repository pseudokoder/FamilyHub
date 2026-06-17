"""API tests: /api/events (polymorphic on individual|family, dual dates)."""


def _individual(client, given="Person"):
    return client.post(
        "/api/individuals", json={"name": {"given": given}}
    ).get_json()["id"]


def test_event_on_individual(member_client):
    pid = _individual(member_client, "Wilhelmina")
    response = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid, "event_tag": "BIRT",
        "date_original": "ABT 1850", "date_sort": "1850-00-00",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["event_tag"] == "BIRT"
    assert data["subject_label"] == "Wilhelmina"
    assert data["date_original"] == "ABT 1850"


def test_event_subject_validation(member_client):
    # subject_type not allowed for events
    bad_type = member_client.post("/api/events", json={
        "subject_type": "name", "subject_id": 1, "event_tag": "BIRT"})
    assert bad_type.status_code == 400
    assert "subject_type" in bad_type.get_json()["fields"]

    # subject_id points at nothing
    ghost = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": 99999, "event_tag": "BIRT"})
    assert ghost.status_code == 400
    assert "subject_id" in ghost.get_json()["fields"]

    # event_tag missing
    pid = _individual(member_client)
    no_tag = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid})
    assert no_tag.status_code == 400


def test_event_filter_by_subject(member_client):
    pid = _individual(member_client)
    member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid, "event_tag": "BIRT"})
    member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid, "event_tag": "DEAT"})
    result = member_client.get(
        f"/api/events?subject_type=individual&subject_id={pid}"
    ).get_json()
    assert len(result["events"]) == 2


def test_event_place_validation_and_update(member_client):
    pid = _individual(member_client)
    event = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid, "event_tag": "RESI"}).get_json()

    assert member_client.put(
        f"/api/events/{event['id']}", json={"place_id": 99999}
    ).status_code == 400

    member_client.put(f"/api/events/{event['id']}", json={"event_value": "Nashville"})
    assert member_client.get(
        f"/api/events/{event['id']}"
    ).get_json()["event_value"] == "Nashville"


def test_event_delete(member_client):
    pid = _individual(member_client)
    event = member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": pid, "event_tag": "BIRT"}).get_json()
    assert member_client.delete(f"/api/events/{event['id']}").status_code == 204
    assert member_client.get(f"/api/events/{event['id']}").status_code == 404
