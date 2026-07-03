"""/api — Account↔Person link, "my person", self-edit, and the tree root (ADR-0002).

  * GET  /api/me/person                 — the current user's linked individual.
  * PUT  /api/me/person                 — edit your OWN person record (self-authoring).
  * GET  /api/tree/root                 — where the tree opens (linked or oldest ancestor).
  * PUT  /api/users/<id>/individual     — admin: link an account to a person.
  * DELETE /api/users/<id>/individual   — admin: unlink.

Thin controllers over account_service; the link operations are gated by the
``link_account`` permission (Admin), self-edit only by being logged in (it's your
own data).
"""

from flask import jsonify
from flask_login import current_user, login_required

from app.routes.api import api_bp, json_body
from app.services import account_service, permissions
from app.services.authz import permission_required


# --- The current user's person ------------------------------------------------

@api_bp.route("/me/person", methods=["GET"])
@login_required
def my_person():
    return jsonify(individual=account_service.my_person(current_user))


@api_bp.route("/me/person", methods=["PUT"])
@login_required  # any linked member may edit their OWN record (ADR-0002)
def update_my_person():
    return jsonify(account_service.self_update(current_user, json_body()))


@api_bp.route("/tree/root", methods=["GET"])
@login_required
def tree_root():
    """The individual the tree should open on: the caller's linked person, or the
    oldest ancestor if they're unlinked."""
    return jsonify(account_service.tree_root(current_user))


# --- Admin: link / unlink an account to a person ------------------------------

@api_bp.route("/users/<int:user_id>/individual", methods=["PUT"])
@permission_required(permissions.LINK_ACCOUNT)
def link_account(user_id):
    return jsonify(account_service.link(
        user_id, json_body().get("individual_id"), actor=current_user))


@api_bp.route("/users/<int:user_id>/individual", methods=["DELETE"])
@permission_required(permissions.LINK_ACCOUNT)
def unlink_account(user_id):
    return jsonify(account_service.unlink(user_id, actor=current_user))
