"""Forms for albums, photo uploads, and comments."""

from flask_wtf import FlaskForm
from wtforms import MultipleFileField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class AlbumForm(FlaskForm):
    title = StringField(
        "Album name (e.g. “Thanksgiving 1987”)",
        validators=[
            DataRequired(message="Please give the album a name."),
            Length(max=140, message="That name is a little long — 140 characters max."),
        ],
    )
    description = TextAreaField(
        "What's this album about? (optional)",
        validators=[Optional(), Length(max=2000)],
    )
    submit = SubmitField("Create Album")


class UploadPhotosForm(FlaskForm):
    """The upload form is deliberately tiny: choose files, press the button.

    TEACHING NOTE: notice there are no validators on the file field. File
    checking (type, real-image verification) happens in photo_service, the
    single source of truth — the same checks would protect a future JSON API
    endpoint in v2, where WTForms won't exist.
    """

    photos = MultipleFileField("Choose your photos")
    submit = SubmitField("⬆ Upload Photos")


# CommentForm used to live here — it moved to comment_forms.py the day the
# blog needed the identical form. See the teaching note there (DRY).
