"""/api/events — events & attributes, attachable to a person or a family.

GET /api/events?subject_type=individual&subject_id=5 returns that person's
events in timeline order — the query the WP4 timeline view will build on.
"""

from flask import jsonify, request
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import event_service as svc
from app.services.authz import role_required


@api_bp.route("/events", methods=["GET"])
@login_required
def list_events():
    # Optional filter to one subject (?subject_type=…&subject_id=…).
    subject_type = request.args.get("subject_type")
    subject_id = request.args.get("subject_id", type=int)
    return jsonify(events=svc.list_all(subject_type, subject_id))


@api_bp.route("/events", methods=["POST"])
@role_required(Role.USER)
def create_event():
    return jsonify(svc.create(json_body())), 201


@api_bp.route("/events/<int:event_id>", methods=["GET"])
@login_required
def get_event(event_id):
    return jsonify(svc.get(event_id))


@api_bp.route("/events/<int:event_id>", methods=["PUT"])
@role_required(Role.USER)
def update_event(event_id):
    return jsonify(svc.update(event_id, json_body()))


@api_bp.route("/events/<int:event_id>", methods=["DELETE"])
@role_required(Role.USER)
def delete_event(event_id):
    svc.delete(event_id)
    return "", 204
