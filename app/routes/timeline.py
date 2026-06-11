"""Family timeline routes — editable by every authenticated member
(CLAUDE.md), deletable by the event's creator or an admin.

    GET  /timeline                    the whole family story, in order
    GET+POST /timeline/new            add an event
    GET+POST /timeline/<id>/edit      fix or enrich one (any member)
    POST /timeline/<id>/delete        remove one (creator/admin, confirmed)
"""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.timeline_forms import TimelineEventForm
from app.models import TimelineEvent
from app.services import timeline_service

timeline_bp = Blueprint("timeline", __name__)


@timeline_bp.route("/timeline")
@login_required
def list_events():
    return render_template(
        "timeline/timeline.html", events=timeline_service.get_all_events()
    )


@timeline_bp.route("/timeline/new", methods=["GET", "POST"])
@login_required
def create_event():
    form = TimelineEventForm()
    if form.validate_on_submit():
        event = timeline_service.create_event(form.data, current_user)
        flash(f'"{event.title}" is on the family timeline!', "success")
        return redirect(url_for("timeline.list_events"))
    return render_template("timeline/new_event.html", form=form)


@timeline_bp.route("/timeline/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = db.get_or_404(TimelineEvent, event_id)
    form = TimelineEventForm(obj=event)
    if form.validate_on_submit():
        timeline_service.update_event(event, form.data)
        flash("The event is updated.", "success")
        return redirect(url_for("timeline.list_events"))
    return render_template("timeline/edit_event.html", form=form, event=event)


@timeline_bp.route("/timeline/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = db.get_or_404(TimelineEvent, event_id)
    if not timeline_service.can_delete(event, current_user):
        abort(403)
    timeline_service.delete_event(event)
    flash("The event was removed from the timeline.", "success")
    return redirect(url_for("timeline.list_events"))
