# DEVDIARY — FamilyHub v1

**What this file is:** the living learning roadmap for FamilyHub. Each chapter
covers one build session: what was built, *why* it's best practice, every
technology choice, the WGU course where you'll meet the concept again, and any
decisions made while you were asleep. Read it top to bottom and you should be
able to explain every file in this repo.

**How to use it:** read the chapter, then open the files it mentions. The code
comments and this diary are written as a pair — the comments explain the line
in front of you, the diary explains the big picture.

---

## Chapter 0 — Codebase Audit (June 11, 2026)

Before building anything new, the existing Day-2/Day-3 skeleton was audited
against the rewritten CLAUDE.md. Verdict: **the foundation is solid** — the
application-factory pattern, Blueprint structure, `Config`-from-environment,
and the shared `db` object are all textbook-correct and were kept as-is.
Six issues were found and fixed:

| # | Finding | Fix | Lesson |
|---|---------|-----|--------|
| 1 | `requirements.txt` was a `pip freeze` of a polluted environment — it listed poetry, pipenv, keyring, and ~40 other packages this app never imports. | Rewritten to the ~10 direct dependencies, pinned to exact versions. | A requirements file documents *your app's* needs, not your machine's history. Pinned versions = identical installs on the desktop, the ThinkPad, and the Lightsail server. |
| 2 | A `static/` folder sat at the *project root*, but Flask serves static files from `app/static` (next to the package that created the app). The stylesheet in it was empty AND unreachable — double dead. | Deleted root `static/`; created `app/static/css/style.css` with real elderly-first styles (see Chapter 2). | Flask convention: `templates/` and `static/` live inside the package passed to `Flask(__name__)`. Files outside that are silently ignored — no error, just a 404. |
| 3 | `index.html` was a standalone page pulling Bootstrap from a CDN, ignoring the installed Bootstrap-Flask extension, with no shared layout. | Rebuilt on a `base.html` layout in Chapter 2 — every page now inherits one navbar, one stylesheet, one flash-message area. | **Template inheritance** is the DRY principle for HTML (D276 Web Development Foundations). Change the navbar once, every page updates. |
| 4 | No `.env` file existed locally, so the app silently ran with the hardcoded fallback `SECRET_KEY = "dev-fallback-key"`. Anyone knowing that string could forge session cookies. | Created `.env` (git-ignored) with a cryptographically random 64-hex-char key; added `.flaskenv` (committed) holding the non-secret `FLASK_APP=run.py`. | Secrets belong in the environment, never in code (the "12-Factor App" rule; D315 Network and Security – Foundations). Fallback values are fine for *booting*, dangerous for *running*. |
| 5 | `.gitignore` had the typo `__pychache__/` — Python bytecode caches (`__pycache__/`) were one `git add .` away from being committed. | Fixed the typo; also added `uploads/` (family photos must never enter git). | Generated artifacts don't belong in version control (D197 Version Control). |
| 6 | `README.md` was an empty Angular-CLI template leftover. | Replaced with real quick-start instructions and a project-layout map. | The README is the front door for any reviewer — including future-you. |

Also committed in this pass: the rewritten **CLAUDE.md** (new mission/spec)
and this file.

**New dependencies installed** (each gets its own chapter as it's used):

| Package | Job | v2 (Spring Boot) equivalent |
|---------|-----|------------------------------|
| Flask-Migrate 4.1.0 | Database schema migrations (Alembic) | Flyway / Liquibase |
| Flask-Login 0.6.3 | "Who is logged in?" session management | Spring Security session auth |
| Flask-WTF 1.3.0 | Form validation + CSRF protection | Spring `@Valid` + Spring Security CSRF |
| Flask-Bcrypt 1.0.1 | Password hashing | Spring Security `BCryptPasswordEncoder` — *literally the same algorithm* |
| Pillow 12.2.0 | Image validation + thumbnails | Thumbnailator / ImageIO |

---

## Chapter 1 — Database Migrations & CLI Commands

**What was built:** Flask-Migrate wired into the app factory, a `migrations/`
folder (committed to git), the first migration script, and a custom
`flask init-db` command ([app/cli.py](app/cli.py)).

### Why migrations instead of `db.create_all()`?

`db.create_all()` reads your models and creates whatever tables don't exist.
Sounds fine — until you *change* a model. It won't alter existing tables, it
keeps no history, and your laptop's database silently drifts away from the
server's. **Migrations are version control for your database schema**: every
change is a dated script in `migrations/versions/` that can be applied
(`upgrade`) or rolled back (`downgrade`) on any machine, in order.

The daily workflow from now on:

1. Edit/add a model class in `app/models/`
2. `flask db migrate -m "describe the change"` — Alembic *compares your
   models to the live database* and autogenerates the script
3. **Read the generated script** (autogenerate is good, not perfect)
4. `flask init-db` (or `flask db upgrade`) — apply it

WGU connection: D426 Data Management – Foundations (schema design) +
D197 Version Control (why history matters). v2 equivalent: **Flyway** — same
concept, SQL scripts instead of Python.

### Why a custom `init-db` command?

`flask init-db` is the one blessed way to set up or upgrade a database — on
your desktop, the ThinkPad, or the Lightsail server over SSH. It's a thin
wrapper around `flask db upgrade` today and will grow setup chores (like
ensuring the uploads folder exists) without anyone having to relearn anything.
Doing this in the terminal instead of a "setup page" means the app is never
on the internet with an unauthenticated setup endpoint.

### Files to read, in order

1. [app/__init__.py](app/__init__.py) — `migrate.init_app(app, db)` + `register_cli(app)`
2. [app/cli.py](app/cli.py) — the `init-db` command
3. [migrations/versions/](migrations/versions/) — the first migration: `create family_member table`

---

## Chapter 2 — Authentication

*(Being written — filled in when this step lands.)*

---

## Chapter 3 — Photo Albums

*(Being written — filled in when this step lands.)*

---

## Decisions Made Without Wes

Running log of judgment calls made mid-build, per the workflow rules
("make the simplest reasonable choice, document it, keep going").

1. **(Ch. 0)** Added a `.flaskenv` file. Flask's CLI auto-loads it when
   python-dotenv is installed; it holds only the non-secret `FLASK_APP=run.py`
   so `flask run`/`flask db` work without manual environment setup. Secrets
   still live only in `.env`.

---

## v1 → v2 Migration Map

Grows as the schema grows. The contract: every v1 concept has a named v2 home,
so the rewrite is a translation, not a redesign.

| v1 (Flask) | v2 (Spring Boot / Angular / MySQL) |
|------------|-------------------------------------|
| `app/routes/*.py` (Blueprints) | `@RestController` classes |
| `app/services/*.py` | `@Service` classes |
| `app/models/*.py` (SQLAlchemy) | `@Entity` classes + Spring Data `Repository` interfaces |
| `app/forms/*.py` (WTForms) | DTOs + Bean Validation (`@Valid`) |
| Jinja2 templates | Angular components |
| `migrations/` (Alembic) | Flyway migration scripts |
| SQLite (`instance/familyhub.db`) | MySQL (schema is portable SQL — no SQLite-only features used) |
| `.env` + `app/config.py` | `application.properties` / Spring profiles |

---

## Backups (upcoming required feature)

Placeholder: nightly SQLite + uploads backup to a Lightsail bucket, with a
documented, tested restore procedure. Not built yet; tracked so it isn't
forgotten.
