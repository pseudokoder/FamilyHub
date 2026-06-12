"""Forms for logging in and managing accounts."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

# One shared rule: 8+ characters. For a small invite-only family site this
# beats "uppercase + symbol + blood sample" rules that just push elderly
# users into writing passwords on sticky notes. Length > complexity is also
# the modern NIST guidance.
PASSWORD_RULES = [
    DataRequired(message="Please choose a password."),
    Length(min=8, message="Passwords need at least 8 characters."),
]


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(message="Please type your username.")],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please type your password.")],
    )
    # default=True: the box arrives pre-checked. DESIGN DECISION (DEVDIARY):
    # for ~8 trusted family members on their own devices, staying logged in
    # for 30 days beats making Mom re-type a password every visit.
    remember_me = BooleanField("Keep me logged in on this device", default=True)
    submit = SubmitField("Log In")


class CreateUserForm(FlaskForm):
    """Admin-only: create a family member's account. No self-registration
    exists anywhere in this app — the family is invite-only by design."""

    username = StringField(
        "Username (what they'll type to log in)",
        validators=[
            DataRequired(message="Please choose a username."),
            Length(max=64),
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
    is_admin = BooleanField("Make this person an admin")
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
    """Admin-only: fix a display name or set the email reset links go to.

    TEACHING NOTE on the email validation: it's just "contains an @".
    WTForms' full Email() validator drags in an extra dependency to chase
    RFC 5322 corner cases, and the REAL test of an address is whether the
    reset mail arrives. Validate cheaply, verify by delivery."""

    display_name = StringField(
        "Display name",
        validators=[DataRequired(message="Please enter a display name."),
                    Length(max=120)],
    )
    email = StringField(
        "Email (for password-reset links — leave blank for none)",
        validators=[Length(max=255)],
    )
    submit = SubmitField("Save Changes")

    def validate_email(self, field):
        if field.data and "@" not in field.data:
            raise ValidationError("That doesn't look like an email address.")


class ForgotPasswordForm(FlaskForm):
    """Step 1 of self-service reset: 'who are you?' The answer is always
    the same friendly message whether the username exists or not — no
    username harvesting (same principle as the vague login error)."""

    username = StringField(
        "Your username",
        validators=[DataRequired(message="Please type your username.")],
    )
    submit = SubmitField("Email Me a Reset Link")


class ChangePasswordForm(FlaskForm):
    """Any member: change your OWN password.

    Asking for the current password first is the standard defense against
    the walk-away-from-the-laptop attack: a stranger at an unlocked,
    logged-in screen still can't lock the real owner out (D315)."""

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
