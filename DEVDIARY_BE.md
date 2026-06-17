# FamilyHub — Backend Dev Diary

> The learning roadmap for the **backend + infrastructure** half of FamilyHub,
> written like textbook chapters: what was built, **why** it's best practice,
> every technology choice and its WGU curriculum connection, and the v2 (Java/
> Spring Boot) mapping. **Claude Code owns this file.** Cowork keeps the
> front-end story in [`DEVDIARY_FE.md`](DEVDIARY_FE.md); the thin
> [`DEVDIARY.md`](DEVDIARY.md) indexes both. The architecture/scope source of
> truth is [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md).

---

## Preserved Infrastructure (carried over from the first build)

FamilyHub's first build (66 commits) produced excellent engineering scaffolding
on the *wrong data core*. Per **Path A** (Master Plan §1), WP1 **kept** that
scaffolding and rebuilt only the data model. The carried-over infrastructure —
each documented in detail in the original `DEVDIARY.md` chapters, which remain in
**git history** — is:

- **App factory + Blueprints** (`app/__init__.py`, `app/extensions.py`) — the
  `create_app(Config)` pattern, the `init_app` extension wiring, and the
  constraint **naming convention** (`fk_…`, `ix_…`) that keeps migrations
  portable from SQLite to MySQL. (Old Ch. 0–1.)
- **Authentication** — Flask-Login sessions, bcrypt hashing, the `users` table,
  `flask create-admin`, password self-service, and the tokenless forgot-password
  email flow (`itsdangerous`-signed, single-use). (Old Ch. 2, 20.)
- **Admin panel** — user management, site settings (hero/about/contact), backups
  UI, and the audit-trail view. (Old Ch. 7, 18.)
- **Backups + data export** — `flask backup` (consistent SQLite snapshot, zip,
  verify, S3 upload), `flask restore-backup`, and `flask export-data` (portable
  JSON + checksummed file manifest = the v2 zero-data-loss guarantee). (Old Ch. 8–9.)
- **Security hardening (§9 Tier 1)** — strict CSP (no `unsafe-inline`), the full
  security-header set, CSRF on every POST, login rate limiting, login-walled
  file serving, secure cookies. (Old Ch. 11–13, 19.)
- **Quality + ops** — pytest + Flask test client, CI with a 90% coverage floor,
  the test-enforced OpenAPI spec, Docker + compose, PWA (manifest + service
  worker), friendly error pages, `scripts/deploy/`. (Old Ch. 10, 13, 21–26.)

What this diary stops describing as live: the **feature layer** (photo albums,
memory blog, family wiki, timeline, family plans, site search, the "What's New"
feed, photo tagging, content locking, the old GEDCOM export). Those were built on
the superseded data model and were **removed** in WP1 (see below). Their code
lives in git history if any of it is worth salvaging — most notably
`photo_service`'s EXIF/GPS-stripping + thumbnailing, which WP2's media-upload
pipeline should lift from history rather than rewrite.

---

## WP1 — Database Foundation (2026-06-16)

**Goal (Master Plan §6, WP1):** replace the feature-shaped data model with the
**GEDCOM-7 genealogy schema** as SQLAlchemy models, on one fresh Flask-Migrate
baseline, with `seed.py` mock data and pytest — keeping the app booting and the
coverage floor green. Build *nothing* beyond that (the feature/UX layer is
WP2/WP3).

### 1. The corrected vision: one database, many views

The old app had a table per *feature* (`photos`, `posts`, `timeline_events`, …).
The Master Plan's core insight (§1–§2): FamilyHub is really **one genealogy
database**, and the wiki, timeline, album, and memory blog are just different
**queries** against it. So the schema models genealogy *facts*, not website
*pages*. Get that right and a "feature" is a view, not a new table.

### 2. What was removed (and why it's safe)

