"""Timeline business logic."""

from app.extensions import db
from app.models import TimelineEvent


def get_all_events():
    """Chronological. coalesce(month, 0) is portable SQL (SQLite and MySQL)
    that sorts year-only events at the top of their year — the database
    can't compare NULL with 6, so we tell it 'treat unknown as 0'."""
    return TimelineEvent.query.order_by(
        TimelineEvent.year,
        db.func.coalesce(TimelineEvent.month, 0),
        db.func.coalesce(TimelineEvent.day, 0),
    ).all()


def create_event(form_data, user):
    event = TimelineEvent(
        title=form_data["title"].strip(),
        description=(form_data["description"] or "").strip(),
        year=form_data["year"],
        month=form_data["month"] or None,  # the form sends 0 for "unknown"
        day=form_data["day"],
        created_by=user.id,
    )
    db.session.add(event)
    db.session.commit()
    return event


def update_event(event, form_data):
    event.title = form_data["title"].strip()
    event.description = (form_data["description"] or "").strip()
    event.year = form_data["year"]
    event.month = form_data["month"] or None
    event.day = form_data["day"]
    db.session.commit()
    return event


def can_delete(event, user):
    """Same family rule as photos and posts: creator or admin."""
    return user.is_admin or event.created_by == user.id


def delete_event(event):
    db.session.delete(event)
    db.session.commit()
