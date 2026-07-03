"""WP3 Phase 1 — schema/RBAC/permissions unit tests.

Covers the pure-logic additions from the schema phase: the RBAC rename + legacy
coercion, the permissions-as-data map (§10 seam), the soft-delete mixin, the
historical-events almanac service, and the audit before/after recorder (ADR-0001).
Endpoint-level behaviour (restore/revert, account link, gap endpoints) is proven
in the later-phase test files.
"""

import json

from app.extensions import db
from app.models import HistoricalEvent, Individual
from app.models.role import Role
from app.services import audit_service, historical_event_service, permissions


# --- RBAC rename + legacy coercion --------------------------------------------

def test_role_ladder_order_and_meets():
    assert Role.VIEWER.rank < Role.CONTRIBUTOR.rank < Role.CURATOR.rank < Role.ADMIN.rank
    assert Role.CURATOR.meets(Role.CONTRIBUTOR)
    assert not Role.CONTRIBUTOR.meets(Role.CURATOR)


def test_role_coerce_accepts_legacy_values():
    # A database written before the 2026-07-03 rename still resolves correctly.
    assert Role.coerce("guest") is Role.VIEWER
    assert Role.coerce("user") is Role.CONTRIBUTOR
    assert Role.coerce("power_user") is Role.CURATOR
    assert Role.coerce("admin") is Role.ADMIN
    # Unknown / blank fails CLOSED to the least-privileged role.
    assert Role.coerce("nonsense") is Role.VIEWER
    assert Role.coerce("") is Role.VIEWER


def test_role_choices_use_new_labels():
    values = [value for value, _label in Role.choices()]
    assert values == ["viewer", "contributor", "curator", "admin"]


# --- Permissions as data (§10 seam) -------------------------------------------

def test_permissions_bundle_per_role():
    assert permissions.permissions_for(Role.VIEWER) == frozenset({permissions.VIEW})
    assert permissions.CONTRIBUTE in permissions.permissions_for(Role.CONTRIBUTOR)
    assert permissions.REVERT in permissions.permissions_for(Role.CURATOR)
    # Only admin holds the administer/link_account flags.
    assert permissions.LINK_ACCOUNT in permissions.permissions_for(Role.ADMIN)
    assert permissions.LINK_ACCOUNT not in permissions.permissions_for(Role.CURATOR)


def test_permissions_can_fails_closed_for_anonymous():
    assert permissions.can(None, permissions.VIEW) is False

    class Anon:
        is_authenticated = False
        is_active = True
        role = "admin"

    assert permissions.can(Anon(), permissions.VIEW) is False


def test_permissions_can_for_real_users(app, admin, viewer):
    assert permissions.can(admin, permissions.ADMINISTER) is True
    assert permissions.can(viewer, permissions.VIEW) is True
    assert permissions.can(viewer, permissions.CONTRIBUTE) is False


def test_permission_matrix_shape():
    m = permissions.matrix()
    assert list(m.keys()) == ["viewer", "contributor", "curator", "admin"]
    assert m["admin"][permissions.ADMINISTER] is True
    assert m["viewer"][permissions.CONTRIBUTE] is False


# --- Soft-delete mixin --------------------------------------------------------

def test_soft_delete_flag(app):
    person = Individual(sex="F")
    db.session.add(person)
    db.session.commit()
    assert person.is_deleted is False
    from datetime import datetime, timezone
    person.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    assert person.is_deleted is True


# --- Historical-events almanac service ----------------------------------------

def test_seed_historical_is_idempotent(app):
    first = historical_event_service.seed_defaults()
    assert first == len(historical_event_service.DEFAULT_EVENTS) > 0
    assert historical_event_service.seed_defaults() == 0  # already populated


def test_historical_list_filters(app):
    historical_event_service.seed_defaults()
    us_only = historical_event_service.list_events(scope="US")
    assert us_only and all(e["scope"] == "US" for e in us_only)
    # Every entry carries the required one-line description.
    assert all(e["description"] for e in us_only)
    ranged = historical_event_service.list_events(year_from=1900, year_to=1950)
    assert ranged and all(1900 <= e["year"] <= 1950 for e in ranged)
    # Oldest first.
    years = [e["year"] for e in ranged]
    assert years == sorted(years)


# --- Audit before/after recorder (ADR-0001) -----------------------------------

def test_record_change_writes_before_after_json(app, admin):
    entry = audit_service.record_change(
        admin, "update", "individual", 5,
        before={"sex": "M"}, after={"sex": "F"}, detail="fixed sex",
    )
    db.session.commit()
    assert json.loads(entry.before_json) == {"sex": "M"}
    assert json.loads(entry.after_json) == {"sex": "F"}
    assert entry.action == "update"
    assert entry.subject_type == "individual"
    assert entry.user_id == admin.id
