"""The Account blueprint: My Contributions + Account & Security (FE-5).

Thin controllers, same rule as every other route in this app (CLAUDE.md's
layered architecture) and the exact pattern memories.py/search.py/tree.py
already established: each view just renders a shell template. All data comes
from the browser calling the WP2 JSON API (docs/openapi.yaml) with fetch() —
see app/static/js/account.js.

Both pages act on the SESSION's OWN account only — there is no id in either
URL, so there's no path from these routes into another member's data (the
`/api/me/*` endpoints these pages call enforce the same rule server-side).

v2 mapping: AccountController.java, each @GetMapping returning a Thymeleaf-
free view name for Angular's router to mount a component on.
"""

from flask import Blueprint, render_template
from flask_login import login_required

account_bp = Blueprint("account", __name__, url_prefix="/account")


@account_bp.route("")
@login_required
def security():
    """Account & Security: profile (display name/timezone), role badge +
    request-a-role-change, email (verify/change), password (links to the
    existing /auth/change-password flow), and delete-my-account (anonymize).
    Client-rendered against GET /api/me + the rest of the Account tag."""
    return render_template("account/security.html")


@account_bp.route("/contributions")
@login_required
def contributions():
    """My Contributions: a member's own audit rows (GET /api/me/contributions)
    — summary cards, then a paginated, filterable list, newest first."""
    return render_template("account/contributions.html")
