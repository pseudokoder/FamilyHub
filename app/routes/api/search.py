"""/api/search — the genealogy search endpoint (Master Plan §12).

Query params (all optional; combine freely):
  q           free text — matches a person's name AND notes/memories
  given       given-name fragment        surname  surname fragment
  sex         M | F | X | U              living   true | false
  birth_from  / birth_to                 birth year range
  place       place-name fragment

Returns {"query", "people": [...], "notes": [...], "counts": {...}}.
"""

from flask import jsonify, request
from flask_login import login_required

from app.routes.api import api_bp
from app.services import search_service as svc


@api_bp.route("/search", methods=["GET"])
@login_required  # search reads family PII — members only
def search():
    return jsonify(svc.search(request.args))
