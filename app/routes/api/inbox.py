"""/api — the suggestions inbox and role-change requests (Master Plan §5, §10).

  * POST /api/suggestions              — any member submits an idea/bug/request.
  * GET  /api/suggestions              — admin inbox (filters + prioritized queue).
  * PUT  /api/suggestions/<id>         — admin: set status / priority.
  * POST /api/role-requests            — member asks for a role.
  * GET  /api/role-requests            — admin lists (filter by status).
  * POST /api/role-requests/<id>/approve|deny — admin decides.

Submitting needs any logged-in member; triage/decisions need Admin.
"""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.routes.api import api_bp, json_body
from app.services import role_request_service, suggestion_service
from app.services.authz import admin_required


# --- Suggestions --------------------------------------------------------------

@api_bp.route("/suggestions", methods=["POST"])
@login_required
def submit_suggestion():
    data = json_body()
    return jsonify(suggestion_service.submit(
        current_user, data.get("topic"), data.get("body"))), 201


@api_bp.route("/suggestions", methods=["GET"])
@admin_required
def list_suggestions():
    return jsonify(suggestions=suggestion_service.list_all(
        status=request.args.get("status") or None,
        topic=request.args.get("topic") or None,
        prioritized=request.args.get("prioritized") in ("1", "true", "yes"),
    ))


@api_bp.route("/suggestions/<int:suggestion_id>", methods=["PUT"])
@admin_required
def update_suggestion(suggestion_id):
    return jsonify(suggestion_service.update(suggestion_id, json_body()))


# --- Role-change requests -----------------------------------------------------

@api_bp.route("/role-requests", methods=["POST"])
@login_required
def submit_role_request():
    return jsonify(role_request_service.submit(
        current_user, json_body().get("requested_role"))), 201


@api_bp.route("/role-requests", methods=["GET"])
@admin_required
def list_role_requests():
    return jsonify(role_requests=role_request_service.list_all(
        status=request.args.get("status") or None))


@api_bp.route("/role-requests/<int:request_id>/approve", methods=["POST"])
@admin_required
def approve_role_request(request_id):
    return jsonify(role_request_service.approve(request_id, current_user))


@api_bp.route("/role-requests/<int:request_id>/deny", methods=["POST"])
@admin_required
def deny_role_request(request_id):
    return jsonify(role_request_service.deny(request_id, current_user))
