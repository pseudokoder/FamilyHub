"""suggestion_service — the "suggest an idea" → admin inbox (Master Plan §5).

Any member can submit; admins triage. The "prioritized queue" the design calls
for isn't a second table — it's just this table filtered to the accepted items and
ordered by ``priority``. One table, many views (the same principle as the whole app).
"""

from app.extensions import db
from app.models import Suggestion
from app.models.suggestion import STATUSES, TOPICS
from app.services import api_errors


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def serialize(s):
    return {
        "id": s.id,
        "author_user_id": s.author_user_id,
        "author": s.author.display_name if s.author else None,
        "topic": s.topic,
        "body": s.body,
        "status": s.status,
        "priority": s.priority,
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
    }


def submit(author, topic, body):
    """Any authenticated member files a suggestion. Validates the closed topic
    vocabulary; the body is required (an empty suggestion is noise)."""
    topic = (topic or "idea")
    if topic not in TOPICS:
        raise api_errors.ApiError(
            f"topic must be one of: {', '.join(TOPICS)}.", 400,
            fields={"topic": "invalid"})
    if not (body or "").strip():
        raise api_errors.ApiError("A suggestion needs a body.", 400,
                                  fields={"body": "required"})
    suggestion = Suggestion(
        author_user_id=author.id if author is not None else None,
        topic=topic, body=body.strip(), status="new")
    db.session.add(suggestion)
    db.session.commit()
    return serialize(suggestion)


def list_all(status=None, topic=None, prioritized=False):
    """The admin inbox. Filter by status/topic; ``prioritized`` returns the queue
    view — items that HAVE a priority, ranked (lowest number first)."""
    query = Suggestion.query
    if status:
        query = query.filter(Suggestion.status == status)
    if topic:
        query = query.filter(Suggestion.topic == topic)
    if prioritized:
        query = (query.filter(Suggestion.priority.isnot(None))
                 .order_by(Suggestion.priority.asc(), Suggestion.created_at))
    else:
        query = query.order_by(Suggestion.created_at.desc())
    return [serialize(s) for s in query.all()]


def _get(suggestion_id):
    s = db.session.get(Suggestion, suggestion_id)
    if s is None:
        raise api_errors.ApiError(
            f"No suggestion found with id {suggestion_id}.", 404)
    return s


def update(suggestion_id, data):
    """Admin triage: set status and/or the priority rank (an integer, or null to
    clear it — untriaged)."""
    s = _get(suggestion_id)
    if "status" in data:
        status = data.get("status")
        if status not in STATUSES:
            raise api_errors.ApiError(
                f"status must be one of: {', '.join(STATUSES)}.", 400,
                fields={"status": "invalid"})
        s.status = status
    if "priority" in data:
        raw = data.get("priority")
        if raw in (None, ""):
            s.priority = None
        else:
            try:
                s.priority = int(raw)
            except (TypeError, ValueError):
                raise api_errors.ApiError(
                    "priority must be a whole number or null.", 400,
                    fields={"priority": "invalid"})
    db.session.commit()
    return serialize(s)
