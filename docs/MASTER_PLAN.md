# FamilyHub — Master Plan

> The single source of truth for the project's architecture, schema, scope, and
> roadmap. Build one piece at a time; review each piece before starting the next.

**Version 1.6.0** · Last updated 2026-06-29 · Status: WP2 complete; WP3 next.
*Git is the source of truth — repo HEAD is always current. Per §11 change control, when
a change is approved, bump this version and add a line to the Revision History (bottom).*
---

## Contents

- [1. The Corrected Vision](#1-the-corrected-vision)
- [2. Core Principle: One Database, Many Views](#2-core-principle-one-database-many-views)
- [3. The Schema (the centerpiece)](#3-the-schema-the-centerpiece)
- [4. Feature → View Mapping](#4-feature--view-mapping)
- [5. FamilySearch-Modeled Functionality (v1 scope)](#5-familysearch-modeled-functionality-v1-scope)
  - [5A. Build Quality Bar — Depth, Not Stubs](#5a-build-quality-bar--depth-not-stubs)
  - [5B. Visual Requirements & Constraints (frontend)](#5b-visual-requirements--constraints-frontend)
- [6. Roadmap (CompTIA Project+ aligned)](#6-roadmap-comptia-project-aligned)
- [7. Orchestration & Division of Labor](#7-orchestration--division-of-labor)
- [8. Decisions Made On Your Behalf (correct any of these)](#8-decisions-made-on-your-behalf-correct-any-of-these)
- [9. Security & Privacy Maturity Ladder](#9-security--privacy-maturity-ladder)
- [10. Access Control — Roles & Admin Panel (progressive)](#10-access-control--roles--admin-panel-progressive)
- [11. Change Management & Parking Lots (Project+ change control)](#11-change-management--parking-lots-project-change-control)
- [12. Search (a genealogy site is useless without it)](#12-search-a-genealogy-site-is-useless-without-it)
- [Revision History](#revision-history)

---

## 1. The Corrected Vision

FamilyHub is, at its core, a **GEDCOM 7–compliant genealogy database** with a
**FamilySearch-style website** layered on top that lets logged-in family members
perform full **CRUD** on every genealogy element.

Everything else — the wiki, the timeline, the photo album, the memory blog — is
**not a separate feature**. Each is just a different **view** of the one shared
database. Build the genealogy core once; every "feature" becomes a query against it.

**This replaces** the earlier "photo-album-plus-blog app" conception. The first build
(66 commits, polished GitHub presentation) had excellent engineering scaffolding but a
hollow, unusable feature/UX layer on the wrong data core — so v1 is a **rebuild**, not
a patch, per this map:
- **KEEP (deliberately preserved):** repo structure, the GitHub presentation/README
  style, CI + test infrastructure, Docker, the layered architecture pattern, security
  hardening, the backup system, DEVDIARY/CONTRIBUTING, management commands.
- **REBUILD:** the data model (→ the GEDCOM-7 core below) and the **entire feature +
  UX layer** (→ full-depth, Frontend Builder (FE)-designed pages per §5A/§5B).

**Version naming** (avoids collision with the Cowork Websites project's scope words):
- **v1 = "Full"** (Flask/Python) — built now. **v2 = "Enterprise"** (Java/Spring
  Boot/Angular/MySQL/Docker) — the senior project.
- **v1 / v2 are the durable anchors;** "Full"/"Enterprise" are edition labels. Never
  use "Lite" here — in the Cowork project "Lite" = static HTML and "Full" = Flask, so
  our v1 (Flask) aligns with their "Full."

[↑ Back to Contents](#contents)

---

## 2. Core Principle: One Database, Many Views

```
                    ┌─────────────────────────────────┐
                    │   GEDCOM 7 Genealogy Database    │
                    │  (individuals, families, events, │
                    │   places, sources, media, notes) │
                    └─────────────────────────────────┘
                                   ▲
              ┌──────────┬─────────┼─────────┬──────────┐
              │          │         │         │          │
          Family      Person    Time-      Photo      Memory
          Tree /       Page      line      Album      Blog
          Fan Chart   (Wiki)
              │          │         │         │          │
         INDI+FAM    one INDI   events    OBJE media   NOTE/SNOTE
         links       + facts    by DATE   (images)     narratives
```

Every view reads from the same tables. No feature gets its own private data store.

[↑ Back to Contents](#contents)

---

## 3. The Schema (the centerpiece)

Logical schema written for **SQLite first** (v1, the "Full" edition). SQLAlchemy models are the
source of truth; Alembic/Flask-Migrate handles the dialect translation to **MySQL**
in v2. Notes on engine differences are inline.

### Design rules baked into this schema
- **Durable identity = internal integer primary key.** Per the GEDCOM 7 spec,
  cross-reference IDs (`@I1@`) are transient between files and must not be shown to
  users. The `gedcom_xref` columns are **nullable and reserved for future
  import/export work**; they are never used as durable keys.
- **Polymorphic attachment** (`subject_type` + `subject_id`) lets events, citations,
  media, and notes attach to *any* record. This is the mechanism that makes
  "everything is a view" work. (Trade-off: polymorphic FKs can't be DB-enforced;
  documented in §8. v2/Hibernate can formalize via `@Any` or per-type junctions.)
- **Dates** keep BOTH the original GEDCOM string (`date_original`, e.g. `"ABT 1850"`)
  and a sortable normalized value (`date_sort`) so fuzzy dates display faithfully but
  still sort on a timeline.
- **Standard SQL only** — no engine-specific tricks — so the schema is portable.

### 3.1 Genealogy core

```sql
-- INDIVIDUALS  (GEDCOM INDI record)
CREATE TABLE individuals (
    id            INTEGER PRIMARY KEY,         -- MySQL: BIGINT AUTO_INCREMENT
    gedcom_xref   VARCHAR(20)  UNIQUE,         -- @I1@
    sex           VARCHAR(1),                  -- M, F, X, U (GEDCOM SEX enum)
    living        BOOLEAN DEFAULT 1,           -- drives PII hiding (see §5)
    restriction   VARCHAR(20),                 -- GEDCOM RESN: confidential, locked, privacy
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NAMES  (GEDCOM INDI.NAME — a person may have several)
CREATE TABLE names (
    id             INTEGER PRIMARY KEY,
    individual_id  INTEGER NOT NULL REFERENCES individuals(id) ON DELETE CASCADE,
    name_type      VARCHAR(20) DEFAULT 'birth', -- birth, married, aka, immigrant, maiden
    name_prefix    VARCHAR(50),                 -- Dr., Capt.
    given          VARCHAR(150),
    nickname       VARCHAR(100),
    surname_prefix VARCHAR(50),                 -- van, de, von
    surname        VARCHAR(150),
    name_suffix    VARCHAR(50),                 -- Jr., III
    is_primary     BOOLEAN DEFAULT 0,
    sort_order     INTEGER DEFAULT 0
);

-- FAMILIES  (GEDCOM FAM record — links partners)
CREATE TABLE families (
    id           INTEGER PRIMARY KEY,
    gedcom_xref  VARCHAR(20) UNIQUE,            -- @F1@
    partner1_id  INTEGER REFERENCES individuals(id) ON DELETE SET NULL,  -- GEDCOM HUSB
    partner2_id  INTEGER REFERENCES individuals(id) ON DELETE SET NULL,  -- GEDCOM WIFE
    -- NOTE: per GEDCOM 7, do NOT infer sex/gender/role from partner1 vs partner2.
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FAMILY_CHILDREN  (GEDCOM FAM.CHIL — resolves the many-to-many parent/child graph)
CREATE TABLE family_children (
    family_id          INTEGER REFERENCES families(id)    ON DELETE CASCADE,
    child_id           INTEGER REFERENCES individuals(id) ON DELETE CASCADE,
    pedigree_type      VARCHAR(20) DEFAULT 'birth',  -- birth, adopted, foster, step
    child_order        INTEGER DEFAULT 0,            -- GEDCOM: chronological by birth
    PRIMARY KEY (family_id, child_id)
);
```

### 3.2 Events & places (the heart of the timeline)

```sql
-- PLACES  (GEDCOM PLAC — hierarchical, reused across many events)
CREATE TABLE places (
    id          INTEGER PRIMARY KEY,
    full_name   VARCHAR(255),                  -- "Spring Hill, Maury, Tennessee, USA"
    city        VARCHAR(120),
    county      VARCHAR(120),
    state       VARCHAR(120),
    country     VARCHAR(120),
    latitude    DECIMAL(10,7),
    longitude   DECIMAL(10,7)
);

-- EVENTS  (GEDCOM events AND attributes: BIRT, DEAT, MARR, DIV, BURI, OCCU, RESI, …)
-- Polymorphic: an event belongs to an individual OR a family.
CREATE TABLE events (
    id             INTEGER PRIMARY KEY,
    subject_type   VARCHAR(20) NOT NULL,        -- 'individual' | 'family'
    subject_id     INTEGER     NOT NULL,
    event_tag      VARCHAR(10) NOT NULL,        -- GEDCOM tag: BIRT, DEAT, MARR, OCCU…
    event_value    VARCHAR(255),                -- attribute value (e.g. occupation text)
    date_original  VARCHAR(100),                -- raw GEDCOM date string, e.g. "ABT 1850"
    date_sort      VARCHAR(20),                 -- normalized sortable, e.g. "1850-00-00"
    place_id       INTEGER REFERENCES places(id) ON DELETE SET NULL,
    age            VARCHAR(30),
    cause          VARCHAR(255),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Index (subject_type, subject_id) and date_sort for fast person/timeline views.
);
```

### 3.3 Sources & citations (genealogy's evidence layer)

```sql
-- REPOSITORIES  (GEDCOM REPO — archives/libraries where sources live)
CREATE TABLE repositories (
    id           INTEGER PRIMARY KEY,
    gedcom_xref  VARCHAR(20) UNIQUE,            -- @R1@
    name         VARCHAR(255),
    address      VARCHAR(500),
    website      VARCHAR(255)
);

-- SOURCES  (GEDCOM SOUR — a whole source document)
CREATE TABLE sources (
    id             INTEGER PRIMARY KEY,
    gedcom_xref    VARCHAR(20) UNIQUE,          -- @S1@
    title          VARCHAR(255),
    author         VARCHAR(255),
    publication    VARCHAR(255),
    repository_id  INTEGER REFERENCES repositories(id) ON DELETE SET NULL
);

-- CITATIONS  (GEDCOM SOURCE_CITATION — links a specific fact to a source)
-- Polymorphic: a citation can back an individual, family, event, or name.
CREATE TABLE citations (
    id            INTEGER PRIMARY KEY,
    source_id     INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    subject_type  VARCHAR(20) NOT NULL,         -- 'individual'|'family'|'event'|'name'
    subject_id    INTEGER     NOT NULL,
    page          VARCHAR(255),                 -- "p. 42" / film/frame
    quality       INTEGER,                      -- GEDCOM QUAY 0–3 (evidence quality)
    notes         TEXT
);
```

### 3.4 Media & narratives (photo album + memory blog + wiki text)

```sql
-- MEDIA_OBJECTS  (GEDCOM OBJE — photos now; video deferred to v2)
CREATE TABLE media_objects (
    id           INTEGER PRIMARY KEY,
    gedcom_xref  VARCHAR(20) UNIQUE,            -- @O1@
    file_path    VARCHAR(500),                  -- stored OUTSIDE web root
    media_type   VARCHAR(50),                   -- image/jpeg, image/png
    title        VARCHAR(255),
    description  TEXT,
    uploaded_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MEDIA_LINKS  (attach one media object to any record — drives the album view)
CREATE TABLE media_links (
    media_id      INTEGER REFERENCES media_objects(id) ON DELETE CASCADE,
    subject_type  VARCHAR(20) NOT NULL,         -- 'individual'|'family'|'event'
    subject_id    INTEGER     NOT NULL,
    PRIMARY KEY (media_id, subject_type, subject_id)
);

-- NOTES  (GEDCOM NOTE/SNOTE — life stories, memories, wiki narrative)
CREATE TABLE notes (
    id           INTEGER PRIMARY KEY,
    gedcom_xref  VARCHAR(20) UNIQUE,            -- @N1@ (shared notes only)
    title        VARCHAR(255),
    content      TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'markdown',-- 'markdown' | 'plain'
    is_shared    BOOLEAN DEFAULT 0,             -- SNOTE (shared) vs inline NOTE
    author_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NOTE_LINKS  (attach a note to any record — drives memory blog + wiki text)
CREATE TABLE note_links (
    note_id       INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    subject_type  VARCHAR(20) NOT NULL,         -- 'individual'|'family'|'event'
    subject_id    INTEGER     NOT NULL,
    PRIMARY KEY (note_id, subject_type, subject_id)
);
```

### 3.5 Application layer (not GEDCOM — the website's own needs)

```sql
-- USERS  (authentication; small trusted family group)
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,        -- bcrypt/argon2
    display_name  VARCHAR(120),
    role          VARCHAR(20) DEFAULT 'member', -- 'admin' | 'member'
    is_active     BOOLEAN DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SITE_SETTINGS  (admin-editable text: hero, about, contact — simple key/value)
CREATE TABLE site_settings (
    setting_key   VARCHAR(80) PRIMARY KEY,      -- 'hero_tagline', 'about_text'
    setting_value TEXT
);
```

### 3.6 Deferred to v2 (out of v1 scope)
These are **additive** — each is a new table or feature that Flask-Migrate can add
later without disturbing existing data, so deferring them now does NOT lock anything
in. Recommended home: **v2** (could land in a later v1 revision if ever needed).
- **ASSO** (associations: godparent, witness, >2-partner families)
- **SUBM** (submitter / researcher records)
- **Video / audio** media (photos are in v1)
- **Merge** duplicate individuals
- **Change history / restore** (v1 uses created/updated timestamps instead)
- **Full GEDCOM-7 import/export** — see WP6 in §6 (tentative for v1, firm for v2)

[↑ Back to Contents](#contents)

---

## 4. Feature → View Mapping

| User-facing "feature" | What it really is | Tables it reads |
|---|---|---|
| Family tree / fan chart | Graph of INDI via FAM links | individuals, families, family_children |
| Person page (wiki) | One individual + all their facts | individuals, names, events, citations, media_links, note_links |
| Timeline | A person's (or family's) events by date | events (ordered by `date_sort`), places |
| Photo album | Image media filtered & grouped | media_objects, media_links |
| Memory blog | Markdown narratives | notes, note_links |
| Sources view | Evidence behind each fact | sources, citations, repositories |

[↑ Back to Contents](#contents)

---

## 5. FamilySearch-Modeled Functionality (v1 scope)

Logged-in members can:
- **Add / edit / delete** individuals, names, families, parent/child links (core CRUD)
- **Add events & attributes** (birth, death, marriage, residence, occupation…) with
  fuzzy dates and reusable places
- **Person page** showing vitals, all names, life events, relationships, attached
  sources, photos, and stories
- **Pedigree + fan chart** views (start simple: a few generations, ancestor traversal)
- **Attach sources / citations** to facts; view the evidence behind a person
- **Upload photos** and attach them to people, families, or events
- **Write memories** (Markdown) attached to people or events
- **Admin panel** (admin role): manage users, edit site text, verify backups

### 5A. Build Quality Bar — Depth, Not Stubs

The first build failed by over-simplifying every feature into a hollow shell (e.g.
"Memories" was two blank fields — no who, when, where, or photo). The rework's
non-negotiable quality bar:

- **Schema completeness ↔ form completeness.** Every *user-meaningful* field in the
  schema maps to a thoughtful input control on the appropriate page. A form
  corresponds to a table; each input maps to a column; submitting creates/updates a
  row. A feature is not "done" until every field the schema can hold is capturable and
  editable through the UI.
- **System/auto fields are excluded** from user input: `id`, `created_at`/`updated_at`,
  the reserved `gedcom_xref`, `author_id`, etc. The app sets those.
- **Depth ≠ scope.** Deferring *which* features ship (scope) is fine; shipping an
  in-scope feature at shallow depth is not. MVP here = **fewer features, each fully
  realized** — never all features, each hollow.
- **Worked example — a "Memory" form** exposes: Title · who it's about (person/family
  selector) · when (fuzzy dates) · where (place) · the story (rich text) · attached
  photos · tags — mirroring the `notes`/`note_links` (+ optional event/place) schema
  instead of ignoring it.
- **The Frontend Builder (FE) gets design leadership**, not micromanagement. Give it
  the data model + §5B constraints and let it architect rich, intuitive pages — to the
  *standard* of polish and intuitiveness set by Wes's Datumology and CinephileHub
  sites (including Cinephile's admin panel), **not as a copy of them.** The specific
  control, layout, and visual expression is governed by **docs/FRONTEND_DESIGN.md**
  (FE-owned); §5A still sets the **depth** bar — every user-meaningful field must be
  capturable, however the page chooses to present it.

### 5B. Visual *Requirements* & Constraints (frontend)

_(Intentionally empty. Visual requirements/constraints will be re-introduced here after the
front end is built, stable, and tested — see docs/FRONTEND_DESIGN.md → Design Parking Lot for
candidates.)_

[↑ Back to Contents](#contents)

---

## 6. Roadmap (CompTIA Project+ aligned)

Structured and named per the current **CompTIA Project+ (PK0-005)** lifecycle so the
project doubles as cert practice. The five Project+ phases wrap the technical build;
the build stages are **work packages** inside Execution (renamed from "Phase N" to
avoid colliding with Project+ "phases").

### Project+ lifecycle & required artifacts
- **Initiation** — *Project Charter* (purpose, high-level scope, success criteria),
  *Stakeholder Register* (parents = primary users; Wes = developer/PM; employer
  audience = portfolio reviewer), kickoff.
- **Planning** — *Scope statement & WBS* (the work packages below), *Milestone
  schedule*, *RACI* (who builds what — §7), *Risk Register*, *Communication plan*.
  This Master Plan is the core planning artifact.
- **Execution** — build the work packages (WP1–WP6 below); produce deliverables.
- **Monitoring & Controlling** — *Issue Log*, *Change Log*, phase-gate review at each
  work-package boundary; the dev diaries (`DEVDIARY_BE.md` / `DEVDIARY_FE.md`) serve as
  the status/knowledge record. (Change-control flow + parking lot in §11.)
  **External phase-gate review:** at each WP boundary, Wes can have Claude fetch the
  public GitHub repo and check it against this plan to catch drift early.
- **Closure** — validate deliverables, *Lessons Learned*, archive artifacts, obtain
  sign-off (acceptance = parents actively using the site).

### Execution — v1 "Full" work packages (Python / Flask / SQLite)
Build ONE work package at a time; phase-gate review before the next.
- **WP1 – Database Foundation.** §3 schema as SQLAlchemy models + Flask-Migrate
  migrations + `seed.py` (3 generations of mock data, fuzzy dates, Markdown bios).
  *pytest before gate.*
- **WP2 – Backend CRUD.** Service + REST-shaped route layer for individuals, families,
  events, sources, media, notes. *pytest each resource.* **Deliverable: the API
  contract** (endpoints + JSON shapes) — the interface the frontend builds against.
- **WP3 – Frontend.** The Frontend Builder (FE) builds the UI per the §5B constraints
  (design language in `docs/FRONTEND_DESIGN.md`) against the WP2 API contract.
  Elderly-accessible + cross-generational polish.
- **WP4 – The Views & Search.** Tree/fan chart, timeline, album, memory blog, and a
  rich **Search** interface — all queries against the existing schema. (See §12.)
- **WP5 – Deploy.** AWS Lightsail, gunicorn + nginx, SSL, DNS, nightly backups.
- **WP6 (TENTATIVE) – GEDCOM Import/Export Engine.** Full GEDCOM-7 round-trip,
  validated against the gedcom.io registry. Technically possible in v1, but it's the
  heaviest single piece. **Decision gate:** at the *start of WP5*, reevaluate whether
  it stays in v1 WP6 or moves to v2. Either way it is a **firm v2 deliverable**. Does
  NOT block WP1–WP5 or the parents-first launch.

### Execution — v2 "Enterprise" work packages (Java / Spring Boot / Angular / MySQL / Docker)
- **WP-A** Stand up MySQL (Docker), Flyway baseline schema
- **WP-B** Spring Boot REST API (Controller → Service → Repository)
- **WP-C** Angular SPA consuming the REST API
- **WP-D** Data export → import → verify zero loss (v1 → v2 migration)
- **WP-F** Full GEDCOM-7 import/export engine (firm v2 deliverable, if not done in WP6)
- **WP-E** Containerize, deploy, capstone write-up

[↑ Back to Contents](#contents)

---

## 7. Orchestration & Division of Labor

**Two builders, one repo, a contract between them.**

> FE and BE are distinct roles/lanes (separate ownership; the cross-builder blocker
> protocol applies) regardless of whether the same or different implementer fills them.

- **Backend Builder (BE) → backend + the whole repo/infra.** The preserved scaffolding,
  GEDCOM-7 schema, models, migrations, services, REST routes, pytest, seed data,
  backups, Docker, deployment. Commits as it goes.
- **Frontend Builder (FE) → front-end ONLY.** **HTML (Jinja2 templates), CSS, and
  vanilla JS — with UX and UI as first-class concerns** — for the v1 ("Full") site,
  per the §5A depth bar and §5B constraints (the living design language is
  `docs/FRONTEND_DESIGN.md`). The Frontend Builder (FE) does **not** own the backend,
  infra, or deployment — that's the BE's domain. This is *less* than a normal Cowork
  "Scope B" site, so the Cowork project's "outgrown → split out" rule is **explicitly
  waived** for FamilyHub.
- **v2 ("Enterprise") is handled entirely outside the Cowork project.**

### The contract that guarantees the pieces fit
- **WP2 produces the API/route contract** — endpoints + JSON shapes (the existing
  OpenAPI spec is the artifact). This is the stable interface the Frontend Builder (FE)
  builds against.
- **Build order:** the Backend Builder (BE) finishes the backend contract (WP1–WP2)
  *before* the Frontend Builder (FE) starts the front-end (WP3). The Frontend Builder
  (FE) builds to the contract, not a moving target.
- **One canonical working folder.** Clone the repo once into the chosen location;
  point all development tools and builders at that single folder. Never edit in two
  copies.
- **Deploy target = AWS (Lightsail).** DigitalOcean is at most a fallback and needs no
  configuration. Deployment is the Backend Builder's (BE) job, not the Frontend
  Builder's (FE).

### Build sequence (who's active when — Wes is the switch operator)
Only one builder is active at a time, except WP4's controlled interleave.

| WP | Active | Other | Sync / handoff |
|---|---|---|---|
| WP1 Database Foundation | BE | FE idle | schema + migrations + seed; pytest green |
| WP2 Backend CRUD + API contract | BE | FE idle | **BE publishes the contract → handoff to FE** |
| WP3 Front-end (core CRUD UI) | FE | BE on-call for contract fixes | built to the WP2 contract |
| WP4 Views + Search | BE → FE per view | — | BE adds each query endpoint, then FE builds that view |
| WP5 Deploy | BE | FE idle | AWS Lightsail, SSL, DNS, backups |
| WP6 Import/Export (tentative) | BE | FE idle | decision gate at start of WP5 |

**The one rule that matters most:** the Frontend Builder (FE) does not start until WP2's
contract exists.

### Branch-per-work-package (trunk protection / the merge gate)
Each WP is built on its **own branch off master** (e.g., `wp3-frontend-crud`).
Tests MAY be red on a WP branch while it's mid-build (expected work-in-progress).
A branch merges to master **ONLY when the full suite is green — the CI merge
gate**. **master is always green.** Cross-lane contract edits (e.g., the
front-end adding `text/html` routes to `docs/openapi.yaml`) are allowed **on the
WP branch**; the owning builder (BE) reviews/approves them at merge. **Wes is
the integrator:** he reviews and merges/pushes. One builder active at a time
still holds.

### Two dev diaries (avoid the write conflict)
FE and BE must not write the same file. Split it:
- **`DEVDIARY_BE.md`** — backend (BE). H1 title: "FamilyHub — Backend Dev Diary."
- **`DEVDIARY_FE.md`** — frontend (FE). H1 title: "FamilyHub — Frontend Dev Diary."
- **`DEVDIARY.md`** — thin index pointing to both, so the README "start here" still works.

### README ownership (the Backend Builder (BE) keeps the portfolio face current)
Owner: the Backend Builder (BE) — the README is repo presentation, which is the BE's
domain (FE is frontend-only). Keep it accurate at each WP boundary (never describing
removed features), and deliver the definitive, capstone-grade professional rewrite by
WP5 at the latest, matching the polish of the original presentation.

### Document map & ownership (RACI)
Who owns which document, and how each one changes:
- **`docs/MASTER_PLAN.md`** — the durable **baseline** (requirements, schema, scope,
  security, architecture, process). **Owner: BE.** Changes go through §11 Tier 1 +
  a version bump.
- **`docs/FRONTEND_DESIGN.md`** — the living **front-end design language** + design-
  decision log + design parking lot. **Owner: FE.** Changes freely *within* the §5B
  constraints (§11 Tier 2), logged in its own decision log — no Master Plan revision.
- **`DEVDIARY_BE.md`** (BE) · **`DEVDIARY_FE.md`** (FE) · **`DEVDIARY.md`** (index).
- **`README.md`** — BE (repo presentation).
- **`BLOCKERS.md`** — shared (the cross-builder handoff log).
- **`docs/openapi.yaml`** — BE (the API contract); the front-end may add `text/html`
  routes on its WP branch with BE's approval at merge (per the §7 branch-per-WP rule).

### Cross-builder blocker handoff (so you always know who to spin up)
A builder will hit things only the *other* builder can fix (the FE finds a missing or
wrong endpoint; the BE finds the front-end needs a different data shape). Protocol:
- **Never fake or stub around a cross-boundary blocker** — that recreates the hollow
  failure mode. Stop *that item*; continue other in-scope work if safe.
- **Record it in `BLOCKERS.md`** (repo root) as an OPEN entry: date · raised-by
  (BE/FE) · what's blocked · exactly what the other builder must do · status.
- **Surface it in the end-of-session summary** so Wes sees it unmistakably and knows
  which tool to spin up next.
- **Start of every session:** each builder reads `BLOCKERS.md` first, resolves any OPEN
  item addressed to it, marks it RESOLVED, then proceeds.
- **Distinct from "don't stop for permission":** design *preferences* → pick a
  reasonable option and continue; hard *dependencies* on the other builder → log and
  flag, never fake.

### Workflow discipline (the lesson from the credits burned)
- **One work package at a time.** Don't let either builder run the whole project
  unattended. Phase-gate review (run it, read the DEVDIARY entry) before the next WP.
- **Self-verifying:** backend work includes pytest; no "please test this for me"
  pauses. Manual checks batch into a checklist cleared at each WP boundary.

[↑ Back to Contents](#contents)

---

## 8. Decisions Made On Your Behalf (correct any of these)

1. **Polymorphic attachment** (`subject_type`+`subject_id`) for events/citations/media/
   notes — one table attaches to people, families, or events alike; this is the engine
   behind "everything is a view." Trade-off: the database can't auto-enforce these
   links, so the app code does (zero user-facing impact). v2/Hibernate can formalize.
2. **`partner1_id`/`partner2_id`** on families (maps directly to GEDCOM HUSB/WIFE)
   rather than a partners junction table — simpler for v1.
3. **v1 scope = the essential subset** (per §5): individual & family vital records,
   biographical narratives (= "memories"), photo uploads, events, sources, citations.
   **Deferred to v2** (additive, no lock-in — see §3.6): ASSO, SUBM, video/audio, merge,
   change-history/restore. **Full GEDCOM import/export:** tentative v1 WP6, firm v2.
4. **Markdown** for all narrative content (bios, memories).
5. **`living` flag + `restriction`** drive PII hiding rather than a separate privacy
   subsystem.

[↑ Back to Contents](#contents)

---

## 9. Security & Privacy Maturity Ladder

Nearly everything in the live site is sensitive family PII, so security grows
deliberately. The first build already cleared the MVP tier — build upward from there.

- **Tier 1 — MVP (already present, carry forward):** bcrypt password hashing, CSRF
  protection, strict CSP, login rate limiting, security headers, login-walled photo
  serving, secure session cookies, password reset, HTTPS, PII hidden for `living`
  individuals, upload validation, files stored outside the web root.
- **Tier 2 — Hardening (mid-project WPs):** role-based access control (§10), audit
  logging, encryption at rest for backups, secrets management, dependency/vulnerability
  scanning in CI, granular per-record privacy.
- **Tier 3 — Mature (v2 / ongoing):** MFA, penetration testing, PII minimization,
  data export/delete (subject-rights) tooling, monitoring / intrusion detection.
- Ties directly to Wes's **ISC2 CC** and the **WGU Security** coursework.

[↑ Back to Contents](#contents)

---

## 10. Access Control — Roles & Admin Panel (progressive)

Target model is standard **RBAC** with four roles:
- **GUEST** — trusted outsider (e.g., relative by marriage): minimal, e.g. comment only.
- **USER** — standard family member: normal CRUD on family content.
- **POWER USER** — technically savvy member: elevated permissions just below admin.
- **ADMIN** — full control.

**Anti-lock-in design (do this early):** put the `role` enum on `users` from the start
and route every permission check through a **single authorization layer** (one
decorator/service), so adding roles or granular permissions later is a centralized
change, not a scattered rewrite. No technical limit in Flask/SQLite — the only
constraint is build time.

**Progressive ladder (a little more each WP):**
- **WP2:** role scaffolding (enum + auth layer) + basic USER/ADMIN.
- **WP3–WP4:** rich admin-panel UX (FE) + POWER USER and GUEST tiers.
- **Dedicated later WP:** granular per-feature permissions + full admin dashboard.

[↑ Back to Contents](#contents)

---

## 11. Change Management & Parking Lots (Project+ change control)

New ideas or changes after handoff go through a lightweight Project+ flow instead of
derailing an in-flight work package:

1. **Log it** — capture the idea/change request (`CHANGES.md` or the DEVDIARY).
2. **Assess impact** — scope/schedule effect.
3. **Decide** — approve into a WP, or **park** it.
4. **Assign** — give approved changes a target WP.

### Two tiers of change (baseline vs. design)
Not every change is the same weight. Route each by which document it touches:
- **Tier 1 — Baseline (`docs/MASTER_PLAN.md`).** Any change to requirements, schema,
  scope, security, architecture, process, or **any §5B visual constraint** → log it,
  assess impact, **Wes approves**, then **version bump + a Revision History line**.
- **Tier 2 — Design (`docs/FRONTEND_DESIGN.md`).** Visual/UX *expression* within the §5B
  constraints (palette, fonts, dark/light, motion, component look) → **the Frontend
  Builder (FE) changes directly** and logs it in that doc's design-decision log;
  **no Master Plan revision**.
- **Escalation (Tier 2 → Tier 1).** A design idea that would **breach a §5B constraint**,
  or that needs **new functionality/endpoints**, escalates to Tier 1: log it, Wes
  approves, the baseline is updated before it ships.

### SemVer bump rules (for Tier-1 changes)
Version format is **MAJOR.MINOR.PATCH**. Prior version 1.4 = 1.4.0.
- **MAJOR (X.0.0):** breaking or scope-altering — add/remove a work package, schema
  change, security/architecture shift, or anything that invalidates built work or a
  published contract.
- **MINOR (x.Y.0):** substantive but non-breaking — new sections, process or ownership
  refinements, role model changes.
- **PATCH (x.y.Z):** clarifications, wording, formatting, typos, TOC updates.

Tier-2 changes (`docs/FRONTEND_DESIGN.md`) stay in that doc's decision log; they do
not carry a Master Plan version bump.

### Parking lots (two of them — captured, not scheduled)
- **Master Plan parking lot (below)** — larger **feature / functionality** ideas
  (Tier-1 scope), revisited after the initial site is seen.
- **`docs/FRONTEND_DESIGN.md` parking lot** — the **visual / design** brainstorm
  (Tier-2), the Frontend Builder's (FE) to keep.

**Master Plan parking lot:**
- Per-member **dashboard** (FamilySearch-style "my contributions" summary).
- **Browse-vs-edit UX** split (subtle edit icon → inline/popup edit) so editing
  controls never intrude on the reading experience.
- **Public surface + PII guardrail.** A curated public landing — not a separate
  feature, but a filtered view of the existing database ("One Database, Many Views").
  Key decisions to carry in:
  - **Per-item "public" flag** (default OFF) on individuals, photos, stories, and
    events; an admin marks specific items public; the public page renders only flagged
    items.
  - **Living-person guardrail** — `living = true` individuals are NEVER eligible for
    the public flag (enforced by the existing `living` field + §9; no exceptions).
  - **Admin PII-gate** — before any item goes public, the admin console shows a
    preview of exactly what would appear, warns/blocks on living-person data and flags
    likely PII (DOB, places, contact info), requires explicit confirmation, and writes
    an `audit_log` entry.
  - **Configurable public layout** — the public page is composed of admin-toggled /
    editable / reorderable sections, so marketing-only sections (e.g. a "Begin your
    family's archive" CTA) can be removed or edited without code changes; section copy
    uses the existing `site_settings` table.
  - **Chronicle shared design system** — the public landing and the logged-in app
    share one design language ("Chronicle"), including a Chronicle-consistent restyle
    of the logged-in dashboard.
  - **Scope + sequence:** spans BE (public flag + API + gate logic + serving rules)
    and FE (curated public rendering + admin curation/layout UI + dashboard restyle).
    Schedule as a focused WP after WP3 (core front-end CRUD UI) is complete.
- (Add future *feature* ideas here rather than expanding MVP scope.)

[↑ Back to Contents](#contents)

---

## 12. Search (a genealogy site is useless without it)

Finding a person by *any* fragment you remember is core, not optional. Scaled so a
strong version ships in v1 — easy here because the dataset is family-sized.

- **v1 (delivered in WP4):** a rich search interface —
  - People by **name** (given or surname, partial/typo-tolerant `LIKE` matching).
  - **Filters:** birth/death year range, place, sex, living/deceased.
  - **Full-text search across notes/memories and bios** via **SQLite FTS5**.
  - Results link straight to the person page; empty/near-miss states are handled.
- **v2 (Enterprise):** advanced **fuzzy/phonetic** matching ("sounds like," Soundex/
  Metaphone), faceted search, and relationship-aware queries on MySQL full-text.
- **Backend note:** the search endpoint is part of the WP2 API contract surface so the
  WP4 search UI has a stable target. No technical limit at family scale.

[↑ Back to Contents](#contents)

---

## Revision History
- v1.6.0 — 2026-06-29 — Parked the public-surface + PII-gate model in §11: curated
  public view of the database (per-item "public" flag, default OFF; `living`-person
  guardrail via §9; admin PII-gate + preview + `audit_log`; configurable section
  layout via `site_settings`; Chronicle shared design system spanning public and
  logged-in app). MINOR bump — parking-lot capture only; no scope committed.
  (Approved by Wes.)
- v1.5.0 — 2026-06-28 — Adopted SemVer (MAJOR.MINOR.PATCH; prior 1.4 = 1.4.0) with
  defined change tiers in §11; generalized the builder model to implementer-agnostic
  roles Frontend Builder (FE) / Backend Builder (BE) — implementer is now assigned at
  task time, not named in this document; added a Contents/TOC. (Approved by Wes.)
- v1.4 — 2026-06-28 — Emptied §5B durable visual constraints (moved to FRONTEND_DESIGN.md
  design parking lot as post-stable candidates); §5B left as a placeholder to be re-populated
  after the front end is built and tested. (Approved by Wes.)
- v1.3 — 2026-06-18 — Separated fluid design from the baseline: trimmed §5B to durable
  Visual Requirements & Constraints (accessibility, calm-by-design, cross-generational
  goal with a lean toward the youngest generation, identity guardrail, imagery-as-
  texture) and moved the living visual/UX design language to a new Cowork-owned
  docs/FRONTEND_DESIGN.md. Added a document map + RACI (§7) and a two-tier change-control
  model + dual parking lots (§11). (Raised by Wes.)
- v1.2 — 2026-06-18 — Added the **branch-per-work-package** workflow to §7: each WP is
  built on its own branch off master; tests may be red on-branch (WIP); a branch merges
  to master only when green (the CI merge gate), so master is always green; cross-lane
  contract edits are allowed on-branch with the owning builder's approval at merge; Wes
  integrates. (Raised by Wes, 2026-06-18.)
- v1.1 — 2026-06-16 — Added README ownership/maintenance directive (Code owns it; keep 
  accurate per WP; definitive professional rewrite due by WP5). (§7)
- **v1.0 — 2026-06-16** — Initial locked plan: Path A re-foundation, GEDCOM-7 schema,
  depth bar (§5A), visual design brief (§5B), orchestration + build sequence + blocker
  handoff (§7), Project+ roadmap (§6), security ladder (§9), RBAC ladder (§10), change
  control + parking lot (§11), search (§12).

[↑ Back to Contents](#contents)
<!-- Add new versions above this line, newest first, when §11 change control approves a change. -->
