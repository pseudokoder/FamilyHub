"""Friendly-error-page tests: the right status code AND the gentle copy.

(500 isn't exercised here: under TESTING the framework re-raises exceptions
instead of rendering the handler, so a 500 test would assert framework
behavior, not ours. The handler is symmetric with these two and the
template is static.)
"""

from tests.conftest import MEMBER_EMAIL, MEMBER_PASSWORD


def test_404_is_friendly(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    # Literal template text isn't autoescaped (only {{ variables }} are),
    # so the apostrophe stays raw.
    assert b"couldn't find that page" in response.data
    assert b"Back to the home page" in response.data


def test_403_is_friendly(client, member):
    """A logged-in non-admin hitting an admin page gets the calm 403 page,
    not a stack trace — and the status code is still honestly 403."""
    client.post("/auth/login",
                data={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD})
    response = client.get("/admin/users")
    assert response.status_code == 403
    assert b"not yours to change" in response.data
    assert b"ask wes" in response.data.lower()


def test_404_keeps_the_navbar_for_logged_in_users(admin_client):
    """The error page extends base.html, so a signed-in visitor still has
    their navigation — the mistake doesn't strand them."""
    response = admin_client.get("/nope")
    assert response.status_code == 404
    assert b"FamilyHub" in response.data  # navbar brand present
