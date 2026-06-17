"""API tests: /api/places (and the SET-NULL-on-delete rule the app enforces)."""


def test_place_crud(member_client):
    created = member_client.post(
        "/api/places",
        json={"full_name": "Spring Hill, Maury, Tennessee, USA",
              "state": "Tennessee", "latitude": 35.75, "longitude": -86.93},
    )
    assert created.status_code == 201
    data = created.get_json()
    assert data["state"] == "Tennessee"
    assert abs(data["latitude"] - 35.75) < 0.001  # DECIMAL came back as a number

    place_id = data["id"]
    member_client.put(f"/api/places/{place_id}", json={"city": "Spring Hill"})
    assert member_client.get(f"/api/places/{place_id}").get_json()["city"] == "Spring Hill"
    assert member_client.delete(f"/api/places/{place_id}").status_code == 204


def test_place_requires_full_name(member_client):
    assert member_client.post(
        "/api/places", json={"city": "Nowhere"}
    ).status_code == 400


def test_bad_coordinate_is_400(member_client):
    response = member_client.post(
        "/api/places", json={"full_name": "X", "latitude": "north"}
    )
    assert response.status_code == 400
    assert "latitude" in response.get_json()["fields"]


def test_deleting_place_detaches_events(member_client, app):
    """A place is shared by many events; deleting it must null those events'
    place_id (the SET NULL the app enforces because SQLite won't)."""
    from app.extensions import db
    from app.models import Event

    place_id = member_client.post(
        "/api/places", json={"full_name": "Old Town"}
    ).get_json()["id"]
    db.session.add(Event(subject_type="individual", subject_id=1,
                         event_tag="RESI", place_id=place_id))
    db.session.commit()

    member_client.delete(f"/api/places/{place_id}")

    db.session.expire_all()
    event = Event.query.filter_by(event_tag="RESI").one()
    assert event.place_id is None
