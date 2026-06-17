"""/api/citations — the polymorphic links from facts to sources."""

from flask import jsonify, request
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import citation_service as svc
from app.services.authz import role_required


@api_bp.route("/citations", methods=["GET"])
@login_required
def list_citations():
    # Optional ?subject_type=…&subject_id=… → the evidence behind one record.
    return jsonify(citations=svc.list_all(
        request.args.get("subject_type"),
        request.args.get("subject_id", type=int),
    ))


@api_bp.route("/citations", methods=["POST"])
@role_required(Role.USER)
def create_citation():
    return jsonify(svc.create(json_body())), 201


@api_bp.route("/citations/<int:citation_id>", methods=["GET"])
@login_required
def get_citation(citation_id):
    return jsonify(svc.get(citation_id))


@api_bp.route("/citations/<int:citation_id>", methods=["PUT"])
@role_required(Role.USER)
def update_citation(citation_id):
    return jsonify(svc.update(citation_id, json_body()))


@api_bp.route("/citations/<int:citation_id>", methods=["DELETE"])
@role_required(Role.USER)
def delete_citation(citation_id):
    svc.delete(citation_id)
    return "", 204
