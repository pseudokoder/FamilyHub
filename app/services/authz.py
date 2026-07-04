"""authz — the ONE place every permission decision is made (Master Plan §10).

THE ANTI-LOCK-IN PRINCIPLE: route every "are you allowed?" check through a single
layer, so adding roles or granular per-feature permissions later is a change in
ONE file, not a hunt-and-peck across forty routes. Today that layer is the
``role_required`` decorator; tomorrow it can grow a ``can(user, action, resource)``
function without any route having to change how it asks.

v2 mapping: this whole module collapses into Spring Security annotations —
``@role_required(Role.ADMIN)`` is exactly ``@PreAuthorize("hasRole('ADMIN')")``,
and the unauthorized/forbidden handling below is Spring's
AuthenticationEntryPoint / AccessDeniedHandler.
"""

from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user

from app.extensions import login_manager
from app.models.role import Role
from app.services import permissions


def role_required(minimum):
    """Decorator: the view requires a logged-in, active account whose role is at
    least ``minimum`` on the ladder (VIEWER < CONTRIBUTOR < CURATOR < ADMIN).

    Three outcomes, each the *correct* HTTP answer:
      * not logged in        → 401 (API) or a redirect to the login page (web)
      * logged in, too junior → 403 Forbidden ("I know who you are; no")
      * logged in, allowed    → the view runs
    """

    def decorator(view):
        @wraps(view)  # keep the name so url_for() still finds the view
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                # Delegate to the shared unauthorized handler (below) so API and
                # web requests each get the right kind of "please log in".
                return login_manager.unauthorized()
            # is_active is enforced at login too, but re-check here: an account
            # could be deactivated mid-session.
            if not current_user.is_active or not current_user.has_role(minimum):
                return _forbidden()
            return view(*args, **kwargs)

        return wrapped

    return decorator


def permission_required(permission):
    """Decorator: the view requires a logged-in, active account that HOLDS a
    specific permission flag (see app/services/permissions.py).

    This is the permissions-as-data half of the authorization layer (§10). Where
    ``role_required`` asks "are you high enough on the ladder?", this asks "does
    your role's *bundle* include this capability?" — the same question v2 will
    answer from an editable ``role_permissions`` table without touching any route.

    Same three outcomes as ``role_required``: 401 (not logged in), 403 (logged in
    but the permission isn't in your bundle), or the view runs.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not permissions.can(current_user, permission):
                return _forbidden()
            return view(*args, **kwargs)

        return wrapped

    return decorator


# THE ADMIN GATE, aligned to the role model (BLOCKERS.md, 2026-07-03): every
# admin-only view requires the ``administer`` permission flag — today held by
# ONLY the Admin role (see permissions.ROLE_PERMISSIONS) — rather than the
# legacy ``current_user.is_admin`` boolean shim on the User model. That shim
# still exists for display/back-compat (e.g. templates showing an "Admin"
# badge), but no ROUTE should gate on it: gating here means a future custom
# role can hold ``administer`` by editing DATA (v2's editable permission
# matrix), with no route ever changing. Curator sits just below — it holds
# ``revert`` (the audit trail + restore/undo), not ``administer``.
admin_required = permission_required(permissions.ADMINISTER)


def _wants_json():
    """True for our JSON API surface. The contract is path-based (/api/...) so
    it's predictable and doesn't depend on a client remembering an Accept
    header."""
    return request.path.startswith("/api/")


def _forbidden():
    """403 as JSON for the API, as a friendly page for the web."""
    if _wants_json():
        return jsonify(error="You don't have permission to do that."), 403
    # The app-level 403 errorhandler renders the friendly page; raising keeps
    # that single presentation in one place.
    from flask import abort
    abort(403)


@login_manager.unauthorized_handler
def _unauthorized():
    """What happens when an anonymous visitor hits a protected view.

    API callers get a clean 401 JSON (a redirect to an HTML login form would
    just confuse a fetch() call). Everyone else gets Flask-Login's friendly
    bounce to the login page with a ?next= so they land where they meant to."""
    if _wants_json():
        return jsonify(error="Please log in to do that."), 401
    flash(login_manager.login_message, login_manager.login_message_category)
    return redirect(url_for(login_manager.login_view, next=request.full_path))
