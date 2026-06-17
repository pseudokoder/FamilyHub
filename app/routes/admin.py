"""Admin panel routes: user account management.

CLAUDE.md's auth requirement is "admin-created accounts" — there is no
public registration page in this app at all. The family is invite-only:
an admin (Wes) creates each account and hands over a temporary password.

v2 mapping: AdminController.java guarded by Spring Security's
@PreAuthorize("hasRole('ADMIN')") — our @admin_required below is the
hand-rolled version of exactly that annotation.
"""

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    send_from_directory, url_for,
)
from flask_login import current_user

from app.forms.admin_forms import SiteSettingsForm
from app.forms.auth_forms import CreateUserForm, EditUserForm, ResetPasswordForm
from app.models import User, db
from app.services import (
    audit_service, backup_service, settings_service, user_service,
)
# The admin gate now comes from the ONE authorization layer (Master Plan §10),
# not a decorator hand-rolled here — so every permission rule lives in one place.
from app.services.authz import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users")
@admin_required
def list_users():
    return render_template("admin/users.html", users=user_service.get_all_users())


@admin_bp.route("/activity")
@admin_required
def activity():
    """The audit trail: who did what, newest first. Append-only — this
    page only reads. 'Who deleted the Thanksgiving album?' lives here."""
    return render_template(
        "admin/activity.html", events=audit_service.recent_events(limit=100)
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def site_settings():
    """The 'basic site text fields' panel from CLAUDE.md: tagline, about,
    contact, and the dashboard hero photo."""
    form = SiteSettingsForm(data=settings_service.get_all())
    if form.validate_on_submit():
        settings_service.set_value("tagline", form.tagline.data)
        settings_service.set_value("about_text", form.about_text.data)
        settings_service.set_value("contact_text", form.contact_text.data)
        if form.hero.data and form.hero.data.filename:
            error = settings_service.save_hero_image(form.hero.data)
            if error:
                flash(error, "danger")
                return render_template("admin/settings.html", form=form)
        audit_service.log_event(current_user, "edit", "site settings")
        db.session.commit()
        flash("Site settings saved.", "success")
        return redirect(url_for("admin.site_settings"))
    return render_template(
        "admin/settings.html", form=form, hero_exists=settings_service.hero_exists()
    )


@admin_bp.route("/backups")
@admin_required
def backups():
    """The 'trigger/verify backups' panel from CLAUDE.md."""
    return render_template("admin/backups.html", backups=backup_service.list_backups())


@admin_bp.route("/backups/run", methods=["POST"])
@admin_required
def run_backup():
    """Back Up Now: create, verify, and (if configured) upload — then tell
    the admin exactly what happened, honestly."""
    path = backup_service.create_backup()
    report = backup_service.verify_backup(path)
    audit_service.log_event(
        current_user, "run backup", "backup",
        detail="verified" if report["ok"] else "FAILED verification",
    )
    db.session.commit()
    if report["ok"]:
        flash(
            f"Backup created and verified — DB ({report['db_tables']} tables) "
            f"plus {report['file_count']} uploaded file(s).",
            "success",
        )
        uploaded, message = backup_service.upload_backup(path)
        flash(message, "success" if uploaded else "warning")
    else:
        flash("Backup FAILED verification: " + "; ".join(report["problems"]), "danger")
    return redirect(url_for("admin.backups"))


@admin_bp.route("/backups/<filename>/download")
@admin_required
def download_backup(filename):
    """Let the admin pull a backup zip to their own computer — a manual
    off-site copy that works even before the bucket is set up.

    SECURITY: the filename comes from the URL, so we only accept names that
    appear in our own backup list — no path tricks can reach other files.
    """
    known = {b["filename"] for b in backup_service.list_backups()}
    if filename not in known:
        abort(404)
    return send_from_directory(
        current_app.config["BACKUP_FOLDER"], filename, as_attachment=True
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        try:
            user = user_service.create_user(
                email=form.email.data,
                display_name=form.display_name.data,
                password=form.password.data,
                role=form.role.data,
                actor=current_user,
            )
        except ValueError as err:
            # Duplicate email. Re-render the form with everything the admin
            # typed still in place — forgiving forms, always.
            flash(str(err), "danger")
        else:
            flash(
                f"Account for {user.display_name} created! "
                "Share the email and temporary password with them.",
                "success",
            )
            return redirect(url_for("admin.list_users"))
    return render_template("admin/new_user.html", form=form)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    """Fix a display name, change the login email, or change the role."""
    user = db.get_or_404(User, user_id)
    # obj=user pre-fills the form (display_name, email, role) from the account.
    form = EditUserForm(obj=user)
    if form.validate_on_submit():
        try:
            # Email first — it's the one change that can be rejected (a clash
            # with another account's address).
            user_service.set_email(user, form.email.data, actor=current_user)
        except ValueError as err:
            flash(str(err), "danger")
            return render_template("admin/edit_user.html", form=form, user=user)
        user_service.set_display_name(user, form.display_name.data,
                                      actor=current_user)
        user_service.set_role(user, form.role.data, actor=current_user)
        flash(f"{user.display_name}'s account is updated.", "success")
        return redirect(url_for("admin.list_users"))
    return render_template("admin/edit_user.html", form=form, user=user)


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@admin_required
def reset_password(user_id):
    # get_or_404: fetch the row or show a 404 page — never a crash. A wrong
    # id in the URL is a user mistake, not a server error.
    user = db.get_or_404(User, user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_service.set_password(user, form.password.data, actor=current_user)
        flash(f"New password set for {user.display_name}.", "success")
        return redirect(url_for("admin.list_users"))
    return render_template("admin/reset_password.html", form=form, user=user)
