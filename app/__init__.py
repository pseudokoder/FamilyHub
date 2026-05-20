from flask import Flask
from flask_bootstrap import Bootstrap5

def create_app():
  app = Flask(__name__)
  Bootstrap5(app)

  # Config
  app.config["SECRET_KEY"] = 'dev-key-change-later'

  # Register blueprints
  from app.routes.main import main_bp
  app.register_blueprint(main_bp)

  return app
