"""/api — dashboard stats and "On This Day" (Master Plan §4).

  * GET /api/stats           — aggregate counts + storage, for Home + Admin.
  * GET /api/on-this-day     — births/marriages/deaths sharing today's date.
  * GET /api/historical-events — the world/US almanac backdrop for the timeline.

All reads need any logged-in member.
"""

from flask import jsonify, request
from flask_login import login_required

from app.routes.api import api_bp
from app.services import historical_event_service, stats_service


@api_bp.route("/stats", methods=["GET"])
@login_required
def stats():
    return jsonify(stats_service.aggregate_stats())


@api_bp.route("/on-this-day", methods=["GET"])
@login_required
def on_this_day():
    """Today's family anniversaries, or a specific ?month=&day= (1-12 / 1-31)."""
    return jsonify(stats_service.on_this_day(
        month=request.args.get("month", type=int),
        day=request.args.get("day", type=int),
    ))


@api_bp.route("/historical-events", methods=["GET"])
@login_required
def historical_events():
    """The dated world/US almanac (each WITH a description) to blend into the
    timeline, optionally filtered by scope and year range."""
    return jsonify(historical_events=historical_event_service.list_events(
        scope=request.args.get("scope") or None,
        year_from=request.args.get("year_from", type=int),
        year_to=request.args.get("year_to", type=int),
    ))
