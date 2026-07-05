# FamilyHub — Master Plan

> The single source of truth for the project's architecture, schema, scope, and
> roadmap. Build one piece at a time; review each piece before starting the next.

**Revision 2.5.0** · Last updated 2026-07-04 · Status: v1 build in progress — WP3 (frontend) underway.
*Git is the source of truth — repo HEAD is always current. Per §11 change control, when
a change is approved, bump this version (SemVer) and add a line to the Revision History
(bottom).*

*Document control: the Revision number above versions THIS DOCUMENT (SemVer, per §11
change control). It is independent of the product versions — v1 "Full" (Flask) and v2
"Enterprise" (Java) — whose release versions are Git tags (1.x / 2.x) beginning at WP5
(see §6).*

> **Design decisions live in ADRs.** Point-in-time architecture decisions are recorded
> under [`docs/adr/`](adr/README.md): **ADR-0001** (write-control model — post-moderation:
> RBAC + audit + soft-delete + revert), **ADR-0002** (Account↔Person link), **ADR-0003**
> (white-label — neutral language, no personal data in the app itself), and **ADR-0004**
> (defer all FE design constraints until the front end is stable). The Master Plan
> cites them where they bite; the ADRs hold the full rationale.

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
          Pedigree    (Wiki)
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
- **Soft-delete, never hard-delete** (per **ADR-0001**). Every user-editable record
  carries a nullable `deleted_at` timestamp; "delete" sets it, queries filter it out,
  and any state is recoverable. Paired with `audit_log` (§3.5) this gives full
  provenance + one-click **Curator revert**. This is a v1 design rule, not a v2
  deferral (see §3.6, §8, §9).
- **The person graph is a graph, not a linked list.** Parent/child and partner links
  (`families` + `family_children`) form a directed graph an individual can have many
  ancestors, descendants, and spouses. Traversal code (pedigree, relationship view)
  must treat it as such: no assumption of a single linear chain, and the traversal
  endpoint supports **lazy subtree fetch from any node** (the seam for the v2 dynamic
  pan/zoom canvas — §11).
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
    role          VARCHAR(20) DEFAULT 'contributor', -- viewer|contributor|curator|admin (§10)
    is_active     BOOLEAN DEFAULT 1,
    email_verified_at TIMESTAMP,                 -- transactional-email verification (§9)
    individual_id INTEGER REFERENCES individuals(id) ON DELETE SET NULL,  -- Account↔Person (ADR-0002)
    timezone      VARCHAR(50),                   -- per-user override of the site default (§5)
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Account↔Person (ADR-0002): individual_id is NULLABLE. A linked user is the same
-- person as an INDI record (enables self-authored living-member records, §5). Unlinked
-- users have no anchor, so the tree defaults to the OLDEST-ANCESTOR root.

-- SITE_SETTINGS  (admin-editable config: branding, page text, security baseline — key/value)
CREATE TABLE site_settings (
    setting_key   VARCHAR(80) PRIMARY KEY,      -- see the config groups below
    setting_value TEXT
);
-- White-label / config-driven branding (§5): 'site_name' and 'family_name' feed the app
-- header, page <title>s, and the Chronicle masthead, so the app is forkable/rebrandable.
-- Also holds the site default 'timezone' and the security baseline (§9): min password
-- length, breach-list check on/off, login rate-limit/lockout thresholds, session timeout.

-- AUDIT_LOG  (provenance — every mutating write, before -> after; ADR-0001, §9 Tier-1)
-- Present since WP2 as preserved security infra; ADR-0001 promotes it to core v1 scope.
CREATE TABLE audit_log (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- who
    action        VARCHAR(20),                  -- create | update | delete | revert
    subject_type  VARCHAR(20),                  -- table/entity acted on
    subject_id    INTEGER,
    before_json   TEXT,                          -- prior values (NULL on create)
    after_json    TEXT,                          -- new values (NULL on delete)
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- when
);

