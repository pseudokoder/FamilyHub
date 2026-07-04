# DEVDIARY — FamilyHub v1 (index)

FamilyHub is built by **two builders** (Master Plan §7), so the dev diary is
split in two — one file per builder — and this page is the "start here" index
that ties them together.

## The two diaries

- **[`DEVDIARY_BE.md`](DEVDIARY_BE.md) — Backend Dev Diary.** Owned by **Claude
  Code**: the GEDCOM-7 schema, models, migrations, services, REST routes, pytest,
  seed data, backups, Docker, deployment, and all infrastructure.
- **[`DEVDIARY_FE.md`](DEVDIARY_FE.md) — Frontend Dev Diary.** Owned by
  **Cowork**: the Jinja templates, CSS, vanilla JS, and the UX/UI story. (Begins
  at WP3, once the WP2 API contract is published.)

Splitting the file is deliberate: the two builders must never edit the same file
at the same time (Master Plan §7).

## Where the rest lives

- **Architecture, schema, scope, roadmap:** [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md)
  — the single source of truth.
- **Day-to-day working brief:** [`CLAUDE.md`](CLAUDE.md).
- **Cross-builder handoffs / open blockers:** [`BLOCKERS.md`](BLOCKERS.md).
- **The first build's detailed chapters (0–29)** — auth, photos, blog, wiki,
  timeline, backups, CI, Docker, OpenAPI, PWA, etc. — were written against the
  superseded "feature-per-table" data model. They live in this file's **git
  history** (before the WP1 re-foundation). The still-relevant infrastructure
  they describe is summarized in `DEVDIARY_BE.md` under "Preserved
  Infrastructure."

## Current status

- **WP1** (Database Foundation) — complete. See `DEVDIARY_BE.md` → "WP1."
- **WP2** (Backend CRUD + API contract + RBAC) — complete. See `DEVDIARY_BE.md` → "WP2."
- **WP3** (Front-end Chronicle home page) — implementation complete on
  `wp3-frontend-crud`; pending Wes review + merge. See `DEVDIARY_FE.md` → "WP3."
- **WP3 (backend gaps + admin)** and **WP4** (front-end: app shell, Home,
  People) — complete on `wp4-fe-shell` (merged forward from `wp3-frontend-crud`
  onto master); pending Wes review + merge. See `DEVDIARY_BE.md` and
  `DEVDIARY_FE.md` → "WP4."
