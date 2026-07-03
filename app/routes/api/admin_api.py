"""/api — admin actions (Master Plan §9, §10). All Admin-gated JSON.

  * GET  /api/admin/users                         — accounts (role + linked status).
  * POST /api/admin/users/<id>/reset-password     — email them a reset link.
  * POST /api/admin/users/<id>/change-email       — secure change-email (step-up).
  * GET/PUT /api/settings                         — config CRUD (grouped).
  * GET  /api/admin/backups                       — detail (sizes, disk, schedule).
  * POST /api/admin/backups/run                   — back up now.
  * PUT  /api/admin/backups/schedule              — schedule config.
  * POST /api/admin/backups/restore               — guarded restore (confirm + step-up).
  * GET  /api/permissions/matrix                  — read-only role→permission map.

Thin controllers over admin_service / settings_service / permissions.
"""

from flask import jsonify
from flask_login import current_user

from app.routes.api import api_bp, json_body, require
from app.services import admin_service, permissions, settings_service
from app.services.api_errors import ApiError
from app.services.authz import admin_required


# --- Users --------------------------------------------------------------------

@api_bp.route("/admin/users", methods=["GET"])
@admin_required
def admin_users():
    return jsonify(users=admin_service.list_users())


@api_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    admin_service.send_password_reset_email(admin_service._get_user(user_id))
    return jsonify(status="reset_email_sent")


@api_bp.route("/admin/users/<int:user_id>/change-email", methods=["POST"])
@admin_required
def admin_change_email(user_id):
    data = json_body()
    require(data, "new_email", "current_password")
    try:
        result = admin_service.change_user_email(
            current_user, user_id, data["new_email"], data["current_password"])
    except ValueError as err:            # duplicate email from user_service
        raise ApiError(str(err), 400, fields={"new_email": "in use"})
    return jsonify(result)


# --- Site settings CRUD -------------------------------------------------------

@api_bp.route("/settings", methods=["GET"])
@admin_required
def get_settings():
    return jsonify(settings_service.editable_settings())


@api_bp.route("/settings", methods=["PUT"])
@admin_required
def update_settings():
    try:
        updated = settings_service.update_settings(json_body())
    except ValueError as err:
        raise ApiError(str(err), 400)
    from app.services import audit_service
    from app.extensions import db
    audit_service.log_event(current_user, "edit", "site settings")
    db.session.commit()
    return jsonify(updated)


# --- Backups ------------------------------------------------------------------

@api_bp.route("/admin/backups", methods=["GET"])
@admin_required
def admin_backups():
    return jsonify(admin_service.backup_overview())


@api_bp.route("/admin/backups/run", methods=["POST"])
@admin_required
def admin_run_backup():
    return jsonify(admin_service.run_backup_now(current_user))


@api_bp.route("/admin/backups/schedule", methods=["PUT"])
@admin_required
def admin_backup_schedule():
    return jsonify(admin_service.set_backup_schedule(json_body()))


@api_bp.route("/admin/backups/restore", methods=["POST"])
@admin_required
def admin_restore_backup():
    data = json_body()
    require(data, "filename", "current_password")
    return jsonify(admin_service.restore_backup(
        current_user, data["filename"], data["current_password"],
        confirm=bool(data.get("confirm")),
    ))


# --- Read-only permission matrix ----------------------------------------------

@api_bp.route("/permissions/matrix", methods=["GET"])
@admin_required
def permission_matrix():
    """The permissions-as-data map for the admin Users tab (§10). Read-only in v1;
    editable roles are v2."""
    return jsonify(permissions=list(permissions.ALL_PERMISSIONS),
                   matrix=permissions.matrix())
