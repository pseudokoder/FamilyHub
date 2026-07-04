"""The People blueprint: find/register/browse pages (Master Plan §4, WP4).

Thin controllers, same as every other route in this app (CLAUDE.md's layered
architecture): every one of these views just renders a template. The actual
data comes from the browser calling the WP2 JSON API (docs/openapi.yaml)
with fetch() — see app/static/js/people.js. That split is deliberate: it's
the same JSON contract a v2 Angular @Component would call, so nothing here
is thrown away in the rewrite.

v2 mapping: PeopleController.java, each @GetMapping returning a Thymeleaf-free
view name for Angular's router to mount a component on.
"""

from flask import Blueprint, render_template
from flask_login import login_required

people_bp = Blueprint("people", __name__, url_prefix="/people")


@people_bp.route("")
@login_required
def index():
    """Find a person + browse the register. All data loads via people.js
    calling GET /api/search (see FRONTEND_DESIGN.md for why search doubles
    as the browse-everyone list: with no filters it returns everyone)."""
    return render_template("people/index.html")


@people_bp.route("/new")
@login_required
def new():
    """The depth-complete register-a-person form (Master Plan §5A). Submits
    via JS to POST /api/individuals (+ /api/places, /api/events for vitals),
    not a Flask POST route — this view only ever renders the form."""
    return render_template("people/new.html")


@people_bp.route("/<int:individual_id>")
@login_required
def show(individual_id):
    """The Person Page. A placeholder for now — Master Plan says this is a
    LATER FE prompt (FE-2) — but it's a real, resource-oriented route already,
    so every People-list row and search result has a stable link that never
    breaks when FE-2 fills this in."""
    return render_template("people/show.html", individual_id=individual_id)
