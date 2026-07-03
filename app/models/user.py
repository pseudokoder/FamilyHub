"""The User model — a login account for one family member.

DESIGN DECISION (documented in DEVDIARY): User is deliberately SEPARATE from
Individual. An Individual is a person in the family tree — including great-
grandparents born in 1890 who will obviously never log in. A User is a login
account. Roughly 6-10 Users will ever exist; the individuals table may hold
dozens of people. Keeping them apart is basic normalization — one table per
real-world concept (D426 Data Management – Foundations).

WP2 CHANGE — aligned to Master Plan §3.5 + §10 RBAC: the login identifier is now
the **email address** (not a username), and a four-rung **role** replaces the old
two-state ``is_admin`` boolean. The security *mechanisms* (bcrypt, reset tokens,
rate limiting, CSRF) are unchanged — only the lookup key and the permission field
moved. ``is_admin`` lives on as a computed property so every existing
``current_user.is_admin`` check keeps working untouched.
"""

from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db, login_manager
from app.models.role import Role


class User(UserMixin, db.Model):
    """An authenticated account. v2 mapping: @Entity + Spring Security UserDetails.

    UserMixin is Flask-Login's helper: it adds the small methods
    (is_authenticated, get_id(), …) Flask-Login needs to track a logged-in user
    in the session, so we don't write that boilerplate ourselves. (Note: our
    ``is_active`` COLUMN below intentionally overrides UserMixin's always-True
    ``is_active`` — Flask-Login refuses to log in a user whose is_active is
    False, so deactivating an account is a one-column switch.)
    """

    # Explicit plural table name. The default would be "user", which is a
    # RESERVED WORD in several databases (PostgreSQL, for one). Naming it
    # "users" keeps the schema portable — this exact schema must move to MySQL
    # for v2 without surgery.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # THE LOGIN KEY (Master Plan §3.5). UNIQUE so no two accounts share an inbox;
    # NOT NULL because it's how you sign in; indexed because we look it up on
    # every single login (an index turns "scan the whole table" into "binary
    # search" — overkill for 10 users, but the habit matters; D427).
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # What the family actually sees: "Grandma Jo", not "jo@example.com".
    display_name = db.Column(db.String(120), nullable=False)

    # We store a bcrypt HASH, never the password itself (D315). bcrypt output is
    # 60 chars; 255 leaves generous headroom and matches the §3.5 spec width.
    password_hash = db.Column(db.String(255), nullable=False)

    # The RBAC rung (Master Plan §10), stored as the role's string value in a
    # portable VARCHAR. Defaults to USER — a brand-new account is a normal member
    # until an admin says otherwise. server_default makes the column safe to add
    # to an existing table in a migration.
    role = db.Column(
        db.String(20), nullable=False,
        default=Role.CONTRIBUTOR.value, server_default=Role.CONTRIBUTOR.value,
    )

    # Soft on/off switch for an account. Flask-Login reads this on login, so a
    # deactivated user simply can't sign in — no need to delete the row (which
    # would orphan the content they authored). Defaults to active.
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.text("1")
    )

    # ACCOUNT ↔ PERSON LINK (ADR-0002). A living family member is usually BOTH a
    # login (this row) AND a person in the tree (an Individual). This nullable FK
    # ties the two together — one user links to at most one individual. Nullable
    # on purpose: a brand-new member, or a view-only relative, may have no linked
    # person yet, in which case the tree falls back to the oldest-ancestor root
    # (see genealogy_service). SET NULL so deleting a person never deletes the
    # account. We deliberately do NOT merge users into individuals — they are
    # different concepts (auth vs. genealogy), kept separate per §3.5.
    individual_id = db.Column(
        db.Integer,
        db.ForeignKey("individuals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # PER-USER TIMEZONE (Master Plan §5). NULL means "use the site default"
    # (a site_settings value); an account can override it. Stored as an IANA
    # zone name ("America/Chicago"), the portable standard — not a bare UTC
    # offset, which breaks across daylight-saving changes.
    timezone = db.Column(db.String(50), nullable=True)

    # EMAIL VERIFICATION (§9). When the CURRENT email address was verified via a
    # signed link; NULL until then, and cleared whenever the address changes.
    email_verified_at = db.Column(db.DateTime, nullable=True)

    # LOGIN LOCKOUT (§9). Consecutive failed sign-ins (reset to 0 on success); once
    # the settings-driven threshold is hit, locked_until parks a timestamp the
    # login check honors. Complements the IP-based rate limiter with per-account
    # protection.
    failed_login_count = db.Column(
        db.Integer, nullable=False, default=0, server_default="0")
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # The linked person (ADR-0002), or None. A plain many-to-one: each account
    # points at zero or one individual.
    individual = db.relationship("Individual", foreign_keys=[individual_id])

    # --- Role helpers (the model's slice of the §10 authorization layer) ------

    @property
    def is_admin(self):
        """Back-compat shim: every old ``current_user.is_admin`` check (the nav
        bar, the admin decorator) keeps working without edits, now answered by
        the role instead of a dropped boolean column."""
        return self.role == Role.ADMIN.value

    @property
    def email_verified(self):
        """True once the current email address has been verified (§9)."""
        return self.email_verified_at is not None

    def is_locked(self, now=None):
        """True if the account is currently locked out (§9)."""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone as _tz
        now = now or datetime.now(_tz.utc)
        # Stored datetimes may be naive (SQLite); compare on the same basis.
        locked = self.locked_until
        if locked.tzinfo is None:
            now = now.replace(tzinfo=None)
        return locked > now

    def has_role(self, minimum):
        """True if this account is at least ``minimum`` on the role ladder.
        The actual permission decisions route through app/services/authz.py;
        this is the per-user predicate that decorator calls."""
        return Role.coerce(self.role).meets(minimum)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on EVERY request from a logged-in browser.

    The session cookie stores only the user's id (signed, so it can't be
    tampered with). This function turns that id back into a full User object,
    available everywhere as ``current_user``.
    """
    return db.session.get(User, int(user_id))
