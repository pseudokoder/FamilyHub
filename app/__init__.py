"""The application factory — the heart of the whole app.

TEACHING NOTE: instead of creating one global `app` object at import time,
we define a *function* that builds and returns a fully-configured app.
This is Flask's **application factory pattern**, and it buys us:

  1. Testability — tests can build a throwaway app with test settings.
  2. No circular imports — extensions (db, login, ...) are created empty at
     module level and connected to the app here, inside the function.
  3. Multiple configs — dev, production, and testing all use the same factory
     with a different Config class.

The v2 mapping: this file is what Spring Boot's auto-configuration +
`@SpringBootApplication` does for you automatically. Here we wire it by hand,
which is exactly why v1 is the better learning vehicle.
"""

import os

from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_migrate import Migrate

from app.config import Config
from app.models import db

# Extensions are created "empty" at module level and bound to the app inside
# the factory via init_app(). (Same idea as `db` in app/models/__init__.py.)
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the instance/ folder exists so SQLite can create its file there.
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions against this app.
    Bootstrap5(app)
    db.init_app(app)
    # Flask-Migrate needs both the app AND the db — it compares your models
    # against the live database to generate migration scripts.
    migrate.init_app(app, db)

    # Register blueprints — each one is a self-contained feature area.
    # v2 mapping: one Blueprint ≈ one Spring Boot @Controller class.
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # Custom terminal commands (flask init-db, flask create-admin, ...)
    from app.cli import register_cli
    register_cli(app)

    return app
