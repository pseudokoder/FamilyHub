"""citation_service — the link from one FACT to one source (polymorphic).

A citation can back an individual, a family, an event, or even a specific name
("this surname spelling per the parish register"). It's the most polymorphic
record in the schema, and it goes through the same ``require_subject`` gate as
everything else — one validation path for every polymorphic write.
"""

from app.extensions import db
from app.models import Citation, Source
from app.services import genealogy_service as gs
from app.services.api_errors import ApiError

CITATION_SUBJECTS = {
    gs.SUBJECT_INDIVIDUAL, gs.SUBJECT_FAMILY, gs.SUBJECT_EVENT, gs.SUBJECT_NAME,
}


def _validate_source(source_id):
    if db.session.get(Source, source_id) is None:
        raise ApiError(f"No source with id {source_id}.", 400,
                       fields={"source_id": "no such source"})
    return source_id


def _quality(data):
    """GEDCOM QUAY is 0–3 (unreliable → direct evidence). Reject anything else."""
    value = data.get("quality")
    if value is None or value == "":
        return None
    try:
        quality = int(value)
    except (TypeError, ValueError):
        raise ApiError("quality must be a whole number 0–3.", 400,
                       fields={"quality": "invalid"})
    if not 0 <= quality <= 3:
        raise ApiError("quality must be between 0 and 3.", 400,
                       fields={"quality": "out of range"})
    return quality


def serialize(citation):
    return {
        "id": citation.id,
        "source_id": citation.source_id,
        "source_title": citation.source.title if citation.source else None,
        "subject_type": citation.subject_type,
        "subject_id": citation.subject_id,
        "subject_label": gs.subject_label(citation.subject_type, citation.subject_id),
        "page": citation.page,
        "quality": citation.quality,
        "notes": citation.notes,
    }


def list_all(subject_type=None, subject_id=None):
    query = Citation.query
    if subject_type and subject_id is not None:
        query = query.filter_by(subject_type=subject_type, subject_id=subject_id)
    return [serialize(c) for c in query.order_by(Citation.id).all()]


def get(citation_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Citation, citation_id, "citation"))


def create(data):
    from app.routes.api import require
    require(data, "source_id")
    _validate_source(data["source_id"])
    subject_type, subject_id = gs.require_subject(
        data.get("subject_type"), data.get("subject_id"), CITATION_SUBJECTS
    )
    citation = Citation(
        source_id=data["source_id"],
        subject_type=subject_type, subject_id=subject_id,
        page=data.get("page") or None,
        quality=_quality(data),
        notes=data.get("notes") or None,
    )
    db.session.add(citation)
    db.session.commit()
    return serialize(citation)


def update(citation_id, data):
    from app.routes.api import get_or_404
    citation = get_or_404(Citation, citation_id, "citation")
    if "source_id" in data:
        citation.source_id = _validate_source(data["source_id"])
    if "subject_type" in data or "subject_id" in data:
        citation.subject_type, citation.subject_id = gs.require_subject(
            data.get("subject_type", citation.subject_type),
            data.get("subject_id", citation.subject_id), CITATION_SUBJECTS,
        )
    for field in ("page", "notes"):
        if field in data:
            setattr(citation, field, data.get(field) or None)
    if "quality" in data:
        citation.quality = _quality(data)
    db.session.commit()
    return serialize(citation)


def delete(citation_id):
    from app.routes.api import get_or_404
    citation = get_or_404(Citation, citation_id, "citation")
    db.session.delete(citation)
    db.session.commit()
