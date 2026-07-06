"""Admin panel routes (Master Plan §9, §10) — FE-6 native-Chronicle console.

THIN VIEW CONTROLLERS ONLY: every route below either renders a client-rendered
shell (JS drives the WP2 JSON API — the same "Flask renders a shell, fetch()
does the rest" split as every other FE-2..FE-5 page) or keeps an existing
server-rendered form that already worked (create/edit account, the legacy
site-text-and-hero form, the legacy direct-set-password form) — restyled by
the shared Chronicle stylesheet cascade, not rewritten. See
docs/FRONTEND_DESIGN.md's FE-6 entry for which sections went which way, and
why the legacy site-text form and the new grouped settings console are two
separate pages rather than one.

v2 mapping: AdminController.java + a couple of small sibling @Controllers for
the legacy form flows — same layered-architecture rule as every other blueprint.
"""

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    send_from_directory, url_for,
)
from flask_login import current_user

from app.forms.admin_forms import SiteSettingsForm
from app.forms.auth_forms import CreateUserForm, EditUserForm, ResetPasswordForm
from app.models import User, db
from app.models.role import Role
from app.services import (
    audit_service, backup_service, settings_service, user_service,
)
# The admin gate routes through the ONE authorization layer (Master Plan §10):
# most of this console needs `administer` (Admin only); Activity needs only
# `revert` (Curator+ — see its own route below for why).
from app.services.authz import admin_required, role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================================
# THE NATIVE CHRONICLE CONSOLE (FE-6) — each view renders a thin shell; all
# data comes from the browser calling docs/openapi.yaml's AdminApi/Inbox/
# WriteControl/Tree endpoints (see app/static/js/admin.js).
# ============================================================================

@admin_bp.route("")
@admin_required
def dashboard():
    """The console's landing view: aggregate stats, backup health at a
    glance, and the two queues that need eyes (suggestions, role requests),
    each with a one-click jump to its own section."""
    return render_template("admin/dashboard.html")


@admin_bp.route("/users")
@admin_required
def list_users():
    """Every account — role, linked person, active/verified state — plus
    email-a-reset-link / secure change-email / link-unlink-person actions and
    the read-only role→permission matrix. Client-rendered against
    GET /api/admin/users + GET /api/permissions/matrix (FE-6; replaces the old
    server-rendered table at this same URL/endpoint name, so the redirects in
    create_user/edit_user below need no change)."""
    return render_template("admin/users.html")


@admin_bp.route("/suggestions")
@admin_required
def suggestions():
    """The suggestions inbox: filterable triage list (status/topic/priority)
    over GET/PUT /api/suggestions."""
    return render_template("admin/suggestions.html")


@admin_bp.route("/role-requests")
@admin_required
def role_requests():
    """Pending role-change requests (approve/deny) + decided history, over
    GET /api/role-requests + its approve/deny actions."""
    return render_template("admin/role_requests.html")


@admin_bp.route("/config")
@admin_required
def settings_console():
    """The grouped config-as-data settings — branding/defaults/security/email
    — over GET/PUT /api/settings.

    DELIBERATELY A SEPARATE PAGE from the legacy /admin/settings site-text-
    and-hero form below: the backend already carries two independent settings
    surfaces (settings_service.KNOWN_KEYS's tagline/about_text/contact_text/
    hero vs. SETTING_GROUPS's site_name/security/email/defaults) that share no
    keys and no endpoint. Rather than force them into one page (and rather
    than move the working legacy form to a new URL, which would strand its
    existing pytest coverage), this new page lives at its own URL and links to
    the legacy one. See docs/FRONTEND_DESIGN.md's FE-6 entry."""
    return render_template("admin/config.html")


@admin_bp.route("/backups")
@admin_required
def backups():
    """Overview (list + sizes, storage location, disk headroom, schedule),
    back-up-now with its verification report, the schedule editor, and the
    guarded restore — client-rendered against GET /api/admin/backups + friends
    (FE-6; replaces the old static list at this same URL/endpoint name)."""
    return render_template("admin/backups.html")


@admin_bp.route("/activity")
@role_required(Role.CURATOR)
def activity():
    """The full audit trail: paginated, filterable, with per-entry revert and
    restore-a-deleted-record actions (FE-6; replaces the old static table).

    CURATOR+, not Admin-only: Curator holds the `revert` permission (§10;
    BLOCKERS.md, 2026-07-03 RESOLVED), so this is the one console page a
    non-Admin Curator can reach — the shared admin subnav hides every OTHER
    section from a Curator who isn't also an Admin."""
    return render_template("admin/activity.html")


# ============================================================================
# LEGACY SERVER-RENDERED FLOWS — kept exactly as they were (still work;
# restyled for free by the shared Chronicle stylesheet cascade, same as every
# other Bootstrap-classed page in this app). Linked from the new console
# pages above where a section still needs them.
# ============================================================================

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
    """Set a new password directly, by hand.

    Superseded in the new Users console by the emailed reset-link action
    (POST /api/admin/users/{id}/reset-password), which is safer (the admin
    never sees or chooses the member's password) — that's the action the new
    console page links to. Left reachable at this URL, not deleted: it still
    works correctly, and removing a working feature nobody asked to remove is
    a bigger change than this FE-6 brief called for."""
    # get_or_404: fetch the row or show a 404 page — never a crash. A wrong
    # id in the URL is a user mistake, not a server error.
    user = db.get_or_404(User, user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_service.set_password(user, form.password.data, actor=current_user)
        flash(f"New password set for {user.display_name}.", "success")
        return redirect(url_for("admin.list_users"))
    return render_template("admin/reset_password.html", form=form, user=user)


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def site_settings():
    """The 'basic site text fields' panel: tagline, about, contact, and the
    dashboard hero photo — a real, still-needed capability the grouped
    /api/settings contract doesn't cover (see settings_console above)."""
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


@admin_bp.route("/backups/run", methods=["POST"])
@admin_required
def run_backup():
    """Back Up Now via a plain form POST + flash messages.

    Superseded in the new Backups console by POST /api/admin/backups/run,
    which shows the verification report inline without a redirect — that's
    the action the new console page's button calls. Left reachable at this
    URL, not deleted, same reasoning as reset_password above."""
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
