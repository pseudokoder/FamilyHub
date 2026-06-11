"""The one CommentForm, shared by photos AND blog posts.

TEACHING NOTE: it started life inside photo_forms.py. The moment a second
feature needed the identical form, it moved to its own module instead of
being copy-pasted — the DRY principle (Don't Repeat Yourself, D284). One
definition means one place to change the validation rule later.
"""

from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class CommentForm(FlaskForm):
    body = TextAreaField(
        "Write a comment",
        validators=[
            DataRequired(message="Type your comment first, then press the button."),
            Length(max=2000),
        ],
    )
    submit = SubmitField("Add Comment")
