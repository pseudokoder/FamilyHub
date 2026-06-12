"""Spec-sync tests: the OpenAPI file can never quietly drift.

The big one walks Flask's LIVE route map and fails if any route is
missing from docs/openapi.yaml — add a route without documenting it and
the build goes red. (This is how API-first stays true after day one.)
"""

import re

from app.services import spec_service

# Routes that aren't part of the application's API surface.
NOT_API = {
    "/static/<path:filename>",            # Flask's static machinery
    "/bootstrap/static/<path:filename>",  # Bootstrap-Flask's static blueprint
}


def _flask_rule_to_openapi(rule):
    """Flask writes /photos/<int:photo_id>; OpenAPI writes
    /photos/{photo_id}. Converters (int:, path:) vanish."""
    return re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", rule)


def test_every_route_is_documented(app):
    with app.app_context():
        spec_paths = set(spec_service.load_spec()["paths"].keys())
    missing = []
    for rule in app.url_map.iter_rules():
        if rule.rule in NOT_API:
            continue
        openapi_path = _flask_rule_to_openapi(rule.rule)
        if openapi_path not in spec_paths:
            missing.append(rule.rule)
    assert not missing, f"Routes missing from docs/openapi.yaml: {missing}"


def test_spec_parses_and_has_the_basics(app):
    with app.app_context():
        spec = spec_service.load_spec()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "FamilyHub API"
    assert len(spec["paths"]) >= 40


def test_apidocs_page_renders(admin_client):
    page = admin_client.get("/apidocs")
    assert page.status_code == 200
    assert b"FamilyHub API" in page.data
    assert b"/albums/{album_id}/reorder" in page.data

    raw = admin_client.get("/openapi.yaml")
    assert raw.status_code == 200
    assert raw.content_type.startswith("text/yaml")
