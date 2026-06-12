"""All configuration in one place, loaded from the environment.

TEACHING NOTE: the rule here is **code is public, configuration is secret**.
This file is committed to git; the VALUES it reads come from `.env`, which
never is. Same app code runs on your desktop and on Lightsail — only the
environment differs. (The "12-Factor App" methodology; v2 equivalent:
application.properties + Spring profiles.)
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

# Project root = one level up from this file (app/config.py -> FamilyHub/)
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Read key=value pairs from the .env file into the environment.
# (Running via `python run.py` does NOT auto-load .env, so we do it here.)
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration, read from environment variables."""

    # Signs session cookies so they can't be forged. Falls back to an obvious
    # dummy so the app still boots if .env is missing — fine for booting,
    # NEVER fine for production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-key")

    # --- Database ---------------------------------------------------------
    # Default to a SQLite file in the instance/ folder (git-ignored).
    # In production this same variable can point at MySQL — that's the v2
    # migration path in a single line.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "instance", "familyhub.db"),
    )

    # Turn off a feature we don't use; silences a startup warning.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session / cookie security (D315 Network and Security) -------------
    # HTTPONLY: JavaScript can't read the session cookie, so even an XSS bug
    # can't steal logins. SAMESITE=Lax: the browser won't send our cookie on
    # cross-site POSTs — a second wall against CSRF alongside form tokens.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # SECURE=True means "only send this cookie over HTTPS". Must be True in
    # production (Let's Encrypt), but has to stay False in local dev where
    # we use plain http://127.0.0.1 — hence env-driven.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"

    # The "keep me logged in" cookie (login form's pre-checked box).
    # 30 days = parents aren't retyping passwords every visit.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # --- Rate limiting (D315) ----------------------------------------------
    # Master switch Flask-Limiter reads. Tests turn it off (like CSRF) and
    # one dedicated test turns it back on to prove the brake works.
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "True") == "True"

    # True only in production behind nginx — see the ProxyFix note in the
    # application factory. Trusting proxy headers without a proxy = spoofable.
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "False") == "True"

    # --- Email (password-reset links) ---------------------------------------
    # MAIL_SERVER unset = the whole forgot-password feature hides itself
    # and the login page says "ask Wes" instead. Set all five in .env to
    # turn it on (e.g. Gmail SMTP with an app password).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "familyhub@localhost"
    )

    # --- Photo uploads ------------------------------------------------------
    # Uploads live OUTSIDE app/static on purpose: nothing in this folder is
    # ever served directly by the web server. Every photo goes through an
    # authenticated Flask route — family photos must never be one guessable
    # URL away from public (CLAUDE.md PII rule).
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(basedir, "uploads")
    )

    # Reject any request body over 25 MB *before* it's processed. Plenty for
    # phone photos (~3-10 MB); stops a 4 GB video upload from filling the disk
    # (video is explicitly a v2 feature).
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024

    # --- Backups ------------------------------------------------------------
    # Where backup zips are written locally (git-ignored). The OFF-SITE copy
    # goes to the Lightsail bucket named in BACKUP_S3_BUCKET — read straight
    # from the environment by backup_service, alongside the AWS credentials.
    BACKUP_FOLDER = os.environ.get(
        "BACKUP_FOLDER", os.path.join(basedir, "backups")
    )

    # Where `flask export-data` writes (git-ignored). In config rather than
    # hardcoded in the service — hardcoded paths are untestable paths.
    EXPORT_FOLDER = os.environ.get(
        "EXPORT_FOLDER", os.path.join(basedir, "export")
    )
