import os

from dotenv import load_dotenv

# Project root = one level up from this file (app/config.py -> FamilyHub/)
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Read key=value pairs from the .env file into the environment.
# (Running via `python run.py` does NOT auto-load .env, so we do it here.)
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration, read from environment variables."""

    # Falls back to an obvious dummy so the app still boots if .env is missing.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-key")

    # Default to a SQLite file in the instance/ folder (git-ignored).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "instance", "familyhub.db"),
    )

    # Turn off a feature we don't use; silences a startup warning.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
