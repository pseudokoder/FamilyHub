"""The User model — a login account for one family member.

DESIGN DECISION (documented in DEVDIARY): User is deliberately SEPARATE from
FamilyMember. A FamilyMember is a person in the family tree — including
great-grandparents born in 1890 who will obviously never log in. A User is a
login account. Roughly 6-10 Users will ever exist; the FamilyMember wiki may
hold dozens of people. Keeping them apart is basic normalization — one table
per real-world concept (D426 Data Management – Foundations).
"""

from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """An authenticated account. v2 mapping: @Entity + Spring Security UserDetails.

    UserMixin is Flask-Login's helper: it adds the four tiny methods
    (is_authenticated, get_id(), ...) Flask-Login needs to track a logged-in
    user in the session, so we don't write that boilerplate ourselves.
    """

    # Explicit plural table name. The default would be "user", which is a
    # RESERVED WORD in several databases (PostgreSQL, for one). Naming it
    # "users" keeps the schema portable — remember, this exact schema must
    # move to MySQL for v2 without surgery.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # index=True because we look users up by username on every single login.
    # An index turns that lookup from "scan the whole table" into "binary
    # search" — overkill for 10 users, but the habit matters (D427 Data
    # Management – Applications covers indexes).
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # What the family actually sees: "Grandma Jo", not "jleiter1947".
    display_name = db.Column(db.String(120), nullable=False)

    # We store a bcrypt HASH, never the password itself. bcrypt output is
    # 60 characters; 128 leaves headroom if the algorithm's format grows.
    # Even a full database leak doesn't reveal anyone's actual password —
    # that's the whole point of one-way hashing (D315 Network and Security).
    password_hash = db.Column(db.String(128), nullable=False)

    # Simple two-tier permission model for v1: admin or not. Robust
    # permission tiers are explicitly deferred to v2 (see CLAUDE.md).
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on EVERY request from a logged-in browser.

    The session cookie stores only the user's id (signed, so it can't be
    tampered with). This function turns that id back into a full User object,
    available everywhere as `current_user`.
    """
    return db.session.get(User, int(user_id))
