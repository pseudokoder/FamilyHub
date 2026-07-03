"""The Role enum — FamilyHub's access-control ladder (Master Plan §10).

WHY AN ENUM (and why the values are plain strings): roles are a fixed, ordered
ladder of trust, not free text. An enum makes the four legal values the ONLY
values the code can name — a typo like ``"curatr"`` becomes an ``ImportError``
the instant you write it, not a silent security hole at runtime. We store the
*string value* (``"admin"``) in a ``VARCHAR(20)`` column rather than a database-
native ENUM type, because native ENUMs differ between SQLite and MySQL — a
portable VARCHAR moves to v2 without surgery (the §3 "standard SQL only" rule).

THE LADDER (low trust → high trust), renamed 2026-07-03 (Master Plan v2.0.0):
    VIEWER       — a trusted outsider (relative by marriage): minimal, read-only.
    CONTRIBUTOR  — a standard family member: normal CRUD on family content.
    CURATOR      — a technically-savvy member: elevated, just below admin,
                   including the audit-driven revert (ADR-0001).
    ADMIN        — full control (manage users, site settings, backups).

The old names map straight across — GUEST→VIEWER, USER→CONTRIBUTOR,
POWER_USER→CURATOR, ADMIN→ADMIN — and ``coerce`` below still accepts the old
stored strings, so a database written before the rename keeps working while the
one-shot data migration rewrites the rows.

WHAT A ROLE *MEANS* is defined as data, not code, in
``app/services/permissions.py`` (a role = a bundle of permission flags). That is
the anti-lock-in seam (§10): v2 can make roles editable by moving that map into a
table, and no permission *check* has to change.

v2 mapping: these become Spring Security authorities ("ROLE_ADMIN", …), and
``role_required(Role.ADMIN)`` becomes ``@PreAuthorize("hasRole('ADMIN')")``.
"""

import enum


class Role(str, enum.Enum):
    # Subclassing ``str`` means a Role IS a string ("admin"), so it serializes
    # to JSON and compares to stored values naturally — while still being a
    # closed set of named constants.
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    CURATOR = "curator"
    ADMIN = "admin"

    @property
    def rank(self):
        """Position on the ladder (VIEWER=0 … ADMIN=3) for ``>=`` comparisons.

        This is what turns "is this role *at least* X?" into one cheap integer
        compare, so the authorization layer never hard-codes "admin or
        curator or…" lists that rot the moment a role is added."""
        return _ORDER.index(self)

    def meets(self, minimum):
        """True if this role sits at or above ``minimum`` on the ladder."""
        return self.rank >= Role.coerce(minimum).rank

    @classmethod
    def coerce(cls, value):
        """Turn a stored string (or a Role) into a Role. Accepts the pre-2026-07-03
        names as aliases so old rows still resolve; unknown/blank values fall back
        to the LEAST privileged role — fail closed, never open, which is the
        correct default for anything touching access control (D315)."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            return _LEGACY_ALIASES.get(value, cls.VIEWER)

    @classmethod
    def choices(cls):
        """(value, label) pairs for a WTForms SelectField — admin role picker."""
        labels = {
            cls.VIEWER: "Viewer (read only)",
            cls.CONTRIBUTOR: "Contributor (normal access)",
            cls.CURATOR: "Curator (elevated)",
            cls.ADMIN: "Admin (full control)",
        }
        return [(role.value, labels[role]) for role in _ORDER]


# Defined after the class because the entries ARE Role members. The list order
# IS the trust order — the single source of truth for `rank`.
_ORDER = [Role.VIEWER, Role.CONTRIBUTOR, Role.CURATOR, Role.ADMIN]

# The pre-rename stored strings, mapped to the current ladder. Used by ``coerce``
# so a database written before the 2026-07-03 rename keeps resolving correctly
# even if a row somehow escaped the data migration.
_LEGACY_ALIASES = {
    "guest": Role.VIEWER,
    "user": Role.CONTRIBUTOR,
    "power_user": Role.CURATOR,
    "admin": Role.ADMIN,
}
