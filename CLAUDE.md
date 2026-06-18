# Project: FamilyHub v1 ("Full")

> **Source of truth:** [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) governs this
> project — architecture, schema, scope, roadmap. When this file and the Master
> Plan disagree, the **Master Plan wins**; fix this file and log it in
> `BLOCKERS.md`. This file is the day-to-day working brief that points at it.

## Mission — Read This First
FamilyHub is, at its core, a **GEDCOM 7–compliant genealogy database** with a
**FamilySearch-style website** on top that lets logged-in family members do full
**CRUD** on every genealogy element. Everything else — the wiki, timeline, photo
album, memory blog — is **not a separate feature**; each is a different **view**
of the one shared database (Master Plan §1–§2). Build the genealogy core once;
every "feature" becomes a query against it.

This is a real production app for a real family (Wes's aging parents will upload
photos and write family-history memories), AND a **learning aid**: Wes will
reverse-engineer it for his WGU senior project — a Java/Spring Boot rewrite
(**v2, "Enterprise"**). Every decision must keep that migration painless.

**Naming:** v1 = "Full" (Flask/Python, built now). v2 = "Enterprise" (Java/Spring
Boot/Angular/MySQL/Docker). Never use "Lite" here (it means something else in the
sibling Cowork project).

## Who Builds What (two builders, one repo — Master Plan §7)
- **Claude Code → backend + the whole repo/infra.** GEDCOM-7 schema, models,
  migrations, services, REST routes, pytest, seed data, backups, Docker, deploy.
- **Cowork → front-end ONLY.** Jinja templates, CSS, vanilla JS — UX/UI as
  first-class concerns — built against the WP2 API contract.
- **Only one builder is active at a time** (Wes is the switch operator). Cowork
  does **not** start until WP2's contract exists.
- Wes reviews, learns, and gives feedback; he is **not** writing code alongside
  you. Deliver complete, working, reviewable work — no TODOs left for him.

## Cross-Builder Blocker Protocol (Master Plan §7 — non-negotiable)
- **Read `BLOCKERS.md` at the START of every session.** Resolve any `OPEN` item
  addressed to you, mark it `RESOLVED`, then proceed.
