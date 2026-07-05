# FamilyHub — Backend Dev Diary

> The learning roadmap for the **backend + infrastructure** half of FamilyHub,
> written like textbook chapters: what was built, **why** it's best practice,
> every technology choice and its WGU curriculum connection, and the v2 (Java/
> Spring Boot) mapping. **The Backend Builder (BE) owns this file.** The Frontend
> Builder (FE) keeps the front-end story in [`DEVDIARY_FE.md`](DEVDIARY_FE.md); the thin
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
UI to eyeball. The UI manual checks return when the Frontend Builder (FE) builds the front-end
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
the Frontend Builder (FE) start WP3. Before starting WP2, read `BLOCKERS.md` (the `users` §3.5
alignment is the one open item, and it's a WP2 task).

---

## WP2 — Backend CRUD + API Contract + RBAC (2026-06-17)

**Goal (Master Plan §6):** build the backend that the front-end (WP3) consumes —
a JSON CRUD + search API over the GEDCOM-7 schema — resolve the `users`/RBAC
blocker (§3.5/§10), and **publish the API contract**. Code writes no genealogy
templates; that's the Frontend Builder's (FE) WP3.

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
`family_service`, …). Because the service returns plain dicts, the Frontend
Builder's (FE) WP3 can fetch the JSON *or* server-render Jinja by calling the same
service — identical shape either way. Uniform errors (`ApiError` → `{"error", "fields"}` with the
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
1. **`/api/*` prefix** for the JSON API — leaves the root URLs free for the Frontend
   Builder's (FE) WP3 human pages; conventional; v2 Angular consumes `/api/*`.
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

**The contract is ready for the Frontend Builder (FE).** `docs/openapi.yaml` is the
stable interface: JSON CRUD for every genealogy resource + sub-records + polymorphic
links, a search endpoint, uniform error shapes, and a documented auth model (login →
reads; USER → writes; `X-CSRFToken` on writes). The Frontend Builder's (FE) WP3
builds the elderly-accessible, cross-generational UI (§5A/§5B) against it — server-rendering via the services or
fetching the JSON, their choice. No cross-builder blockers are open; the one
former blocker (`users` §3.5) is RESOLVED in `BLOCKERS.md`.

---

## Docs — v1 Design Reconciliation (2026-07-03)

**Docs-only run** (no application code, migrations, or endpoints — those are BE
Prompt 2). Goal: fold a batch of approved design decisions into the Master Plan,
bump it, and stand up the ADR index. Branch `docs/reconcile-v1-design` off master.

**Why a MAJOR bump (→ 2.0.0).** SemVer for a *plan* tracks the scope contract, not
code. One decision — **promoting write-control (audit + soft-delete + revert) into
v1** — changes the schema and the definition of "delete," so it's a breaking change
to the contract downstream builders rely on. That forces MAJOR; everything else
(role rename, new additive scope) rides along under it.

**What landed in `docs/MASTER_PLAN.md`:**
1. **Write-control → v1** (ADR-0001). Added a **soft-delete design rule** (§3), an
   **`audit_log` table** to §3.5, flipped §3.6 / §8 / §9 from "deferred" to
   "v1-active." Audit logging moved from §9 Tier-2 to **Tier-1** because it's now
   a data-fidelity guarantee, not a nice-to-have.
2. **Fan Chart → v2.** v1 tree is now Pedigree + Family Group + Relationship View.
   The teaching point I wrote into §3: **the person graph is a graph, not a linked
   list** — traversal must not assume one linear ancestor chain (this is the exact
   bug a beginner writes first). The renderer is orientation-parameterized and the
   endpoint does lazy subtree fetch — those are *seams*, deliberately cheap now so
   the v2 horizontal-toggle and pan/zoom canvas aren't rewrites.
3. **Associations → v2 confirmed**, but I drew the line explicitly: **core family
   relationships (via FAM links) stay v1**; only the non-family "Other
   Relationships" (ASSO) section defers.
4. **RBAC rename** GUEST/USER/POWER USER/ADMIN → **Viewer/Contributor/Curator/
   Admin**, plus **permissions-as-data** (a role = a bundle of flags) with a
   read-only matrix in v1. The "as data" framing is the anti-lock-in move: custom
   roles become a row, not a code change.
5. **New v1 scope** wired into §3.5/§5/§8/§9: Account↔Person link (ADR-0002,
   `users.individual_id`, oldest-ancestor fallback), self-authored living-member
   records, suggestions inbox + role-change requests (two new tables sketched),
   transactional email (verification), white-label branding, per-user timezone,
   and a config-driven security baseline.
6. **v1.x + parking lot** captured (Family Address Book; MFA/TOTP, notification
   email, pan/zoom canvas, theme switcher, the reserved **Family Bunch** seam).

**ADR index.** Created `docs/adr/README.md` — a one-row-per-decision table so future
threads orient in one glance instead of re-reading every ADR.

### Decisions Made Without Wes (docs reconciliation)
1. **Schema sketched in the plan, not just prose.** I added real `CREATE TABLE`
   stubs for `audit_log`, `suggestions`, and `role_requests` (and new columns on
   `users`) rather than describing them in words. The Master Plan §3 is written *as*
   schema, so keeping new v1 scope in that form keeps the doc coherent and gives BE
   Prompt 2 an unambiguous target. No migration was written — that's BE Prompt 2.
2. **README role labels left as-is** (`GUEST/USER/POWER_USER/ADMIN`). The rename is
   a *plan* decision; the shipped **code enums still use the old names**, and the
   README documents what's actually built. I'll rename README (and the enums) in
   **BE Prompt 2** when the code changes, so the portfolio face never describes
   something that isn't there yet.
3. **`site_settings` stays key/value** for branding + the security baseline rather
   than growing typed columns — matches the existing §3.5 shape and keeps new config
   additive.

### Blocked this run
**Task A is half-blocked.** The two files Wes was to drop in —
`docs/adr/0002-account-person-link.md` and `docs/CONTEXT_LOG.md` — **were not in the
working tree** (confirmed by `find` + a clean `git status`). Per the blocker
protocol I did **not** author them (the brief says "commit as-is, do not rewrite").
The ADR index and every Master-Plan reference already point at ADR-0002 by its
agreed title, so dropping the file in later closes the loop with no rework. Logged
in `BLOCKERS.md`; see the session summary for the one next action.

### Manual Testing Checklist (docs reconciliation)
Nothing browser-only. Verify the Master Plan renders on GitHub (tables in §3.5/§4/
§10, the Revision History list) and that the ADR index links resolve **once
ADR-0002 is committed**.

---

## WP3 — Backend Gaps: write-control, account link, tree endpoints (2026-07-03)

**Goal:** build the backend pieces the WP3 front-end needs but WP2 didn't have —
the ADR-0001 write-control model, the ADR-0002 account↔person link, and the "view"
endpoints (pedigree, relationships, stats, timeline). Docs-only reconciliation
(v2.0.0) approved the scope; this is the code. Built in five phase-gated steps,
each ending green.

### 1. Schema, migration, and the RBAC rename (Phase 1)

One additive migration (`c2f1a7b9d4e0`) carries the whole schema delta:
- **Soft-delete** (`deleted_at`) on the 11 user-editable tables, via a reusable
  `SoftDeleteMixin`. *Why a mixin:* the column is identical everywhere — define it
  once (DRY), and a new soft-deletable table inherits one class. (D426/D480.)
- **`users.individual_id`** (nullable FK, ADR-0002) + **`timezone`**.
- **`audit_log`** renamed `target_*` → `subject_*` (matching the schema-wide
  polymorphic convention) + `before_json`/`after_json` for revert.
- **`media_objects.capture_date`** (+ sortable) — *when a photo was taken*, which
  is not when it was uploaded (`created_at`). Same dual-date trick as events.
- **`historical_events`** almanac table (timeline backdrop, seeded from a bundled
  list; `flask seed-historical` is prod-safe + idempotent).
- **RBAC rename** GUEST/USER/POWER_USER/ADMIN → **Viewer/Contributor/Curator/
  Admin**, with a data migration for existing rows. `Role.coerce` still accepts
  the old strings, so a pre-rename database keeps resolving (belt *and* suspenders
  alongside the migration).
- **Permissions as data** (`permissions.py`): a role → a frozenset of permission
  flags, checked via `authz.permission_required`. This is the §10 anti-lock-in
  seam — v2 moves the map into an editable table and *no check changes*.

*Teaching note (batch_alter_table):* SQLite can't rename/drop a column in place, so
every change goes through Alembic's table-rebuild. Verified the migration
upgrades, downgrades, and re-upgrades cleanly against a temp DB.

### 2. Write-control: the recoverability guarantee (Phase 2)

`write_control.py` is the ONE place mutations are audited and reversed (ADR-0001):
- Every create/update/(soft-)delete on the genealogy entities writes an audit row
  with a **generic column snapshot** — one `snapshot()`/`_apply()` pair serves
  every table, so there's no per-entity audit serializer to keep in sync.
- **Delete = soft delete** everywhere. Reads hide deleted rows through a SINGLE
  guard in `get_or_404` (every GET/PUT/DELETE/sub-resource lookup routes through
  it) plus per-`list_all` filters. Media keeps its files on disk; source/note
  deletes no longer cascade — recoverability forbids destroying the children.
- **Revert is uniform** because `before_json` is a full row image: replay it to
  undo an update/delete/restore; soft-delete the row to undo a create.
- Endpoints: `GET /api/activity` (Curator+), `POST /api/restore`,
  `POST /api/audit/<id>/revert` (both need the `revert` permission).

*Decision:* three old tests asserted hard-delete/cascade behaviour (files removed,
citations/links cascaded). ADR-0001 deliberately reverses that, so those tests now
assert soft-delete semantics — the requirement changed, not the test's honesty.

### 3. Account ↔ Person + self-authoring (Phase 3)

`account_service.py`: admin link/unlink (one person ↔ one account, enforced +
audited), "my person", **self-edit** (a linked member may edit their OWN record
regardless of role — the ADR-0002 self-authoring case), and the **fallback tree
root** (linked person, else the earliest-born ancestor who is nobody's child).

### 4. The view endpoints (Phase 4)

- **Pedigree** (`tree_service.graph`): a bounded **graph slice** (nodes + edges)
  from any node, ancestors/descendants, `depth`-limited, with per-node
  `has_ancestors`/`has_descendants` flags for **lazy subtree fetch**. Written as a
  BFS because *the tree is a graph, not a linked list* — branches rejoin, people
  have many spouses; assuming a linear chain is the first bug a beginner writes.
- **Relationship finder** (`tree_service.relationship`): BFS to each person's
  ancestor set, pick the nearest common ancestor by least combined distance, then
  translate the two distances into English — direct line, sibling, Nth cousin M
  times removed, aunt/uncle, with spouse/in-law as best-effort fallbacks. Verified
  against an explicit clan fixture (the label matrix is a test, not a hope).
- **List item** now carries birth/death year + a place; the People list, search,
  and tree nodes share one `PersonListItem` shape.
- **Stats + On This Day + almanac** (`stats_service`, `historical_event_service`)
  feed Home and the Admin dashboard.

### 5. Contract + docs (Phase 5)

`docs/openapi.yaml` documents every new path and schema (the sync test enforces
it), and its delete summaries now say "soft-delete (recoverable)". README and this
diary updated. `openapi.yaml`'s Contributor/soft-delete notes replace the old
USER/hard-delete language.

### v1 → v2 mapping (added this WP)

| v1 (Flask) | v2 (Spring Boot) |
|---|---|
| `SoftDeleteMixin` + `deleted_at` filters | `@SQLDelete` + `@Where("deleted_at is null")` |
| `write_control` snapshot/revert | Hibernate Envers audit history |
| `permissions.py` role→flags dict | a `role_permissions` table + `hasAuthority` |
| `authz.permission_required` | `@PreAuthorize("hasAuthority('revert')")` |
| `tree_service` BFS graph slice | a `TreeService` over JPA, same BFS |
| `users.individual_id` FK (ADR-0002) | the same nullable FK on the JPA `User` |

### Decisions Made Without Wes (WP3 backend gaps)

1. **audit_log kept `user_id` (not `actor_user_id`)** — the committed Master Plan
   §3.5 sketch and the existing column both use `user_id`; matching them avoided a
   needless rename that would break the preserved admin/backup logging. (The
   Phase-1 prompt's `actor_user_id` was a naming variance; the spec wins.)
2. **Soft-delete does NOT cascade to owned children.** Deleting an individual
   soft-deletes just that row; its names/events stay (hidden with the parent) so a
   restore/revert brings the person back whole. Simpler and fully recoverable; a
   future WP can add cascade-soft-delete if the FE wants a "trash" view of children.
3. **Places/repositories stay hard-delete** (reference data, `SET NULL`), so
   they're not in the write-control/soft-delete set. Noted here rather than
   forcing them into a model they don't fit.
4. **Restore/revert are generic endpoints** (`/api/restore`, `/api/audit/<id>/
   revert`) rather than per-resource — one contract surface, driven by the audit
   trail, instead of eight near-identical routes.
5. **`historical_events` is not in the data export** — it's regenerable reference
   data (re-seeded from the bundled list), like not backing up a package cache.

### Manual Testing Checklist (WP3 backend gaps)

Nothing browser-only for Code — the whole surface is JSON, fully covered by pytest
(176 tests, ~93% coverage, floor 90%). For the integrator: after `flask db
upgrade`, run `flask seed-historical` once on any real environment so the timeline
has its almanac backdrop (dev `flask seed` already does this).

### WP3 backend → front-end readiness

The contract in `docs/openapi.yaml` now covers write-control, the account link,
and every view endpoint the FE needs (pedigree, relationships, stats, On This Day,
historical events). No cross-builder blockers are open.

---

## WP3 — Admin, Email & Security (2026-07-03)

**Goal:** the backend for the admin console the FE (WP3, Cowork) will build —
suggestions inbox, role requests, transactional email + email verification, the
settings-driven security baseline, and the sensitive admin actions (change-email,
backups). The rule this run lived by: **extend the preserved MVP security tier,
never rebuild it.** Five phase-gated steps, each green.

### 1. Config as DATA, and two small tables (Phase 1)

`site_settings` was already key/value, so the entire admin/security/branding config
is just NEW ROWS — no columns, no migration. `settings_service` grew a `DEFAULTS`
map, typed accessors (`get_int`/`get_bool`), grouped `editable_settings()`, and a
validating `update_settings()`. The **SMTP password stays in `.env`** (the existing
secrets mechanism); only non-secret SMTP config lives in settings. Two additive
tables — `suggestions` and `role_requests` (migration `d4a2c8e1f7b3`).

### 2. Email + security hardening — extend, don't duplicate (Phase 2)

- **mail_service** kept Flask-Mail as the transport (so the suite's
  `record_messages()` capture still works) but became **settings-driven**: SMTP host/
  port/user/from come from settings, falling back to env, and it's DB-tolerant so a
  fresh install (no settings table yet) still sends via env. Added generic `send()`,
  email verification, a change-notice, and a send-test.
- **One password gate.** `security_service.validate_password` is called by *every*
  set-password path (create, admin reset, self change, token reset), so the length
  minimum + the **HIBP breach check** can't be bypassed by picking a different door.
  The breach check is textbook **k-anonymity**: SHA-1 the password, send only the
  5-char prefix, scan suffixes locally — the password never leaves the process — and
  it **fails open** on a network outage (availability beats a nice-to-have).
- **Lockout + session timeout.** Migration `e7b5c9d3a1f2` added `email_verified_at`,
  `failed_login_count`, `locked_until`. `authenticate` now counts failures and locks
  the account at the settings threshold (complementing the per-IP limiter); the
  factory reads `session_timeout_days` per request to expire idle sessions. All live
  values, tunable without a redeploy.

### 3. Inbox + role requests (Phase 3)

`suggestion_service` / `role_request_service` + `/api/suggestions` and
`/api/role-requests`. The "prioritized queue" is not a second table — it's this
table filtered to items with a priority, ranked (one table, many views again).
**Approving a role request applies the change through the audited
`user_service.set_role`** — the elevation is as traceable as any edit (ADR-0001).

### 4. The sensitive admin actions (Phase 4)

`admin_service` + `/api/admin/*`, all extending the existing audited services:
- **Secure change-email** — the careful dance: **step-up re-auth** (the admin
  re-enters their OWN password, defeating the walk-away-from-the-laptop attack),
  notify BOTH addresses, apply (un-verifies), verification link to the new address,
  then **force a password reset** by scrambling the old credential + emailing a reset
  link. One audit line for the whole thing.
- **Guarded restore** — the scariest button in the app, so: explicit `confirm`,
  step-up re-auth, our-list-only filename (no path tricks), and an **automatic
  safety backup taken FIRST**, so even a bad restore is itself recoverable.
- Settings CRUD, backup detail (sizes, disk headroom, schedule, last/next run) +
  back-up-now, and the read-only **permission matrix** (permissions-as-data, §10;
  editable roles stay v2).

### v1 → v2 mapping (added this WP)

| v1 (Flask) | v2 (Spring Boot) |
|---|---|
| `settings_service` key/value config | `@ConfigurationProperties` + a settings table |
| HIBP k-anonymity via `urllib` | a `PwnedClient` bean, same range query |
| per-account lockout columns | Spring Security `AccountStatusUserDetailsChecker` |
| step-up re-auth before sensitive ops | Spring Security re-authentication / `AuthorizationManager` |
| `mail_service` (Flask-Mail) | `JavaMailSender` + a `MailService` |

### Decisions Made Without Wes (WP3 admin)

1. **New admin capabilities are JSON `/api/*`, not HTML.** The FE builds against the
   contract (the established WP3 pattern); the preserved HTML admin panel keeps
   working untouched. So there are now two surfaces to the same audited services.
2. **SMTP transport stayed Flask-Mail** (settings drive its config) rather than a
   hand-rolled `smtplib` sender — keeps the test-capture mechanism and avoids
   duplicating a working feature. A best-effort `_apply_settings()` pushes admin
   config onto the live mail state; env remains the reliable fallback.
3. **"Force a password reset" = scramble + reset link.** After an admin email
   change, the old credential is set to an unguessable random value so it's truly
   dead until the user completes the emailed reset — the strongest reading of
   "force."
4. **The cron RUNNER is out of scope.** The backup *schedule* is stored + surfaced
   (with a computed next-run) for the admin UI; the actual nightly trigger remains an
   OS-cron/deploy concern (Master Plan §9), not an in-app scheduler.
5. **suggestions/role_requests are not in the JSON data export** — operational data,
   low migration value; noted so it's a conscious choice, not an oversight.

### Manual Testing Checklist (WP3 admin)

Nothing browser-only for Code — all JSON, fully covered by pytest (207 tests, ~92%
coverage, floor 90%). For the integrator, on a real environment after `flask db
upgrade`: run `flask seed-settings` (config defaults) and configure SMTP (settings +
`MAIL_PASSWORD` in `.env`) to light up email; the breach check and lockout are on
once their settings are enabled.

### WP3 admin → front-end readiness

`docs/openapi.yaml` now documents the inbox, role requests, email verification, all
admin actions, and the permission matrix. No cross-builder blockers are open.

---

## WP5 — Docs Reconciliation + Cross-Builder Blockers (2026-07-03)

**Goal:** a docs-and-fixes run bridging WP3 (backend admin) and WP4 (frontend
shell) — commit ADR-0003, reconcile the Master Plan, and resolve the two blockers
FE raised while building the WP4 nav and Home page.

### 1. ADR-0003 — and finding its own motivating bug still live

Committed `docs/adr/0003-white-label-neutral-language.md` verbatim (the rule: no
personal names/contact in the app's own UI copy, config defaults, or build-detail
docs; author credit and origin narrative stay fine elsewhere). The ADR's own
motivating example — a login page reading *"Call or text Wes"* — turned out to
still be live in the app, not hypothetical: `login.html`, `forgot_password.html`,
the 403/429/500 error pages, and a flash message in `auth.py` all named the
author. Worse, the login-page copy was **stale advice**: it told people to text
someone for a password reset when self-serve email reset has existed since
WP3-backend-admin Phase 2. Fixed all of it to neutral phrasing ("contact your
family administrator") and updated the two tests that asserted the old copy.
Seed data (`seed.py`'s fictional "Hartwell family") is untouched — ADR-0003
explicitly allows fictional demo names.

### 2. Master Plan MINOR bump (2.1.0 → 2.2.0)

Decision-capture only: a §8 pointer + the top-of-doc ADR callout now cite
ADR-0003. No new scope — the white-label rule was already implicit in the
existing branding scope (§5/§8.9); this makes it explicit and citable.

### 3. Blocker 1 — the admin gate, aligned to permissions-as-data

Before touching anything, I verified the CLAIM in the blocker: is a non-admin
actually getting a wrong answer today? A quick probe (viewer/contributor/curator
clients against `GET /api/admin/users`) showed correct 403s across the board —
so this was an **architectural gap, not a live bug**. `admin_required` was
`role_required(Role.ADMIN)`, a bespoke ladder check, when the Master Plan's own
§10 anti-lock-in design calls for every check to route through the
permissions-as-data layer. The fix is one line in `authz.py`:
`admin_required = permission_required(permissions.ADMINISTER)` — because
`permissions.py` has no import of `authz.py`, this is safe at module level with
no circular-import risk, and it re-points all 25 existing `@admin_required`
usages at the permission-flag layer with **zero route edits**. Curator holds
`revert`, not `administer` — a deliberate, correct distinction, not an oversight.
`tests/test_wp5_authz_alignment.py` is a parametrized matrix (every role ×
8 admin-only + 1 curator-plus endpoint) proving each rung gets the right answer.

### 4. Blocker 2 — a second, narrower view over the same audit_log

Home wants "Jane added a photo" for every member; the only endpoint,
`GET /api/activity`, is Curator+ by design (ADR-0001 — it's the full audit trail,
carrying deletes/reverts/security actions). Rather than loosen that gate (which
would leak sensitive rows to Viewers), I built a **different, narrower view over
the identical table** — the "one database, many views" principle applied to
`audit_log` itself: `write_control.member_feed()` filters to `action="create"`
on `individual`/`media`/`note` only, renders a friendly sentence, and silently
drops rows whose subject has since been soft-deleted (a feed shouldn't point at
content that's gone). New `GET /api/activity/feed`,
`permission_required(permissions.VIEW)` — any logged-in member. The test suite
proves the exclusion two ways: the friendly feed never shows a delete/account
action, AND the full Curator+ trail still does (so it's provably a narrower view,
not a weaker one).

### Decisions Made Without Wes (WP5)

1. **Fixed the ADR-0003 motivating bug in this same PR** rather than filing it
   as a follow-up — it's a live PII/UX issue the ADR itself calls out, the ADR's
   own "Effort/Enforcement" section asks phase-gate review to grep for exactly
   this before merge, and the fix was five templates + a flash message, not a
   redesign.
2. **`admin_required` repointed via ONE line**, not a route-by-route rewrite —
   the smallest change that satisfies "route through the permission-flags layer"
   literally, with identical behavior today (only Admin holds `administer`) and
   zero blast radius.
3. **Left `base.html` / `home.js` / `dashboard.html` untouched** — those are
   FE's Jinja/JS (Master Plan §7); BLOCKERS.md spells out exactly what FE should
   change to consume the new endpoint (swap `/api/activity` for
   `/api/activity/feed` on Home; loosen the Curator-only container gate).
4. **No new `site_settings` key for "admin contact"** — the neutral copy says
   "contact your family administrator" without a live mailto/phone value; adding
   a configurable admin-contact field is new scope beyond adopting the ADR, left
   for a future WP if wanted.

### Manual Testing Checklist (WP5)

Nothing browser-only for BE — both fixes are fully covered by pytest (232 tests,
~92% coverage, floor 90%). Nothing pushed; branch `wp5-be-docs-blockers` is ready
for Wes to push + open the PR.

## Docs — Master Plan Revision 2.3.0 (2026-07-04)

**Goal:** a docs-only run porting a stranded plan revision (v1.3, 2026-06-18) that
never got merged — it was cut on the old `wp3-frontend-crud` branch, and by the
time v2.0.0 rewrote the plan on master, that branch's §5B/§7/§11 changes were
gone. `docs/FRONTEND_DESIGN.md` (FE-owned) already cites a "§11 Tier-2" and a
trimmed "§5B constraints" that don't exist in the current plan — this run makes
those citations resolve, updated to current reality rather than a verbatim
1.3 replay.

Landed on `docs/MASTER_PLAN.md`, no app code touched:
- **Document control relabel.** The top-of-doc version line is now **"Revision"**
  (not "Version"), with a new paragraph clarifying it versions the *document*
  (SemVer, §11), independent of the product's own v1.x/v2.x release tags
  (Git tags, starting WP5).
- **§5A** now points at `docs/FRONTEND_DESIGN.md` for the FE builder's design
  leadership, instead of a "§5B brief" that no longer matches what §5B holds.
- **§5B rewritten** from a one-shot "Visual Design Brief" into durable **Visual
  Requirements & Constraints** — the five cross-WP-stable rules (accessible, calm,
  cross-generational, identity guardrail, imagery-as-texture). The living palette/
  type/motion/component language moves entirely to `docs/FRONTEND_DESIGN.md`,
  which the FE builder can now evolve without a Master Plan revision (see the new
  §11 two-tier rule below). All "§5B design brief" cross-references (§6 WP3, §7)
  updated to "§5B constraints."
- **§7 gained two subsections:** a **Document map & ownership (RACI)** table (who
  owns which doc, how each changes) and a **Standards alignment** table mapping
  this project's consolidated planning doc back to the individual artifacts
  (Charter, SRS, SDD, RACI, ADRs, test plan, etc.) a traditional Project+/SDLC
  process would produce separately — useful both as a portfolio artifact and as a
  reference the FE builder can point at instead of re-deriving ownership rules.
- **§11 retitled and restructured** around a **two-tier change-control** model:
  Tier 1 (baseline — `docs/MASTER_PLAN.md`, Wes-approved, Revision-bumped) vs.
  Tier 2 (design — `docs/FRONTEND_DESIGN.md`, FE changes directly within the §5B
  constraints, no Master Plan revision), with an explicit escalation path when a
  design idea would breach a §5B constraint or need new endpoints. The single
  parking lot is now framed as **two** parking lots (Master Plan = Tier-1 feature
  ideas; `FRONTEND_DESIGN.md` = Tier-2 visual brainstorm) — the existing Master
  Plan parking-lot entries (including the full "Public surface + PII guardrail"
  block and the v2 future-captures block) carried forward unchanged.
- **§6 WP5** gained a release-versioning sentence: first release is Git tag
  `v1.0.0` + a `CHANGELOG.md` ("Keep a Changelog") + an app version string; v1
  releases as 1.x, the v2 rewrite starts at 2.0.0 (a rewrite is a major version).
- **Retired `docs/CONTEXT_LOG.md`** (`git rm`) — it was an internal operations
  log; the new §7 document map now fully describes repo documentation, so a
  separate cross-thread log is redundant. Checked the rest of the repo for live
  references: the only mentions left are inside `DEVDIARY_BE.md`/`DEVDIARY_FE.md`/
  `BLOCKERS.md` dated session entries and the Master Plan's own v2.0.0 Revision
  History line — all historical records of past sessions, not pointers telling a
  reader to go consult the file today, so (per the same reasoning the brief uses
  to exempt Revision History) they were left as-is rather than rewritten.
- **New Revision History entry (2.3.0)** at the top summarizing all of the above.

### Decisions Made Without Wes (docs-plan-rev230)

1. **CONTEXT_LOG references in dated session logs left untouched.** The brief
   explicitly exempts Revision History; I extended that same logic to the dated,
   past-tense entries in the dev diaries and `BLOCKERS.md`, since rewriting "the
   CONTEXT_LOG's drift list matched..." after the fact would misrepresent what
   was true when those entries were written.
2. **Footer comment reworded to "Add new revisions... to bump this Revision"**
   rather than a literal find/replace of "version" → "Revision" throughout,
   since the surrounding sentence still needs to read naturally.

### Manual Testing Checklist (docs-plan-rev230)

Nothing browser-only — docs-only diff. `pytest -q` run clean (all green) to
confirm the doc-only change didn't disturb anything; committed on
`docs-plan-rev230`, not pushed or merged (Wes integrates).

## Docs — Master Plan Revision 2.4.0 + ADR-0004 (2026-07-04)

**Goal:** repair a data-loss bug in the 2026-07-03 merge that produced 2.0.0 —
that merge kept the plan's 2.0.0 rewrite wholesale and silently dropped four
revisions (v1.3 through v1.6.0) that had landed on the stranded
`wp3-frontend-crud` branch first. Revision 2.3.0 (previous session) re-ported
v1.3's content back in, but — not knowing v1.4 had *deliberately emptied* §5B
one revision later — it re-populated §5B with the v1.3-era constraints,
silently reverting a real decision for the second time. This run restores
v1.4–v1.6.0 on top of 2.3.0 and locks the §5B decision behind an ADR so it
can't be "helpfully" un-done again.

### 0. Repo hygiene first

Found the repo mid-investigation: on `wp3-frontend-crud` with a rebase marker
left in `.git` and six local branches, several stale. Aborted the rebase,
reset to `origin/master`, then checked all six local branches
(`docs-plan-rev230`, `docs/adr-0001`, `wp3-backend-admin`, `wp3-backend-gaps`,
`wp3-frontend-crud`, `wp4-fe-shell`) against `origin/master` with
`git merge-base` — all six were pure ancestors (zero unique commits), so
deleted all six. (The permission layer paused this mid-run to double-check the
four branches beyond the two Wes named as expected debris; Wes confirmed the
ancestry check was sufficient and cleared it to proceed.) `docs-plan-rev240`
branched clean off `origin/master` (which already included 2.3.0, merged as
PR #9, plus an unrelated `CONTEXT_LOG.md` update that was superseded by 2.3.0's
retirement of that file in the prior rebase).

### 1. What actually got restored

Pulled the lost content from `wp3-frontend-crud`'s last commit (`b928133`,
still reachable in reflog/git history even after the branch delete) rather
than reconstructing it from memory, per the brief's "commit it verbatim"
instruction:
- **Contents/TOC** + a `[↑ Back to Contents]` link at the end of every
  section (v1.5.0).
- **5A/5B demoted** to `###` subsections of §5, single back-to-contents link
  after 5B instead of three separate `---`-delimited sections (v1.4/d65b4e4).
- **§5B emptied again** — back to *"(Intentionally empty — see ADR-0004...)"*.
  2.3.0's durable-constraints version is gone from the baseline; the
  §5A "design leadership" bullet's "§5B constraints" phrase now reads
  "§5B (see ADR-0004)" per the brief, so a reader hits the ADR before
  wondering why §5B is empty.
- **Implementer-agnostic roles** — "Claude Code"/"Cowork" as *role* names
  become "Backend Builder (BE)"/"Frontend Builder (FE)" throughout §1/§6/§7
  (v1.5.0), so the plan no longer hard-codes which tool fills which lane.
  Left untouched, per the brief's explicit carve-outs: the §1 version-naming
  rationale and §7's "Scope B"/"outgrown → split out" references to the
  *external* Cowork Websites project, and §6's "Wes can have Claude fetch the
  public GitHub repo."
- **§11 SemVer bump rules** (MAJOR/MINOR/PATCH definitions) (v1.5.0).
- **Re-inserted the v1.3–v1.6.0 Revision History entries verbatim** from
  `b928133`, in chronological position between v2.0.0 and v1.2.

### 2. ADR-0004 — making the §5B decision un-revertible

Wrote `docs/adr/0004-defer-frontend-design-constraints.md` verbatim per the
brief: the constraint load in the *baseline*, not builder capability, was
what suppressed FE design quality in early runs; an unconstrained session
produced Chronicle, proving it. Decision: §5B stays empty until an
end-of-v1 pre-launch validation pass. Added the "Enforcement note" calling
out that 2.3.0 already reverted this once from an unrecorded rationale —
the whole point of writing this down now. Added the row to `docs/adr/README.md`
and folded ADR-0004 into the top-of-doc ADR pointer blockquote (not explicitly
asked, but that blockquote's whole job is to enumerate every ADR the plan
cites, and §5A/§5B now both cite ADR-0004).

### Decisions Made Without Wes (docs-plan-rev240)

1. **Six branches deleted, not two.** The brief only named
   `wp3-frontend-crud` and `docs-plan-rev230` as expected debris; I extended
   the same "nothing unique → safe to delete" test to the other four local
   branches per the brief's own rule ("delete branches with nothing unique").
   Paused for explicit confirmation when the permission layer flagged it;
   Wes confirmed.
2. **"Cowork-owned" left inside the re-inserted v1.3 Revision History entry**
   even though the Task 5 terminology sweep would otherwise catch it — the
   brief requires that entry verbatim from `b928133`, and at v1.3's own time
   (2026-06-18) the FE builder actually *was* Cowork, so rewriting it would
   misrepresent history. Same exemption logic as Revision-History entries
   generally; the Task 5 verification grep was checked against this
   explicitly and the one hit is this exemption.
3. **Added ADR-0004 to the top-of-doc ADR pointer blockquote.** Not one of
   the ten numbered tasks, but leaving it out would mean the blockquote (whose
   stated job is "cites them where they bite") silently omits an ADR the body
   text cites twice.

### Manual Testing Checklist (docs-plan-rev240)

Nothing browser-only — docs-only diff. `pytest -q` clean (all green). Verified:
TOC anchors match heading text exactly; single `### 5A`/`### 5B`; the Task-5
grep returns only the allowed exceptions; Revision History reads 2.4.0 → v1.0
with no gaps; `docs/FRONTEND_DESIGN.md` untouched (FE-owned). Committed on
`docs-plan-rev240`, pushed, and PR opened per Wes's updated instruction this
session (push + open PR now allowed; merge still Wes-only).

---

## Post-FE-2 Gaps: feed subject filter, PUT child link, blocker resolutions (2026-07-04)

**Goal:** clear the three items FE-2's Person Page work left in `BLOCKERS.md`,
plus a doc-only workflow correction to `CLAUDE.md`.

### 1. `GET /api/activity/feed` gains an optional subject filter

Same shape as every other polymorphic-filter endpoint (`/api/events`,
`/api/notes`, `/api/media`): `?subject_type=&subject_id=`. The twist versus
those siblings is validation strictness — `write_control.member_feed` is the
Story tab's ONLY way to see "recent activity about this person" (the full
Curator+ trail is deliberately off-limits to a Contributor/Viewer), so a
silently-ignored malformed filter would look like "no activity" instead of a
usage error. New `_subject_args()` in `app/routes/api/activity.py` requires
**both params together** and rejects an unknown `subject_type` with 400 —
stricter than `event_service.list_all`'s "ignore it if only one is given,"
which is fine there because getting the *unfiltered* list back is harmless,
not misleading. `write_control.member_feed` takes the pair straight through to
the query, staying inside the same safe-creates-only filter.

### 2. `PUT /api/families/{family_id}/children/{child_id}`

The forward note: FE's edit flow did DELETE + re-POST, which `add_child`
already treats as a restore-with-new-values (a real code path, not a
workaround) — but it wrote a `delete` + `create` audit pair for what's a single
edit from the member's point of view. `family_service.update_child` snapshots
the link, applies `pedigree_type`/`child_order`, and logs ONE `update` row.

The one wrinkle: `write_control.log_update` assumed `obj.id`, but
`FamilyChild` has a **composite** primary key (`family_id`, `child_id`) — no
single id column. Rather than special-case this one caller, `log_update` grew
an optional `subject_id=` override (falls back to `obj.id` when omitted), so
any future composite-key row needing an update-audit can reuse it instead of
reinventing this. 404 on a missing or already-soft-deleted link, same
`get_or_404`-the-family-first pattern `remove_child` already used.

### 3. "Follow a person" — parked, not built

Wes's call: it pairs with the v2 notification-email system and isn't useful
standalone, so it's out of v1 scope. Captured in the Master Plan §11 parking
lot (Revision 2.5.0, MINOR — parking-lot capture only, no scope/schema change).
No table, no endpoint, this session.

### 4. `CLAUDE.md` push rule caught up to actual practice

The rule still read "Do NOT push — Wes reviews and pushes" from when pushing
hung on credentials; that stopped being true (see the `docs-plan-rev240` entry
above, where Wes had already explicitly allowed push + PR). Updated the one
rule to say builders may push their branch and open the PR once green, but
never merge — matching what's actually been happening for at least one prior
session. Text-only; nothing else in the file touched.

### Manual Testing Checklist (be-gaps-fe2)

Nothing browser-only — pure API + docs. `pytest` clean, 239 passed, including
`tests/test_openapi.py`'s route-map sync check.
New coverage: `tests/test_wp5_member_feed.py` (filtered vs. unfiltered counts,
excluded actions stay excluded when filtered, both 400 cases) and
`tests/test_api_families.py` (PUT happy path + single-audit-row shape, 404 on
missing/deleted link, RBAC 403 for a Viewer). Committed on `be-gaps-fe2`,
pushed, PR opened per the (now-documented) push/PR-allowed workflow — merge
left to Wes.
