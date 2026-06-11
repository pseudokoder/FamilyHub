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

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.wiki_forms import FamilyMemberForm
from app.models import FamilyMember
from app.services import wiki_service

wiki_bp = Blueprint("wiki", __name__)


@wiki_bp.route("/family")
@login_required
def list_members():
    return render_template("wiki/members.html", members=wiki_service.get_all_members())


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
    return render_template("wiki/member.html", member=member)


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
    if not current_user.is_admin:
        abort(403)
    member = db.get_or_404(FamilyMember, member_id)
    name = member.name
    wiki_service.delete_member(member)
    flash(f"The page for {name} was deleted.", "success")
    return redirect(url_for("wiki.list_members"))
