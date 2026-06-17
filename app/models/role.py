"""The Role enum — FamilyHub's access-control ladder (Master Plan §10).

WHY AN ENUM (and why the values are plain strings): roles are a fixed, ordered
ladder of trust, not free text. An enum makes the four legal values the ONLY
values the code can name — a typo like ``"amdin"`` becomes an ``ImportError``
the instant you write it, not a silent security hole at runtime. We store the
*string value* (``"admin"``) in a ``VARCHAR(20)`` column rather than a database-
native ENUM type, because native ENUMs differ between SQLite and MySQL — a
portable VARCHAR moves to v2 without surgery (the §3 "standard SQL only" rule).

THE LADDER (low trust → high trust):
    GUEST       — a trusted outsider (relative by marriage): minimal, e.g. comment only.
    USER        — a standard family member: normal CRUD on family content.
    POWER_USER  — a technically-savvy member: elevated, just below admin.
    ADMIN       — full control (manage users, site settings, backups).

WP2 only ENFORCES the USER/ADMIN rungs; GUEST and POWER_USER are defined now so
the ladder exists from the start and later WPs add their rules in ONE place
(the §10 anti-lock-in principle).

v2 mapping: these become Spring Security authorities ("ROLE_ADMIN", …), and
``role_required(Role.ADMIN)`` becomes ``@PreAuthorize("hasRole('ADMIN')")``.
"""

import enum


class Role(str, enum.Enum):
    # Subclassing ``str`` means a Role IS a string ("admin"), so it serializes
    # to JSON and compares to stored values naturally — while still being a
    # closed set of named constants.
    GUEST = "guest"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"

    @property
    def rank(self):
        """Position on the ladder (GUEST=0 … ADMIN=3) for ``>=`` comparisons.

        This is what turns "is this role *at least* X?" into one cheap integer
        compare, so the authorization layer never hard-codes "admin or
        power_user or…" lists that rot the moment a role is added."""
        return _ORDER.index(self)

    def meets(self, minimum):
        """True if this role sits at or above ``minimum`` on the ladder."""
        return self.rank >= Role.coerce(minimum).rank

    @classmethod
    def coerce(cls, value):
        """Turn a stored string (or a Role) into a Role. Unknown/blank values
        fall back to the LEAST privileged role — fail closed, never open, which
        is the correct default for anything touching access control (D315)."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            return cls.GUEST

    @classmethod
    def choices(cls):
        """(value, label) pairs for a WTForms SelectField — admin role picker."""
        labels = {
            cls.GUEST: "Guest (comment only)",
            cls.USER: "Member (normal access)",
            cls.POWER_USER: "Power user (elevated)",
            cls.ADMIN: "Admin (full control)",
        }
        return [(role.value, labels[role]) for role in _ORDER]


# Defined after the class because the entries ARE Role members. The list order
# IS the trust order — the single source of truth for `rank`.
_ORDER = [Role.GUEST, Role.USER, Role.POWER_USER, Role.ADMIN]
