"""Family wiki routes — one encyclopedia page per family member.

    GET  /family                  everyone, alphabetically
    GET+POST /family/new          add a person
    GET  /family/<id>             read their page
    GET+POST /family/<id>/edit    ANY family member may edit (collaborative!)
    POST /family/<id>/delete      admin only — removing a person is a big deal

Editing is open to all authenticated members by design (CLAUDE.md): this is
the family's shared encyclopedia, Wikipedia-style. Trust the family; keep
delete behind the admin.
"""

from flask import (
    Blueprint, Response, abort, flash, redirect, render_template, url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.wiki_forms import FamilyMemberForm
from app.models import FamilyMember
from app.services import (
    audit_service, gedcom_service, lock_service, tag_service, wiki_service,
)

wiki_bp = Blueprint("wiki", __name__)


@wiki_bp.route("/family")
@login_required
def list_members():
    return render_template("wiki/members.html", members=wiki_service.get_all_members())


@wiki_bp.route("/family/export.ged")
@login_required
def export_gedcom():
    """Download the whole wiki as a GEDCOM file for Ancestry/FamilySearch/
    Gramps. Admin-only, like every other BULK data export here (JSON
    export and backups) — a single page is fine for any member to read,
    but shipping everyone's birthdates out in one file is an admin call.
    Audited, because bulk PII leaving the building should leave a trace."""
    if not current_user.is_admin:
        abort(403)
    document = gedcom_service.build_gedcom()
    audit_service.log_event(current_user, "export", "family tree (GEDCOM)")
    db.session.commit()
    return Response(
        document,
        mimetype="application/x-gedcom",
        headers={"Content-Disposition": "attachment; filename=familyhub.ged"},
    )


@wiki_bp.route("/family/new", methods=["GET", "POST"])
@login_required
def create_member():
    form = FamilyMemberForm()
    if form.validate_on_submit():
        existing = wiki_service.find_by_name(form.name.data)
        if existing:
            # Forgiving: don't create a duplicate page, walk them to the
            # one that exists — they probably want to add to it.
            flash(
                f'There\'s already a page for {existing.name} — here it is. '
                "You can add to it with the Edit button.",
                "warning",
            )
            return redirect(url_for("wiki.view_member", member_id=existing.id))
        member = wiki_service.create_member(form.data, current_user)
        flash(f"{member.name} now has a page in the family wiki!", "success")
        return redirect(url_for("wiki.view_member", member_id=member.id))
    return render_template("wiki/new_member.html", form=form)


@wiki_bp.route("/family/<int:member_id>")
@login_required
def view_member(member_id):
    member = db.get_or_404(FamilyMember, member_id)
    return render_template(
        "wiki/member.html", member=member,
        can_delete=wiki_service.can_delete(member, current_user),
        featured_photos=tag_service.photos_featuring(member),
    )


@wiki_bp.route("/family/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    member = db.get_or_404(FamilyMember, member_id)
    form = FamilyMemberForm(obj=member)
    if form.validate_on_submit():
        wiki_service.update_member(member, form.data, current_user)
        flash(f"{member.name}'s page is updated.", "success")
        return redirect(url_for("wiki.view_member", member_id=member.id))
    return render_template("wiki/edit_member.html", form=form, member=member)


@wiki_bp.route("/family/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    # POLICY CHANGE (June 12, 2026 — Wes's Trial Period rule): no longer
    # admin-only. The page's CREATOR may delete while it's unlocked; once
    # an admin locks it, admin-only. The rule lives in the service.
    member = db.get_or_404(FamilyMember, member_id)
    if not wiki_service.can_delete(member, current_user):
        abort(403)
    name = member.name
    wiki_service.delete_member(member, current_user)
    flash(f"The page for {name} was deleted.", "success")
    return redirect(url_for("wiki.list_members"))


@wiki_bp.route("/family/<int:member_id>/lock", methods=["POST"])
@login_required
def lock_member(member_id):
    if not current_user.is_admin:
        abort(403)
    member = db.get_or_404(FamilyMember, member_id)
    lock_service.lock(member, current_user)
    flash(f"{member.name}'s page is locked into the family archive — only an admin can delete it now.", "success")
    return redirect(url_for("wiki.view_member", member_id=member.id))


@wiki_bp.route("/family/<int:member_id>/unlock", methods=["POST"])
@login_required
def unlock_member(member_id):
    if not current_user.is_admin:
        abort(403)
    member = db.get_or_404(FamilyMember, member_id)
    lock_service.unlock(member, current_user)
    flash(f"{member.name}'s page is unlocked — its creator can delete it again.", "success")
    return redirect(url_for("wiki.view_member", member_id=member.id))


# --- Page history (the wiki's undo button) -----------------------------------
#
# RESTful shape: revisions are a sub-resource of the page —
#   GET  /family/<id>/history                 list every saved version
#   GET  /family/<id>/history/<rev_id>        read one old version
#   POST /family/<id>/history/<rev_id>/restore  copy it back onto the page
#
# Restore is open to every member, same as editing — a restore IS an edit
# (and it records a new revision itself, so even a restore can be undone).

@wiki_bp.route("/family/<int:member_id>/history")
@login_required
def member_history(member_id):
    member = db.get_or_404(FamilyMember, member_id)
    return render_template("wiki/history.html", member=member)


@wiki_bp.route("/family/<int:member_id>/history/<int:revision_id>")
@login_required
def view_revision(member_id, revision_id):
    member = db.get_or_404(FamilyMember, member_id)
    revision = wiki_service.get_revision(member, revision_id)
    if revision is None:
        abort(404)
    # Version numbers count up from 1 (oldest), like Wikipedia — stable
    # even as new revisions are added on top.
    older = [r for r in member.revisions if r.id < revision.id]
    return render_template(
        "wiki/revision.html",
        member=member, revision=revision, version_number=len(older) + 1,
        is_current=(revision.id == member.revisions[0].id),
    )


@wiki_bp.route("/family/<int:member_id>/history/<int:revision_id>/restore",
               methods=["POST"])
@login_required
def restore_revision(member_id, revision_id):
    member = db.get_or_404(FamilyMember, member_id)
    revision = wiki_service.get_revision(member, revision_id)
    if revision is None:
        abort(404)
    wiki_service.restore_revision(member, revision, current_user)
    flash(f"{member.name}'s page was restored to the older version.", "success")
    return redirect(url_for("wiki.view_member", member_id=member.id))
