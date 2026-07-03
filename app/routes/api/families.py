"""/api/families — the FAM resource and its children sub-resource."""

from flask import jsonify
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import family_service as svc
from app.services.authz import role_required


@api_bp.route("/families", methods=["GET"])
@login_required
def list_families():
    return jsonify(families=svc.list_all())


@api_bp.route("/families", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def create_family():
    return jsonify(svc.create(json_body())), 201


@api_bp.route("/families/<int:family_id>", methods=["GET"])
@login_required
def get_family(family_id):
    return jsonify(svc.get(family_id))


@api_bp.route("/families/<int:family_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_family(family_id):
    return jsonify(svc.update(family_id, json_body()))


@api_bp.route("/families/<int:family_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_family(family_id):
    svc.delete(family_id)
    return "", 204


@api_bp.route("/families/<int:family_id>/children", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def add_child(family_id):
    return jsonify(svc.add_child(family_id, json_body())), 201


@api_bp.route("/families/<int:family_id>/children/<int:child_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def remove_child(family_id, child_id):
    svc.remove_child(family_id, child_id)
    return "", 204