Deleted from the working tree: the models `family_member`, `photo`, `photo_tag`,
`post`, `wiki_revision`, `timeline`, `family_plan`, `mixins`; their routes
(`photos`, `posts`, `wiki`, `timeline`, `plans`, `search`); their services
(`activity`, `gedcom`, `lock`, `photo`, `plan`, `post`, `search`, `tag`,
`timeline`, `wiki`); their forms, templates, the `album-reorder` JS, and their
tests. The `main` blueprint lost its `/activity` route; `app/__init__.py` lost
five blueprint registrations.

**Why delete instead of archive on a branch?** Git history *is* the archive —
nothing is lost, and a learning codebase is clearer without dead feature code
confusing the reader. (Recorded as a decision below.)

**Two boot-critical seams** had to be cut carefully, because `base.html` (which
every page extends) and the home page rendered links/imports into the removed
code:
- `base.html` / `index.html` called `url_for('photos.…')` etc. — removing the
  blueprints without editing the templates would 500 *every* page. Both were
  trimmed to the surviving nav (Home, About, Admin) with a teacher-note comment
  pointing at the WP2/WP4 rebuild.
- `settings_service` imported `ALLOWED_EXTENSIONS` from the (removed)
  `photo_service`. That import was **severed** by giving the hero-image feature
  its own local allow-list — a small "depend on nothing you don't need" win.

### 3. The GEDCOM-7 schema (Master Plan §3)

16 tables, one file per logical group under `app/models/`. The design rules,
each chosen for a reason worth learning:

- **Durable identity = internal integer PK.** Per the GEDCOM 7 spec, the
  `@I1@`-style cross-reference ids are *transient* between files and must never
  be shown to users or used as keys. So every table has an integer `id` as its
  real identity, and a **nullable `gedcom_xref`** reserved for future
  import/export (WP6). (WGU D426: choose a stable primary key.)
- **Polymorphic attachment** (`subject_type` + `subject_id`) on `events`,
  `citations`, `media_links`, `note_links`. One `events` table attaches to an
  *individual* OR a *family*; one `media_links` table attaches a photo to a
  person, family, or event. This is the mechanism that makes "everything is a
  view" work. **Trade-off:** the database can't enforce a polymorphic link with
  a real foreign key, so the *application* does (see §4). (Master Plan §8; v2/
  Hibernate can formalize with `@Any`.)
- **Dual dates.** Genealogy is full of fuzzy dates. Each event stores BOTH the
  raw GEDCOM string `date_original` ("ABT 1850", "March 1962") for faithful
  display AND a normalized, sortable `date_sort` ("1850-00-00") so a timeline can
  `ORDER BY` it. Faithful *and* sortable, neither sacrificed.
- **Standard SQL only** — `Numeric(10,7)` for lat/long (not float, which loses
  precision), `db.Text` vs `db.String(n)`, real `Boolean`/`Date` types,
  deterministic constraint names — so the whole schema moves to MySQL in v2
  without surgery. (WGU D426/D427.)

The tables, by group:
- **Genealogy core:** `individuals` + `names` (a person collects many names —
  normalized into a child table); `families` + `family_children` (the
  parent/child many-to-many resolved with a junction table that also carries
  `pedigree_type`); `places` (reused across events).
- **Events & evidence:** `events` (births, deaths, marriages, occupations…,
  polymorphic + indexed on subject and `date_sort`); `repositories` → `sources`
  → `citations` (genealogy's evidence chain, citations polymorphic with a QUAY
  quality score).
- **Media & narrative:** `media_objects` + `media_links` (the photo album,
  GEDCOM-style); `notes` + `note_links` (Markdown memories/bios). Both link
  tables are polymorphic with composite primary keys.
- **Application layer:** `users`, `site_settings`, `audit_log` (carried over).

### 4. The polymorphic trade-off, paid in `genealogy_service`

Because a polymorphic link has no real FK, the database can't cascade-delete an
individual's events/media/notes/citations. So `app/services/genealogy_service.py`
owns that: `delete_individual()` / `delete_family()` sweep up every polymorphic
attachment (including citations on the person's *names* and links on their
*events*), then delete the record — whose real-FK children (names,
family_children) the ORM cascade removes automatically. Routing every delete
through one service is the §10 "single authorization/service layer" principle and
maps straight to a Spring Boot `@Service` method.

