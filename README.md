# FamilyHub v1 (Lite)

[![CI](https://github.com/pseudokoder/FamilyHub/actions/workflows/ci.yml/badge.svg)](https://github.com/pseudokoder/FamilyHub/actions/workflows/ci.yml)

A private family portal: photo albums, family-history blog, member wiki, and
timeline — built with Python/Flask as both a real production app and a
learning project for a future Java/Spring Boot rewrite (v2).

**Start here:** read [DEVDIARY.md](DEVDIARY.md) — it's the guided tour of the
whole codebase, written like textbook chapters.

## Quick start (development)

```powershell
# 1. Activate the virtual environment (Windows)
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy .env.example to .env and set a real SECRET_KEY
copy .env.example .env

# 4. Create/upgrade the database (runs all migrations)
flask init-db

# 5. Create your first admin account
flask create-admin yourusername

# 6. Run the dev server
flask run
```

Then open http://127.0.0.1:5000 and log in.

## Management commands

```powershell
flask init-db                  # create/upgrade the database (runs migrations)
flask create-admin <username>  # bootstrap the first admin account
flask backup                   # full backup zip: DB + photos, verified,
                               # uploaded off-site if BACKUP_S3_BUCKET is set
flask restore-backup <zip>     # DESTRUCTIVE: restore DB + photos from a backup
flask export-data              # portable JSON export of everything (v2 migration)
```

## Stack

Python 3 · Flask · SQLAlchemy · Flask-Migrate · SQLite (dev) · Bootstrap 5

## Project layout

```
run.py            # entry point — creates the app via the factory
app/
  __init__.py     # application factory (create_app)
  config.py       # configuration, loaded from .env
  cli.py          # custom flask commands (init-db, create-admin)
  models/         # SQLAlchemy models        (≈ Spring Boot @Entity/Repository)
  services/       # business logic           (≈ Spring Boot @Service)
  routes/         # blueprints / view funcs  (≈ Spring Boot @Controller)
  forms/          # WTForms form classes + validation
  templates/      # Jinja2 HTML templates
  static/         # CSS/JS served by Flask
migrations/       # Alembic database migration scripts
instance/         # SQLite DB lives here (git-ignored)
uploads/          # uploaded photos (git-ignored, outside web root)
```
