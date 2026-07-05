"""The Tree blueprint: Pedigree, Family Group, and Relationship view pages
(Master Plan §4, FE-3).

Thin controllers, same rule as every other route in this app (CLAUDE.md's
layered architecture): each view just renders a shell template. All data
comes from the browser calling the WP2 JSON API (docs/openapi.yaml) with
fetch() — see app/static/js/tree.js. One blueprint, three resource-oriented
routes (pedigree is the bare /tree default; family and relationship each get
their own path) rather than one hash-switched page, so every family sheet and
relationship query has its own shareable, bookmarkable URL.

v2 mapping: TreeController.java, each @GetMapping returning a Thymeleaf-free
view name for Angular's router to mount a component on.
"""

from flask import Blueprint, render_template
from flask_login import login_required

tree_bp = Blueprint("tree", __name__, url_prefix="/tree")


@tree_bp.route("")
@login_required
def pedigree():
    """The default Tree view: a vertical ancestor pedigree. Root person comes
    from GET /api/tree/root unless a ?root= query param recenters it — see
    app/static/js/tree.js. The template carries no root id itself so a
    recenter is a client-side URL change (history.pushState), not a
    server round-trip."""
    return render_template("tree/pedigree.html")


@tree_bp.route("/family/<int:family_id>")
@login_required
def family(family_id):
    """One Family Group sheet — both partners, marriage/divorce events, and
    children in birth order. Reachable from a pedigree node's family context
    or directly by this URL."""
    return render_template("tree/family.html", family_id=family_id)


@tree_bp.route("/relationship")
@login_required
def relationship():
    """The Relationship Finder: two person pickers over GET /api/search, the
    plain-English label + hop-by-hop chain from GET
    /api/individuals/{a}/relationship/{b}. ?a=/?b= pre-fill the pickers (the
    Person Page's "View Relationship" button sets ?a= to itself)."""
    return render_template("tree/relationship.html")
