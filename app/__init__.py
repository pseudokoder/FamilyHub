"""The application factory — the heart of the whole app.

TEACHING NOTE: instead of creating one global `app` object at import time,
we define a *function* that builds and returns a fully-configured app.
This is Flask's **application factory pattern**, and it buys us:

  1. Testability — tests can build a throwaway app with test settings.
  2. No circular imports — extensions are created empty in
     app/extensions.py and connected to the app here, inside the function.
  3. Multiple configs — dev, production, and testing all use the same
     factory with a different Config class.

The v2 mapping: this file is what Spring Boot's auto-configuration +
`@SpringBootApplication` does for you automatically. Here we wire it by
hand, which is exactly why v1 is the better learning vehicle.
"""

import os

from flask import Flask

from app.config import Config
from app.extensions import (
    bcrypt, bootstrap, csrf, db, limiter, login_manager, mail, migrate,
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the folders the app writes to exist before anything needs
    # them: instance/ for the SQLite file, uploads/ for family photos.
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions against this app (see app/extensions.py for
    # who's who and why they're created over there).
    bootstrap.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    # CSRFProtect makes EVERY POST in the app require a valid token — secure
    # by default, instead of remembering to protect each form individually.
    csrf.init_app(app)
    # Rate limiting (only the login route opts in — see routes/auth.py).
    limiter.init_app(app)
    # Email (password-reset links only; hides itself when unconfigured).
    mail.init_app(app)

    # Behind nginx, every request "comes from" 127.0.0.1 — the real visitor
    # IP travels in the X-Forwarded-For header. ProxyFix teaches Flask to
    # trust that header (and X-Forwarded-Proto for https detection), which
    # the rate limiter needs to count per-visitor instead of lumping the
    # whole world together. Off by default: trusting these headers when
    # there ISN'T a proxy in front lets anyone spoof their IP.
    if app.config["TRUST_PROXY"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Friendly error pages instead of bare status dumps. Elderly-first
    # means even the failures guide rather than alarm — the visitor always
    # gets a calm explanation and a button home. Each returns its real HTTP
    # status code (so crawlers, monitors, and the browser still know the
    # truth); only the PRESENTATION is gentler.
    from flask import jsonify, render_template, request

    # WP2: the same error must speak the right language for its caller — a
    # friendly HTML page for the website, clean JSON for the /api surface (an
    # HTML error page would just confuse a fetch() call). One path check decides.
    def _api_request():
        return request.path.startswith("/api/")

    @app.errorhandler(400)
    def bad_request(error):
        if _api_request():
            return jsonify(error=getattr(error, "description", "Bad request.")), 400
        return error.get_response()  # web: the default page (e.g. CSRF rejection)

    @app.errorhandler(403)
    def forbidden(error):
        if _api_request():
            return jsonify(error="You don't have permission to do that."), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        if _api_request():
            return jsonify(error="Not found."), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if _api_request():
            return jsonify(error="That method isn't allowed on this URL."), 405
        return error.get_response()

    @app.errorhandler(429)
    def too_many_requests(error):
        if _api_request():
            return jsonify(error="Too many requests — please slow down."), 429
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(error):
        # NB: a real 500 means an unhandled exception already rolled back
        # the request; we render a static page and touch no database here.
        if _api_request():
            return jsonify(error="Something went wrong on our end."), 500
        return render_template("errors/500.html"), 500

    # --- HTTP security headers (D315) — sent with EVERY response. -----------
    # Each one closes a specific attack class. The star is the
    # Content-Security-Policy: the browser refuses to run any script that
    # isn't a file from OUR origin. Even if an XSS bug slipped past the
    # template escaping, the injected <script> would not execute — that's
    # defense in depth. Note there is NO 'unsafe-inline': every confirm
    # dialog and style lives in static files (see static/js/familyhub.js
    # for the refactor story).
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "       # data: = Bootstrap's tiny inline icons
            "font-src 'self'; "
            "object-src 'none'; "           # no Flash/plugins, ever
            "base-uri 'self'; "             # <base> tag can't be hijacked
            "frame-ancestors 'none'; "      # nobody may iframe us (clickjacking)
            "form-action 'self'",           # forms can only submit to US
        )
        # Belt and suspenders for older browsers that predate frame-ancestors.
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Browsers must not "sniff" a response into a different content type
        # (classic trick: upload a "photo" that sniffs as HTML+script).
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Outbound links learn our domain, never the full URL (which could
        # leak /family/<id> style paths to other sites).
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # We use none of these device APIs; say so explicitly.
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            # HSTS: once a browser has seen us over HTTPS, it refuses plain
            # http for six months. Only sent in production — pinning HTTPS
            # on http://127.0.0.1 would lock you out of your own dev server.
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=15552000; includeSubDomains"
            )
        return response

    # Register blueprints — each one is a self-contained feature area.
    # v2 mapping: one Blueprint ≈ one Spring Boot @Controller class.
    #
    # WP1 RE-FOUNDATION NOTE: this is deliberately a SHORT list. The old
    # photo/blog/wiki/timeline/plans/search blueprints were built on the wrong
    # data core and have been removed (Master Plan §1, "REBUILD the feature
    # layer"). What's left is the preserved infrastructure — auth, the admin
    # panel, and the public/plumbing routes in `main`. WP2 rebuilds the feature
    # routes against the new GEDCOM-7 schema, registering them right here.
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    # The WP2 JSON API (Master Plan §6/§7) — the contract Cowork builds WP3 on.
    app.register_blueprint(api_bp)

    # Custom Jinja filter — {{ about_text | family_text }} renders admin-entered
    # text as safe, paragraphed HTML (see text_service for the escaping story).
    from app.services.text_service import family_text
    app.jinja_env.filters["family_text"] = family_text

    # Custom terminal commands (flask init-db, flask create-admin, flask seed)
    from app.cli import register_cli
    register_cli(app)

    return app
