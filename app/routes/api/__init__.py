"""The ``/api`` blueprint — FamilyHub's JSON REST surface (the WP2 contract).

This is the stable interface Cowork builds the WP3 front-end against (Master Plan
§7) and the shape v2's Angular app will consume almost unchanged. Every route in
this package is a thin **controller**: it parses the request, calls ONE service
function, and ``jsonify``s the result. All the thinking lives in the services.

DESIGN of the surface:
  * Resource-oriented URLs: ``/api/individuals``, ``/api/individuals/<id>`` …
  * Standard verbs: GET (read), POST (create → 201), PUT (update), DELETE (→ 204).
  * Reads require any logged-in member; writes require at least USER (§10),
    enforced by the one authorization layer (app/services/authz.py).
  * Errors are uniform JSON: ``{"error": "...", "fields": {...}}`` with the right
    status — see ApiError. That uniformity is what makes the contract usable.

v2 mapping: this blueprint ≈ a set of Spring Boot ``@RestController`` classes;
the error handlers below ≈ a ``@ControllerAdvice``.
"""

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.services.api_errors import ApiError

api_bp = Blueprint("api", __name__, url_prefix="/api")


# --- Uniform error handling ---------------------------------------------------

@api_bp.errorhandler(ApiError)
def _handle_api_error(err):
    payload = {"error": err.message}
    if err.fields:
        payload["fields"] = err.fields
    return jsonify(payload), err.status


@api_bp.errorhandler(404)
def _api_not_found(err):
    return jsonify(error="Not found."), 404


@api_bp.errorhandler(405)
def _api_method_not_allowed(err):
    return jsonify(error="That method isn't allowed on this URL."), 405


# --- Request helpers (keep every route a one-liner of parsing) ----------------

def json_body():
    """The request's JSON object, or ``{}`` — never raise on a missing or
    malformed body. We validate the FIELDS explicitly below and return friendly
    messages, which beats a bare 'invalid JSON' 500."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def require(data, *fields):
    """Raise a 400 ApiError naming any required field that's missing or blank."""
    missing = {
        name: "required"
        for name in fields
        if data.get(name) is None
        or (isinstance(data.get(name), str) and not data.get(name).strip())
    }
    if missing:
        raise ApiError("Some required fields are missing.", 400, fields=missing)


def one_of(data, field, allowed, required=False):
    """Validate that ``data[field]`` (if present) is in the ``allowed`` set —
    the guard for the schema's closed enums (sex, pedigree_type, …). Returns the
    value (or None). Raises 400 with a helpful list on a bad value."""
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ApiError("Some required fields are missing.", 400,
                           fields={field: "required"})
        return None
    if value not in allowed:
        raise ApiError(
            f"{field} must be one of: {', '.join(sorted(allowed))}.",
            400, fields={field: "invalid"},
        )
    return value


def get_or_404(model, obj_id, what="record"):
    """Fetch a row by id or raise a JSON 404 — the API's get-or-404.

    SOFT-DELETE AWARE (ADR-0001): a soft-deleted row (``deleted_at`` set) reads as
    "gone" everywhere the normal API looks — GET, PUT, DELETE, and every
    sub-resource lookup route through here, so this ONE guard hides deleted rows
    from all of them. Restore/revert deliberately bypass this (they use
    write_control's own getter) because they must see the deleted row to bring it
    back."""
    obj = db.session.get(model, obj_id)
    if obj is None or getattr(obj, "deleted_at", None) is not None:
        raise ApiError(f"No {what} found with id {obj_id}.", 404)
    return obj


# Import the resource modules LAST so their routes attach to api_bp above.
# (Defining api_bp first, importing after, is the standard Flask way to avoid a
# circular import between this package and its route modules.)
from app.routes.api import (  # noqa: E402,F401
    account, activity, citations, events, families, individuals, media, notes,
    places, search, sources,
)
