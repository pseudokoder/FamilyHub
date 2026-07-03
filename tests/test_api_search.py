"""API tests: /api/search — name matching, filters, notes text, escaping."""


def _person(client, given, surname=None, sex=None):
    body = {"name": {"given": given, "surname": surname}}
    if sex:
        body["sex"] = sex
    return client.post("/api/individuals", json=body).get_json()["id"]


def _birth(client, individual_id, date_sort):
    client.post("/api/events", json={
        "subject_type": "individual", "subject_id": individual_id,
        "event_tag": "BIRT", "date_sort": date_sort})


def test_search_requires_login(client):
    assert client.get("/api/search?q=x").status_code == 401


def test_search_by_name(member_client):
    _person(member_client, "Wilhelmina", "Berg")
    _person(member_client, "Thomas", "Hartwell")
    result = member_client.get("/api/search?q=berg").get_json()
    assert result["counts"]["people"] == 1
    assert result["people"][0]["primary_name"] == "Wilhelmina Berg"


def test_search_filter_by_sex(member_client):
    f = _person(member_client, "Ada", "Lovelace", sex="F")
    m = _person(member_client, "Charles", "Babbage", sex="M")
    ids = [p["id"] for p in member_client.get("/api/search?sex=F").get_json()["people"]]
    assert f in ids and m not in ids


def test_search_birth_year_range(member_client):
    old = _person(member_client, "Old", "Timer")
    _birth(member_client, old, "1850-00-00")
    young = _person(member_client, "Young", "Un")
    _birth(member_client, young, "1990-00-00")

    result = member_client.get("/api/search?birth_from=1800&birth_to=1900").get_json()
    ids = [p["id"] for p in result["people"]]
    assert old in ids and young not in ids
    assert any(p["birth_year"] == 1850 for p in result["people"])


def test_search_place_filter(member_client):
    local = _person(member_client, "Local", "Person")
    place_id = member_client.post(
        "/api/places", json={"full_name": "Spring Hill, Tennessee"}).get_json()["id"]
    member_client.post("/api/events", json={
        "subject_type": "individual", "subject_id": local,
        "event_tag": "RESI", "place_id": place_id})
    elsewhere = _person(member_client, "Far", "Away")

    ids = [p["id"] for p in
           member_client.get("/api/search?place=spring").get_json()["people"]]
    assert local in ids and elsewhere not in ids


def test_search_notes_text(member_client):
    member_client.post("/api/notes",
                       json={"title": "Crossing", "content": "sailed from Amsterdam"})
    result = member_client.get("/api/search?q=amsterdam").get_json()
    assert result["counts"]["notes"] == 1
    assert "Amsterdam" in result["notes"][0]["snippet"]


def test_like_wildcards_are_escaped(member_client):
    _person(member_client, "Real", "Person")
    # '%' (sent url-encoded as %25) must match LITERALLY, not act as a wildcard
    # that returns everyone — proof the escaping works.
    result = member_client.get("/api/search?q=%25").get_json()
    assert result["counts"]["people"] == 0
