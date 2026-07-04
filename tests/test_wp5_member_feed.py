"""WP5 — member-safe activity feed for Home (BLOCKERS.md, 2026-07-03).

GET /api/activity/feed is reachable by ANY logged-in member (unlike the Curator+
GET /api/activity full trail) and surfaces only friendly, non-sensitive CREATE
events — new people/photos/stories, never deletes/reverts/account actions.
"""


def test_viewer_can_read_the_member_feed(viewer_client):
    """The whole point: a Viewer (below Contributor) can read this, unlike the
    full audit trail which 403s a Viewer."""
    assert viewer_client.get("/api/activity/feed").status_code == 200
    assert viewer_client.get("/api/activity").status_code == 403


def test_new_person_and_note_appear_as_friendly_sentences(member_client):
    person = member_client.post(
        "/api/individuals", json={"name": {"given": "Jo", "surname": "Hartwell"}}
    ).get_json()
    member_client.post("/api/notes", json={
        "title": "The crossing", "content": "## Story",
        "subject_type": "individual", "subject_id": person["id"],
    })

    feed = member_client.get("/api/activity/feed").get_json()["activity"]
    texts = [row["text"] for row in feed]
    assert any("Jo Hartwell" in t for t in texts)
    assert any("story" in t.lower() for t in texts)
    # Every row is a safe subject type only.
    assert all(row["subject_type"] in ("individual", "media", "note") for row in feed)


def test_deletes_and_updates_never_appear_in_the_feed(member_client):
    person = member_client.post("/api/individuals", json={"sex": "F"}).get_json()
    member_client.put(f"/api/individuals/{person['id']}", json={"sex": "U"})
    member_client.delete(f"/api/individuals/{person['id']}")

    feed = member_client.get("/api/activity/feed").get_json()["activity"]
    # The create is filtered out too, because the row is now soft-deleted (a
    # friendly feed shouldn't point at content that's no longer there).
    assert all(row["subject_id"] != person["id"] for row in feed)

    # But the full Curator+ trail DOES see the delete — proving it's a
    # different, narrower view, not a broken one.
    from app.services import write_control
    full = write_control.list_activity(subject_type="individual")["activity"]
    assert any(e["action"] == "delete" and e["subject_id"] == person["id"] for e in full)


def test_account_and_security_actions_never_appear(admin_client, member):
    """A password reset / role edit / lockout must never leak into the
    all-members feed — those are 'user'/'backup' subject types, not in the
    MEMBER_SAFE_SUBJECTS allow-list."""
    admin_client.post(f"/api/admin/users/{member.id}/reset-password")
    feed = admin_client.get("/api/activity/feed").get_json()["activity"]
    assert all(row["subject_type"] != "user" for row in feed)


def test_feed_respects_limit(member_client):
    for i in range(5):
        member_client.post("/api/individuals", json={"name": {"given": f"P{i}"}})
    feed = member_client.get("/api/activity/feed?limit=2").get_json()["activity"]
    assert len(feed) == 2
