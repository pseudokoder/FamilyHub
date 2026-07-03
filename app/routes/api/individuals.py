"""/api/individuals — the INDI resource and its names sub-resource.

Look how THIN every view is: parse the body, call one service function, jsonify.
That's the @Controller's whole job — "translate HTTP <-> Python" — with the rules
living in individual_service (@Service). The same split lets v2 drop a Spring
@RestController on top of an identical service with no logic to re-derive.
"""

from flask import jsonify
from flask_login import login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import individual_service as svc
from app.services.authz import role_required


# --- Individuals --------------------------------------------------------------

@api_bp.route("/individuals", methods=["GET"])
@login_required  # reading family PII requires a logged-in member
def list_individuals():
    return jsonify(individuals=svc.list_all())


@api_bp.route("/individuals", methods=["POST"])
@role_required(Role.CONTRIBUTOR)  # writing requires at least a normal member (§10)
def create_individual():
    return jsonify(svc.create(json_body())), 201  # 201 Created


@api_bp.route("/individuals/<int:individual_id>", methods=["GET"])
@login_required
def get_individual(individual_id):
    return jsonify(svc.get(individual_id))


@api_bp.route("/individuals/<int:individual_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_individual(individual_id):
    return jsonify(svc.update(individual_id, json_body()))


@api_bp.route("/individuals/<int:individual_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_individual(individual_id):
    svc.delete(individual_id)
    return "", 204  # 204 No Content — deleted, nothing to return


# --- Names (a sub-resource of an individual) ----------------------------------

@api_bp.route("/individuals/<int:individual_id>/names", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def add_name(individual_id):
    return jsonify(svc.add_name(individual_id, json_body())), 201


@api_bp.route("/names/<int:name_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_name(name_id):
    return jsonify(svc.update_name(name_id, json_body()))


@api_bp.route("/names/<int:name_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_name(name_id):
    svc.delete_name(name_id)
    return "", 204
