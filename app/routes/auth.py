"""Authentication routes: log in, log out. That's the whole file — routes
stay thin, the interesting work happens in user_service.

v2 mapping: AuthController.java (@Controller) calling AuthService.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import limiter
from app.forms.auth_forms import (
    ChangePasswordForm, ForgotPasswordForm, LoginForm, ResetPasswordForm,
)
from app.services import mail_service, user_service

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(target):
    """Only follow ?next= redirects that stay on OUR site.

    SECURITY NOTE: Flask-Login adds ?next=/albums/3 when it bounces someone
    to the login page, so we can return them where they were headed. But if
    we blindly redirect wherever ?next= says, an attacker could email Mom a
    link like /auth/login?next=https://evil.example — she logs in on the REAL
    site, then lands on a fake one. This is an "open redirect" vulnerability
    (D315). Rule: the target must be a relative path on this site.
    """
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    # SECURITY NOTE (D315): the @limiter.limit decorator above is the
    # anti-brute-force brake. A human mistyping a password hits maybe 3-4
    # tries a minute; a password-guessing robot hits hundreds. After 10
    # requests in a minute from one IP, the route answers "429 Too Many
    # Requests" (a friendly page) instead of running the check at all.
    # bcrypt already makes each guess SLOW — this makes volume IMPOSSIBLE.
    # Already logged in? There's nothing to do here — go home.
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    # validate_on_submit() is False for GET (just show the form) and runs
    # all validators + the CSRF check on POST. One route, both jobs.
    if form.validate_on_submit():
        user = user_service.authenticate(form.email.data, form.password.data)
        if user is None:
            # Deliberately vague — see the security note in user_service.
            flash("That email and password don't match. Please try again.", "danger")
        else:
            # login_user writes the signed session cookie. remember=True adds
            # a separate 30-day cookie so closing the browser doesn't log
            # them out (lifetime set in config.py).
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.display_name}!", "success")
            return redirect(_safe_next(request.args.get("next")) or url_for("main.home"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    """Step 1: type your email, get an emailed link. Rate-limited even tighter
    than login — each POST can trigger an outbound email."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if not mail_service.is_configured():
        flash("Email isn't set up on this server yet — ask Wes and he'll reset it for you.", "warning")
        return redirect(url_for("auth.login"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = user_service.find_by_email(form.email.data)
        if user is not None:
            token = user_service.generate_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            mail_service.send_password_reset(user, reset_url)
        # The SAME message whether the email exists or not — an attacker learns
        # nothing by guessing addresses here.
        flash(
            "If that email matches an account, a reset link is on its way. "
            "The link works for one hour — check spam if it's shy.",
            "success",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Step 2: arrive from the emailed link, choose a new password.
    user_service.verify_reset_token does all the deciding — expired,
    forged, and already-used tokens all come back None."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = user_service.verify_reset_token(token)
    if user is None:
        flash("That reset link is invalid or has expired — request a fresh one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user_service.set_password(user, form.password.data, actor=user)
        flash("Your password is reset — log in with the new one!", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, user=user)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Self-service password change — Wes shouldn't be a human helpdesk
    for every password the family wants to rotate."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Re-authenticate with the CURRENT password before changing
        # anything — see the form's docstring for the threat this stops.
        verified = user_service.authenticate(
            current_user.email, form.current_password.data
        )
        if verified is None:
            flash("That current password isn't right — nothing was changed.", "danger")
        else:
            user_service.set_password(
                current_user, form.password.data, actor=current_user
            )
            flash("Your password is changed! Use the new one from now on.", "success")
            return redirect(url_for("main.home"))
    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    """Arrive from a verification email and confirm the address (§9). A browser
    GET (it's an emailed link), so this is a web route, not JSON."""
    user = user_service.confirm_email_token(token)
    if user is None:
        flash("That verification link is invalid or has expired.", "danger")
    else:
        flash("Thanks — your email address is confirmed!", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """POST-only on purpose: actions that CHANGE state (logging out changes
    the session) must never be GET links. A GET logout can be triggered by a
    simple <img src="/auth/logout"> on any website — and POST gets CSRF
    protection automatically. RESTful discipline now = clean API for the
    Angular frontend in v2."""
    logout_user()
    flash("You've been logged out. See you soon!", "success")
    return redirect(url_for("main.home"))
