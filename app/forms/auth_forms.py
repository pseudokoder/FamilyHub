"""Forms for logging in and managing accounts.

WP2: login is by **email** (Master Plan §3.5) and accounts carry a **role**
(§10). The validation philosophy is unchanged — cheap, forgiving rules; the real
test of an email is whether the reset mail arrives, so we only check for an "@".
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, PasswordField, SelectField, StringField, SubmitField,
)
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from app.models.role import Role

# One shared rule: 8+ characters. For a small invite-only family site this beats
# "uppercase + symbol + blood sample" rules that just push elderly users into
# writing passwords on sticky notes. Length > complexity is modern NIST guidance.
PASSWORD_RULES = [
    DataRequired(message="Please choose a password."),
    Length(min=8, message="Passwords need at least 8 characters."),
]


def _looks_like_email(form, field):
    """Cheap "@" check (see module docstring for why we don't chase RFC 5322)."""
    if field.data and "@" not in field.data:
        raise ValidationError("That doesn't look like an email address.")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(message="Please type your email address.")],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please type your password.")],
    )
    # default=True: the box arrives pre-checked. DESIGN DECISION (DEVDIARY): for
    # ~8 trusted family members on their own devices, staying logged in for 30
    # days beats making Mom re-type a password every visit.
    remember_me = BooleanField("Keep me logged in on this device", default=True)
    submit = SubmitField("Log In")


class CreateUserForm(FlaskForm):
    """Admin-only: create a family member's account. No self-registration exists
    anywhere in this app — the family is invite-only by design."""

    email = StringField(
        "Email (what they'll use to log in)",
        validators=[
            DataRequired(message="Please enter an email address."),
            Length(max=255), _looks_like_email,
        ],
    )
    display_name = StringField(
        "Display name (what everyone sees, e.g. “Grandma Jo”)",
        validators=[
            DataRequired(message="Please enter a display name."),
            Length(max=120),
        ],
    )
    password = PasswordField("Temporary password", validators=PASSWORD_RULES)
    # The §10 role ladder as a dropdown. coerce=str because the stored value is
    # the role's string ("user", "admin", …).
    role = SelectField(
        "Role", choices=Role.choices(), default=Role.USER.value, coerce=str,
    )
    submit = SubmitField("Create Account")


class ResetPasswordForm(FlaskForm):
    """Admin-only: set a new password for someone who forgot theirs."""

    password = PasswordField("New password", validators=PASSWORD_RULES)
    confirm = PasswordField(
        "Type it again to be sure",
        validators=[EqualTo("password", message="Those two don't match — try again.")],
    )
    submit = SubmitField("Set New Password")


class EditUserForm(FlaskForm):
    """Admin-only: fix a display name, change the login email, or change the role."""

    display_name = StringField(
        "Display name",
        validators=[DataRequired(message="Please enter a display name."),
                    Length(max=120)],
    )
    email = StringField(
        "Email (the login address)",
        validators=[DataRequired(message="Please enter an email address."),
                    Length(max=255), _looks_like_email],
    )
    role = SelectField("Role", choices=Role.choices(), coerce=str)
    submit = SubmitField("Save Changes")


class ForgotPasswordForm(FlaskForm):
    """Step 1 of self-service reset: 'what's your email?' The answer is always
    the same friendly message whether the email exists or not — no account
    harvesting (same principle as the vague login error)."""

    email = StringField(
        "Your email",
        validators=[DataRequired(message="Please type your email address.")],
    )
    submit = SubmitField("Email Me a Reset Link")


class ChangePasswordForm(FlaskForm):
    """Any member: change your OWN password.

    Asking for the current password first is the standard defense against the
    walk-away-from-the-laptop attack: a stranger at an unlocked, logged-in screen
    still can't lock the real owner out (D315)."""

    current_password = PasswordField(
        "Your current password",
        validators=[DataRequired(message="Please type your current password.")],
    )
    password = PasswordField("New password", validators=PASSWORD_RULES)
    confirm = PasswordField(
        "Type the new one again to be sure",
        validators=[EqualTo("password", message="Those two don't match — try again.")],
    )
    submit = SubmitField("Change My Password")
