"""/api/places — reusable place records (PLAC)."""

from flask import jsonify
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import place_service as svc
from app.services.authz import role_required


@api_bp.route("/places", methods=["GET"])
@login_required
def list_places():
    return jsonify(places=svc.list_all())


@api_bp.route("/places", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def create_place():
    return jsonify(svc.create(json_body())), 201


@api_bp.route("/places/<int:place_id>", methods=["GET"])
@login_required
def get_place(place_id):
    return jsonify(svc.get(place_id))


@api_bp.route("/places/<int:place_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_place(place_id):
    return jsonify(svc.update(place_id, json_body()))


@api_bp.route("/places/<int:place_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_place(place_id):
    svc.delete(place_id)
    return "", 204
