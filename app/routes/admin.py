"""Admin panel routes: user account management.

CLAUDE.md's auth requirement is "admin-created accounts" — there is no
public registration page in this app at all. The family is invite-only:
an admin (Wes) creates each account and hands over a temporary password.

v2 mapping: AdminController.java guarded by Spring Security's
@PreAuthorize("hasRole('ADMIN')") — our @admin_required below is the
hand-rolled version of exactly that annotation.
"""

from functools import wraps

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    send_from_directory, url_for,
)
from flask_login import current_user, login_required

from app.forms.admin_forms import SiteSettingsForm
from app.forms.auth_forms import CreateUserForm, ResetPasswordForm
from app.models import User, db
from app.services import (
    audit_service, backup_service, settings_service, user_service,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    """Decorator: the page needs a logged-in user AND the admin flag.

    TEACHING NOTE: a decorator wraps a function in extra behavior without
    touching its body — here, a bouncer at the door of every admin view.
    @wraps preserves the original function's name so url_for() still works.
    """

    @wraps(view)
    @login_required  # first hurdle: logged in at all? (else -> login page)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            # 403 Forbidden = "I know who you are, and the answer is no."
            # (401 would mean "I don't know who you are.")
            abort(403)
        return view(*args, **kwargs)

    return wrapped


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
                username=form.username.data,
                display_name=form.display_name.data,
                password=form.password.data,
                is_admin=form.is_admin.data,
                actor=current_user,
            )
        except ValueError as err:
            # Duplicate username. Re-render the form with everything the
            # admin typed still in place — forgiving forms, always.
            flash(str(err), "danger")
        else:
            flash(
                f"Account for {user.display_name} created! "
                "Share the username and temporary password with them.",
                "success",
            )
            return redirect(url_for("admin.list_users"))
    return render_template("admin/new_user.html", form=form)


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
