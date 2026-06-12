"""Search route: GET /search?q=ruth — thin, like every route here.

RESTful note for v2: search is a GET with the query in the URL, never a
POST. That makes results bookmarkable, shareable ("look what I found —
sends the link"), and back-button friendly. The Angular frontend will call
the same URL and get JSON from a SearchController.

v2 mapping: SearchController.java calling SearchService.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services import search_service

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
@login_required  # results are family content — PII stays behind the wall
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        # Forgiving, not scolding: a single letter would match half the
        # archive and help nobody. Nudge and send them home.
        flash("Type at least two letters into the search box, then try again.", "warning")
        return redirect(url_for("main.home"))

    results = search_service.search_all(query)
    total = sum(len(section) for section in results.values())
    return render_template(
        "search/results.html", query=query, results=results, total=total
    )
