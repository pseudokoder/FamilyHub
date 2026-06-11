"""The form for creating/editing a family member's wiki page."""

from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class FamilyMemberForm(FlaskForm):
    name = StringField(
        "Full name",
        validators=[
            DataRequired(message="Please enter the person's name."),
            Length(max=120),
        ],
    )
    location = StringField(
        "Where they live(d) — e.g. “Spring Hill, TN” (optional)",
        validators=[Optional(), Length(max=120)],
    )
    # DateField renders as <input type="date"> — the browser shows its own
    # calendar picker, which beats teaching anyone a date format.
    birth_date = DateField("Date of birth (optional)", validators=[Optional()])
    death_date = DateField("Date of death (leave blank if living)", validators=[Optional()])
    bio = TextAreaField(
        "Their story — life, work, family, the good anecdotes",
        validators=[Optional()],
        render_kw={"rows": 12},
        description="Tip: type [[a person's name]] in double brackets to link to their page.",
    )
    submit = SubmitField("Save This Page")

    def validate_death_date(self, field):
        """TEACHING NOTE: a CUSTOM validator. WTForms automatically runs any
        method named validate_<fieldname> after the built-in validators.
        Cross-field rules (death can't be before birth) live here, next to
        the form they protect."""
        if field.data and self.birth_date.data and field.data < self.birth_date.data:
            raise ValidationError(
                "The date of death is earlier than the date of birth — "
                "please double-check those two dates."
            )
