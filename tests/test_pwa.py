"""PWA plumbing tests: manifest, service worker, offline page, icons —
all public (app shell only), all with the right content types."""


def test_manifest_is_served_with_pwa_mimetype(client):
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response.content_type.startswith("application/manifest+json")
    body = response.get_json(force=True)  # force: nonstandard mimetype
    assert body["name"] == "FamilyHub"
    assert body["display"] == "standalone"
    assert len(body["icons"]) >= 2


def test_service_worker_served_from_root_scope(client):
    """Served at /sw.js (not /static/...) so it can control "/"."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    assert b"addEventListener" in response.data
    # The privacy promise, pinned: the worker must never cache photo bytes.
    assert b"/photos/" not in response.data


def test_offline_page_is_public_standalone_and_content_free(client):
    response = client.get("/offline")
    assert response.status_code == 200
    assert b"offline" in response.data.lower()
    # Standalone shell: no navbar (whose links would 404 from cache) and
    # certainly no family content.
    assert b"navbar" not in response.data
    assert b"Log Out" not in response.data


def test_icons_exist_as_static_files(client):
    for name in ("icon-192.png", "icon-512.png", "icon-180.png"):
        response = client.get(f"/static/icons/{name}")
        assert response.status_code == 200, name
        assert response.content_type == "image/png"


def test_base_layout_advertises_the_pwa(client):
    """The login page (public) carries the manifest link + iPhone icon."""
    page = client.get("/auth/login").data
    assert b'rel="manifest"' in page
    assert b"apple-touch-icon" in page
    assert b"js/pwa.js" in page
