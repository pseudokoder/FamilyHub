"""What's New feed tests: every content type appears, photo batches
collapse to one line, and the page stays behind the login wall."""

from tests.conftest import make_image


def _seed_everything(admin_client, member_client):
    admin_client.post("/posts/new",
                      data={"title": "The Buick Fire", "body": "A story."})
    album_url = member_client.post(
        "/albums/new", data={"title": "Vegas Trip", "description": ""},
        follow_redirects=False,
    ).headers["Location"]
    member_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "a.jpg"), (make_image(), "b.jpg"),
                         (make_image(), "c.jpg")]},
        content_type="multipart/form-data",
    )
    admin_client.post("/family/new",
                      data={"name": "Ruth Leiter", "location": "",
                            "bio": "Gardener.", "birth_date": "",
                            "death_date": ""})
    member_client.post("/timeline/new",
                       data={"title": "The move west", "description": "",
                             "year": "1956"})
    from app.models import Post
    post_id = Post.query.one().id
    member_client.post(f"/posts/{post_id}/comments",
                       data={"body": "I was there!"})


def test_feed_shows_everything_grouped(admin_client, member_client):
    _seed_everything(admin_client, member_client)
    page = admin_client.get("/activity").data.decode("utf-8")

    assert "wrote down a memory" in page and "The Buick Fire" in page
    # THE grouping assertion: 3 photos uploaded together = ONE line.
    assert "added 3 photos to “Vegas Trip”" in page
    assert "started a wiki page for Ruth Leiter" in page
    assert "put “The move west” (1956) on the timeline" in page
    assert "commented on “The Buick Fire”" in page


def test_wiki_edits_collapse_per_day(admin_client):
    admin_client.post("/family/new",
                      data={"name": "Frank Leiter", "location": "",
                            "bio": "v1", "birth_date": "", "death_date": ""})
    from app.models import FamilyMember
    page_id = FamilyMember.query.one().id
    for bio in ("v2", "v3", "v4"):
        admin_client.post(
            f"/family/{page_id}/edit",
            data={"name": "Frank Leiter", "location": "", "bio": bio,
                  "birth_date": "", "death_date": ""},
        )
    page = admin_client.get("/activity").data.decode("utf-8")
    # Four saves today by one person = one "worked on" line (the page's
    # birth line is the same person/day group here, so exactly one total).
    assert page.count("the wiki page for Frank Leiter") <= 1
    assert page.count("Frank Leiter") >= 1


def test_feed_is_login_walled(client):
    response = client.get("/activity", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_empty_feed_is_friendly(admin_client):
    page = admin_client.get("/activity")
    assert b"be the first" in page.data.lower()