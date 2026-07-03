"""WP3 Phase 4 — pedigree graph, relationship finder, stats, On This Day, almanac.

Builds a small, explicit family so the relationship labels are checkable:

        GP1 ═══ GP2                (grandparents)
             │
       ┌─────┴─────┐
     ParentA     ParentB          (siblings)
       ║            ║
    SpouseA      SpouseB
       │            │
      KidA         KidB           (1st cousins)
"""

import pytest


def _person(client, given, sex="U", birth_year=None):
    pid = client.post("/api/individuals",
                      json={"sex": sex, "name": {"given": given}}).get_json()["id"]
    if birth_year is not None:
        client.post("/api/events", json={
            "subject_type": "individual", "subject_id": pid,
            "event_tag": "BIRT", "date_sort": f"{birth_year}-06-15",
            "date_original": str(birth_year)})
    return pid


def _family(client, p1=None, p2=None, children=()):
    fam = client.post("/api/families",
                      json={"partner1_id": p1, "partner2_id": p2}).get_json()["id"]
    for child in children:
        client.post(f"/api/families/{fam}/children", json={"child_id": child})
    return fam


@pytest.fixture
def clan(member_client):
    c = member_client
    gp1 = _person(c, "Grand One", birth_year=1900)
    gp2 = _person(c, "Grand Two", birth_year=1902)
    parent_a = _person(c, "Parent A", birth_year=1930)
    parent_b = _person(c, "Parent B", birth_year=1933)
    _family(c, gp1, gp2, children=[parent_a, parent_b])
    spouse_a = _person(c, "Spouse A", birth_year=1931)
    spouse_b = _person(c, "Spouse B", birth_year=1934)
    kid_a = _person(c, "Kid A", birth_year=1960)
    kid_b = _person(c, "Kid B", birth_year=1962)
    _family(c, parent_a, spouse_a, children=[kid_a])
    _family(c, parent_b, spouse_b, children=[kid_b])
    return dict(gp1=gp1, gp2=gp2, parent_a=parent_a, parent_b=parent_b,
                spouse_a=spouse_a, spouse_b=spouse_b, kid_a=kid_a, kid_b=kid_b)


def _rel(client, a, b):
    return client.get(f"/api/individuals/{a}/relationship/{b}").get_json()["relationship"]


# --- Relationship labels ------------------------------------------------------

def test_direct_line_labels(member_client, clan):
    c = member_client
    assert _rel(c, clan["parent_a"], clan["gp1"]) == "parent"
    assert _rel(c, clan["gp1"], clan["parent_a"]) == "child"
    assert _rel(c, clan["kid_a"], clan["gp1"]) == "grandparent"
    assert _rel(c, clan["gp1"], clan["kid_a"]) == "grandchild"


def test_sibling_cousin_and_aunt_labels(member_client, clan):
    c = member_client
    assert _rel(c, clan["parent_a"], clan["parent_b"]) == "sibling"
    assert _rel(c, clan["kid_a"], clan["kid_b"]) == "1st cousin"
    # ParentB is KidA's aunt/uncle; KidA is ParentB's niece/nephew.
    assert _rel(c, clan["kid_a"], clan["parent_b"]) == "aunt/uncle"
    assert _rel(c, clan["parent_b"], clan["kid_a"]) == "niece/nephew"


def test_spouse_and_inlaw_and_none(member_client, clan):
    c = member_client
    assert _rel(c, clan["parent_a"], clan["spouse_a"]) == "spouse"
    # SpouseA's spouse (ParentA) is ParentB's blood sibling → in-law.
    assert _rel(c, clan["spouse_a"], clan["parent_b"]) == "in-law"
    stranger = _person(c, "Nobody")
    assert _rel(c, clan["kid_a"], stranger) == "no known relationship"


def test_self_relationship(member_client, clan):
    assert _rel(member_client, clan["kid_a"], clan["kid_a"]) == "self"


# --- Pedigree graph slice -----------------------------------------------------

def test_pedigree_graph_from_any_node(member_client, clan):
    graph = member_client.get(
        f"/api/individuals/{clan['kid_a']}/pedigree?direction=ancestors&depth=2"
    ).get_json()
    node_ids = {n["id"] for n in graph["nodes"]}
    # KidA + parents + grandparents are all in the 2-generation ancestor slice.
    assert {clan["kid_a"], clan["parent_a"], clan["spouse_a"],
            clan["gp1"], clan["gp2"]} <= node_ids
    # ParentB (a sibling of ParentA) is NOT an ancestor of KidA.
    assert clan["parent_b"] not in node_ids
    # Lazy-fetch hint: ParentA still has ancestors above the slice boundary.
    parent_a_node = next(n for n in graph["nodes"] if n["id"] == clan["parent_a"])
    assert parent_a_node["has_ancestors"] is True
    # Edges carry both parent-child and partner links.
    assert {e["type"] for e in graph["edges"]} == {"parent-child", "partner"}


def test_depth_limits_the_slice(member_client, clan):
    graph = member_client.get(
        f"/api/individuals/{clan['kid_a']}/pedigree?direction=ancestors&depth=1"
    ).get_json()
    node_ids = {n["id"] for n in graph["nodes"]}
    assert clan["parent_a"] in node_ids       # 1 generation up
    assert clan["gp1"] not in node_ids         # 2 generations up — beyond depth=1


# --- Stats, On This Day, almanac ---------------------------------------------

def test_aggregate_stats(member_client, clan):
    stats = member_client.get("/api/stats").get_json()
    assert stats["counts"]["people"] == 8
    assert stats["counts"]["families"] == 3
    assert "storage_bytes" in stats


def test_on_this_day_matches_month_day(member_client, clan):
    # The clan's births are all on 06-15 (see the fixture).
    result = member_client.get("/api/on-this-day?month=6&day=15").get_json()
    assert len(result["births"]) == 8
    assert all(b["who"] for b in result["births"])
    # A day with no family events is empty, not an error.
    empty = member_client.get("/api/on-this-day?month=1&day=1").get_json()
    assert empty["births"] == []


def test_historical_events_have_descriptions(member_client):
    from app.services import historical_event_service
    historical_event_service.seed_defaults()
    events = member_client.get("/api/historical-events?scope=US").get_json()
    assert events["historical_events"]
    assert all(e["description"] and e["scope"] == "US"
               for e in events["historical_events"])


def test_media_capture_ordering_param_accepted(member_client):
    # The endpoint accepts order_by=capture (full upload flow is covered elsewhere).
    assert member_client.get("/api/media?order_by=capture").status_code == 200
