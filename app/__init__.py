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
from app.extensions import bcrypt, bootstrap, csrf, db, login_manager, migrate


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

    # Register blueprints — each one is a self-contained feature area.
    # v2 mapping: one Blueprint ≈ one Spring Boot @Controller class.
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.photos import photos_bp
    from app.routes.posts import posts_bp
    from app.routes.timeline import timeline_bp
    from app.routes.wiki import wiki_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(wiki_bp)
    app.register_blueprint(timeline_bp)

    # Custom Jinja filters — tiny functions templates can pipe text through:
    # {{ post.body | family_text }} renders typed text as safe HTML.
    from app.services.text_service import family_text
    app.jinja_env.filters["family_text"] = family_text

    # Custom terminal commands (flask init-db, flask create-admin)
    from app.cli import register_cli
    register_cli(app)

    return app
