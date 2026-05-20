from flask_bootstrap import Bootstrap5
from flask import Flask

def create_app():
  app = Flask(__name__)
  bootstrap = Bootstrap5(app)

  # Config
  app.config["SECRET_KEY"] = 'dev-key-change-later'

  # Register blueprints
  from app.routes.main import main_bp
  app.register_blueprint(main_bp)

  return app
