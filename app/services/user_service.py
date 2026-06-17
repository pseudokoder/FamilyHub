"""User business logic: creating accounts, checking passwords, resetting them.

WP2: the login identifier is the **email address** and accounts carry a **role**
(Master Plan §3.5/§10). Note what did NOT change — bcrypt hashing, the salted
one-way storage, and the signed single-use reset tokens are byte-for-byte the
same. Only the lookup key moved from username to email. Security mechanisms are
independent of *which* column identifies the account.

v2 mapping: this file becomes ``UserService.java`` (@Service) almost verbatim.
"""

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import bcrypt, db
from app.models import User
from app.models.role import Role
from app.services import audit_service

# Reset links die after one hour — long enough to walk to the computer, short
# enough that a link forwarded around or sitting in a hacked inbox next month is
# worthless.
RESET_TOKEN_MAX_AGE_SECONDS = 3600


def _normalize_email(email):
    return (email or "").strip().lower()


def create_user(email, display_name, password, role=Role.USER, actor=None):
    """Create a new account with a securely hashed password.

    Raises ValueError if the email is already in use — the route layer turns
    that into a friendly form error. Services raise meaningful errors; routes
    decide how to SHOW them. (Same split as @Service exceptions ->
    @ControllerAdvice handlers in Spring Boot.)
    """
    email = _normalize_email(email)
    if not email:
        raise ValueError("An email address is required.")
    if User.query.filter_by(email=email).first() is not None:
        raise ValueError(f'The email "{email}" is already in use.')

    user = User(
        email=email,
        display_name=display_name.strip(),
        # generate_password_hash runs bcrypt with a random SALT baked into the
        # output. Two users with the same password get totally different hashes,
        # defeating precomputed "rainbow table" attacks (D315).
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=Role.coerce(role).value,
    )
    db.session.add(user)
    db.session.flush()  # assigns user.id so the audit row can name it
    audit_service.log_event(actor, "create", "user", user.id, email)
    db.session.commit()
    return user


def authenticate(email, password):
    """Return the User if email + password are correct AND the account is
    active, else None.

    SECURITY NOTE: we never reveal WHICH part was wrong — unknown email, wrong
    password, and deactivated account all return the same None, so an attacker
    can't harvest which emails are real or active.
    """
    user = User.query.filter_by(email=_normalize_email(email)).first()
    if user is None or not user.is_active:
        return None
    # check_password_hash re-hashes the attempt with the salt stored inside
    # user.password_hash and compares in constant time (no timing attacks).
    if not bcrypt.check_password_hash(user.password_hash, password):
        return None
    return user


def set_password(user, new_password, actor=None):
    """Set a new password — used by the admin reset button AND the self-service
    change page. The audit row records who did it; the hash itself, of course,
    never appears anywhere."""
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    audit_service.log_event(actor, "set password", "user", user.id, user.email)
    db.session.commit()


def get_all_users():
    """Every account, oldest first — for the admin user list."""
    return User.query.order_by(User.created_at).all()


def find_by_email(email):
    return User.query.filter_by(email=_normalize_email(email)).first()


def set_email(user, email, actor=None):
    """Change the login email. Enforces the same uniqueness rule as create."""
    email = _normalize_email(email)
    if not email:
        raise ValueError("An email address is required.")
    clash = User.query.filter_by(email=email).first()
    if clash is not None and clash.id != user.id:
        raise ValueError(f'The email "{email}" is already in use.')
    user.email = email
    audit_service.log_event(actor, "edit", "user", user.id, f"email -> {email}")
    db.session.commit()
    return user


def set_display_name(user, display_name, actor=None):
    user.display_name = display_name.strip()
    audit_service.log_event(actor, "edit", "user", user.id,
                            f"display name for {user.email}")
    db.session.commit()
    return user


def set_role(user, role, actor=None):
    """Change an account's RBAC rung (§10). Routed through here, not set on the
    model directly, so the change is always audited."""
    user.role = Role.coerce(role).value
    audit_service.log_event(actor, "edit", "user", user.id,
                            f"role -> {user.role} for {user.email}")
    db.session.commit()
    return user


# --- Password-reset tokens (the forgot-password email flow) -------------------
#
# TEACHING NOTE: no token table! The token IS the proof, thanks to itsdangerous
# (the same library Flask uses to sign session cookies):
#
#   token = sign({user id, last 12 chars of the CURRENT password hash})
#
# - Tamper with it     -> signature breaks                     -> rejected.
# - Older than an hour -> timestamp check fails                -> rejected.
# - Already used       -> the password CHANGED, so the hash fragment inside the
#   token no longer matches                                    -> rejected.
#
# That last trick gives single-use semantics with zero database state — the kind
# of design worth remembering for v2 (Spring's equivalent would be a signed JWT
# carrying the same fragment).

def _reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="password-reset"
    )


def generate_reset_token(user):
    return _reset_serializer().dumps(
        {"uid": user.id, "frag": user.password_hash[-12:]}
    )


def verify_reset_token(token):
    """The User this token belongs to, or None if it's expired, forged, already
    used, or otherwise not believable."""
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
