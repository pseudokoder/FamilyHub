"""Photo album routes — the #1 feature of the whole site.

ROUTE DESIGN (RESTful, per CLAUDE.md): URLs name RESOURCES, verbs come from
HTTP methods. GET reads, POST changes. When v2's Angular frontend arrives,
these same URLs can return JSON instead of HTML — the route design survives
the rewrite (D288 Back-End Programming).

    GET  /albums                    the shelf of albums
    GET+POST /albums/new            create one
    GET  /albums/<id>               one album's gallery
    POST /albums/<id>/photos        upload photos into it
    GET  /photos/<id>               one photo + its comments
    POST /photos/<id>/comments      add a comment
    POST /photos/<id>/delete        delete (uploader or admin only)
    GET  /photos/<id>/file|thumb    the image bytes (login-walled!)

Every route is @login_required — family photos are PII (CLAUDE.md rule).
"""

import os

from flask import (
    Blueprint, abort, flash, redirect, render_template, send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.photo_forms import AlbumForm, CommentForm, UploadPhotosForm
from app.models import Album, Photo
from app.services import photo_service

photos_bp = Blueprint("photos", __name__)


# --- Albums -------------------------------------------------------------------

@photos_bp.route("/albums")
@login_required
def list_albums():
    return render_template("photos/albums.html", albums=photo_service.get_all_albums())


@photos_bp.route("/albums/new", methods=["GET", "POST"])
@login_required
def create_album():
    form = AlbumForm()
    if form.validate_on_submit():
        album = photo_service.create_album(
            form.title.data, form.description.data, current_user
        )
        flash(f'Album "{album.title}" created! Now add some photos.', "success")
        # Straight into the new album — the next thing anyone wants to do
        # with an empty album is fill it. One step, not three.
        return redirect(url_for("photos.view_album", album_id=album.id))
    return render_template("photos/new_album.html", form=form)


@photos_bp.route("/albums/<int:album_id>")
@login_required
def view_album(album_id):
    album = db.get_or_404(Album, album_id)
    return render_template(
        "photos/album.html", album=album, upload_form=UploadPhotosForm()
    )


@photos_bp.route("/albums/<int:album_id>/photos", methods=["POST"])
@login_required
def upload_photos(album_id):
    album = db.get_or_404(Album, album_id)
    form = UploadPhotosForm()
    if form.validate_on_submit():
        saved, errors = photo_service.save_photos(album, form.photos.data, current_user)
        # Honest, specific feedback: celebrate what worked, explain what
        # didn't, never a bare "error occurred".
        if saved:
            flash(f"{saved} photo{'s' if saved != 1 else ''} added to the album!", "success")
        for message in errors:
            flash(message, "danger")
        if not saved and not errors:
            flash("No photos were chosen. Press “Choose your photos” first, then Upload.", "warning")
    return redirect(url_for("photos.view_album", album_id=album.id))


# --- Single photo ----------------------------------------------------------------

@photos_bp.route("/photos/<int:photo_id>")
@login_required
def view_photo(photo_id):
    photo = db.get_or_404(Photo, photo_id)
    return render_template(
        "photos/photo.html",
        photo=photo,
        comment_form=CommentForm(),
        can_delete=photo_service.can_delete(photo, current_user),
    )


@photos_bp.route("/photos/<int:photo_id>/comments", methods=["POST"])
@login_required
def add_comment(photo_id):
    photo = db.get_or_404(Photo, photo_id)
    form = CommentForm()
    if form.validate_on_submit():
        photo_service.add_comment(photo, current_user, form.body.data)
        flash("Comment added!", "success")
    else:
        for messages in form.body.errors:
            flash(messages, "danger")
    return redirect(url_for("photos.view_photo", photo_id=photo.id))


@photos_bp.route("/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    photo = db.get_or_404(Photo, photo_id)
    # Authorization (may you?) is a different question from authentication
    # (who are you?) — the service owns the rule, the route enforces it.
    if not photo_service.can_delete(photo, current_user):
        abort(403)
    album_id = photo.album_id
    photo_service.delete_photo(photo)
    flash("Photo deleted.", "success")
    return redirect(url_for("photos.view_album", album_id=album_id))


# --- Serving the image bytes -------------------------------------------------------

@photos_bp.route("/photos/<int:photo_id>/file")
@login_required
def photo_file(photo_id):
    """The ONLY way to see a full-size photo — through the login wall.

    TEACHING NOTE: photos are deliberately NOT in app/static. Static files
    skip all of Flask's checks; anyone with the URL could fetch Grandma's
    photos. Here the request must carry a valid session cookie first.
    send_from_directory safely joins the path (it refuses ../ escapes).
    """
    photo = db.get_or_404(Photo, photo_id)
    full_path, _ = photo_service.photo_paths(photo)
    return send_from_directory(
        os.path.dirname(full_path), os.path.basename(full_path)
    )


@photos_bp.route("/photos/<int:photo_id>/thumb")
@login_required
def photo_thumb(photo_id):
    photo = db.get_or_404(Photo, photo_id)
    full_path, thumb_path = photo_service.photo_paths(photo)
    # Thumbnail generation can occasionally fail (see photo_service) — in
    # that case serve the original rather than a broken image icon.
    path = thumb_path if os.path.exists(thumb_path) else full_path
    return send_from_directory(os.path.dirname(path), os.path.basename(path))
