"""Plumbing-route tests: /health, robots.txt, security.txt.

Small routes, but they're load-bearing in production — the health check is
what monitoring watches, and robots.txt is a privacy layer. Tests keep
them from quietly disappearing in a refactor.
"""


def test_health_says_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_robots_disallows_everything(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b"Disallow: /" in response.data


def test_security_txt_has_required_fields(client):
    response = client.get("/.well-known/security.txt")
    assert response.status_code == 200
    assert b"Contact: mailto:" in response.data
    assert b"Expires:" in response.data  # required by RFC 9116
