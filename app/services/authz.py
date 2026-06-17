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


def role_required(minimum):
    """Decorator: the view requires a logged-in, active account whose role is at
    least ``minimum`` on the ladder (GUEST < USER < POWER_USER < ADMIN).

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


# The common rungs, named once so routes read like English:
#   @admin_required            → ADMIN only
#   @role_required(Role.USER)  → any normal member or above (the CRUD default)
admin_required = role_required(Role.ADMIN)


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
