"""role_request_service — members request elevated access; admins rule (§5, §10).

Approval applies the role change THROUGH the audited ``user_service.set_role`` — so
an elevation is as traceable as any other change (ADR-0001), and the request row is
the standing record of who asked, who decided, and when.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import RoleRequest
from app.models.role import Role
from app.services import api_errors, user_service


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def serialize(r):
    return {
        "id": r.id,
        "user_id": r.user_id,
        "user": r.user.display_name if r.user else None,
        "requested_role": r.requested_role,
        "status": r.status,
        "decided_by_user_id": r.decided_by_user_id,
        "decided_by": r.decided_by.display_name if r.decided_by else None,
        "created_at": _iso(r.created_at),
        "decided_at": _iso(r.decided_at),
    }


def submit(user, requested_role):
    """A member asks to become ``requested_role``. Validates the role is real and
    is actually a change; blocks a second pending request (no queue-spamming)."""
    try:
        role = Role(requested_role)
    except (ValueError, TypeError):
        raise api_errors.ApiError(
            "requested_role must be a valid role.", 400,
            fields={"requested_role": "invalid"})
    if role.value == user.role:
        raise api_errors.ApiError("You already have that role.", 400,
                                  fields={"requested_role": "no change"})
    existing = (RoleRequest.query
                .filter_by(user_id=user.id, status="pending").first())
    if existing is not None:
        raise api_errors.ApiError(
            "You already have a pending role request.", 409)
    request = RoleRequest(user_id=user.id, requested_role=role.value,
                          status="pending")
    db.session.add(request)
    db.session.commit()
    return serialize(request)


def list_all(status=None):
    query = RoleRequest.query
    if status:
        query = query.filter(RoleRequest.status == status)
    return [serialize(r) for r in
            query.order_by(RoleRequest.created_at.desc()).all()]


def _get_pending(request_id):
    r = db.session.get(RoleRequest, request_id)
    if r is None:
        raise api_errors.ApiError(
            f"No role request found with id {request_id}.", 404)
    if r.status != "pending":
        raise api_errors.ApiError("That request has already been decided.", 409)
    return r


def approve(request_id, admin):
    """Admin approves: apply the role change (audited) and stamp the decision."""
    r = _get_pending(request_id)
    if r.user is not None:
        user_service.set_role(r.user, r.requested_role, actor=admin)
    r.status = "approved"
    r.decided_by_user_id = admin.id if admin is not None else None
    r.decided_at = datetime.now(timezone.utc)
    db.session.commit()
    return serialize(r)


def deny(request_id, admin):
    """Admin denies: no role change, just a recorded decision."""
    r = _get_pending(request_id)
    r.status = "denied"
    r.decided_by_user_id = admin.id if admin is not None else None
    r.decided_at = datetime.now(timezone.utc)
    db.session.commit()
    return serialize(r)
