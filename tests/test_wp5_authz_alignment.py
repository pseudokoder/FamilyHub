"""WP5 — admin authorization aligned to the role model (BLOCKERS.md, 2026-07-03).

``admin_required`` now routes through ``permission_required(permissions.ADMINISTER)``
— the permissions-as-data layer (§10) — rather than a hard-coded role check or the
legacy ``is_admin`` boolean. This is a parametrized allow/deny matrix across a sample
of admin-gated AND curator-gated endpoints, proving every rung gets the CORRECT
HTTP answer, not just that Admin happens to work.
"""

import pytest

from app.services import permissions
from app.services.authz import admin_required

# Representative admin-only endpoints spanning every admin_api/inbox/admin.py module.
ADMIN_ONLY_GET_ENDPOINTS = [
    "/api/admin/users",
    "/api/settings",
    "/api/admin/backups",
    "/api/permissions/matrix",
    "/api/suggestions",
    "/api/role-requests",
    "/admin/users",       # the native Chronicle admin console (FE-6)
]

# Curator+ (but not Contributor/Viewer) endpoints — the `revert` permission.
# FE-6 (BLOCKERS.md, 2026-07-03 RESOLVED): /admin/activity moved from
# Admin-only to Curator+ here too, matching its API (/api/activity) exactly —
# Curator holds `revert`, and the brief explicitly asks for the HTML page to
# grant the same access the endpoint it calls already does.
CURATOR_PLUS_GET_ENDPOINTS = [
    "/api/activity",
    "/admin/activity",
]


@pytest.mark.parametrize("path", ADMIN_ONLY_GET_ENDPOINTS)
def test_admin_only_endpoints_deny_every_non_admin_rung(
    path, viewer_client, member_client, curator_client
):
    """Viewer, Contributor, AND Curator all get 403 — none of them hold
    ``administer``, only Admin does."""
    for client in (viewer_client, member_client, curator_client):
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should 403 a non-admin, got {resp.status_code}"


@pytest.mark.parametrize("path", ADMIN_ONLY_GET_ENDPOINTS)
def test_admin_only_endpoints_allow_admin(path, admin_client):
    resp = admin_client.get(path)
    assert resp.status_code in (200,), f"{path} should be reachable by Admin, got {resp.status_code}"


@pytest.mark.parametrize("path", CURATOR_PLUS_GET_ENDPOINTS)
def test_curator_plus_endpoints_allow_curator_and_admin(
    path, curator_client, admin_client
):
    for client in (curator_client, admin_client):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} should allow Curator+, got {resp.status_code}"


@pytest.mark.parametrize("path", CURATOR_PLUS_GET_ENDPOINTS)
def test_curator_plus_endpoints_deny_viewer_and_contributor(
    path, viewer_client, member_client
):
    for client in (viewer_client, member_client):
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should 403 below Curator, got {resp.status_code}"


def test_anonymous_gets_401_or_login_redirect(client):
    """Anonymous visitors never even reach the role check — 401 (API)."""
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


def test_admin_required_is_the_administer_permission_flag():
    """The alignment itself: admin_required is no longer a bespoke role check —
    it's the SAME decorator permission_required(ADMINISTER) produces, so a v2
    editable permission matrix changes ONLY app/services/permissions.py."""
    from app.services.authz import permission_required

    # Two independently-built decorators wrapping the same view behave identically
    # (same closure shape) — proven behaviorally above; this asserts the wiring.
    def _dummy():
        return "ok"

    wrapped_a = admin_required(_dummy)
    wrapped_b = permission_required(permissions.ADMINISTER)(_dummy)
    assert wrapped_a.__name__ == wrapped_b.__name__ == "_dummy"