> **Teaching note on cascades + SQLite:** the DB-level `ON DELETE CASCADE` we
> declare is for MySQL/direct-SQL fidelity; in pytest (SQLite with FK
> enforcement off) it's the **SQLAlchemy relationship cascade**
> (`cascade="all, delete-orphan"`) that does the work. Belt and suspenders.

### 5. Migrations — one clean baseline

No production data exists, so the 12 old migration files were deleted and a
single fresh migration generated: `flask db migrate -m "initial GEDCOM-7 schema"`
→ `flask db upgrade` builds all 16 tables from scratch. Verified by running
`flask seed` against the migration-built database — if the migration and the
models disagreed, seed would fail; it didn't. (Tests themselves use
`db.create_all()` for speed, so migrations get their real workout here.)

### 6. `seed.py` — three generations as a proof

`seed_all()` builds the fictional **Hartwell family**: 9 individuals (several
names each), 3 families with children of varied pedigree (birth/adopted), 12
events with fuzzy *and* exact dates over 4 reusable places, a repository + 2
sources + 4 citations, 2 placeholder media objects, and 3 Markdown notes. It
deliberately exercises **every table and every polymorphic subject kind**
(citations touch all four: individual/family/event/name). A clean run is the WP1
acceptance proof; `flask seed` runs it, and `tests/test_seed.py` asserts the
exact row counts so the seed and its proof stay in lockstep.

### 7. Tests + coverage

New `tests/test_models.py` (creation, name reassembly, real-FK + ORM cascade
deletes, polymorphic attach/query, the `genealogy_service` sweep helpers) and
`tests/test_seed.py`. The old feature tests were removed; `test_backup_export`,
`test_security_headers`, `test_auth`, and `test_openapi` were updated to the
surviving surface; a new `tests/test_cli.py` covers the operator commands
(`create-admin`, `seed`, `backup`, `export-data`). **Result: green at ~93%
coverage** (floor 90%).

### 8. v1 → v2 mapping (new this WP)

| v1 (Flask/SQLAlchemy) | v2 (Spring Boot/JPA) |
|---|---|
| `Individual`, `Name`, `Family`… models | `@Entity` classes |
| `db.relationship(..., cascade="all, delete-orphan")` | `@OneToMany(cascade=ALL, orphanRemoval=true)` |
| Polymorphic `subject_type`+`subject_id` | Hibernate `@Any` or per-type junctions |
| `genealogy_service` delete helpers | `@Service` methods |
| Flask-Migrate baseline | Flyway baseline (WP-A) |
| `flask export-data` JSON + manifest | the v1→v2 import (WP-D) reads it |

---

## Decisions Made Without Wes (WP1)

