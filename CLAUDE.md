# Project: FamilyHub Lite (v1)

## Mission — Read This First
Build a working, secure, production-ready family portal **quickly** so Wes's aging
parents can start uploading family photo albums and writing blog-style family
history memories **as soon as possible**. Speed to a usable, safe product is the
top priority. This is a real production app for a real family, not a toy.

Second mission: the codebase itself is a **learning aid**. Wes will reverse-engineer
this app to prepare for his WGU senior project — a full rewrite in Java/Spring Boot
(FamilyHub v2). Every design decision must keep that migration painless.

## Who Builds What
- **Claude Code builds the app.** Wes reviews, learns, and gives feedback.
- Wes is NOT writing the code alongside you. Do not leave TODOs for him to fill in.
- Deliver complete, working, reviewable features. Wes often reviews the next morning.

## Educational Requirements (non-negotiable)
- **Teacher-voice code comments.** Write comments as the world's greatest web-dev
  tutor — enthusiastic, clear, explaining **WHY, not just WHAT**. Where applicable,
  reference the WGU B.S. Software Engineering course that teaches the concept
  (e.g., "Data Management – Foundations covers this normalization rule").
- **DEVDIARY.md is a required, living deliverable.** A learning roadmap written like
  textbook chapters: what was built, why it's best practice, every technology choice
  and its WGU curriculum connection, and any mid-build decisions made.
- Comments and DEVDIARY together should let a beginner-to-intermediate Python student
  fully understand the system without outside help.

## Workflow Rules
- **Front-load all clarifying questions before building. Never stop mid-task to ask.**
- If something is ambiguous mid-build: make the simplest reasonable choice, document
  it in DEVDIARY.md under "Decisions Made Without Wes," and keep going.
- Every session ends with the app in a complete, running state. No broken builds.
- Commit logically grouped changes to git with clear messages; push to GitHub.
- **Never pause the build to ask Wes to manually test anything.** Verify your own
  work with automated tests: pytest + Flask's test client covering routes, auth,
  and file uploads (simulate uploads with generated sample files). Anything that
  truly requires human eyes in a browser goes into the **"Manual Testing
  Checklist"** section of DEVDIARY.md; Wes runs the entire checklist once at the
  end of the build.

## About the Developer
- Wes Leiter — WGU B.S. Software Engineering student (expected Fall 2027)
- Currently in Python Intro: beginner-to-intermediate Python skill
- Background in C/C++ (rusty), returning to coding after ~8-year gap
- ADHD-inattentive: concise explanations, concrete examples, no rabbit holes
- Communication: bullet points, **bold key terms**, short paragraphs, ONE next
  action at a time, never more than one open question at a time

## FamilyHub v1 "Lite" — Scope
A simplified version that performs the essential functions of the planned
Full version and migrates to it later with **zero data loss**.

### Core features (priority order)
1. **Photo albums** — authenticated family members upload, arrange, and comment on
   photos. Elderly-friendly upload flow is critical.