-- SUGGESTIONS  (Suggest-an-idea -> admin inbox; §5)
CREATE TABLE suggestions (
    id            INTEGER PRIMARY KEY,
    author_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    topic         VARCHAR(120),
    body          TEXT,
    status        VARCHAR(20) DEFAULT 'new',    -- new | triaged | planned | done | declined
    priority      INTEGER DEFAULT 0,            -- admin's priority-queue ordering
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ROLE_REQUESTS  (a member asks for elevated access -> admin approval; §5, §10)
CREATE TABLE role_requests (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
    requested_role VARCHAR(20),                 -- the role ladder rung being requested
    reason        TEXT,
    status        VARCHAR(20) DEFAULT 'pending',-- pending | approved | denied
    decided_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.6 Deferred to v2 (out of v1 scope)
These are **additive** — each is a new table or feature that Flask-Migrate can add
later without disturbing existing data, so deferring them now does NOT lock anything
in. Recommended home: **v2** (could land in a later v1 revision if ever needed).
- **ASSO** (associations — non-family relationships: apprenticeship, employment,
  godparent, enslavement, household, neighbor, "relative"). This is the data behind the
  Person Page **"Other Relationships"** section, which is **v2**. **Core family
  relationships (parents / spouses / children / siblings via FAM links) remain v1** —
  only the non-family associations defer.
- **SUBM** (submitter / researcher records)
- **Fan Chart** — the radial tree view. v1 ships **Pedigree + Family Group +
  Relationship View** (§5); the fan chart is a v2 renderer.
- **Video / audio** media (photos are in v1)
- **Merge** duplicate individuals (tools may land in **v1.x** — §5; firm by v2)
- **Full GEDCOM-7 import/export** — see WP6 in §6 (tentative for v1, firm for v2)

> **No longer deferred:** change-history / restore has been **promoted to v1** per
> **ADR-0001** — `audit_log` (before→after) + soft-delete + Curator revert are core v1
> scope (§3.5, §8, §9), not the old "timestamps only" fallback.

[↑ Back to Contents](#contents)

---

## 4. Feature → View Mapping

| User-facing "feature" | What it really is | Tables it reads |
|---|---|---|
| Family tree (pedigree) | Graph of INDI via FAM links, traversed from a root | individuals, families, family_children |
| Person page (wiki) | One individual + all their facts | individuals, names, events, citations, media_links, note_links |
| Timeline | A person's (or family's) events by date | events (ordered by `date_sort`), places |
| Photo album | Image media filtered & grouped | media_objects, media_links |
| Memory blog | Markdown narratives | notes, note_links |
| Sources view | Evidence behind each fact | sources, citations, repositories |
| Change history / revert | Provenance + one-click undo (ADR-0001) | audit_log |
| Suggestions inbox | Suggest-an-idea → admin triage queue | suggestions |
| Admin: role requests | Elevation requests → admin approval | role_requests, users |

> **v2 views (reserved, not built in v1):** **Fan Chart** (radial tree), the Person Page
> **"Other Relationships"** section (non-family ASSO), and the **dynamic pan/zoom tree
> canvas** (§11). The v1 pedigree renderer and traversal endpoint are built with the
> seams for these (§3 design rules, §5).

[↑ Back to Contents](#contents)

---

## 5. FamilySearch-Modeled Functionality (v1 scope)

Logged-in members can:
- **Add / edit / delete** individuals, names, families, parent/child links (core CRUD).
  "Delete" is a **soft-delete** — recoverable, audited, revertible (ADR-0001, §3.5).
- **Add events & attributes** (birth, death, marriage, residence, occupation…) with
  fuzzy dates and reusable places
- **Person page** showing vitals, all names, life events, **core family relationships**
  (parents / spouses / children / siblings), attached sources, photos, and stories.
  *(Non-family "Other Relationships" — apprenticeship, employment, godparent, etc. — is
  v2; see §3.6.)*
- **Tree views:** **Pedigree** (ancestor traversal — vertical layout is the v1 default;
  a horizontal orientation is reserved as a **v2 toggle**), a **Family Group** view, and
  a **Relationship View**. *(Fan Chart is v2 — §3.6.)* The renderer is
  **orientation-parameterized** and the traversal endpoint supports **lazy subtree fetch
  from any node**, so the v2 horizontal toggle and pan/zoom canvas (§11) are seams, not
  rewrites.
- **Attach sources / citations** to facts; view the evidence behind a person
- **Upload photos** and attach them to people, families, or events
- **Write memories** (Markdown) attached to people or events
- **Edit their own person record** — a member **linked** to an INDI (ADR-0002) may
  self-author their living record (profession, achievements, life sketch): high-value
  original data, not just transcription.
- **See a tree even when unlinked** — a user with no `individual_id` gets the
  **oldest-ancestor** as the default tree root (ADR-0002).
- **Change their timezone** — the site has a default; each account can override it.
- **Suggest an idea** (→ admin **Suggestions inbox**: topic + status lifecycle +
  priority) and **request a role change** (→ admin approval).
- **Self-serve account email** — password reset and **email verification** via
  configurable **transactional email** (Option A: SMTP/provider — §9 Tier-1).
- **Admin panel** (admin role): manage users + role requests, triage the suggestions
  inbox, edit **branding** (`site_name` / `family_name`) and site text, tune the
  **security baseline** (min password length, breach-list check, rate-limit/lockout,
  session timeout — §9), verify backups, and **revert** any audited change.

### v1.x — additive scope (lands *after* core CRUD, no schema lock-in)
These are approved for v1 but sequenced after the core CRUD UI so they never block the
parents-first launch. Each is additive (a new table/view), so deferring the *timing*
costs nothing:
- **Member Profile + privacy-controlled contact fields** and a **Family Address Book**
  view — **default-deny, per-field sharing**, kept *inside* FamilyHub (not a separate
  app). Feeds off the Account↔Person link (ADR-0002).
- **Merge / duplicate** tools for individuals (also listed v2-adjacent in §3.6; may land
  in v1.x).

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
- **The FE builder gets design leadership**, not micromanagement. Give it the data
  model + §5B (see ADR-0004) and let it architect rich, intuitive pages — to the
  *standard* of polish and intuitiveness set by the Datumology and CinephileHub
  sites (including Cinephile's admin panel), **not as a copy of them.** The specific
  control, layout, and visual expression is governed by
  **`docs/FRONTEND_DESIGN.md`** (FE-owned); §5A still sets the **depth** bar —
  every user-meaningful field must be capturable, however the page chooses to
  present it.

### 5B. Visual *Requirements* & Constraints (frontend)

_(Intentionally empty — see **ADR-0004**. Visual requirements/constraints will be
re-introduced here only after the front end is built, stable, and tested — see
docs/FRONTEND_DESIGN.md → Design Parking Lot for the candidates.)_

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
- **WP3 – Frontend.** The Frontend Builder (FE) builds the UI per the §5B constraints against the WP2
  API contract. Elderly-accessible + cross-generational polish.
- **WP4 – The Views & Search.** Tree (pedigree + family-group + relationship view),
  timeline, album, memory blog, and a rich **Search** interface — all queries against
  the existing schema. (See §12; fan chart is v2 per §3.6.)
- **WP5 – Deploy.** AWS Lightsail, gunicorn + nginx, SSL, DNS, nightly backups.
  First release = Git tag `v1.0.0` + GitHub Release + a new `CHANGELOG.md` ("Keep a
  Changelog" format) + an app version string (`pyproject.toml` / `app.__version__`);
  the product v1 "Full" line releases as 1.x and the v2 "Enterprise" rewrite will
  begin at 2.0.0 (SemVer: a rewrite is a major version).
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
  per the §5A depth bar and §5B constraints. The Frontend Builder (FE) does **not**
  own the backend, infra, or deployment — that's the BE's domain. This is *less*
  than a normal Cowork "Scope B" site, so the Cowork project's "outgrown → split
  out" rule is **explicitly waived** for FamilyHub.
- **v2 ("Enterprise") is handled entirely outside the Cowork project.**

### The contract that guarantees the pieces fit
- **WP2 produces the API/route contract** — endpoints + JSON shapes (the existing
  OpenAPI spec is the artifact). This is the stable interface the FE builds against.
- **Build order:** the BE finishes the backend contract (WP1–WP2) *before* the FE
  starts the front-end (WP3). The FE builds to the contract, not a moving target.
- **One canonical working folder.** Clone the repo once into the chosen location;
  point all development tools and builders at that single folder. Never edit in two
  copies.
- **Deploy target = AWS (Lightsail).** DigitalOcean is at most a fallback and needs no
  configuration. Deployment is the BE's job, not the FE's.

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

**The one rule that matters most:** the FE does not start until WP2's contract exists.

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
  security, architecture, process). **Owner: BE.** Changes via §11 Tier 1 + a
  Revision bump and Revision History line.
- **`docs/FRONTEND_DESIGN.md`** — the living **front-end design language** +
  design-decision log + design parking lot. **Owner: FE.** Changes freely *within*
  the §5B constraints (§11 Tier 2), logged in its own decision log — no Master Plan
  revision.
- **`docs/adr/`** — immutable **Architecture Decision Records** (context · decision ·
  consequences). A new ADR requires project-owner approval; once Accepted, an ADR is
  superseded by a new one, never edited.
- **`docs/openapi.yaml`** — the API contract. **Owner: BE.** The FE may add
  `text/html` routes on its WP branch with BE approval at merge (per the §7
  branch-per-WP rule).
- **`DEVDIARY_BE.md`** (BE) · **`DEVDIARY_FE.md`** (FE) · **`DEVDIARY.md`** (index).
- **`README.md`** — BE (repo presentation). · **`BLOCKERS.md`** — shared (the
  cross-builder handoff log).
- **`CHANGELOG.md`** — created at first release (WP5); release notes per SemVer tag.

### Standards alignment (which industry artifact each document fulfills)
This project deliberately consolidates the traditional planning artifacts into one
maintained plan (the small-team "design doc" pattern) rather than separate documents;
this table maps each standard artifact to where it lives here.

| Industry artifact | Where it lives in this project |
|---|---|
| Project Charter | §1 (vision, success criteria) + §6 Initiation |
| Scope Statement & WBS | §5 (scope) + §6 (work packages) |
| Software Requirements Specification (SRS) | §5 / §5A (functional + quality bar) + §5B (UX constraints) + §12 |
| Software Design Description (SDD) | §2–§4 (architecture, schema, view mapping) |
| RACI / resource plan | §7 |
| Risk & security plan | §9 |
| Change-management plan + change log | §11 + Revision History |
| Architecture Decision Records | `docs/adr/` |
| API contract | `docs/openapi.yaml` |
| Test plan | pytest per WP + the CI merge gate (§6, §7) |
| Status / knowledge record | `DEVDIARY_BE.md` / `DEVDIARY_FE.md` |
| Release versioning | Git tags + `CHANGELOG.md`, from WP5 (§6) |

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
   **Deferred to v2** (additive, no lock-in — see §3.6): ASSO (non-family "Other
   Relationships"), SUBM, video/audio, **Fan Chart**. **Full GEDCOM import/export:**
   tentative v1 WP6, firm v2. **Merge** is v2-adjacent (may land v1.x — §5).
4. **Markdown** for all narrative content (bios, memories).
5. **`living` flag + `restriction`** drive PII hiding rather than a separate privacy
   subsystem.
6. **Post-moderation write-control is v1** (**ADR-0001**, reversing the earlier v2
   deferral): direct writes gated by RBAC (§10), a full `audit_log` (before→after),
   **soft-delete only**, and **Curator revert**. A pre-moderation approval queue stays
   v2 (additive `change_request` table). This is the scope/schema change that makes this
   revision a **MAJOR** bump.
7. **Account↔Person link is v1** (**ADR-0002**): a nullable `users.individual_id` FK ties
   an account to its INDI record (enables self-authored living-member records);
   **unlinked users default the tree root to the oldest ancestor**.
8. **RBAC roles renamed** to **Viewer / Contributor / Curator / Admin** (was GUEST / USER
   / POWER USER / ADMIN — §10). Same ladder; **permissions modeled as data** (a role = a
   bundle of permission flags) so custom roles are a later data change, not a rewrite.
9. **App is white-labelable** — `site_name` / `family_name` in `site_settings` drive
   header, page titles, and the Chronicle masthead, so the codebase is forkable.
10. **Transactional email (Option A)** — configurable SMTP/provider powers self-serve
    password reset + email verification (§9). A separate *notification* email stream is
    v2 (§11).
11. **Neutral language, no personal data in the app itself** (**ADR-0003**): white-label
    means no specific family's name/contact info appears in the app's own UI copy, config
    defaults, or the technical/build-detail language describing the schema and
    architecture — that's what makes the codebase genuinely forkable and keeps a public
    repo PII-clean. Author credit and the project's origin story remain fine in docs
    (README, this plan's own narrative) — the line is between *attribution* (allowed) and
    *the app's operative voice* (must stay generic, e.g. "contact your family
    administrator").

[↑ Back to Contents](#contents)

---

## 9. Security & Privacy Maturity Ladder

Nearly everything in the live site is sensitive family PII, so security grows
deliberately. The first build already cleared the MVP tier — build upward from there.

- **Tier 1 — MVP (already present, carry forward):** bcrypt password hashing, CSRF
  protection, strict CSP, login rate limiting, security headers, login-walled photo
  serving, secure session cookies, password reset, HTTPS, PII hidden for `living`
  individuals, upload validation, files stored outside the web root.
  **Now also v1-active (per ADR-0001):** **RBAC** (§10, shipped in WP2), **audit logging**
  (before→after on every mutation), and **soft-delete + Curator revert**. **Email
  verification** joins password reset on the configurable transactional-email stream
  (§8.10). The **security baseline is admin-configurable** via `site_settings` (§3.5):
  min password length, **breach-list check** (HaveIBeenPwned k-anonymity), login
  rate-limit / lockout thresholds, and session timeout.
- **Tier 2 — Hardening (mid-project WPs):** encryption at rest for backups, secrets
  management, dependency/vulnerability scanning in CI, granular **per-record** privacy,
  and the **permission-as-data** role→permission matrix (read-only view in v1; editable
  toggle UI is v2 — §10).
- **Tier 3 — Mature (v2 / ongoing):** **MFA (TOTP** — no SMS/phone dependency; §11),
  penetration testing, PII minimization, data export/delete (subject-rights) tooling,
  monitoring / intrusion detection.
- Ties directly to Wes's **ISC2 CC** and the **WGU Security** coursework.

[↑ Back to Contents](#contents)

---

## 10. Access Control — Roles & Admin Panel (progressive)

Target model is standard **RBAC** with four roles (renamed 2026-07-03 — same ladder,
warmer/clearer labels):
- **Viewer** — trusted outsider (e.g., relative by marriage): minimal, e.g. comment only.
  *(was GUEST)*
- **Contributor** — standard family member: normal CRUD on family content. *(was USER)*
- **Curator** — technically savvy member: elevated permissions just below admin,
  including the audit-driven **revert** (ADR-0001). *(was POWER USER)*
- **Admin** — full control.

**Anti-lock-in design (do this early):** put the `role` enum on `users` from the start
and route every permission check through a **single authorization layer** (one
decorator/service), so adding roles or granular permissions later is a centralized
change, not a scattered rewrite. No technical limit in Flask/SQLite — the only
constraint is build time.

**Permissions modeled as data (do this in v1):** a role is a **bundle of permission
flags**, not a hard-coded `if role == 'admin'` scattered through the code. Storing the
role→permission mapping as data means a new or custom role is a **data change**, not a
rewrite. v1 exposes a **read-only role→permission matrix** in the admin panel (so the
model is legible); the **editable toggle UI** that lets an admin re-bundle permissions
or mint custom roles is reserved for **v2**.

**Progressive ladder (a little more each WP):**
- **WP2:** role scaffolding (enum + single auth layer) + basic Contributor/Admin. *(done)*
- **WP3–WP4:** rich admin-panel UX (FE) + Curator and Viewer tiers + the read-only
  permission matrix; role-change requests routed to admin approval (§5).
- **v2:** editable permission-matrix UI + custom roles (the data model already allows it).

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
  assess impact, **Wes approves**, then **Revision bump + a Revision History line**.
- **Tier 2 — Design (`docs/FRONTEND_DESIGN.md`).** Visual/UX *expression* within the
  §5B constraints (palette, fonts, dark/light, motion, component look) → **the FE
  builder changes directly** and logs it in that doc's design-decision log; **no
  Master Plan revision**.
- **Escalation (Tier 2 → Tier 1).** A design idea that would **breach a §5B
  constraint**, or that needs **new functionality/endpoints**, escalates to Tier 1:
  log it, Wes approves, the baseline is updated before it ships.

### SemVer bump rules (for Tier-1 changes)

Revision format is **MAJOR.MINOR.PATCH**.
- **MAJOR (X.0.0):** breaking or scope-altering — add/remove a work package, schema
  change, security/architecture shift, or anything that invalidates built work or a
  published contract.
- **MINOR (x.Y.0):** substantive but non-breaking — new sections, process or ownership
  refinements, role model changes.
- **PATCH (x.y.Z):** clarifications, wording, formatting, typos, TOC updates.

Tier-2 changes (`docs/FRONTEND_DESIGN.md`) stay in that doc's decision log; they do
not carry a Master Plan revision bump.

### Parking lots (two of them — captured, not scheduled)
- **Master Plan parking lot (below)** — larger **feature / functionality** ideas
  (Tier-1 scope), revisited after the initial site is seen.
- **`docs/FRONTEND_DESIGN.md` parking lot** — the **visual / design** brainstorm
  (Tier-2), the FE builder's to keep.

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
    Schedule as a focused WP after WP4 (front-end shell + core CRUD UI) is complete.
    (Approved by Wes 2026-06-29; carried forward from the `wp3-frontend-crud` branch
    at merge into `wp4-fe-shell`, 2026-07-03.)
- **Follow a person** — a member subscribes to updates on one individual (surfaced
  on the Person Page header). Parked from the FE-2 wireframe (2026-07-04): needs a
  `follows` join table + endpoints and only becomes truly useful alongside the v2
  notification-email system (§11 v2 captures). Target: v1.x at the earliest.

**v2 / future captures (reserved seams, do NOT build now):**
- **MFA (TOTP)** — authenticator-app second factor, **no SMS/phone dependency** (§9 Tier-3).
- **Notification email system** — event-triggered emails with a **preference center**,
  **digests**, and **unsubscribe/compliance**, on a **separate sending stream** from the
  transactional email of §8.10 (deliverability + compliance hygiene).
- **Dynamic pan/zoom tree canvas** — lazy-expand from any node; the v1 traversal endpoint's
  "lazy subtree fetch" (§3 design rules) is the seam for it.
- **Admin theme switcher** — pick among predetermined designs (pairs with white-label
  branding, §8.9).
- **Family Bunch** — a *separate*, present-tense family **social** app (not genealogy).
  **Do NOT build it here.** FamilyHub stays the system of record: it owns accounts,
  member profiles, and stable IDs, and merely **reserves an identity/API seam** so a
  future Family Bunch could authenticate against it.
- (Add future ideas here rather than expanding MVP scope.)

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
- **2.5.0 — 2026-07-04 — MINOR.** Parking-lot capture: **Follow a person** (from the
  FE-2 Person Page wireframe) parked to v1.x — no v1 scope change; pairs with the v2
  notification-email system. Decision recorded from FE-2's BLOCKERS item. (Raised by FE;
  decided by Wes.)
- **2.4.0 — 2026-07-04 — MINOR.** Restored content lost in the 2026-07-03 merge-conflict
  resolution that kept the 2.0.0 rewrite over revisions v1.3–v1.6.0: implementer-agnostic
  builder roles (Backend Builder (BE) / Frontend Builder (FE)) across §1/§6/§7 (v1.5.0);
  Contents/TOC + back-to-contents links (v1.5.0); §11 SemVer bump rules (v1.5.0); 5A/5B
  demoted to §5 subsections; §5B returned to its **intentionally empty** v1.4 state —
  reversing 2.3.0's §5B re-population — with the rationale now permanently recorded as
  **ADR-0004** (defer all FE design constraints until the front end is stable; end-of-v1
  pre-launch gate). Re-inserted the v1.3–v1.6.0 Revision History entries for a complete
  audit trail. (Raised by Wes.)
- **2.3.0 — 2026-07-04 — MINOR.** Ported the stranded v1.3 revision (2026-06-18,
  `wp3-frontend-crud` branch) into the current plan: §5B trimmed to durable **Visual
  Requirements & Constraints** (the living design language lives in
  `docs/FRONTEND_DESIGN.md`); §7 **Document map & ownership (RACI)**; §11 **two-tier
  change control + dual parking lots** — this also repairs the cross-references in
  `docs/FRONTEND_DESIGN.md` that cited these sections. Additionally: added the §7
  **Standards-alignment table** (industry artifact → location), a WP5
  **release-versioning** note (Git tag `v1.0.0` + `CHANGELOG.md`), relabeled the
  document version as **"Revision"** (document control is independent of the product's
  v1/v2 release versions), and retired `docs/CONTEXT_LOG.md` (internal operations
  moved out of the public repo). (Raised by Wes.)
- **v2.2.0 — 2026-07-03 — MINOR.** Adopted **ADR-0003** (white-label — neutral language,
  no personal data in the app itself): §8 decision #11 points at the ADR; the top-of-doc
  ADR pointer lists it alongside ADR-0001/0002. Decision-capture only — the rule was
  already implicit in the white-label scope (§5/§8.9); this makes it explicit and citable.
  A same-session fix (outside this doc) removed the ADR's own motivating example — a
  hardcoded personal name in the login/error-page copy — from the app surface. (Raised by
  Wes.)
- **v2.1.0 — 2026-07-03 — MINOR.** Carried forward the **public surface + PII guardrail**
  parking-lot entry (§11) from the `wp3-frontend-crud` branch (approved by Wes
  2026-06-29) when that branch's Chronicle front-end work was merged forward onto
  `wp4-fe-shell`. Parking-lot capture only — no scope committed. (Raised by FE.)
- **v2.0.0 — 2026-07-03 — MAJOR (v1 design reconciliation).** Scope/schema-altering, so
  a major bump. (Raised by Wes; decisions captured in ADR-0001, ADR-0002, and
  `docs/CONTEXT_LOG.md`.)
  1. **Write-control → v1** (per **ADR-0001**, reversing the old v2 deferral): `audit_log`
     (before→after) + **soft-delete** + **Curator revert** are core v1 scope. Reflected in
     §3 design rules, §3.5 (audit_log table), §3.6, §8.6, §9 (audit now Tier-1).
  2. **Fan Chart → v2.** v1 tree = **Pedigree** (vertical default; horizontal reserved as
     a v2 toggle) **+ Family Group + Relationship View**. Renderer is
     orientation-parameterized; traversal endpoint supports lazy subtree fetch from any
     node; the person graph is a **graph, not a linked list** (§2, §3, §4, §5, §6).
  3. **Associations (ASSO) → v2, confirmed.** The Person Page **"Other Relationships"**
     (non-family) section is v2; **core family relationships remain v1** (§3.6, §4, §5, §8.3).
  4. **RBAC rename (§10):** GUEST/USER/POWER USER/ADMIN → **Viewer/Contributor/Curator/
     Admin**; **permissions modeled as data** + a **read-only** role→permission matrix in
     v1 (editable UI is v2). Also §3.5, §8.8, §9.
  5. **New v1 scope:** Account↔Person link (**ADR-0002**, `users.individual_id`;
     oldest-ancestor fallback), self-authored living-member records, suggestions inbox +
     role-change requests, transactional email (verification + reset), white-label
     branding (`site_name`/`family_name`), per-user timezone, and a configurable security
     baseline (§3.5, §5, §8.7–8.10, §9).
  6. **New v1.x (additive, post-core-CRUD):** Member Profile + privacy-controlled contact
     fields + **Family Address Book** (default-deny, per-field sharing); merge/duplicate
     tools (§5).
  7. **Parking lot (§11):** MFA (TOTP), notification-email system, dynamic pan/zoom tree
     canvas, admin theme switcher, and the **Family Bunch** identity/API seam (reserved,
     not built).
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
<!-- Add new revisions above this line, newest first, when §11 change control approves a change to bump this Revision. -->

[↑ Back to Contents](#contents)
