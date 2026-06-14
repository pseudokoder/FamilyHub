"""Forms for the Family Plans pillar.

The attachment field has no validators here on purpose — the same reason
the photo upload form doesn't: file checking (allowed type, real-bytes
verification, PDF magic-byte check) lives in plan_service, the single
source of truth that a future JSON API would share too.
"""

from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class PlanForm(FlaskForm):
    title = StringField(
        "Plan name (e.g. “Summer Reunion 2026”)",
        validators=[
            DataRequired(message="Please give the plan a name."),
            Length(max=200),
        ],
    )
    description = TextAreaField(
        "What's this plan about? (optional)",
        validators=[Optional(), Length(max=5000)],
    )
    submit = SubmitField("Save Plan")


class PlanItemForm(FlaskForm):
    text = StringField(
        "Add a to-do or idea",
        validators=[DataRequired(message="Type something first."),
                    Length(max=300)],
    )
    submit = SubmitField("Add")


class PlanAttachmentForm(FlaskForm):
    file = FileField("Share a photo or PDF")
    submit = SubmitField("Upload")
