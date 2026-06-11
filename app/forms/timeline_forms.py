"""The form for adding/editing timeline events — built for partial dates."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

# The month dropdown: a SelectField so nobody types "Jume". Value 0 means
# "I don't know the month" — first in the list, totally acceptable answer.
MONTH_CHOICES = [
    (0, "— don't know / doesn't matter —"),
    (1, "January"), (2, "February"), (3, "March"), (4, "April"),
    (5, "May"), (6, "June"), (7, "July"), (8, "August"),
    (9, "September"), (10, "October"), (11, "November"), (12, "December"),
]


class TimelineEventForm(FlaskForm):
    title = StringField(
        "What happened?",
        validators=[
            DataRequired(message="Please describe the event in a few words."),
            Length(max=200),
        ],
    )
    year = IntegerField(
        "Year",
        validators=[
            DataRequired(message="The year is the one thing the timeline needs."),
            NumberRange(min=1700, max=2100, message="That year looks off — please double-check it."),
        ],
    )
    month = SelectField("Month (if known)", choices=MONTH_CHOICES, coerce=int, default=0)
    day = IntegerField(
        "Day (if known)",
        validators=[
            Optional(),
            NumberRange(min=1, max=31, message="Days run from 1 to 31."),
        ],
    )
    description = TextAreaField(
        "The story behind it (optional)",
        validators=[Optional()],
        render_kw={"rows": 6},
    )
    submit = SubmitField("Save This Event")

    def validate_day(self, field):
        """Cross-field rule: a day without a month is meaningless
        ('the 12th of 1947'?) — catch it with a helpful message."""
        if field.data and not self.month.data:
            raise ValidationError("You gave a day but no month — please pick the month too.")
