"""The main blueprint: home page, about page, and the hero image.

The home page is the ONLY public page in the app, and it shows zero family
content — logged-out visitors see a welcome message and a Login button,
nothing else. Everything with family PII lives behind @login_required
(CLAUDE.md privacy rule). Even the hero photo and the admin-written about
text count as family content, so they're login-walled too.
"""

import os

from flask import (
    Blueprint, Response, current_app, jsonify, render_template,
    send_from_directory,
)
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions import db
from app.services import settings_service, spec_service

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    # Settings only matter for the logged-in dashboard; don't even query
    # them for anonymous visitors.
    if current_user.is_authenticated:
        # FE(WP3): authenticated users go to dashboard.html (extends base.html);
        # index.html is now the standalone Chronicle public home page.
        return render_template(
            "dashboard.html",
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


# --- API documentation (developer-facing, still login-walled) -----------------

@main_bp.route("/apidocs")
@login_required
def apidocs():
    """The OpenAPI spec rendered as a browsable page — see spec_service
    for why this is server-side instead of Swagger UI."""
    spec = spec_service.load_spec()
    return render_template(
        "apidocs.html",
        info=spec["info"],
        grouped=spec_service.operations_by_tag(spec),
    )


@main_bp.route("/openapi.yaml")
@login_required
def openapi_yaml():
    """The raw spec — paste it into editor.swagger.io or feed it to v2's
    code generators."""
    with open(spec_service.spec_path(), encoding="utf-8") as handle:
        return Response(handle.read(), mimetype="text/yaml")


# --- Plumbing routes (no family content, deliberately public) -----------------

@main_bp.route("/health")
def health():
    """The standard liveness check every deployed app should have.

    nginx, Lightsail health checks, and uptime monitors all hit a URL like
    this to ask "are you alive?". It's public on purpose: it reveals
    nothing but "app up, database reachable" — and monitoring robots don't
    have logins. 200 = healthy; 503 = the load balancer should worry.
    (Ops habits like this are the deployment half of D480.)
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="ok")
    except Exception:
        return jsonify(status="degraded", database="error"), 503


# --- PWA plumbing (public: app shell only, zero family content) ---------------

@main_bp.route("/manifest.webmanifest")
def manifest():
    """The web app manifest — name, icons, colors — that makes 'Add to
    Home Screen' install a real-feeling app. Served through a route so
    we control the MIME type (Windows dev boxes often don't know
    .webmanifest)."""
    return send_from_directory(
        os.path.join(current_app.root_path, "static"),
        "manifest.webmanifest",
        mimetype="application/manifest+json",
    )


@main_bp.route("/sw.js")
def service_worker():
    """The service worker, served from the ROOT path on purpose: a worker
    may only control pages within its own path, so controlling "/" means
    serving from "/" — /static/js/sw.js could only control /static/."""
    return send_from_directory(
        os.path.join(current_app.root_path, "static", "js"),
        "sw.js",
        mimetype="text/javascript",
    )


@main_bp.route("/offline")
def offline():
    """The page the service worker shows when there's no connection.
    Public and standalone — it must render entirely from cache, and it
    contains no family content."""
    return render_template("offline.html")


@main_bp.route("/robots.txt")
def robots_txt():
    """Tell crawlers to index NOTHING. Everything real is login-walled
    anyway — this is defense in depth for privacy: even the login page
    and home page stay out of Google. A family archive has no SEO goals."""
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@main_bp.route("/.well-known/security.txt")
def security_txt():
    """RFC 9116: a machine-readable 'how to report a security problem'
    note at a standard path. Professional sites have one; it costs six
    lines. The Expires field is REQUIRED by the RFC (stale contact info
    is worse than none)."""
    body = (
        "Contact: mailto:wesley.leiter@gmail.com\n"
        "Expires: 2027-06-12T00:00:00.000Z\n"
        "Preferred-Languages: en\n"
    )
    return Response(body, mimetype="text/plain")
