"""Family Plans routes — the collaborative pillar, thin controllers as always.

    GET  /plans                          all plans, newest first
    GET+POST /plans/new                  start a plan
    GET  /plans/<id>                     a plan: description, checklist, files
    GET+POST /plans/<id>/edit            edit (any member — collaborative)
    POST /plans/<id>/delete              delete (creator until locked, admin always)
    POST /plans/<id>/lock | /unlock      admin: the Trial Period switch
    POST /plans/<id>/items               add a checklist item
    POST /plans/items/<id>/toggle        tick / untick (any member)
    POST /plans/items/<id>/delete        remove an item (author/admin)
    POST /plans/<id>/attachments         upload an image or PDF
    GET  /plans/attachments/<id>/file    the file bytes (login-walled!)
    POST /plans/attachments/<id>/delete  remove a file (uploader/admin)

Editing is open to every member by design — a plan is shared workspace,
like the wiki. Deletion follows the Trial Period rule. Files are served
ONLY through the login-walled route below, never from static.
"""

import os

from flask import (
    Blueprint, abort, flash, redirect, render_template, request,
    send_from_directory, url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.plan_forms import PlanAttachmentForm, PlanForm, PlanItemForm
from app.models import FamilyPlan, PlanAttachment, PlanItem
from app.services import lock_service, plan_service

plans_bp = Blueprint("plans", __name__)


@plans_bp.route("/plans")
@login_required
def list_plans():
    return render_template("plans/plans.html", plans=plan_service.get_all_plans())


@plans_bp.route("/plans/new", methods=["GET", "POST"])
@login_required
def create_plan():
    form = PlanForm()
    if form.validate_on_submit():
        plan = plan_service.create_plan(
            form.title.data, form.description.data, current_user
        )
        flash(f'"{plan.title}" started — add ideas, to-dos, and files below.', "success")
        return redirect(url_for("plans.view_plan", plan_id=plan.id))
    return render_template("plans/new_plan.html", form=form)


@plans_bp.route("/plans/<int:plan_id>")
@login_required
def view_plan(plan_id):
    plan = db.get_or_404(FamilyPlan, plan_id)
    return render_template(
        "plans/plan.html",
        plan=plan,
        item_form=PlanItemForm(),
        attachment_form=PlanAttachmentForm(),
        can_delete=plan_service.can_delete(plan, current_user),
    )


@plans_bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
def edit_plan(plan_id):
    plan = db.get_or_404(FamilyPlan, plan_id)
    form = PlanForm(obj=plan)
    if form.validate_on_submit():
        plan_service.update_plan(
            plan, form.title.data, form.description.data, current_user
        )
        flash("Plan updated.", "success")
        return redirect(url_for("plans.view_plan", plan_id=plan.id))
    return render_template("plans/edit_plan.html", form=form, plan=plan)


@plans_bp.route("/plans/<int:plan_id>/delete", methods=["POST"])
@login_required
def delete_plan(plan_id):
    plan = db.get_or_404(FamilyPlan, plan_id)
    if not plan_service.can_delete(plan, current_user):
        abort(403)
    title = plan.title
    plan_service.delete_plan(plan, current_user)
    flash(f'The plan "{title}" was deleted.', "success")
    return redirect(url_for("plans.list_plans"))


# --- Locking (admin only — the Trial Period switch) ---------------------------

@plans_bp.route("/plans/<int:plan_id>/lock", methods=["POST"])
@login_required
def lock_plan(plan_id):
    if not current_user.is_admin:
        abort(403)
    plan = db.get_or_404(FamilyPlan, plan_id)
    lock_service.lock(plan, current_user)
    flash("Plan locked into the archive — only an admin can delete it now.", "success")
    return redirect(url_for("plans.view_plan", plan_id=plan.id))


@plans_bp.route("/plans/<int:plan_id>/unlock", methods=["POST"])
@login_required
def unlock_plan(plan_id):
    if not current_user.is_admin:
        abort(403)
    plan = db.get_or_404(FamilyPlan, plan_id)
    lock_service.unlock(plan, current_user)
    flash("Plan unlocked — its creator can delete it again.", "success")
    return redirect(url_for("plans.view_plan", plan_id=plan.id))


# --- Checklist items ----------------------------------------------------------

@plans_bp.route("/plans/<int:plan_id>/items", methods=["POST"])
@login_required
def add_item(plan_id):
    plan = db.get_or_404(FamilyPlan, plan_id)
    form = PlanItemForm()
    if form.validate_on_submit():
        plan_service.add_item(plan, form.text.data, current_user)
    else:
        for message in form.text.errors:
            flash(message, "danger")
    return redirect(url_for("plans.view_plan", plan_id=plan.id))


@plans_bp.route("/plans/items/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_item(item_id):
    item = db.get_or_404(PlanItem, item_id)
    plan_service.toggle_item(item)  # any member may tick — collaborative
    return redirect(url_for("plans.view_plan", plan_id=item.plan_id))


@plans_bp.route("/plans/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    item = db.get_or_404(PlanItem, item_id)
    if not plan_service.can_delete_item(item, current_user):
        abort(403)
    plan_id = item.plan_id
    plan_service.delete_item(item)
    return redirect(url_for("plans.view_plan", plan_id=plan_id))


# --- Attachments (images + PDFs only) -----------------------------------------

@plans_bp.route("/plans/<int:plan_id>/attachments", methods=["POST"])
@login_required
def upload_attachment(plan_id):
    plan = db.get_or_404(FamilyPlan, plan_id)
    form = PlanAttachmentForm()
    if form.validate_on_submit():
        attachment, error = plan_service.save_attachment(
            plan, form.file.data, current_user
        )
        flash(error, "danger") if error else flash("File shared.", "success")
    return redirect(url_for("plans.view_plan", plan_id=plan.id))


@plans_bp.route("/plans/attachments/<int:attachment_id>/file")
@login_required
def attachment_file(attachment_id):
    """The ONLY way to fetch a shared file — through the login wall, like
    photos. send_from_directory refuses ../ path escapes."""
    attachment = db.get_or_404(PlanAttachment, attachment_id)
    path = plan_service.attachment_path(attachment)
    return send_from_directory(
        os.path.dirname(path), os.path.basename(path),
        download_name=attachment.original_filename,
    )


@plans_bp.route("/plans/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id):
    attachment = db.get_or_404(PlanAttachment, attachment_id)
    if not plan_service.can_delete_attachment(attachment, current_user):
        abort(403)
    plan_id = attachment.plan_id
    plan_service.delete_attachment(attachment, current_user)
    flash("File removed.", "success")
    return redirect(url_for("plans.view_plan", plan_id=plan_id))
