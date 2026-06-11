"""Forms for writing and editing family memories."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class PostForm(FlaskForm):
    title = StringField(
        "Give this memory a title",
        validators=[
            DataRequired(message="Every memory needs a title — even just “Grandpa's Garden”."),
            Length(max=200, message="A bit shorter, please — 200 characters max."),
        ],
    )
    body = TextAreaField(
        "Tell the story",
        validators=[DataRequired(message="The story box is empty — write as much or as little as you like.")],
        # Rows hint makes the box LOOK like a place to write a story,
        # not a one-line search field.
        render_kw={"rows": 12},
    )
    submit = SubmitField("Save This Memory")
