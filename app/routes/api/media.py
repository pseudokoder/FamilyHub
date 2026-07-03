"""/api/media — photo uploads (OBJE), login-walled serving, and links.

Two things stand out from the other resources: POST is **multipart** (an actual
file, not JSON), and the bytes are served through @login_required routes — a
family photo is PII, so there is no public URL for it, ever (rule 4 in
media_service).
"""

import os

from flask import jsonify, request, send_file
from flask_login import current_user, login_required

from app.models import MediaObject
from app.models.role import Role
from app.routes.api import api_bp, get_or_404, json_body
from app.services import media_service as svc
from app.services.api_errors import ApiError
from app.services.authz import role_required


@api_bp.route("/media", methods=["GET"])
@login_required
def list_media():
    return jsonify(media=svc.list_all(
        request.args.get("subject_type"),
        request.args.get("subject_id", type=int),
    ))


@api_bp.route("/media", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def upload_media():
    # Multipart: the image is in request.files, the metadata in request.form.
    return jsonify(svc.create_from_upload(
        request.files.get("file"), request.form, current_user)), 201


@api_bp.route("/media/<int:media_id>", methods=["GET"])
@login_required
def get_media(media_id):
    return jsonify(svc.get(media_id))


@api_bp.route("/media/<int:media_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_media(media_id):
    return jsonify(svc.update(media_id, json_body()))


@api_bp.route("/media/<int:media_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_media(media_id):
    svc.delete(media_id)
    return "", 204


def _serve(media_id, thumb):
    media = get_or_404(MediaObject, media_id, "media object")
    path = svc.disk_path(media, thumb=thumb)
    if not os.path.exists(path):
        raise ApiError("The image file is missing.", 404)
    return send_file(path, mimetype=media.media_type)


@api_bp.route("/media/<int:media_id>/file", methods=["GET"])
@login_required  # PII: family photos are never served without a login
def media_file(media_id):
    return _serve(media_id, thumb=False)


@api_bp.route("/media/<int:media_id>/thumb", methods=["GET"])
@login_required
def media_thumb(media_id):
    return _serve(media_id, thumb=True)


@api_bp.route("/media/<int:media_id>/links", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def add_media_link(media_id):
    return jsonify(svc.add_link(media_id, json_body())), 201


@api_bp.route("/media/<int:media_id>/links/<subject_type>/<int:subject_id>",
              methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def remove_media_link(media_id, subject_type, subject_id):
    svc.remove_link(media_id, subject_type, subject_id)
    return "", 204
