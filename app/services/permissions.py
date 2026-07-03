"""Permissions as DATA — the seam that lets v2 make roles editable (§10).

WHY THIS FILE EXISTS: the Master Plan (v2.0.0, §10) calls for permissions to be
"modeled as data" — a role is a *bundle of permission flags*, not a hard-coded
``if role == 'admin'`` scattered through the code. Today that bundle is a Python
dict (data, but in source); in v2 the exact same shape becomes a
``role_permissions`` table an admin can edit through a UI. Because every check
goes through ``permissions_for`` / ``can`` (see ``authz.py``), moving the map
into a database later changes ONLY this file — no route, no service, no decorator.

WHAT v1 SHIPS: this fixed map plus a **read-only** role→permission matrix the
admin panel can render (BE Prompt 3). The **editable** toggle UI is v2.

THE PERMISSION VOCABULARY (coarse on purpose — one flag per capability area, not
per endpoint; finer per-record rules are a later WP, §9 Tier 2):

    view          — read genealogy data (any logged-in member).
    contribute    — create / update / (soft-)delete genealogy records.
    revert        — undo an audited change or restore a soft-deleted record
                    (ADR-0001; Curator and above).
    administer    — manage users, site settings, backups (Admin only).
    link_account  — link/unlink a user account to a person record (ADR-0002;
                    Admin only).

v2 mapping: a ``role_permissions`` JPA entity + a ``PermissionService`` that reads
it; ``can(user, perm)`` becomes a Spring Security ``hasAuthority`` check.
"""

from app.models.role import Role

# --- The permission vocabulary (string constants so a typo is a NameError) -----
VIEW = "view"
CONTRIBUTE = "contribute"
REVERT = "revert"
ADMINISTER = "administer"
LINK_ACCOUNT = "link_account"

ALL_PERMISSIONS = (VIEW, CONTRIBUTE, REVERT, ADMINISTER, LINK_ACCOUNT)

# --- The data: which permissions each role bundles -----------------------------
# Each rung INCLUDES everything below it plus its own additions — the ladder made
# explicit as data. (Written out in full rather than computed from rank so the v2
# table migration is a literal copy, and so a future custom role need not be
# ladder-shaped at all.)
ROLE_PERMISSIONS = {
    Role.VIEWER: frozenset({VIEW}),
    Role.CONTRIBUTOR: frozenset({VIEW, CONTRIBUTE}),
    Role.CURATOR: frozenset({VIEW, CONTRIBUTE, REVERT}),
    Role.ADMIN: frozenset({VIEW, CONTRIBUTE, REVERT, ADMINISTER, LINK_ACCOUNT}),
}


def permissions_for(role):
    """The set of permission flags a role holds. Accepts a Role or a stored
    string (coerced, so legacy values still resolve)."""
    return ROLE_PERMISSIONS.get(Role.coerce(role), frozenset())


def can(user, permission):
    """True if ``user`` (a User, or None for an anonymous request) holds
    ``permission``. Anonymous or deactivated accounts hold nothing — fail closed."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    return permission in permissions_for(user.role)


def matrix():
    """The full role→permission table as plain data, for the admin panel's
    READ-ONLY matrix view (v1) and the OpenAPI/JSON surface. Ordered by the trust
    ladder so it renders top-to-bottom sensibly."""
    from app.models.role import _ORDER
    return {
        role.value: {perm: (perm in ROLE_PERMISSIONS[role])
                     for perm in ALL_PERMISSIONS}
        for role in _ORDER
    }
