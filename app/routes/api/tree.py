"""/api — pedigree traversal and the relationship finder (Master Plan §4).

  * GET /api/individuals/<id>/pedigree            — a bounded graph slice from ANY
    node (ancestors and/or descendants, ``depth`` generations, lazy-expandable).
  * GET /api/individuals/<a>/relationship/<b>     — shortest blood path + a
    plain-English label ("1st cousin once removed").

Thin controllers over tree_service; reads need any logged-in member.
"""

from flask import jsonify, request
from flask_login import login_required

from app.routes.api import api_bp
from app.services import tree_service


@api_bp.route("/individuals/<int:individual_id>/pedigree", methods=["GET"])
@login_required
def pedigree(individual_id):
    return jsonify(tree_service.graph(
        individual_id,
        direction=request.args.get("direction", "both"),
        depth=request.args.get("depth", default=3, type=int),
    ))


@api_bp.route("/individuals/<int:a_id>/relationship/<int:b_id>", methods=["GET"])
@login_required
def relationship(a_id, b_id):
    return jsonify(tree_service.relationship(a_id, b_id))