Per the workflow rule ("make the simplest reasonable choice, document it, keep
going"). Cross-plan deviations are also logged in `BLOCKERS.md`.

1. **`users` kept as-is, NOT aligned to §3.5.** Confirmed with Wes in planning:
   keep username-login + `is_admin` (preserved, tested auth) and defer the
   email-login + `role` enum + `is_active` alignment to WP2, where §10 schedules
   the auth/RBAC layer. Logged OPEN in `BLOCKERS.md`.
2. **`audit_log` kept** though it's not in the §3 table list — it's preserved
   security infrastructure (§9 Tier 2) and additive/portable, so it locks
   nothing in.
3. **`site_settings` renamed** `key`/`value` → §3.5 `setting_key`/`setting_value`
   (one-line service change; clean baseline, no data to migrate).
4. **Superseded feature code deleted, not branched.** Git history is the archive.
5. **`requirements.txt` left unpruned.** Pillow/pillow-heif return for WP2 media
   handling; removing them now would just be churn.
6. **`text_service` trimmed, not removed.** The About page still pipes admin text
   through the `family_text` filter; the old `[[Name]]` wiki-linking (which
   depended on the removed wiki) was dropped, leaving a dependency-free
   escape-and-paragraph renderer. WP2 reintroduces rich Markdown rendering.
7. **Export `_serialize` handles `Decimal`** (place lat/long) by emitting floats,
   alongside the existing datetime→ISO-8601 handling.

---

## Manual Testing Checklist

WP1 is a data-foundation work package: **everything in it is verified by pytest
plus the `flask db upgrade` / `flask seed` commands** — there is no new browser
UI to eyeball. The UI manual checks return when Cowork builds the front-end
(WP3), and live in `DEVDIARY_FE.md`.

Carried forward for the **deployment** boundary (WP5), unchanged and still valid:
- [ ] `docker compose up --build` on a Docker host → app on :8000, log in,
      restart the container, data survived.
- [ ] With real `MAIL_*` in the server `.env`: request a reset link, receive the
      real email, complete the reset (logic is tested; only SMTP delivery needs eyes).
- [ ] HTTPS padlock on https://familyhub.pseudokoder.com.
- [ ] Nightly cron backup ran (check `backups/backup.log`) and the zip landed in
      the Lightsail bucket; Lightsail instance snapshot scheduled.

---

## WP1 → WP2 Readiness

The data foundation is in place and green. WP2 can now build the **service + REST
route layer** for individuals/families/events/sources/media/notes against these
models, add the §10 role scaffolding, and — the key deliverable — publish the
**API contract** in `docs/openapi.yaml`. That contract is the handoff that lets
Cowork start WP3. Before starting WP2, read `BLOCKERS.md` (the `users` §3.5
alignment is the one open item, and it's a WP2 task).

---

## WP2 — Backend CRUD + API Contract + RBAC (2026-06-17)

**Goal (Master Plan §6):** build the backend that the front-end (WP3) consumes —
a JSON CRUD + search API over the GEDCOM-7 schema — resolve the `users`/RBAC
blocker (§3.5/§10), and **publish the API contract**. Code writes no genealogy
templates; that's Cowork's WP3.

### 1. The `users` migration — changing the lock without breaking the door

The highest-risk change touched preserved, tested security. The key realization:
**the security *mechanisms* are independent of the login *identifier*.** bcrypt,
CSRF, login rate-limiting, the signed single-use reset tokens, the vague-error
pattern, and the open-redirect guard all stayed byte-for-byte — only the lookup
key moved from `username` to `email`. Two moves de-risked it:

- **`is_admin` became a computed `@property`** over the new `role` (`role ==
  'admin'`). So `base.html`, the admin gate, and every `current_user.is_admin`
  check kept working with zero edits — the blast radius shrank to the handful of
  places that genuinely needed email/role.
- **The hardening tests kept their assertions** (CSRF-fires, rate-limit-fires,
  open-redirect-blocked, vague-error) and stayed green — they're the *proof* the
  migration preserved the security, not just a hope.

`users` now matches §3.5: `email NOT NULL UNIQUE` (the login key), a four-rung
`role` (`app/models/role.py` — GUEST/USER/POWER\_USER/ADMIN, stored as a portable
`VARCHAR(20)`, with a rank order for "at least USER?" checks), and `is_active`
(which Flask-Login reads, so deactivating an account is a one-column switch). The
schema change rode in on a **new Alembic migration** using `batch_alter_table`
(SQLite rebuilds the table to alter a column), with an `is_admin → role` data
backfill. Gotcha learned: in a batch rebuild you must **explicitly `drop_index`**
an index on a column you're dropping, or Alembic tries to recreate it on the new
table and fails (`no such column: username`).

### 2. The one authorization layer (§10 anti-lock-in)

Every permission decision routes through `app/services/authz.py` — the
`role_required(min_role)` decorator (and `admin_required = role_required(ADMIN)`).
The old hand-rolled `admin_required` in `admin.py` now imports from here. Adding a
role or a granular permission later is a change in ONE file. The decorator also
returns the *right kind* of "no": a JSON 401/403 for `/api`, an HTML
redirect/page for the website (one `request.path.startswith("/api/")` check).
v2: this collapses into Spring Security's `@PreAuthorize("hasRole(...)")`.

### 3. The JSON API — thin controllers, fat services (Controller→Service→Repository)

Approved consumption model: a **JSON REST API under `/api/*`**. Every route is a
thin controller — parse, call one service, `jsonify` — and all logic + the
serialization shape lives in per-resource services (`individual_service`,
`family_service`, …). Because the service returns plain dicts, Cowork's WP3 can
fetch the JSON *or* server-render Jinja by calling the same service — identical
shape either way. Uniform errors (`ApiError` → `{"error", "fields"}` with the
right status) make the contract trustworthy.

**Polymorphic writes** all go through one gate, `genealogy_service.require_subject`,
which validates the `subject_type` is allowed for *this* attachment and that the
target row exists — the referential check the database can't do for a polymorphic
FK (§8). Deletes reuse the WP1 cascade helpers and gained a `delete_event` sibling.

### 4. Media — the privacy-critical resource

`media_service` salvages the first build's upload pipeline from git history (the
five rules: extension allow-list, Pillow content-verify, random UUID names,
storage outside the web root, and **EXIF/GPS stripping** by re-encoding). Files
are served only through `@login_required` routes — a family photo never has a
public URL. A pytest uploads a GPS-tagged image and asserts the stored file has no
GPS block — the privacy promise, enforced forever.

### 5. Search (§12) — and a scoping decision

`GET /api/search`: people by name (`LIKE`, wildcards escaped) + filters (sex,
living, birth-year range via `substr(date_sort,1,4)`, place) and a text search
over notes. **Decision:** the notes search uses portable `LIKE` now; Master Plan
§12 schedules **SQLite FTS5** for WP4, and doing it now would pull a SQLite-only
virtual table into the schema, breaking the §3 "standard SQL only" rule. The
endpoint *shape* is the contract — WP4 swaps the implementation behind it.

### 6. The contract + tests

`docs/openapi.yaml` documents every `/api` route with request/response component
schemas; the route↔spec sync test fails the build if a route is undocumented.
**139 tests, ~95% coverage** (floor 90%) — every resource has CRUD happy-path,
validation-400, auth/role-enforcement, and polymorphic-link/cascade tests, all
hittable as JSON with no UI required.

### 7. v1 → v2 mapping (added this WP)

| v1 (Flask) | v2 (Spring Boot) |
|---|---|
| `Role` enum + `role` VARCHAR | Spring Security authorities |
| `authz.role_required(Role.ADMIN)` | `@PreAuthorize("hasRole('ADMIN')")` |
| `/api/*` blueprint + `jsonify` | `@RestController` returning DTOs |
| per-resource `*_service.serialize()` | DTO mappers (MapStruct) |
| `ApiError` → uniform JSON | `@ControllerAdvice` exception handlers |

### Decisions Made Without Wes (WP2)
1. **`/api/*` prefix** for the JSON API — leaves the root URLs free for Cowork's
   WP3 human pages; conventional; v2 Angular consumes `/api/*`.
2. **`is_admin` kept as a computed property** (shrinks the migration blast radius).
3. **Notes search = `LIKE` now, FTS5 in WP4** (§12; honors §3 portability).
4. **Media metadata is immutable** after upload — re-uploading is a new object,
   which keeps the strip-on-upload guarantee simple (no edit path that could
   reintroduce EXIF).
5. **`seed.py` gained demo users** (emails + varied roles, a dev-only password)
   so the API and RBAC have real accounts to exercise.

### Manual Testing Checklist (WP2)

Still nothing browser-only for Code: the API is fully verified by pytest, and the
preserved auth/admin pages are covered too. Carry-forward deployment checks
(WP5) are unchanged from the WP1 entry above.

### WP2 → WP3 Readiness

**The contract is ready for Cowork.** `docs/openapi.yaml` is the stable interface:
JSON CRUD for every genealogy resource + sub-records + polymorphic links, a search
endpoint, uniform error shapes, and a documented auth model (login → reads;
USER → writes; `X-CSRFToken` on writes). Cowork's WP3 builds the elderly-accessible,
cross-generational UI (§5A/§5B) against it — server-rendering via the services or
fetching the JSON, their choice. No cross-builder blockers are open; the one
former blocker (`users` §3.5) is RESOLVED in `BLOCKERS.md`.
