import os

from flask import Flask
from flask_bootstrap import Bootstrap5

from app.config import Config
from app.models import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the instance/ folder exists so SQLite can create its file there.
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions against this app.
    Bootstrap5(app)
    db.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
