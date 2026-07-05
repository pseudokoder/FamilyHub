"""/api — write-control surface: the activity feed, restore, and revert (ADR-0001).

These are the endpoints that make post-moderation safe (Master Plan v2.0.0 §9):
  * GET  /api/activity              — the paginated, filterable audit trail (Curator+).
  * GET  /api/activity/feed         — friendly, ALL-MEMBERS "recent activity" (Home).
  * POST /api/restore               — un-delete a soft-deleted row.
  * POST /api/audit/<id>/revert     — undo the change an audit entry describes.

Reading the full trail needs at least Curator; the Home feed needs only ``view``
(any logged-in member) since it's filtered to safe, non-sensitive creates
(BLOCKERS.md, 2026-07-03). restore/revert need the ``revert`` permission (Curator+
per the permissions map). Thin controllers, as ever — all the logic lives in
write_control.
"""

from datetime import datetime

from flask import jsonify, request

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import permissions, write_control
from app.services.api_errors import ApiError
from app.services.authz import permission_required, role_required


def _parse_date(value, field):
    """Parse an ISO date/datetime query param, or raise a friendly 400."""
    if value is None or value == "":
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ApiError(f"{field} must be an ISO date (YYYY-MM-DD).", 400,
                       fields={field: "invalid"})


def _int_arg(name):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        raise ApiError(f"{name} must be a number.", 400, fields={name: "invalid"})


@api_bp.route("/activity", methods=["GET"])
@role_required(Role.CURATOR)  # the audit trail is a Curator/Admin view
def activity_feed():
    return jsonify(write_control.list_activity(
        action=request.args.get("action") or None,
        actor_id=_int_arg("actor_id"),
        subject_type=request.args.get("subject_type") or None,
        date_from=_parse_date(request.args.get("date_from"), "date_from"),
        date_to=_parse_date(request.args.get("date_to"), "date_to"),
        page=_int_arg("page") or 1,
        per_page=_int_arg("per_page") or 50,
    ))


def _subject_args():
    """Validate an optional subject_type/subject_id filter pair: both or
    neither — never one alone — and subject_type must be a real, known type.
    Mirrors genealogy_service.require_subject's "one gate" pattern, but for a
    read-side filter rather than a polymorphic write."""
    subject_type = request.args.get("subject_type") or None
    subject_id = _int_arg("subject_id")
    if (subject_type is None) != (subject_id is None):
        raise ApiError("subject_type and subject_id must be supplied together.",
                       400, fields={"subject_type": "required with subject_id"})
    if subject_type is not None and subject_type not in write_control.SUBJECT_MODELS:
        raise ApiError(
            f"subject_type must be one of: {', '.join(sorted(write_control.SUBJECT_MODELS))}.",
            400, fields={"subject_type": "invalid"})
    return subject_type, subject_id


@api_bp.route("/activity/feed", methods=["GET"])
@permission_required(permissions.VIEW)  # any logged-in member — deliberately NOT Curator+
def activity_member_feed():
    """The Home page's "recent activity" — friendly sentences over safe creates
    only (new people/photos/stories). Never deletes, reverts, or account/security
    actions — see write_control.member_feed for the exact filter. Optional
    ?subject_type=&subject_id= scopes it to one subject (e.g. a Person Page's
    Story tab wanting "recent activity about THIS person") — same pair-required
    pattern as /api/events, /api/notes, /api/media."""
    subject_type, subject_id = _subject_args()
    return jsonify(activity=write_control.member_feed(
        limit=_int_arg("limit") or 20,
        subject_type=subject_type, subject_id=subject_id,
    ))


@api_bp.route("/restore", methods=["POST"])
@permission_required(permissions.REVERT)
def restore():
    """Un-delete a soft-deleted record. Body: {subject_type, subject_id}."""
    data = json_body()
    subject_id = data.get("subject_id")
    if subject_id is None:
        raise ApiError("subject_id is required.", 400,
                       fields={"subject_id": "required"})
    return jsonify(write_control.restore(data.get("subject_type"), subject_id))


@api_bp.route("/audit/<int:audit_id>/revert", methods=["POST"])
@permission_required(permissions.REVERT)
def revert(audit_id):
    """Undo the change described by one audit entry (ADR-0001)."""
    return jsonify(result=write_control.revert(audit_id))
