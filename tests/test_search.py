"""Search tests: every content type findable, wildcards stay literal,
and results stay behind the login wall (they ARE family content)."""

from tests.conftest import make_image


def _seed_content(client):
    """One of everything, through the real routes."""
    client.post("/posts/new", data={"title": "The Buick Fire",
                                    "body": "Dad swears it was a Chevy."})
    client.post("/family/new", data={"name": "Ruth Leiter",
                                     "location": "Pittsburgh",
                                     "bio": "Loved her garden."})
    client.post("/albums/new", data={"title": "Vegas Trip 100%",
                                     "description": ""})
    client.post("/timeline/new", data={"title": "House fire",
                                       "description": "", "year": "1962",
                                       "month": "3"})


def test_search_finds_each_content_type(admin_client):
    _seed_content(admin_client)
    checks = {
        "ruth": b"Ruth Leiter",        # wiki, by name
        "garden": b"Ruth Leiter",      # wiki, by bio text
        "buick": b"The Buick Fire",    # post, by title
        "chevy": b"The Buick Fire",    # post, by body text
        "vegas": b"Vegas Trip",        # album, by title
        "house": b"House fire",        # timeline, by title
    }
    for term, expected in checks.items():
        response = admin_client.get(f"/search?q={term}")
        assert expected in response.data, f"searching {term!r}"


def test_search_finds_photos_by_original_filename(admin_client):
    location = admin_client.post(
        "/albums/new", data={"title": "Garden", "description": ""},
        follow_redirects=False,
    ).headers["Location"]
    admin_client.post(
        location + "/photos",
        data={"photos": [(make_image(), "grandma_gardening.jpg")]},
        content_type="multipart/form-data",
    )
    response = admin_client.get("/search?q=gardening")
    assert b"grandma_gardening.jpg" in response.data  # the thumbnail's alt text


def test_search_wildcards_are_literal(admin_client):
    """LIKE's % must not act as 'match anything' when the USER types it."""
    _seed_content(admin_client)
    # "100%" (URL-encoded %25) really matches the album called "... 100%".
    assert b"Vegas Trip" in admin_client.get("/search?q=100%25").data
    # "zz%" must match nothing — if % leaked through as a wildcard, it
    # would match... also nothing here, so test the sharper case: a lone
    # "%%" matching everything.
    response = admin_client.get("/search?q=%25%25")
    assert b"Nothing matched" in response.data


def test_short_query_gets_friendly_nudge(admin_client):
    response = admin_client.get("/search?q=a", follow_redirects=True)
    assert b"at least two letters" in response.data


def test_search_is_login_walled(client):
    response = client.get("/search?q=ruth", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
