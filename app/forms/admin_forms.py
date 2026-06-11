"""Admin-only forms: site settings."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional


class SiteSettingsForm(FlaskForm):
    tagline = StringField(
        "Tagline (one line under the welcome message)",
        validators=[Optional(), Length(max=200)],
    )
    about_text = TextAreaField(
        "About page — what this site is, in your words",
        validators=[Optional()],
        render_kw={"rows": 8},
    )
    contact_text = TextAreaField(
        "Contact info — who to call when something's confusing",
        validators=[Optional()],
        render_kw={"rows": 4},
    )
    # flask_wtf's FileField (not plain wtforms') — it knows about uploaded
    # file objects and plays nicely with render_form's multipart handling.
    hero = FileField("Dashboard banner photo (optional — replaces the current one)")
    submit = SubmitField("Save Settings")
