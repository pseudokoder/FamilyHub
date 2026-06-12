"""User business logic: creating accounts, checking passwords, resetting them.

v2 mapping: this file becomes `UserService.java` (@Service) almost verbatim.
"""

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import bcrypt, db
from app.models import User
from app.services import audit_service

# Reset links die after one hour — long enough to walk to the computer,
# short enough that a link forwarded around or sitting in a hacked inbox
# next month is worthless.
RESET_TOKEN_MAX_AGE_SECONDS = 3600


def create_user(username, display_name, password, is_admin=False, actor=None):
    """Create a new account with a securely hashed password.

    Raises ValueError if the username is taken — the route layer turns that
    into a friendly form error. Services raise meaningful errors; routes
    decide how to SHOW them. (Same split as @Service exceptions ->
    @ControllerAdvice handlers in Spring Boot.)
    """
    username = username.strip().lower()
    if User.query.filter_by(username=username).first() is not None:
        raise ValueError(f'The username "{username}" is already taken.')

    user = User(
        username=username,
        display_name=display_name.strip(),
        # generate_password_hash runs bcrypt with a random SALT baked into
        # the output. Two users with the same password get totally different
        # hashes, which defeats precomputed "rainbow table" attacks.
        # (D315 Network and Security – Foundations.)
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        is_admin=is_admin,
    )
    db.session.add(user)
    db.session.flush()  # assigns user.id so the audit row can name it
    # actor=None happens from the command line (flask create-admin).
    audit_service.log_event(actor, "create", "user", user.id, username)
    db.session.commit()
    return user


def authenticate(username, password):
    """Return the User if username + password are correct, else None.

    SECURITY NOTE: we never reveal WHICH part was wrong. "Unknown username"
    vs "wrong password" would let an attacker harvest valid usernames.
    One vague answer — None — covers both.
    """
    user = User.query.filter_by(username=username.strip().lower()).first()
    if user is None:
        return None
    # check_password_hash re-hashes the attempt with the salt stored inside
    # user.password_hash and compares in constant time (no timing attacks).
    if not bcrypt.check_password_hash(user.password_hash, password):
        return None
    return user


def set_password(user, new_password, actor=None):
    """Set a new password — used by the admin reset button AND the
    self-service change page. The audit row records who did it; the hash
    itself, of course, never appears anywhere."""
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    audit_service.log_event(actor, "set password", "user", user.id, user.username)
    db.session.commit()


def get_all_users():
    """Every account, oldest first — for the admin user list."""
    return User.query.order_by(User.created_at).all()


def find_by_username(username):
    return User.query.filter_by(username=username.strip().lower()).first()


def set_email(user, email, actor=None):
    """Set (or clear) the address password-reset links go to."""
    user.email = (email or "").strip().lower() or None
    audit_service.log_event(actor, "edit", "user", user.id,
                            f"email for {user.username}")
    db.session.commit()
    return user


def set_display_name(user, display_name, actor=None):
    user.display_name = display_name.strip()
    audit_service.log_event(actor, "edit", "user", user.id,
                            f"display name for {user.username}")
    db.session.commit()
    return user


# --- Password-reset tokens (the forgot-password email flow) -------------------
#
# TEACHING NOTE: no token table! The token IS the proof, thanks to
# itsdangerous (the same library Flask uses to sign session cookies):
#
#   token = sign({user id, last 12 chars of the CURRENT password hash})
#
# - Tamper with it           -> signature breaks            -> rejected.
# - Older than an hour       -> timestamp check fails       -> rejected.
# - Already used             -> the password CHANGED, so the hash fragment
#   inside the token no longer matches                      -> rejected.
#
# That last trick gives single-use semantics with zero database state —
# the kind of design worth remembering for v2 (Spring's equivalent would
# be a signed JWT carrying the same fragment).

def _reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="password-reset"
    )


def generate_reset_token(user):
    return _reset_serializer().dumps(
        {"uid": user.id, "frag": user.password_hash[-12:]}
    )


def verify_reset_token(token):
    """The User this token belongs to, or None if it's expired, forged,
    already used, or otherwise not believable."""
    try:
        data = _reset_serializer().loads(
            token, max_age=RESET_TOKEN_MAX_AGE_SECONDS
        )
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(User, data.get("uid", -1))
    if user is None or user.password_hash[-12:] != data.get("frag"):
        return None
    return user
