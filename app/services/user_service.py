"""User business logic: creating accounts, checking passwords, resetting them.

v2 mapping: this file becomes `UserService.java` (@Service) almost verbatim.
"""

from app.extensions import bcrypt, db
from app.models import User


def create_user(username, display_name, password, is_admin=False):
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


def set_password(user, new_password):
    """Reset a user's password (admin 'they forgot it again' button)."""
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()


def get_all_users():
    """Every account, oldest first — for the admin user list."""
    return User.query.order_by(User.created_at).all()