- When you hit a wall only the *other* builder can fix: **never fake or stub
  around it.** Stop that item, log it in `BLOCKERS.md` (date · raised-by ·
  what's blocked · what the other builder must do · status), continue other safe
  in-scope work, and **surface it in your end-of-session summary**.
- Design *preference* → pick a reasonable option and keep going (and note it).
  Hard *dependency* on the other builder → log and flag, never fake.

## Educational Requirements (non-negotiable)
- **Teacher-voice code comments.** Write as the world's greatest web-dev tutor —
  explain **WHY, not just WHAT**, and reference the WGU B.S. Software Engineering
  course that teaches the concept (e.g., "D426 Data Management – Foundations
  covers this normalization rule") and the **v2 Spring Boot mapping**.
- **Dev diaries are required, living deliverables** (split so the two builders
  never edit the same file — Master Plan §7):
  - [`DEVDIARY_BE.md`](DEVDIARY_BE.md) — backend (Code).
  - [`DEVDIARY_FE.md`](DEVDIARY_FE.md) — frontend (Cowork). **Code does not write
    this file.**
  - [`DEVDIARY.md`](DEVDIARY.md) — thin index pointing to both.
- Comments + dev diaries together should let a beginner-to-intermediate Python
  student understand the system without outside help.

## Workflow Rules
- **Front-load clarifying questions before building. Don't stop mid-task to ask**
  — except for genuine cross-boundary blockers (use `BLOCKERS.md`, above).
- Ambiguous mid-build? Make the simplest reasonable choice, document it in
  `DEVDIARY_BE.md` under "Decisions Made Without Wes," and keep going.
- **One work package at a time** (Master Plan §6), each on its **own branch off
  master** (e.g., `wp3-frontend-crud`). **Branch-per-WP (Master Plan §7):** tests
  MAY be red on a WP branch mid-build (expected WIP); a branch merges to master
  **only when the full suite is green** (the CI merge gate). So **master stays
  green via the merge gate**, and every WP branch ends in a **known state** —
  green, or red with the remaining work written down in `DEVDIARY_BE.md`. Wes is
  the integrator (reviews + merges/pushes).
- **Verify your own work with pytest** — never pause to ask Wes to manually test.
  Browser-only checks go in the **Manual Testing Checklist** in `DEVDIARY_BE.md`,
  cleared once at each WP boundary.
- **Commit** logically grouped changes with clear messages. **Do NOT push —
  Wes reviews and pushes** (pushing hangs on credentials here anyway).

## About the Developer
- Wes Leiter — WGU B.S. Software Engineering (expected Fall 2027).
- Currently in Python Intro; beginner-to-intermediate Python; rusty C/C++; back
  after ~8 years.
- ADHD-inattentive: concise explanations, concrete examples, no rabbit holes;
  bullet points, **bold key terms**, short paragraphs, ONE next action at a time,
  never more than one open question at a time.

## Scope (Master Plan §5 / §5A)
Logged-in members can: add/edit/delete **individuals, names, families,
parent/child links**; add **events & attributes** (birth, death, marriage,
residence, occupation…) with fuzzy dates + reusable places; see a **person page**
(vitals, names, events, relationships, sources, photos, stories); browse
**pedigree/fan-chart** views; attach **sources/citations**; upload **photos** and
attach them to people/families/events; write **memories** (Markdown); and (admins)
manage users, edit site text, verify backups.

**Depth bar (§5A):** every *user-meaningful* schema field maps to a real input
control. MVP = **fewer features, each fully realized** — never all features, each
hollow. (System/auto fields — `id`, timestamps, `gedcom_xref`, `author_id` — are
not user input.)

**Deferred to v2** (additive, no lock-in — Master Plan §3.6): ASSO (associations),
SUBM (submitters), video/audio, merge, change-history/restore. Full GEDCOM-7
file import/export is tentative v1 **WP6**, firm v2.

## UX/UI (Master Plan §5B — Cowork owns this)
Cross-generational warmth + **elderly-accessible**: large readable type, big tap
targets, high contrast, forgiving forms, minimal nav depth. Polished and
characterful (quality bar: Cinephile/Datumology — not a clone), calm by design
(generous whitespace, one primary action per screen, progressive disclosure).

## Security & Privacy (PII) — Critical (Master Plan §9)
Nearly everything is sensitive family PII. **Tier 1 (present, carry forward):**
bcrypt hashing, CSRF, strict CSP, login rate limiting, security headers,
login-walled photo serving, secure session cookies, password reset, HTTPS, PII
hidden for `living` individuals, upload validation, files stored outside the web
root. **Tier 2 (mid-project):** RBAC (§10), audit logging, encrypted backups,
secrets management, dependency scanning. Secrets in `.env` only, never committed;
`.env.example` stays current.

## Backups — Required Feature (Master Plan, §9)
Nightly automated backup of the SQLite DB + uploads to an AWS (Lightsail) bucket,
plus periodic instance snapshots. Backup/restore documented and tested
(`flask backup` / `flask restore-backup`; round trip covered by pytest).

## Stack
- Python 3.14, Flask (Blueprint structure), SQLite, SQLAlchemy, Flask-Migrate,
  Bootstrap (Bootstrap-Flask 5), venv. **Work inside the project `.venv`; never
  install to global Python; keep `requirements.txt` current.**
- Dev: Windows 11 desktop at `JW\PycharmProjects\FamilyHub` (also a Fedora
  ThinkPad; GitHub is the sync layer — always pull before starting).
- Production target: **AWS Lightsail** Linux (~$12/mo), gunicorn + nginx,
  Let's Encrypt SSL. Dev/staging: https://familyhub.pseudokoder.com.
  Future prod: https://leiters.org (public) + https://family.leiters.org (members).

## Design for the v2 Migration (WGU D286/D287/D288/D387)
v2 = **Java + Spring Boot + Angular + MySQL + Docker.** So now: clean portable
relational schema (no SQLite-only features; moves to MySQL without surgery);
stable integer PKs that survive export/import; **layered architecture** (routes =
Controller, services = Service, models = Repository — say so in comments);
RESTful, resource-oriented routes with view rendering separated from data logic;
a **data-export** management command (`flask export-data` → portable JSON + file
manifest) as the zero-data-loss guarantee. Document the v1→v2 mapping in
`DEVDIARY_BE.md` as the schema evolves.

## Current Status
- **WP1 (Database Foundation) complete (2026-06-16).** Path A re-foundation: the
  preserved infrastructure (auth, admin, backups, CI, Docker, security headers,
  OpenAPI, PWA, management commands, layered architecture) kept; the old feature
  data model replaced with the **GEDCOM-7 schema** (16 tables). One fresh
  Flask-Migrate baseline; `seed.py` + `flask seed`. See `DEVDIARY_BE.md` "WP1."
- **WP2 (Backend CRUD + API contract + RBAC) complete (2026-06-17).** Migrated
  `users` to §3.5 (email login + four-rung `role` + `is_active`); single
  authorization layer (`app/services/authz.py`, §10). **JSON REST API under
  `/api/*`** — full CRUD + search over the GEDCOM-7 schema, with polymorphic
  links and login-walled media (EXIF/GPS stripped). The **contract is
  `docs/openapi.yaml`** (route↔spec sync test enforced). **139 tests, ~95%
  coverage** (floor 90%). See `DEVDIARY_BE.md` "WP2."
- `BLOCKERS.md`: no open cross-builder blockers; the `users` §3.5 item is RESOLVED.

## Next Build Target — WP3 (Front-end, Cowork)
Per Master Plan §6 build order (one work package at a time; **branch-per-WP** per
§7 — WP3 is built on the **`wp3-frontend-crud`** branch off master):
1. **WP3 — Front-end (Cowork).** The elderly-accessible, cross-generational CRUD
   UI (Master Plan §5A depth bar / §5B design brief), built against the WP2 API
   contract in `docs/openapi.yaml`. Cowork owns Jinja templates, CSS, vanilla JS;
   **Code does not build genealogy UI** — it's on-call for contract fixes.
2. Then WP4 (views + search UI) → WP5 (deploy) → WP6 (GEDCOM import/export, tentative).
