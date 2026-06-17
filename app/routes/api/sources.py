"""/api/repositories and /api/sources — the evidence documents."""

from flask import jsonify
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import source_service as svc
from app.services.authz import role_required


# --- Repositories -------------------------------------------------------------

@api_bp.route("/repositories", methods=["GET"])
@login_required
def list_repositories():
    return jsonify(repositories=svc.list_repositories())


@api_bp.route("/repositories", methods=["POST"])
@role_required(Role.USER)
def create_repository():
    return jsonify(svc.create_repository(json_body())), 201


@api_bp.route("/repositories/<int:repo_id>", methods=["GET"])
@login_required
def get_repository(repo_id):
    return jsonify(svc.get_repository(repo_id))


@api_bp.route("/repositories/<int:repo_id>", methods=["PUT"])
@role_required(Role.USER)
def update_repository(repo_id):
    return jsonify(svc.update_repository(repo_id, json_body()))


@api_bp.route("/repositories/<int:repo_id>", methods=["DELETE"])
@role_required(Role.USER)
def delete_repository(repo_id):
    svc.delete_repository(repo_id)
    return "", 204


# --- Sources ------------------------------------------------------------------

@api_bp.route("/sources", methods=["GET"])
@login_required
def list_sources():
    return jsonify(sources=svc.list_sources())


@api_bp.route("/sources", methods=["POST"])
@role_required(Role.USER)
def create_source():
    return jsonify(svc.create_source(json_body())), 201


@api_bp.route("/sources/<int:source_id>", methods=["GET"])
@login_required
def get_source(source_id):
    return jsonify(svc.get_source(source_id))


@api_bp.route("/sources/<int:source_id>", methods=["PUT"])
@role_required(Role.USER)
def update_source(source_id):
    return jsonify(svc.update_source(source_id, json_body()))


@api_bp.route("/sources/<int:source_id>", methods=["DELETE"])
@role_required(Role.USER)
def delete_source(source_id):
    svc.delete_source(source_id)
    return "", 204
