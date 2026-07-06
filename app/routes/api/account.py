"""/api — Account↔Person link, "my person", self-edit, and the tree root (ADR-0002).

  * GET  /api/me                        — my own account snapshot (FE-5).
  * PUT  /api/me                        — edit display_name/timezone (self-serve).
  * GET  /api/me/contributions          — my own audit rows + summary (FE-5).
  * POST /api/me/change-email           — self-serve change-email (verify-then-apply).
  * POST /api/me/delete                 — "delete my account" = anonymize, never erase.
  * GET  /api/me/person                 — the current user's linked individual.
  * PUT  /api/me/person                 — edit your OWN person record (self-authoring).
  * GET  /api/tree/root                 — where the tree opens (linked or oldest ancestor).
  * PUT  /api/users/<id>/individual     — admin: link an account to a person.
  * DELETE /api/users/<id>/individual   — admin: unlink.

Thin controllers over account_service; the link operations are gated by the
``link_account`` permission (Admin), self-edit only by being logged in (it's your
own data).
"""

from flask import jsonify, request, url_for
from flask_login import current_user, login_required, logout_user

from app.routes.api import api_bp, json_body, require
from app.services import account_service, mail_service, permissions, user_service, write_control
from app.services.api_errors import ApiError
from app.services.authz import permission_required


def _int_arg(name):
    """A query-string int, or None — same tiny parser activity.py uses, kept
    local here so this module doesn't reach into another route module."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        raise ApiError(f"{name} must be a number.", 400, fields={name: "invalid"})


# --- The Account & Security page (FE-5) ----------------------------------------

@api_bp.route("/me", methods=["GET"])
@login_required
def my_account():
    return jsonify(account_service.me_snapshot(current_user))


@api_bp.route("/me", methods=["PUT"])
@login_required
def update_my_account():
    return jsonify(account_service.update_me(current_user, json_body()))


@api_bp.route("/me/contributions", methods=["GET"])
@login_required
def my_contributions():
    """My Contributions dashboard: MY OWN audit rows only — actor is always the
    session user, with no ``actor_id`` parameter anywhere in this path (that
    would be a side door into the Curator-only /api/activity trail)."""
    return jsonify(write_control.my_activity(
        current_user,
        action=request.args.get("action") or None,
        subject_type=request.args.get("subject_type") or None,
        page=_int_arg("page") or 1,
        per_page=_int_arg("per_page") or 50,
    ))


@api_bp.route("/me/change-email", methods=["POST"])
@login_required
def change_my_email():
    data = json_body()
    require(data, "new_email", "current_password")
    return jsonify(account_service.request_email_change(
        current_user, data["new_email"], data["current_password"]))


@api_bp.route("/me/delete", methods=["POST"])
@login_required
def delete_me():
    data = json_body()
    require(data, "current_password")
    result = account_service.delete_my_account(current_user, data["current_password"])
    logout_user()
    return jsonify(result)


# --- The current user's person ------------------------------------------------

@api_bp.route("/me/person", methods=["GET"])
@login_required
def my_person():
    return jsonify(individual=account_service.my_person(current_user))


@api_bp.route("/me/person", methods=["PUT"])
@login_required  # any linked member may edit their OWN record (ADR-0002)
def update_my_person():
    return jsonify(account_service.self_update(current_user, json_body()))


@api_bp.route("/me/verify-email", methods=["POST"])
@login_required
def send_my_verification():
    """Email the current user a link to verify their own address (§9)."""
    if not mail_service.is_configured():
        raise ApiError("Email isn't set up on this server yet.", 503)
    if current_user.email_verified:
        return jsonify(status="already_verified")
    token = user_service.generate_email_verify_token(current_user)
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    mail_service.send_email_verification(current_user, verify_url)
    return jsonify(status="sent")


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
