"""Authentication routes: log in, log out. That's the whole file — routes
stay thin, the interesting work happens in user_service.

v2 mapping: AuthController.java (@Controller) calling AuthService.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import limiter
from app.forms.auth_forms import LoginForm
from app.services import user_service

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
        user = user_service.authenticate(form.username.data, form.password.data)
        if user is None:
            # Deliberately vague — see the security note in user_service.
            flash("That username and password don't match. Please try again.", "danger")
        else:
            # login_user writes the signed session cookie. remember=True adds
            # a separate 30-day cookie so closing the browser doesn't log
            # them out (lifetime set in config.py).
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.display_name}!", "success")
            return redirect(_safe_next(request.args.get("next")) or url_for("main.home"))

    return render_template("auth/login.html", form=form)


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
