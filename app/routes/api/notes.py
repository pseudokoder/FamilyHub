"""/api/notes — Markdown memories/bios and their polymorphic attachments."""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.models.role import Role
from app.routes.api import api_bp, json_body
from app.services import note_service as svc
from app.services.authz import role_required


@api_bp.route("/notes", methods=["GET"])
@login_required
def list_notes():
    # Optional ?subject_type=…&subject_id=… → one person's/event's memories.
    return jsonify(notes=svc.list_all(
        request.args.get("subject_type"),
        request.args.get("subject_id", type=int),
    ))


@api_bp.route("/notes", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def create_note():
    # The author is the logged-in member — set by the SERVER, never trusted from
    # the request body (you can't write a memory and sign someone else's name).
    return jsonify(svc.create(json_body(), author=current_user)), 201


@api_bp.route("/notes/<int:note_id>", methods=["GET"])
@login_required
def get_note(note_id):
    return jsonify(svc.get(note_id))


@api_bp.route("/notes/<int:note_id>", methods=["PUT"])
@role_required(Role.CONTRIBUTOR)
def update_note(note_id):
    return jsonify(svc.update(note_id, json_body()))


@api_bp.route("/notes/<int:note_id>", methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def delete_note(note_id):
    svc.delete(note_id)
    return "", 204


@api_bp.route("/notes/<int:note_id>/links", methods=["POST"])
@role_required(Role.CONTRIBUTOR)
def add_note_link(note_id):
    return jsonify(svc.add_link(note_id, json_body())), 201


@api_bp.route("/notes/<int:note_id>/links/<subject_type>/<int:subject_id>",
              methods=["DELETE"])
@role_required(Role.CONTRIBUTOR)
def remove_note_link(note_id, subject_type, subject_id):
    svc.remove_link(note_id, subject_type, subject_id)
    return "", 204
