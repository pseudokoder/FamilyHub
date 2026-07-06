"""The Search blueprint: quick + advanced search (Master Plan §4/§12, FE-4).

One thin controller, same rule as every other route in this app: the page
just renders a shell; all data comes from the browser calling GET
/api/search (docs/openapi.yaml) with fetch() — see app/static/js/search.js.

v2 mapping: SearchController.java, one @GetMapping returning a Thymeleaf-
free view name for Angular's router to mount a component on.
"""

from flask import Blueprint, render_template
from flask_login import login_required

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.route("")
@login_required
def index():
    """Quick search (default) + Advanced search, hash-switched on one page
    (#quick/#advanced) — same URL-hash tab pattern as the Person Page."""
    return render_template("search/index.html")
