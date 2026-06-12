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

**What was built:** the complete login system. Admin-created accounts only —
there is **no public registration page anywhere**; the family is invite-only.

### The pieces, in reading order

1. [app/extensions.py](app/extensions.py) — every Flask extension is born
   here, empty, and wired to the app in the factory (`init_app` pattern —
   the file's docstring explains why this kills circular imports).
2. [app/models/user.py](app/models/user.py) — the `User` model + the
   `user_loader` that turns a session cookie back into a person.
3. [app/services/user_service.py](app/services/user_service.py) — create
   user, authenticate, reset password. **All** business logic; no HTTP.
4. [app/forms/auth_forms.py](app/forms/auth_forms.py) — login/create/reset
   forms with server-side validation rules.
5. [app/routes/auth.py](app/routes/auth.py) — login/logout routes (thin!).
6. [app/routes/admin.py](app/routes/admin.py) — `@admin_required` decorator
   + the user-management pages at `/admin/users`.
7. [app/templates/base.html](app/templates/base.html) — the master layout
   (template inheritance), navbar, flash messages.

### The security decisions and WHY

| Decision | Why | WGU course |
|----------|-----|------------|
| **bcrypt** password hashing (Flask-Bcrypt) | One-way + salted: a stolen database still reveals zero passwords. Chosen over Werkzeug's default specifically because Spring Security's `BCryptPasswordEncoder` reads the *same hash format* — v1 password hashes migrate to v2 **unchanged**. | D315 Network & Security |
| **CSRF tokens on every POST** (global `CSRFProtect`) | Another site can't trick a logged-in parent's browser into submitting our forms. Secure-by-default beats per-form opt-in. | D315 |
| **Session cookies: HttpOnly + SameSite=Lax**, `Secure` flag env-driven | JS can't steal the cookie (XSS defense); browsers won't send it cross-site (CSRF defense #2); HTTPS-only in production. | D315 |
| **Vague login errors** ("username and password don't match") | Saying *which* was wrong lets attackers harvest valid usernames. | D315 |
| **`?next=` redirect validation** in auth.py | Prevents "open redirect" phishing — we only follow relative, on-site paths. | D315 |
| **Logout is POST, not GET** | GET must never change state; a GET logout is triggerable by an `<img>` tag on any website. Also keeps routes REST-clean for v2's Angular API. | D284 / D288 |
| **403 vs 401 vs 404** | `@admin_required` aborts with 403 ("I know you; no"). Unknown ids give 404. Precision in status codes = a clean REST API later. | D288 |
| **First admin via `flask create-admin`** | No "setup page" ever sits unauthenticated on the internet; only someone with SSH/keyboard access can bootstrap. | D284 |

Fun real-world bug from testing: the smoke test searched the page for
`don't match` and failed — because Jinja **autoescapes** the apostrophe to
`don&#39;t`. Autoescaping is itself a security feature (it's what blocks XSS
from user input), and it's on by default in Flask templates.

### Elderly-first touches

- "Keep me logged in" pre-checked, 30-day cookie — no password gauntlet
  every visit.
- 8+ character passwords, no complexity theater (modern NIST guidance:
  length beats symbols; symbols breed sticky notes).
- Friendly, blame-free error messages; forms re-render with input intact.
- Login page tells you exactly what to do if you forgot your password:
  call Wes.

---

## Chapter 3 — Photo Albums (the #1 feature)

**What was built:** albums, multi-photo upload with thumbnails, a gallery,
per-photo comment threads, and safe deletion. The parents can now upload
photos.

### The data model

```
users 1──* albums 1──* photos 1──* photo_comments
```

Three classic one-to-many relationships
([app/models/photo.py](app/models/photo.py)). The database stores *metadata*;
the image bytes live on disk in `uploads/photos/<album_id>/` — **outside**
`app/static`, outside git. The golden rule: the DB remembers files, it
doesn't contain them.

### How an upload actually works (read photo_service.save_photos)

1. **Extension allow-list** — jpg/jpeg/png/gif/webp, judged by the *last*
   extension so `trick.jpg.exe` is seen as `.exe` and rejected.
2. **Content check** — Pillow must parse the bytes as a real image.
   A virus renamed to `vacation.jpg` fails here. Names lie; bytes don't.
3. **Random UUID filename** on disk — kills name collisions (`IMG_0001.jpg`
   × 50) and path tricks (`..\..\evil`). The original name is kept in the DB
   for humans.
4. **Thumbnail** — Pillow shrinks a copy to ≤400px. The gallery loads ~50 KB
   per photo instead of ~8 MB; on the parents' connection that's the
   difference between "instant" and "broken".
5. One **transaction commit** for the whole batch (D427).

Forgiving by design: 9 good photos + 1 broken one = 9 saved, and a message
naming exactly which one failed. Never all-or-nothing, never a bare "error".

### Photos are served through the login wall

`/photos/<id>/file` and `/photos/<id>/thumb` are normal Flask routes with
`@login_required` — verified in testing: an anonymous request for the image
bytes gets redirected to the login page. If photos lived in `app/static`,
anyone holding a URL could fetch them forever. This is THE reason for the
uploads-outside-web-root rule in CLAUDE.md.

### Authorization vs authentication (worth memorizing)

- *Authentication*: who are you? (`@login_required` — everyone sees photos)
- *Authorization*: may YOU do this? (`photo_service.can_delete` — only the
  uploader or an admin may delete a photo)

The rule lives in ONE service function; routes ask it. In v2 this becomes a
Spring Security method rule.

### Elderly-first UX choices

- Upload box at the TOP of the album page, steps numbered **1.** choose,
  **2.** upload. Big file input, big button.
- Whole album/photo cards are clickable (`stretched-link`), not tiny links.
- Deleting asks "Delete this photo for everyone? This cannot be undone."
  — destructive actions always confirm (CLAUDE.md rule).
- Friendly empty states ("yours can be the very first!") instead of blank
  pages.

### Files to read, in order

1. [app/models/photo.py](app/models/photo.py)
2. [app/services/photo_service.py](app/services/photo_service.py)
3. [app/routes/photos.py](app/routes/photos.py)
4. [app/templates/photos/album.html](app/templates/photos/album.html) —
   the hand-written upload form (see why `enctype="multipart/form-data"`
   matters)

### Addendum: iPhone HEIC support + the sideways-photo bug that never was

Half the family shoots on iPhone, and iPhones save **HEIC** — a format
browsers can't display. Two new things in `photo_service`:

- **Convert at the door, not on every view.** `pillow-heif` teaches Pillow
  to read HEIC; uploads ending in `.heic`/`.heif` are re-saved as JPEG
  (quality 90 ≈ visually lossless) *once, at upload time*. Everything on
  disk is therefore something an `<img>` tag can show, and the gallery
  code never needs to know HEIC existed. Paying a cost once at write time
  to keep every read simple is a classic engineering trade
  (D284 Software Engineering). The DB keeps `IMG_4821.heic` as the
  original filename — honest metadata for the v2 export.

- **EXIF orientation gets baked in.** Phone cameras don't rotate pixels;
  they store the pixels sideways plus a metadata tag saying "display me
  rotated." Re-saving an image (conversion, thumbnails) *strips that tag*,
  which is why naive photo sites are full of sideways grandmas.
  `ImageOps.exif_transpose()` applies the rotation to the pixels before
  every re-save. Verified in testing with a synthetic sideways JPEG: its
  thumbnail came out portrait, as the photographer intended.

---

## Chapter 4 — Family History Blog

**What was built:** memory posts with edit/delete and comment threads —
the parents' main writing activity.

The structure deliberately **rhymes with Chapter 3**: `Post`/`PostComment`
mirror `Photo`/`PhotoComment`; `post_service.can_modify` mirrors
`photo_service.can_delete` (author-or-admin); routes are the same RESTful
shapes. Recognizing repeated shapes is how you read big codebases fast.

**The new concept: rendering user text safely**
([app/services/text_service.py](app/services/text_service.py)). We can't
drop typed text into HTML raw — `<script>` in a comment would run in every
family member's browser (**XSS**, the #1 web vulnerability, D315). The
`family_text` Jinja filter escapes *everything* the user typed, then adds
only tags *we* wrote: blank line → paragraph, single newline → `<br>`.
Verified in testing: a post containing `<script>alert(1)</script>` rendered
as harmless visible text.

**Why no Markdown / rich-text editor?** Elderly-first. The parents type
into a big plain box like an email and it comes out right — no toolbar to
learn, nothing to get "wrong". (Decision logged below.)

**Also note:** `CommentForm` moved to
[app/forms/comment_forms.py](app/forms/comment_forms.py) the moment a
second feature needed it — DRY in action, not in advance.

---

## Chapter 5 — Family Member Wiki

**What was built:** a Wikipedia-style page per family member — name,
lifespan, location, a long-form story — editable by **every** authenticated
member (collaborative by design; only deletion is admin-only).

**Schema evolution, live:** the Day-3 `FamilyMember` stub (name, location)
grew six columns: `bio`, `birth_date`, `death_date`, `created_by`,
`updated_by`, `updated_at`. Read the migration in `migrations/versions/` —
that's a real table gaining columns without losing rows. Note
`server_default=""` on `bio`: a NOT NULL column can only be added to a
table with existing rows if the database knows what to put in them.

**The [[wikilink]] feature** (extended
[text_service.py](app/services/text_service.py)): typing `[[Jo O'Brien]]`
in any memory or bio becomes a link to Jo's wiki page. Unknown names render
as plain text — never a broken link. This delivers CLAUDE.md's "posts
linkable to wiki entries" without teaching anyone HTML. Verified both ways:
bios link to bios, blog posts link to bios.

**A real bug worth remembering:** the first wiki migration **crashed** with
`ValueError: Constraint must have a name`. Why: SQLite can't `ALTER TABLE`
in place, so Alembic rebuilds the table ("batch mode") — and it refuses to
copy constraints it can't name, and SQLAlchemy doesn't name them by default.
The fix is a **naming convention** declared once on the metadata
([app/extensions.py](app/extensions.py)): now every constraint gets a
predictable name like `fk_photos_album_id_albums`, on SQLite today and
MySQL in v2. The Alembic docs call this setup step "strongly recommended";
now you know why firsthand.

**Also new:** a custom WTForms validator
([wiki_forms.py](app/forms/wiki_forms.py)) — any method named
`validate_<field>` runs automatically; ours rejects a death date earlier
than the birth date with a friendly message.

---

## Chapter 6 — Family Timeline

**What was built:** the family's history as one chronological page, grouped
by decade, editable by every member.

**The interesting problem: partial dates.** Family history knows "June 12,
1947" but also just "1890". A DATE column can't say "month unknown" — so
[TimelineEvent](app/models/timeline.py) stores three integers: `year`
(required), `month` and `day` (nullable). The page then shows exactly as
much as we know — `1890`, `March 1962`, `June 12, 1947` — because **honest
data beats fake precision** (storing 1890 as "Jan 1, 1890" would look exact
and lie). Sorting uses portable `COALESCE(month, 0)` so year-only events
lead their year, identically on SQLite and MySQL.

Two small new tools in the templates/forms toolbox: Jinja's
`loop.changed()` prints each decade header exactly once, and a second
custom validator rejects a day given without a month. Permissions follow
the established family rules: everyone edits (like the wiki), creator or
admin deletes (like posts and photos).

---

## Chapter 7 — Admin Site Settings

**What was built:** the "basic site text fields" panel from CLAUDE.md —
tagline, About page text, contact info, and a dashboard banner photo —
at Admin → Site Settings.

**The new modeling idea: a key/value table**
([site_setting.py](app/models/site_setting.py)). Settings come and go;
adding a *column* per setting means a migration every time, adding a *row*
is free. The trade-off (the DB can't type-check values) is fine for display
strings and wrong for real entities — knowing which is which is the lesson.
`settings_service.set_value` is an **upsert**: update the row if it exists,
insert it if not.

**The hero image** reuses every upload lesson from Chapter 3 (allow-list,
Pillow verification, EXIF transpose, re-encode to JPEG) plus one new one:
it's shrunk to ≤1600px because it loads on *every* dashboard visit. One
fixed filename — a new upload replaces the old; it's a banner, not an
archive. Served through the login wall like all family images.

Note the navbar change: admin tools moved into one **Admin dropdown** so
the everyday menu stays short for the parents.

---

## Chapter 8 — Backups (required feature, finally built)

**What was built:** [backup_service.py](app/services/backup_service.py),
the `flask backup` / `flask restore-backup` commands, and the Admin →
Backups page ("trigger/verify backups" from CLAUDE.md) with download links.

**One backup = one zip:** `familyhub.db` (a snapshot) + `uploads/…` (every
photo) + `manifest.json` (what's inside, so the backup can prove its own
completeness years later).

The three lessons baked into the code:

1. **You can't just copy a live SQLite file** — a write mid-copy corrupts
   the copy. `sqlite3`'s `backup()` API takes a consistent snapshot even
   while the app runs.
2. **An unverified backup is a hope, not a backup.** `verify_backup()`
   CRC-checks every zip member, cross-checks the manifest, and runs
   SQLite's own `PRAGMA integrity_check` on the database *inside the zip*.
   The CLI exits non-zero on failure so cron monitoring notices.
3. **A backup on the same disk dies with the disk.** `upload_backup()`
   ships the zip to the Lightsail bucket when `BACKUP_S3_BUCKET` is set
   (boto3 reads AWS keys from `.env`). Unconfigured (like local dev), it
   says so honestly instead of erroring. The Download button on the admin
   page is the manual off-site option meanwhile.

### The restore procedure (TESTED June 11, 2026)

```bash
# on the server: stop the app first
sudo systemctl stop familyhub        # (or however gunicorn runs)
flask restore-backup backups/familyhub-backup-YYYYMMDD-HHMMSS.zip
sudo systemctl start familyhub
```

`restore-backup` refuses unverifiable zips, parks the current DB as
`familyhub.db.pre-restore` (an undo button for the undo button), and is
**CLI-only on purpose** — restoring is a deliberate two-hands operation,
never a web button. The round-trip test: photo uploaded → backup → marker
row added → restore → marker gone, photo intact. It works; it's been run.

### Nightly automation (deployment step, documented now)

On the Lightsail server, one crontab line (`crontab -e`):

```cron
15 3 * * * cd /home/ubuntu/FamilyHub && .venv/bin/flask backup >> backups/backup.log 2>&1
```

3:15 AM nightly: create, verify, upload off-site, log the result. Plus
periodic Lightsail instance snapshots from the AWS console (a whole-machine
backup that catches everything else).

---

## Chapter 9 — Data Export (the v2 guarantee, in code)

**What was built:** `flask export-data` →
[export_service.py](app/services/export_service.py). One command dumps the
entire archive to `export/familyhub-export-<timestamp>/`:

- **data.json** — every table, every row. ISO-8601 dates, integer ids,
  foreign keys by name. JSON, not a SQL dump, because JSON has no dialect:
  a future Java importer, a Python script, or a human in 2040 can read it.
- **files_manifest.json** — every uploaded file with size and **sha256**.
  Checksums are how the v2 importer will *prove* every photo arrived
  unchanged — that's what "zero data loss" means, verifiably.
- **README.txt** — the format documents itself, inside the export.

Two details worth studying: `_dump_table()` uses **table introspection**
(`model.__table__.columns`) so one generic function exports every model —
a table added next month exports automatically. And the export records its
**alembic schema version**, so an importer can refuse data shapes it
doesn't understand. The export includes bcrypt `password_hash` values on
purpose: Spring Security reads bcrypt natively, so the family's logins
survive the rewrite — treat exports as sensitive.

---

## Chapter 10 — The Test Suite (73 tests, all passing)

**What was built:** a complete pytest suite — [tests/](tests/), 73 tests
covering every feature chapter — plus [pytest.ini](pytest.ini) and
[requirements-dev.txt](requirements-dev.txt). Run it from the project root:

```bash
pip install -r requirements-dev.txt   # once
pytest                                 # ~6 seconds, 73 green dots
```

This delivers the CLAUDE.md workflow rule directly: **never pause the build
to ask Wes to manually test** — the suite is how the code proves itself.
WGU connection: D480 Software Design and Quality Assurance is the testing
course; nearly every concept below appears in it.

### How the suite is organized

One test file per feature chapter — the suite's table of contents mirrors
this diary's:

| Test file | Covers | Diary chapter |
|-----------|--------|---------------|
| `test_auth.py` (22 tests) | login/logout, sessions, CSRF, password rules, admin gate | Ch. 2 |
| `test_photos.py` | upload security, HEIC, EXIF, login-walled serving, delete rules | Ch. 3 |
| `test_posts.py` | writing, XSS escaping, permissions, comments, forgiving forms | Ch. 4 |
| `test_wiki.py` | collaborative editing, [[wikilinks]], date validation | Ch. 5 |
| `test_timeline.py` | partial dates, decade page, edit/delete rules | Ch. 6 |
| `test_admin.py` | user creation, password reset, site settings, hero image | Ch. 2/7 |
| `test_backup_export.py` | backup/verify/restore round-trip, export format | Ch. 8/9 |
| `test_text_service.py` | the `family_text` filter, called directly | Ch. 4/5 |

### The two kinds of tests in here (the test pyramid)

Most files are **integration tests**: they push a fake HTTP request through
the *whole* stack — route → form → service → model → template — using
Flask's built-in **test client**, then assert on the resulting HTML and
database rows. One file, `test_text_service.py`, is **unit tests**: it
calls one pure function directly and enumerates its edge cases. Pure-logic
modules earn the cheap, fast treatment; anything involving routes and
permissions earns the full-stack treatment, because that's where the
security rules actually live.

### conftest.py — the foundation everything stands on

[tests/conftest.py](tests/conftest.py) defines the shared **fixtures**
(reusable setup that pytest injects by argument name):

- **`app`** — a fresh Flask app *per test*, built by `create_app(TestConfig)`
  with a throwaway SQLite DB, uploads folder, and backup folder inside
  pytest's `tmp_path` temp directory. Tests can't touch the real database
  or real photos, and can't pollute each other. **Isolation is what makes
  a test trustworthy** — and this is the application-factory pattern's
  payoff (Chapter 2 promised "testability"; here's the receipt).
- **`admin_client` / `member_client`** — two test clients, already logged
  in as an admin and a regular member. Having BOTH in one test is how every
  permission rule gets proven from both sides ("member may not delete
  admin's photo").
- **`make_image()` / `make_fake_image()`** — uploads are simulated with
  **generated** files (Pillow draws real JPEG/PNG/HEIC images in memory;
  the fake is text bytes wearing a `.jpg` name). No binary files checked
  into git, and the EXIF-orientation test can manufacture a "sideways
  iPhone photo" on demand.

Three deliberate TestConfig choices worth understanding:

| Setting | Why |
|---------|-----|
| `WTF_CSRF_ENABLED = False` | Otherwise every POST needs token-scraping boilerplate. The protection itself isn't untested — `test_auth.py` switches it back ON in one dedicated test and proves a tokenless POST is rejected. Disable globally, verify explicitly. |
| `BCRYPT_LOG_ROUNDS = 4` | bcrypt's slowness throttles password-guessing in production — and throttles the test suite. 4 rounds runs the same code path fast. |
| `db.create_all()` instead of migrations | Tests exercise app behavior, not migration history. Migrations get their workout on the real dev/prod databases. |

### The bug hunt: what the suite caught (14 failures → 0)

Writing tests after the features is exactly how you find out which
"obviously fine" code isn't. The suite's first full run failed 14 of 73 —
here's what was actually wrong, most interesting first:

**1. The Flask-Login `g`-caching leak (10 of the 14).** The symptom looked
impossible: anonymous clients were getting member pages, members were
passing admin checks. The cause is a genuinely subtle interaction:

- Flask-Login avoids re-querying the user table on every `current_user`
  access by caching the loaded user in `g._login_user`.
- In Flask 3.x, **`g` is scoped to the application context, not the
  request**. In production each request gets its own short-lived app
  context, so the cache dies with the request — invisible, harmless.
- But our `app` fixture holds ONE app context open across the whole test
  (it has to — the test body queries the DB between requests). So the
  admin logged in by request #1 was still sitting in `g._login_user` when
  the anonymous client sent request #2, and Flask-Login never re-read the
  session cookie.

The fix ([conftest.py](tests/conftest.py)) is a test-only `before_request`
hook that pops `g._login_user` before each request, forcing Flask-Login to
reload the user from the session cookie like production would. Note what
we did NOT do: change application code to accommodate the tests. The app
was correct; the test *environment* differed from production in one
documented way, and the fix patches exactly that difference, where the
difference lives.

The transferable lesson: **when a test fails, first ask whether the app is
wrong or the test environment is wrong.** Both answers are valuable; they
lead to fixes in different places.

**2. Empty upload crashed (real app bug).** Submitting the upload form with
no files chosen made `save_photos` iterate over `None` — a `TypeError`
where Mom should get the friendly "No photos were chosen" nudge. A guard
clause in [photo_service.py](app/services/photo_service.py) fixes it. This
one would have bitten a real parent on day one; the test suite caught it
first. That's the whole sales pitch for testing, in one bug.

**3. Export assumed a migrated database (environment-dependent app bug).**
`export_all` reads the `alembic_version` table to stamp the export with its
schema version — but that table only exists on databases built by
migrations, and test databases come from `db.create_all()`. Now wrapped in
try/except with `schema_version: null` in the export
([export_service.py](app/services/export_service.py)). A unit of code
should degrade gracefully when an *optional* environmental fact is absent.

**4–5. Two tests were wrong, not the app.** `test_text_service` called
`family_text` outside a request context — but the wikilink path calls
`url_for`, which needs one (in production it always has one: Jinja filters
run during requests). And a wiki test asserted "no `/family/` href on the
page" — forgetting the Edit button and breadcrumb *always* link there; the
assertion now uses a regex matching only bare `/family/<id>` view links,
which is what a rendered wikilink would produce. Tests are code too;
they can have bugs, and a failing test is a claim to *investigate*, not
automatically a defect in the app.

### Files to read, in order

1. [pytest.ini](pytest.ini) — three lines; why `pytest` just works
2. [tests/conftest.py](tests/conftest.py) — fixtures + the `g` cache fix
3. [tests/test_photos.py](tests/test_photos.py) — the richest file:
   generated uploads, security checks, permission rules
4. [tests/test_text_service.py](tests/test_text_service.py) — what unit
   tests look like next to integration tests

---

## Chapter 11 — EXIF/GPS Stripping (a privacy hole, found and closed)

**What was built (June 12, 2026):** every uploaded photo is now re-encoded
through Pillow before it touches disk, which discards the entire EXIF
metadata block — including GPS coordinates.

### The hole

Phones embed metadata in every photo: camera model, timestamp, and — the
scary one — **GPS coordinates of where the photo was taken**. Our HEIC
conversion path already re-encoded (and so stripped) iPhone photos, but
plain JPG/PNG/WebP uploads were copied to disk **byte-for-byte, metadata
and all**. Anyone who could download a photo could read the family's home
address out of it. That violates the CLAUDE.md PII rule even though the
file sits behind the login wall — defense in depth (D315) says don't store
the secret at all if you don't need it.

### The fix (read photo_service.save_photos)

- **Every raster image is re-encoded**: `Image.open()` → `exif_transpose()`
  (bakes the rotation into the pixels FIRST) → `save()` with no `exif=`
  argument → fresh file, zero metadata. JPEG stays JPEG, PNG stays PNG.
- **GIF is the one passthrough** — re-encoding would flatten animations to
  one frame, and the GIF format predates camera metadata entirely.
- **Trade-off, documented honestly:** re-encoding a JPEG at quality=90 is a
  second lossy pass. For family photos it's visually indistinguishable, and
  privacy wins over byte-perfect originals. (The same number the HEIC path
  already used — one rule to learn.)
- Tests prove it: upload a file with orientation + GPS EXIF, assert the
  saved file has **zero** EXIF entries but the correct (rotated) shape.

---

## Chapter 12 — Login Rate Limiting (brakes for password robots)

**What was built (June 12, 2026):** the login form now allows **10 attempts
per minute per IP address**; attempt 11 gets a polite "please wait one
minute" page (HTTP 429) instead of another chance at the password.

### Why bcrypt alone wasn't enough

bcrypt makes each password guess *slow* (~0.1s of deliberate math). But an
attacker with a botnet doesn't mind slow — they mind **blocked**. Rate
limiting is the second layer (defense in depth, D315): bcrypt taxes every
guess, the limiter caps the number of guesses. A fumbling family member
never notices (humans manage 3–4 tries a minute); a robot hits a wall.

### The pieces

- **Flask-Limiter** in extensions.py — created with no default limits, so
  only routes that opt in are limited. One decorator on the login route:
  `@limiter.limit("10 per minute")`.
- **Counts live in process memory** (`memory://`) — right-sized for one
  gunicorn worker at family scale. The v2/scale-up note: swap in Redis as
  the storage and the route decorator doesn't change.
- **ProxyFix, off by default** — behind nginx every request "comes from"
  127.0.0.1, so the limiter would lump the whole family together. With
  `TRUST_PROXY=True` (production only!) Flask reads the real visitor IP
  from `X-Forwarded-For`. Trusting that header *without* a proxy in front
  would let attackers spoof their IP — hence the env switch.
- **A friendly 429 page** (templates/errors/429.html) — even the brakes
  are elderly-first.
- **Tested like CSRF**: off in TestConfig, one dedicated test turns it on
  and proves try #11 from the same IP gets 429.

---

## Chapter 13 — Continuous Integration (the robot reviewer)

**What was built (June 12, 2026):** a GitHub Actions workflow
(`.github/workflows/ci.yml`) that runs the entire pytest suite on a clean
Ubuntu machine on **every push** — plus a live status badge in README.md.

### Why CI is non-negotiable on a real project

- The runner starts with **nothing installed**, so a missing pin in
  requirements.txt fails the build instead of failing on the Lightsail
  server at deploy time.
- It runs on **Linux** — the same OS as production — so Windows-only
  assumptions get caught while they're cheap to fix.
- The repo now *proves* its own health: the badge is green only while
  every test passes on a neutral machine. (D480 calls this continuous
  integration; v2's Java track runs `mvn test` on the identical service.)

The workflow file itself is heavily commented — read it top to bottom,
it's only four steps: checkout → install Python → install pins → pytest.

---

## Chapter 14 — Site-Wide Search (one box, the whole archive)

**What was built (June 12, 2026):** a search box in the navbar that looks
through **everything at once** — memories (title + body), wiki pages
(name + location + bio), albums, photo captions/filenames, and timeline
events — on one results page, grouped by type, empty sections hidden.

### How it works (read in this order)

1. `app/services/search_service.py` — five `ilike()` queries (one per
   content type), each capped at 25 rows. `ilike` = case-insensitive LIKE,
   portable to MySQL unchanged.
2. `app/routes/search.py` — `GET /search?q=...`. **GET, not POST**: search
   reads data, changes nothing, and a GET result page is bookmarkable and
   shareable. (RESTful discipline → the v2 Angular app calls the same URL.)
3. `templates/search/results.html` — grouped results; sections with no
   matches don't render at all.

### The teaching moment: escaping LIKE wildcards

SQL LIKE treats `%` and `_` as wildcards. The ORM already prevents SQL
*injection* (parameterized queries — the query TEXT can't be altered), but
wildcards are a *semantic* leak: searching `%%` would match every row in
the house. `_escape_like()` backslash-escapes user text so what you type
is what gets matched, literally. Two different bugs, two different
defenses — worth memorizing the distinction (D315 + D426).

### Why LIKE and not a "real" search engine

Family scale: hundreds of rows. A LIKE scan is instant, needs zero new
infrastructure, and the upgrade path (MySQL FULLTEXT in v2) swaps in
*inside the service* without touching route or template. Simplest thing
that works, with the growth path documented.

---

## Chapter 15 — Wiki Page History (the undo button)

**What was built (June 12, 2026):** every save of a wiki page now records
a complete snapshot (`wiki_revisions` table). A **Page History** button
lists every version; any version can be read and restored with one click.

### Why this was the riskiest gap in v1

The wiki is editable by *everyone* — that's the feature. But until now, one
accidental paste-over + Save destroyed the only copy of a bio, forever.
DEVDIARY decision #15 deferred history to v2; Wes promoted it after seeing
it called "the one feature gap that could cause real data loss." He was
right to.

### Design decisions worth studying

- **Snapshots, not diffs (D426).** Each revision stores the full editable
  state. Diffs are smaller; snapshots make restore a simple copy. At
  family scale, storage is free and simple wins.
- **Restore never rewinds — it appends.** Bringing back version 2 creates
  version 5 (identical to 2). History only grows, so even a mistaken
  restore is restorable. No operation in the wiki can lose words anymore.
- **The migration backfills version 1** for pages that existed before the
  feature (hand-written `INSERT ... SELECT` in the migration — a *data*
  migration riding along with the *schema* migration).
- **Relationship check on lookup**: `/family/3/history/99` 404s unless
  revision 99 actually belongs to page 3 — the classic "insecure direct
  object reference" trap (D315), closed in the service.
- New table is in `EXPORTED_MODELS`, so `flask export-data` carries page
  history into v2 too.

---

## Chapter 16 — Quality-of-Life Round 1 (closing the little gaps)

**What was built (June 12, 2026):** three small features that each close a
real annoyance, plus one discovery.

1. **Album deletion** (resolves decision #10's deferral): a "Delete this
   entire album" button at the *bottom* of the album page — far from the
   everyday buttons, with a confirm that spells out the blast radius.
   The service deletes every photo's files first, then one row delete
   cascades away the photo + comment rows. Creator-or-admin for now;
   the locking feature (next chapters) will tighten this.
2. **Self-service password change** — `auth/change-password`, linked from
   a little account menu on the greeting in the navbar. Asks for the
   *current* password first: the standard defense against someone sitting
   down at an unlocked, logged-in laptop and locking the real owner out
   (D315). Wes stops being the family's only password department.
3. **Comment deletion** — your own comment gets a small 🗑 next to it
   (admins see it on every comment). Same one-rule-one-place pattern:
   `can_delete_comment` lives in the service.
4. **Discovery:** "show who last edited a wiki page" was *already built*
   (member.html shows it; test_wiki proves it) — the improvement list had
   flagged it as missing. Lesson: always audit before you build.

---

## Chapter 17 — Quality-of-Life Round 2 (plumbing + polish)

**What was built (June 12, 2026):** five small features.

1. **`GET /health`** — the standard liveness URL: `{"status":"ok",
   "database":"ok"}`, 503 if the DB can't answer `SELECT 1`. nginx and
   uptime monitors hang their health checks on this. Public on purpose
   (monitors don't have logins; it leaks nothing).
2. **`robots.txt`** (`Disallow: /` — a family archive has no SEO goals)
   and **`/.well-known/security.txt`** (RFC 9116: how to report a security
   problem, with the RFC-required Expires field).
3. **Photo caption editing** — `photos/<id>/edit`, uploader-or-admin, the
   photo shown above the box. Typos aren't forever anymore (and captions
   feed search).
4. **Drag-to-rearrange photos** — the `Photo.position` column finally gets
   its UI (decision #8 said "the column exists NOW, the UI costs nothing
   later" — today is later). SortableJS is **vendored locally** (same
   no-CDN rule as Bootstrap), the page works fine without JavaScript
   (progressive enhancement), a tap still opens the photo on touch
   (drag needs a 150 ms hold), and the new order saves itself via the
   app's first JSON endpoint — a deliberate preview of every v2 route.
   The CSRF token travels in an `X-CSRFToken` header since fetch() has no
   form to carry the hidden field.
5. **Lazy-loading thumbnails** — `loading="lazy"` on gallery images: the
   browser only downloads thumbnails as they scroll into view.

---

## Chapter 18 — Content Locking & the Audit Trail (Wes's Trial Period rule)

**What was built (June 12, 2026):** Wes's permission redesign, verbatim:

> "Wiki entries, photo uploads, album creations, history timeline entries
> can be deleted by normal users after upload, but admin needs to have the
> control to lock all those after they've been reviewed and approved, and
> after they've been locked, then no one but an admin can delete them.
> The time between upload and admin approval could be thought of as a
> **Trial Period**."

### The policy, as a table

| Content | During trial (unlocked) | After admin locks |
|---|---|---|
| Photos, albums, wiki pages, timeline events | creator may delete | **admin only** |
| Posts & comments | author may always delete | *(never lockable — your words stay yours)* |

One consequence worth noticing: **wiki deletion actually got looser** —
it was admin-only before; now a page's creator can take back their own
page while it's unlocked. And **the strictest lock wins**: an unlocked
album containing one locked photo can't be deleted by its creator,
because the album would take the protected photo with it.

### How it's built (read in this order)

1. **`app/models/mixins.py`** — `LockableMixin` adds `locked_at` +
   `locked_by` to all four content types *once* (composition over
   copy-paste; the JPA cousin is `@MappedSuperclass`). `is_locked` is just
   "is there a timestamp?" — no boolean to drift out of sync.
2. **The `can_delete` rules** in each service gained one line:
   `... and not item.is_locked`. Rules stay in services; templates and
   routes only ever *ask*.
3. **`lock_service.py`** — one lock()/unlock() pair serves all four types
   (the mixin gave them the same shape). Admin-only, enforced in routes.
4. **Lock badges** show for *everyone* ("🔒 In the family archive") so a
   member understands why their delete button disappeared. Elderly-first
   means permissions explain themselves.
5. **`audit_log` table + `audit_service.log_event()`** — every create,
   edit, upload, delete, lock, unlock, password set, settings change, and
   backup run writes one row *in the same transaction as the action*
   (log_event adds but never commits — the calling service's commit
   carries both, so the log can never disagree with the data).
   Admin → Activity Log shows the latest 100.
6. **A decision to flag for Wes:** locking blocks *deletion* only —
   editing stays open (the wiki is still collaborative; a locked photo's
   caption can still be fixed). If "locked" should also freeze edits,
   that's a one-line change per `can_modify` rule — say the word.

---

## Chapter 19 — HTTP Security Headers & the Strict CSP

**What was built (June 12, 2026):** every response now carries a full set
of security headers, hand-rolled in ~30 lines of `after_request` (no
extension needed — and writing them by hand means knowing what each does).

### The headers and the attack each one stops

| Header | Stops |
|---|---|
| `Content-Security-Policy: script-src 'self' ...` | XSS payloads from *running*, even if one sneaks past escaping |
| `frame-ancestors 'none'` + `X-Frame-Options: DENY` | clickjacking (our pages inside an attacker's iframe) |
| `X-Content-Type-Options: nosniff` | "photo" uploads being re-interpreted as HTML+script |
| `Referrer-Policy: strict-origin-when-cross-origin` | leaking `/family/<id>` URLs to other sites via the Referer header |
| `form-action 'self'` | forms being re-targeted to submit credentials elsewhere |
| `Strict-Transport-Security` (production only) | HTTPS-stripping; not sent in dev where it would lock out http://127.0.0.1 |

### The real work: earning a CSP with NO 'unsafe-inline'

A CSP is only as strong as its weakest `unsafe-*` escape hatch. Ours has
none — which required evicting every scrap of inline code from templates:

- Seven `onsubmit="return confirm(...)"` handlers became plain
  `data-confirm="message"` **attributes** (data, not code), with ONE
  delegated listener in `static/js/familyhub.js` doing the asking. Bonus:
  future forms get confirm dialogs by adding an attribute, zero new JS.
- Six `style="..."` attributes moved into named classes in style.css.
- This is why SortableJS was vendored locally rather than CDN-loaded —
  `script-src 'self'` means OUR origin only, and the whole site already
  worked CDN-free (Bootstrap ships from the installed package).

A test walks the formerly-inline pages and fails if `onsubmit=` ever
returns; another asserts the CSP itself never grows an 'unsafe-inline'.

---

## Chapter 20 — Forgot-Password Email Flow (Wes stops being the helpdesk)

**What was built (June 12, 2026):** "Forgot your password?" on the login
page → type your username → an emailed link → choose a new password. The
most common support call an elderly-user site gets, now self-service.

### The clever part: stateless single-use tokens (no token table)

The emailed link carries a token signed by **itsdangerous** (the same
library that signs Flask's session cookies). Inside: the user's id and
the **last 12 characters of their current password hash**. That fragment
is the trick — using the link changes the password, which changes the
hash, which invalidates the token. Single-use semantics, zero database
state. Expired (1 hour), forged, and reused tokens all die in one
`verify_reset_token()` function, each path tested.

### Privacy + safety details worth reading

- The response to "email me a link" is **identical** whether the username
  exists, has no email, or doesn't exist — no username harvesting (same
  principle as the vague login error, Ch. 2).
- The route is rate-limited at **5/minute** (tighter than login) because
  each POST can trigger an outbound email.
- **Graceful degradation:** no `MAIL_SERVER` in .env → the login page
  shows "call Wes" instead of a dead link, and the route declines
  politely. A feature that half-exists and crashes is worse than one
  that's absent.
- `users.email` is **nullable** — accounts without an email simply have
  no self-service reset (admins set emails at Admin → Users → Edit).
- Reset emails are plain text on purpose: spam filters trust it more and
  every mail app renders it the same.

---

## Manual Testing Checklist

Everything below needs **human eyes in a real browser** — visual layout,
real devices, real photos, things automated tests can't judge. Per the
CLAUDE.md workflow, Wes runs this whole list **once, at the end of the
build** (and again on the Lightsail server after deployment). Everything
functional is already covered by the 73 automated tests; this list is
about how it *looks and feels*.

### Elderly-first look & feel (the point of the whole design)
- [ ] On a desktop: fonts comfortably large, buttons obviously buttons,
      contrast strong enough to read in daylight
- [ ] On a phone AND a tablet: navbar collapses properly, tap targets big
      enough for unsteady hands, nothing requires pinch-zoom
- [ ] Flash messages (green success / red error banners) are noticeable
      but not alarming, and readable at a glance

### Auth & navigation
- [ ] Log in, close the browser entirely, reopen — still logged in
      ("Keep me logged in" 30-day cookie)
- [ ] Logged OUT, visit `/` — generic welcome page, zero family content,
      a single obvious Login button
- [ ] Log in as a non-admin — no Admin dropdown anywhere in the navbar

### Photos (test with REAL files, not generated ones)
- [ ] Upload a real iPhone HEIC photo — displays correctly in gallery
      and full view
- [ ] Upload a real portrait-mode phone photo — appears upright, not
      sideways, in both thumbnail and full size
- [ ] Upload 5+ photos at once — progress is tolerable, success message
      counts correctly
- [ ] Album gallery thumbnails load fast and look uniform
- [ ] Upload a real phone photo, download it back from the site, and check
      its properties — no GPS/location metadata survives (Ch. 11)
- [ ] Drag a photo to a new spot on desktop AND with a finger on a phone —
      "✓ New order saved" appears, the order survives a refresh, and a
      simple TAP still opens the photo (Ch. 17)

### Content rendering
- [ ] Write a blog post with several paragraphs (typed like an email) —
      paragraphs render with visible spacing
- [ ] A `[[Name]]` wikilink in a post/bio is visibly a link, and clicking
      it lands on the right wiki page
- [ ] Timeline page: decade headers appear once per decade, partial dates
      read naturally ("1890", "March 1962", "June 12, 1947")
- [ ] Upload a hero banner at Admin → Site Settings — it appears on the
      dashboard, reasonably cropped, on desktop and phone

### Destructive-action confirmations (click Cancel each time!)
- [ ] Delete photo, delete post, delete wiki page, delete timeline event —
      each pops a browser confirm dialog BEFORE anything happens
- [ ] Validation errors keep typed text: submit a post with no title —
      the body text survives the error page

### Admin & backups
- [ ] Create a new user at Admin → Users, then log in as them in a
      private/incognito window
- [ ] Admin → Backups: trigger a backup, see it verified, download the
      zip, open it locally — DB + photos + manifest are inside
- [ ] As admin: lock a photo — the green "In the family archive" badge
      appears; log in as a member who uploaded it and confirm their
      delete button is gone (Ch. 18)
- [ ] Admin → Activity Log: today's actions are listed, newest first,
      with the right names attached (Ch. 18)

### After deployment (server-only, can't be tested locally)
- [ ] With real MAIL_* settings in the server's .env: request a reset
      link, receive the real email, and complete the reset (Ch. 20 —
      automated tests cover the logic, only real SMTP delivery needs eyes)
- [ ] HTTPS padlock shows on https://familyhub.pseudokoder.com
- [ ] Nightly cron backup ran (check `backups/backup.log` next morning)
      and the zip landed in the Lightsail bucket
- [ ] Lightsail instance snapshot scheduled in the AWS console

---

## Decisions Made Without Wes

Running log of judgment calls made mid-build, per the workflow rules
("make the simplest reasonable choice, document it, keep going").

1. **(Ch. 0)** Added a `.flaskenv` file. Flask's CLI auto-loads it when
   python-dotenv is installed; it holds only the non-secret `FLASK_APP=run.py`
   so `flask run`/`flask db` work without manual environment setup. Secrets
   still live only in `.env`.
2. **(Ch. 1)** `create-admin` shipped with the auth commit, not the CLI
   commit as planned — the command needs the `User` model to exist, and
   commits should be self-contained.
3. **(Ch. 2)** `User` is a separate table from `FamilyMember`. Login accounts
   and family-tree people are different concepts: great-grandpa gets a wiki
   page, never a password. They can be linked with a foreign key later
   without a schema rewrite.
4. **(Ch. 2)** "Keep me logged in" defaults to **checked** with a 30-day
   cookie. ~8 trusted users on personal devices; convenience for elderly
   users outweighs shared-computer risk. Flip the default if anyone uses a
   library computer.
5. **(Ch. 2)** Password rule is "8+ characters", nothing else. Invite-only
   site, modern NIST guidance, elderly-friendly.
6. **(Ch. 3)** ~~HEIC (iPhone photos) not accepted yet~~ — **RESOLVED
   June 11, 2026**: Wes confirmed half the family shoots on iPhone, so
   `pillow-heif` was added and HEIC/HEIF uploads are now accepted and
   **converted to JPEG once, at upload time** (see the Chapter 3 addendum
   below for why convert-at-the-door beats convert-on-view).
7. **(Ch. 3)** No `cover_photo_id` column — the album cover is simply its
   first photo (a computed property). Simplest schema that works; a real
   column can be added later by migration without data loss.
8. **(Ch. 3)** `Photo.position` column exists NOW, but drag-to-rearrange UI
   is deferred. Adding the column later would mean migrating + backfilling
   every album; adding the UI later costs nothing.
9. **(Ch. 3)** Comments attach to *photos*, not albums — CLAUDE.md says
   "comment on photos", and a photo-level thread is where "who is that in
   the back row?" conversations actually happen.
10. **(Ch. 3)** Album deletion has no UI yet — only photo deletion
    (uploader or admin). Deleting a whole album is rare, high-stakes, and a
    natural fit for the admin panel feature later.
11. **(Ch. 4)** Blog posts get **comments** even though CLAUDE.md only
    listed comments for photos — responding to memories ("I was there!")
    is the engagement loop that keeps parents writing, and it reuses the
    photo-comment pattern nearly verbatim.
12. **(Ch. 4)** Plain text with paragraphs, **no Markdown or rich-text
    editor** — elderly-first: type like an email, it comes out right.
13. **(Ch. 4)** No pagination on lists (posts, albums) — at family scale
    (tens of posts, not thousands) it's complexity with no payoff. Easy to
    add later if the archive grows huge.
14. **(Ch. 5)** The wiki page IS the `FamilyMember` row (extended), not a
    separate `WikiEntry` table — one real-world concept, one table.
15. **(Ch. 5)** No edit/revision history on wiki pages (real Wikipedia has
    one; ours has "last edited by"). A full history table is a natural v2
    feature; v1 trusts ~8 family members.
16. **(Ch. 5)** Photo embedding inside wiki pages/posts is deferred —
    [[links]] connect entries to each other; connecting them to photo
    albums needs a tagging system (v2 candidate). Logged so it isn't
    forgotten.
17. **(Ch. 6)** Timeline dates = three integer columns (year/month/day,
    month+day nullable) instead of a DATE — family history has partial
    dates, and honest "unknown" beats invented precision.
18. **(Ch. 6)** Timeline delete is creator-or-admin (like posts/photos),
    even though editing is open to all — consistent, learnable rules.
19. **(Ch. 7)** The About page and hero image are **behind the login**, not
    public — admin-written text and a family banner photo are family
    content under the CLAUDE.md PII rule. The public home page stays
    generic.
20. **(Ch. 7)** Starter settings were seeded (tagline, about, contact
    placeholder text) so the feature is visibly working on first login —
    edit them at Admin → Site Settings.
21. **(Ch. 10)** The Flask-Login `g`-cache leak was fixed **in the test
    fixture, not the app** — a `before_request` hook in conftest.py clears
    the cached user before each test request. The app behaves correctly in
    production (where each request has its own app context); changing app
    code to suit a test-only condition would have been backwards.
22. **(Ch. 10)** `export_all` now treats a missing `alembic_version` table
    as `schema_version: null` instead of crashing — the table is a fact
    about *how the DB was built* (migrations vs `create_all`), not about
    the data being exported.
23. **(Ch. 10)** CSRF is disabled globally in TestConfig but re-enabled
    and verified in one dedicated test — pragmatism for 73 tests,
    explicit proof the protection fires.
24. **(Ch. 11)** Metadata stripping re-encodes (slightly lossy, quality=90)
    instead of surgically removing GPS tags with an extra library (piexif).
    Zero new dependencies, strips ALL metadata not just GPS, and matches
    what the HEIC path already did. Animated GIFs pass through untouched —
    no EXIF block in that format to worry about.
25. **(Ch. 12)** Rate limit is 10/minute on login only — no site-wide
    default limits. Family members click fast when browsing albums;
    limiting reads would punish the people the site is for. Login is the
    one route where volume = attack.
26. **(Ch. 18)** Locking blocks DELETION only, not editing — Wes's spec
    said "no one but an admin can delete them" and said nothing about
    edits, so the collaborative wiki stays collaborative even when locked.
    Flagged in Chapter 18 for Wes to confirm or tighten.
27. **(Ch. 18)** The audit log's target_id is deliberately NOT a foreign
    key: an audit row must outlive the row it describes (an enforced FK
    would either block deletes or cascade the log away — both wrong).
28. **(Ch. 18)** Lock/unlock are idempotent (locking twice = no-op, not
    an error) — admins double-click, and idempotent endpoints are also
    what v2's REST API will want anyway.

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
| `flask export-data` (JSON + sha256 manifest) | the v2 import tool's input format |
| bcrypt password hashes | read natively by Spring Security — logins carry over |

**The final v1 schema** (9 tables, all created by migrations, all portable):

| Table | What it holds | Belongs to feature |
|-------|---------------|--------------------|
| `users` | login accounts (bcrypt hashes, admin flag) | Auth (Ch. 2) |
| `family_member` | wiki pages: bio, birth/death dates, edit tracking | Wiki (Ch. 5) |
| `albums` → `photos` → `photo_comments` | albums, photo metadata (files on disk), comment threads | Photos (Ch. 3) |
| `posts` → `post_comments` | written memories + comment threads | Blog (Ch. 4) |
| `timeline_events` | year/month/day partial-date events | Timeline (Ch. 6) |
| `site_settings` | key/value admin text (tagline, about, contact) | Admin (Ch. 7) |

---

## What's NOT in v1 (on purpose)

Deferred per CLAUDE.md, logged so nothing is forgotten: video uploads,
permission tiers beyond admin/member, wiki revision history, photo tagging
into wiki pages, drag-to-rearrange photos (the `position` column is
waiting), album deletion UI, pagination. The remaining **deployment** work
(not features): Lightsail instance, gunicorn + nginx, Let's Encrypt, the
nightly backup crontab line from Chapter 8, and `BACKUP_S3_BUCKET` in the
server's `.env`.
