"""The main blueprint: home page, about page, and the hero image.

The home page is the ONLY public page in the app, and it shows zero family
content — logged-out visitors see a welcome message and a Login button,
nothing else. Everything with family PII lives behind @login_required
(CLAUDE.md privacy rule). Even the hero photo and the admin-written about
text count as family content, so they're login-walled too.
"""

import os

from flask import Blueprint, render_template, send_from_directory
from flask_login import current_user, login_required

from app.services import settings_service

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    # Settings only matter for the logged-in dashboard; don't even query
    # them for anonymous visitors.
    if current_user.is_authenticated:
        return render_template(
            "index.html",
            tagline=settings_service.get("tagline"),
            hero_exists=settings_service.hero_exists(),
        )
    return render_template("index.html")


@main_bp.route("/about")
@login_required
def about():
    return render_template(
        "about.html",
        about_text=settings_service.get("about_text"),
        contact_text=settings_service.get("contact_text"),
    )


@main_bp.route("/site/hero")
@login_required
def hero_image():
    """The dashboard banner — served through the login wall like every
    other family image (see the photos chapter for the full lesson)."""
    return send_from_directory(
        os.path.dirname(settings_service.hero_path()),
        settings_service.HERO_FILENAME,
    )
