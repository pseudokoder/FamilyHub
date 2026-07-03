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