2. **Family history blog** — blog-style memory posts (the parents' main activity),
   linkable to wiki entries and the timeline.
3. **Family member wiki** — Wikipedia-style entry per family member with links to
   photos and other entries; editable by authenticated members via a simple editor.
4. **Family history timeline** — editable by all authenticated members.
5. **Authentication (simplified)** — per-member accounts, secure password storage,
   session management. Small trusted user base (~6–10 people).
6. **Admin panel (simplified)** — manage user accounts, basic site text fields
   (about, contact, hero image/tagline), and trigger/verify backups.

### Explicitly deferred to v2 (Full version)
- Video uploads
- Robust permission tiers / extended-family sharing
- Full-featured admin control panel (feature toggles, etc.)

## UX/UI Requirements
- **Elderly-first design**: large readable fonts, big tap/click targets, high
  contrast, obvious buttons, minimal navigation depth, forgiving forms
  (confirmations before destructive actions, no data loss on validation errors).
- Bootstrap-based, clean and simple. Function over flash.

## Security & Privacy (PII) — Critical
- Family PII (dates of birth, mother's maiden name, etc.) must NEVER be publicly
  visible. All family content lives behind authentication.
- Passwords hashed (bcrypt/argon2 via a maintained library), CSRF protection,
  secure session cookies, HTTPS in production (Let's Encrypt).
- Uploaded files validated (type/size) and stored outside the web root with
  DB-tracked metadata.
- Secrets in `.env` only; never committed. `.env.example` stays current.

## Backups — Required Feature, Not an Afterthought
- Nightly automated backup of the SQLite DB + uploaded photos to AWS object
  storage (Lightsail bucket), plus periodic Lightsail instance snapshots.
- Backup/restore procedure documented in DEVDIARY.md and tested at least once.

## Stack
- Python 3, Flask (Blueprint structure), SQLite, SQLAlchemy, Flask-Migrate,
  Bootstrap (Bootstrap-Flask), venv
- Dev machine: Windows 11 desktop, repo at JW\PyCharmProjects\FamilyHub
  (cloned from GitHub via PyCharm; also cloned on a Fedora ThinkPad —
  GitHub is the sync layer, always pull before starting work)
- Production target: **AWS Lightsail** Linux instance (~$12/mo plan), gunicorn +
  nginx, Let's Encrypt SSL
- Dev/staging URL: https://familyhub.pseudokoder.com
- Future production: https://leiters.org (public) + https://family.leiters.org
  (authenticated members area)

## Design for the v2 Migration (verified WGU Java-track stack)
v2 will use the exact stack taught in Wes's WGU courses D286/D287/D288/D387:
**Java + Spring Boot (backend), Angular (frontend), MySQL (database), Docker
(deployment)**. Make these choices now so v2 is a translation, not a rescue
mission:
- **Clean relational schema** — portable SQL, no SQLite-only features; must move
  to **MySQL** without surgery. Use Flask-Migrate from the start.
- **Stable IDs** — integer or UUID primary keys that survive export/import.
- **Layered architecture** — routes (controllers) thin; business logic in a
  service layer; data access via models. This maps 1:1 to Spring Boot's
  Controller → Service → Repository pattern; say so in the comments.
- **API-friendly RESTful route design** — v2's Angular frontend will consume a
  REST API, so keep v1 routes resource-oriented (e.g., /photos, /posts/<id>)
  and keep view rendering cleanly separated from data logic, so endpoints can
  later return JSON for Angular instead of HTML templates.
- **Data export** — provide a management command that dumps all data (DB + file
  manifest) to a documented, portable format (JSON/CSV + files). This is the
  zero-data-loss migration guarantee.
- Document the v1 → v2 mapping in DEVDIARY.md as the schema evolves.

## Current Status
- Day 2: Flask skeleton with Blueprint structure — complete
- Day 3: config + database — complete
  - `Config` class in app/config.py reads SECRET_KEY and DATABASE_URL from env
  - `.env` loaded explicitly; untracked from git; `.env.example` committed
  - SQLAlchemy wired via `db.init_app(app)`
  - First model: `FamilyMember` (app/models/family_member.py)
  - DB: SQLite at instance/familyhub.db (gitignored)
  - Dependency fixed: Flask-Bootstrap → Bootstrap-Flask (Bootstrap 5)
- (Note: "Day N" labels are from an earlier learn-as-you-go plan. Going forward,
  work is organized by FEATURE, not by day.)
- **June 12, 2026 — all six core features are built and tested** (auth,
  photos, blog, wiki, timeline, admin) plus the approved 26-item
  improvement build: EXIF/GPS stripping, login rate limiting, CI with a
  90% coverage floor, site-wide search, wiki revision history + restore,
  album deletion, self-service + emailed password resets, comment
  deletion, health/robots/security.txt, caption editing,
  drag-to-rearrange, content **locking** ("Trial Period" rule:
  creator-deletable until an admin locks it; then admin-only) + audit
  trail, strict CSP security headers, OpenAPI spec (test-enforced),
  Docker, What's New feed, photo↔wiki tagging, PWA, and portfolio
  artifacts (architecture diagram, CONTRIBUTING.md, scripts/deploy/).
- **June 13, 2026 — post-build refinements:** friendly 404/403/500 pages,
  **GEDCOM family-tree export** (Ancestry/FamilySearch — INDI records from
  the wiki), public homepage polish + skip-to-content accessibility, and a
  new **Family Plans** pillar (Ch. 29): shared collaborative checklist +
  image/PDF file sharing (locked-down allow-list — no arbitrary uploads).
- **157 tests, ~92% coverage.** 15 tables, all portable SQL, all via
  migrations. DEVDIARY chapters 0–29 document everything.
- Open question for Wes (DEVDIARY Ch. 18): locking currently guards
  **deletion only** — edits stay collaborative. Confirm or tighten.

## Next Build Target
1. **Deploy to Lightsail** — follow `scripts/deploy/README.md` end to
   end (instance + bucket, nginx, systemd, certbot, backup crontab).
2. **Wes runs the Manual Testing Checklist** (DEVDIARY) once, on the
   deployed site — real phones, real photos, PWA install, real SMTP.
3. Then: create the family's accounts, upload the first albums, go live.
