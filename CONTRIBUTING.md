# Contributing to FamilyHub

This is a family project with an audience of ~8 — but it's run like a
real one, because that's the point (it's also a learning vehicle for a
WGU senior project). Here's everything you need to get productive.

## Local setup (Windows / macOS / Linux)

```bash
git clone https://github.com/pseudokoder/FamilyHub.git
cd FamilyHub
python -m venv .venv
# Windows:           .venv\Scripts\activate
# macOS/Linux:       source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then set a real SECRET_KEY inside
flask init-db               # creates the SQLite DB via migrations
flask create-admin you      # your login
flask run                   # http://127.0.0.1:5000
```

Prefer containers? `docker compose up --build` does all of it (see the
README's Docker section).

## Running the tests

```bash
pytest                      # the suite (133 tests, ~10s)
pytest --cov=app            # with the coverage report CI enforces (>=90%)
```

Every change ships with tests. The suite is the spec: permission rules,
security promises, and the OpenAPI contract are all *enforced* by tests,
not described in prose.

## House rules

1. **Layers stay separated.** Routes are thin; business rules live in
   `app/services/`; templates never re-derive a permission — they ask.
2. **Teacher-voice comments.** Code comments explain WHY, like a tutor
   would. If you make a non-obvious choice, say why right there.
3. **DEVDIARY.md is part of the change.** New feature → new chapter (or
   an addendum). Judgment call nobody approved → log it under "Decisions
   Made Without Wes."
4. **Migrations, always.** Schema changes go through `flask db migrate`
   + a human review of the generated script. Portable SQL only — this
   schema must move to MySQL without surgery.
5. **Document new routes** in `docs/openapi.yaml` — `test_openapi.py`
   fails the build if you forget (on purpose).
6. **No inline JavaScript or styles** in templates — the strict CSP
   blocks them. Behaviors go in `app/static/js/`, styles in `style.css`.
7. **Commit style:** `feat:` / `fix:` / `docs:` / `chore:` prefix, body
   says why. Group logically — one feature, one commit.

## Where things live

| What | Where |
|---|---|
| App factory + security headers | `app/__init__.py` |
| Config (all env-driven) | `app/config.py` + `.env.example` |
| One file per table | `app/models/` |
| Business rules | `app/services/` |
| Blueprints (controllers) | `app/routes/` |
| WTForms + validation | `app/forms/` |
| The API contract | `docs/openapi.yaml` (rendered at `/apidocs`) |
| Deployment artifacts | `Dockerfile`, `docker-compose.yml`, `scripts/deploy/` |
