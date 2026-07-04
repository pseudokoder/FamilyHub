# FamilyHub — Context Log

> **What this is:** operational facts, environment settings, and gotchas that keep
> getting re-learned across Cowork threads — plus a co-manager thread-startup
> checklist and a running ledger of decisions. Read this FIRST in a new thread.
>
> **What this is NOT:** decisions with trade-offs (those are ADRs in `docs/adr/`) or
> unbaked ideas (those are the Parking Lots in Master_Plan §11 / FRONTEND_DESIGN).
> This log is the *what-is* + the *what-we-decided* index.

---

## ★ Co-manager thread-startup checklist (do this before any work)

1. Read this Context Log top to bottom.
2. Read the **ENTIRE** `docs/MASTER_PLAN.md`, cover to cover — not just selected
   sections. It is the source of truth; do NOT reconstruct it from chat memory. (Also
   read `docs/FRONTEND_DESIGN.md` if the task is front-end.)
3. Skim `docs/adr/` index for prior decisions.
4. Check `BLOCKERS.md` for open cross-builder items.
5. Only then write builder prompts or wireframes.

## ★ Master Plan orientation cheat-sheet (the durable facts)

- **Product:** GEDCOM-7-compliant genealogy DB + FamilySearch-style CRUD site.
  v1 = "Full" (Flask/Python/SQLite/SQLAlchemy); v2 = "Enterprise"
  (Java/Spring Boot/Angular/MySQL/Docker).
- **Core principle (§2):** One Database, Many Views. No feature owns private data.
- **Schema (§3) is GEDCOM-7-aligned by design:** tables map to INDI/FAM/PLAC/SOUR/
  REPO/OBJE/NOTE + GEDCOM event tags. `gedcom_xref` columns are **nullable, reserved
  for future import/export** (never durable keys). Polymorphic attachment
  (`subject_type`+`subject_id`) is what makes "everything is a view" work. Dates keep
  BOTH original GEDCOM string + sortable value. Standard SQL only (portable to MySQL).
- **v1 scope = essential subset (§5/§8).** Deferred to v2 (§3.6, additive, no lock-in):
  ASSO (associations), SUBM, video/audio, merge duplicates, and **GEDCOM import/export
  (WP6, tentative v1 / firm v2).**
- **Roadmap (§6):** WP1 DB ✅ · WP2 backend CRUD + API contract ✅ · WP3 frontend (active,
  `wp3-frontend-crud`) · WP4 views + search · WP5 deploy (AWS Lightsail) · WP6 GEDCOM
  (tentative v1 / firm v2).
- **RBAC ladder (§10):** four roles, one central authorization layer (anti-lock-in).
- **Change control (§11):** Tier 1 = Master_Plan (BE-owned; Wes approves; SemVer bump +
  Revision History line). Tier 2 = FRONTEND_DESIGN.md (FE-owned). Two parking lots.
- **Doc ownership (§7 RACI):** Master_Plan, README, openapi.yaml, DEVDIARY_BE = **BE**.
  FRONTEND_DESIGN, DEVDIARY_FE = **FE**. BLOCKERS = shared. §5B is intentionally EMPTY.
- **Security (§9):** password reset + hashing + rate-limit already MVP tier; RBAC +
  audit logging = Tier 2; MFA = Tier 3 (v2).

## ★ Doc-stewardship standard (put in EVERY builder prompt)

The BE Builder owns repo docs (Master_Plan, README, openapi.yaml, DEVDIARY_BE) and MUST
keep them to the **original Opus-4.8-grade standard** — accurate at every WP boundary,
professionally written, never describing removed features, versioned per §11. Do not let
doc quality regress on smaller models.

## ★ CURRENT BUILD STATE (as of 2026-07-03)

**Design phase: COMPLETE.** Every v1 screen was wireframed and approved with Wes (Person
Page, Tree, Home, People, Memories, Search, User area, Admin). **Build phase: in progress.**

### Prompt ledger — status of every builder run

| Run | Scope | Status |
|---|---|---|
| BE-1 | Docs reconciliation (Master Plan → v2.0.0, ADR index) | ✅ merged |
| BE-2 | Foundation + ◆ endpoints (schema, RBAC rename, audit/soft-delete/revert, account↔person, pedigree/relationship/stats/on-this-day/historical/list-item/capture-date) | ✅ merged + verified |
| BE-3 | Transactional email + security hardening, Suggestions inbox, admin actions | ✅ merged + verified |
| FE-1 | App shell + Home + People | ✅ merged (was Bootstrap + had a hardcoded name → fixed by FE-fix) |
| BE-fix | ADR-0003 commit + Master Plan/README + Context Log clarify + 2 blockers (admin authz → role model; member-safe activity feed) | ✅ merged |
| FE-fix | Chronicle authenticated base + reskin shell/Home/People + copy neutralization | 🔄 RUNNING (branch `wp5-fe-chronicle`) |

### Remaining work packages (the plan ahead)

- **FE-2** — Person Page (6 tabs), native Chronicle.
- **FE-3** — Tree (vertical Pedigree · Family Group · Relationship View).
- **FE-4** — Memories (album views) + Search (quick + Advanced).
- **FE-5** — User area (My Contributions dashboard + Account & Security).
- **FE-6** — Admin console (Dashboard · Users · Suggestions · Settings · Backups · Activity).
- **BE WP4 view endpoints** as FE needs them (Memories album filters, any search facets) —
  check `openapi.yaml` first; add only what's missing.
- **Late-v1 passes:** accessibility/elderly/§5B constraints; **WP5 deploy** (AWS Lightsail);
  **WP6 GEDCOM** decision gate (tentative v1, firm v2).
- **v1.x (additive):** Family Address Book + member profile contact fields; merge/duplicate.
- **v2:** Fan Chart, dynamic pan/zoom tree canvas, MFA/TOTP, notification-email system,
  editable-roles UI, admin theme switcher, Family Bunch (separate app), GEDCOM import/export.

### Immediate next steps for the incoming thread

1. **Verify FE-fix + BE-fix once merged** (copy sweep truly name-free; ADR-0003 committed;
   admin endpoints 403 correctly by role; Chronicle renders on the logged-in app; member-safe
   activity feed live). Verification = fetch the repo, read the actual code/docs, check vs
   plan/ADRs/contract. (raw.githubusercontent CDN caches ~5 min — re-fetch if stale.)
2. **Draft FE-2 (Person Page)** — native Chronicle, wired to `openapi.yaml`.
3. Continue FE-3 → FE-6, verifying each merge.

## ★ DECISIONS (this session) the Person Page + later FE prompts must honor

- **RBAC ladder:** Viewer / Contributor / Curator / Admin. Admin menu/endpoints = Admin only.
- **Chronicle styling is applied NOW** during the build; only accessibility/elderly/§5B
  *constraints* are deferred to end-of-v1. §5A depth bar always holds (no hollow stubs).
- **Global nav:** Home · Tree · People · Memories · Search + user menu (Account & Security,
  Suggest an idea, Admin [Admin only], Log out). Brand from `site_settings`.
- **Person Page — 6 tabs, order:** Story · Relationships · Timeline · Photos · Details ·
  Sources. Story = read view; Details = the CRUD workbench. Inner bio card = "Life Sketch."
  Header: portrait + name + lifespan + ID, with View Tree / View Relationship / Follow.
  Story right rail = **slim Timeline** (fills desktop height, internal scroll, drops below on
  narrow); main column stacks Life Story → Photos → Family → Name Meaning → Vitals → Latest
  Changes → Sources (full cards). Timeline (full tab) = age-spine + life chapters + migration
  thread, color-coded Life/Family/World events, "N Sources" badges. **ASSO "Other
  Relationships" = v2** (core family relationships stay v1).
- **Tree v1:** vertical Pedigree (horizontal toggle = reserved v2 seam) · Family Group sheet ·
  Relationship View (plain-English label + chain). **Fan Chart = v2.** Person is a GRAPH;
  click-to-recenter; lazy subtree fetch is the v2-canvas seam.
- **Home:** Quick Add, warm On This Day, member-safe Recent Activity, small growth stat strip.
- **People:** find/filter(All/Living/Deceased/Surname)/sort/paginate; list row = name +
  birth–death year + primary place; depth-complete Register form.
- **Memories:** one photo store, album VIEWS (By Person · By Family · By Event · Chronological
  by capture-date). Views are cheap filters; don't cut for cost.
- **Search:** quick nav (people + families) + Advanced multi-field.
- **User area:** Dashboard (My Contributions) + Account & Security — PM-friendly password
  fields (autocomplete tokens, no paste-block), self-serve email reset + verification, MFA
  TOTP seam (v2), Delete = anonymize contributor + keep records/audit, per-user timezone,
  role badge + "Request role change" → admin inbox.
- **Admin:** role-filtered Dashboard (counts/storage/queues) · Users (read-only RBAC matrix +
  reset password + secure change-email + view profile) · Suggestions (chronological inbox →
  prioritized queue) · Settings (config/white-label branding; NO logged-in landing selector;
  fallback root = oldest ancestor; security knobs; email config; public-page tool = v1 build
  LAST) · Backups (DB backup/restore v1; GEDCOM v2) · Activity (audit_log + revert).

## ★ Verified endpoint names (on master — but always confirm against openapi.yaml)

`/api/individuals` (+ `/{id}/names`), `/api/search`,
`/api/individuals/{individual_id}/pedigree`, `/api/individuals/{a_id}/relationship/{b_id}`,
`/api/stats`, `/api/on-this-day`, `/api/historical-events`, `/api/activity`, `/api/restore`,
plus BE-3 suggestions/role-request/admin/change-email routes (see `openapi.yaml`).

## ★ Model-selection guidance (recommend ONE per prompt, set before the run)

- Docs / architecture / security / algorithms → **Opus high** (or Sonnet high).
- Routine CRUD / template wiring → **Sonnet medium**.
- Design-system foundation work (e.g., the Chronicle base) → **Sonnet high**.

---

## 2026-07-03 · CLARIFICATIONS (Chronicle styling + author-name nuance)
- **Chronicle styling is applied DURING the build, not deferred.** Only the
  accessibility/elderly/§5B visual *constraints* are deferred to end-of-v1 (they can gate; the
  styling cannot). Authenticated pages get the Chronicle look as they are built.
- **Author name nuance (ADR-0003):** the author's name is allowed for credit/attribution and
  the project-inspiration story in docs, but NOT in the app's UI copy, config defaults, or the
  technical/plan build-detail language.

## 2026-07-03 · PROCESS conventions (co-manager ↔ builder workflow)
- **Embed verbatim doc content in prompts.** When a prompt must land a doc committed as-is
  (ADR, Context Log, etc.), the co-manager embeds the full content in the prompt so the
  builder writes it. Never ask Wes to hand-place files — slow on the MacBook Air; it caused
  a blocker on BE Prompt 1.
- **Prompts are 100% copy-paste-ready.** The prompt contains ONLY text meant for the
  Builder. All Wes-facing meta (model/effort recommendation, coaching, run notes) goes in
  the Cowork chat, never in the prompt.
- **Builders do NOT read the whole Master_Plan.** The co-manager distills what a task needs
  into the prompt and points to specific sections/ADRs. Cover-to-cover reading of
  MASTER_PLAN.md is a Co-Manager-thread startup step ONLY.
- **Division of labor / cost.** All thinking + doc authoring (README, Master_Plan text,
  ADRs, Context Log, contributor docs) happens in the Co-Manager thread (Opus 4.8). Builders
  execute at low token cost on a fast model: commit doc content verbatim and write code. Aim
  for low cost at the maximum reasonable performance.
- **One model per prompt.** Model/effort is set once before a run and cannot change
  mid-execution. The co-manager recommends a single model/effort per prompt so Wes can start
  it and walk away.

---

## 2026-07-03 · Design-session decisions (Person Page + Tree + Home/People + Memories/Search + User area + Admin)

Wireframes approved with Wes this session. **Targets** = where each must be committed.

**Person Page — 6 tabs approved.** Order: **Story · Relationships · Timeline · Photos ·
Details · Sources** (edit tab trails; presentation leads). "Overview"→**Story**; inner
card "Life Story"→**Life Sketch**. Details = the CRUD workbench; Story/About = read view.
Timeline: age-spine + life chapters + migration thread (improve on FamilySearch), slim
rail on Story that scrolls. → *FRONTEND_DESIGN + Master_Plan feature map.*

**Tree — v1 = Pedigree (VERTICAL default; horizontal toggle staged for v2) · Family
Group · Relationship View.** **Fan Chart → v2** (was v1 in §5 — DRIFT, see below).
Dynamic pan/zoom canvas → v2 (reserve lazy-subtree fetch on ◆1). Person node = a GRAPH,
not a linked list. → *Master_Plan + FRONTEND_DESIGN.*

**User area:** Dashboard (My Contributions) + Account & Security. PM-friendly password
fields (autocomplete tokens, no paste-block). **Self-serve email reset + verification =
Option A (transactional email in v1).** MFA = TOTP, v2. Delete Account = anonymize the
contributor, keep records + audit. Per-user timezone override. Role badge + "Request role
change" (→ admin inbox). Profile + privacy-controlled contact fields + **Family Address
Book = v1.x** (kept in FamilyHub, not a separate app; default-deny per-field sharing).

**Admin console tabs:** Dashboard (role-filtered curator stats — counts, storage/cost,
queues; via ◆5) · Users (RBAC matrix + reset password + admin email-change w/ out-of-band
verify + view profile) · Suggestions (chronological inbox → prioritized queue) · Settings
(config/white-label branding; NO logged-in landing selector; fallback tree root = oldest
ancestor auto) · Backups (full DB backup/restore v1; GEDCOM in/out v2) · Activity
(audit_log + revert).

**New features to capture in Master_Plan (Tier-1) / parking lot:**
- Suggest-an-idea → admin inbox (v1). Role-change requests → admin inbox (v1).
- **Account↔Person link = ADR-0002** (linchpin: tree roots on your own node; self-edit
  your record; address book; future social seam).
- Living members author their OWN enduring record (profession, achievements, "how
  remembered") = v1 core via account↔person link.
- **White-label / config-driven branding** (site_name/family_name feed header + Chronicle
  masthead) so the app is forkable/rebrandable. (Note: `site_settings` table already exists.)
- **Family Bunch** = separate future social app (present-tense life sharing); reserve an
  identity/API seam; do NOT build in v1.
- Admin **theme switcher** (predetermined designs) → v2 parking lot.

## 2026-07-03 · DRIFTS between this session and Master_Plan — reconcile in the ADR-0001 Master_Plan update (Tier-1)

1. **ADR-0001 (write-control):** change-history/restore is DEFERRED to v2 in §3.6/§8, but
   ADR-0001 puts **audit_log + soft-delete + revert in v1**. ADR-0001 supersedes → bring
   into v1 scope. (Recommend MAJOR bump — scope/schema-altering.)
2. **Fan Chart:** §5 lists it as v1 ("pedigree + fan chart"); we moved it to **v2**. Update §5.
3. **Associations (ASSO / "Other Relationships"):** RESOLVED — **defer to v2** (matches
   §3.6). The Person Page "Other Relationships" section (non-family: apprenticeship,
   employment, godparent, etc.) is v2. Core family relationships (parents/spouses/
   children/siblings via FAM links) STAY v1 — the Relationships tab remains.
4. **RBAC rename:** CONFIRMED — **Viewer / Contributor / Curator / Admin** ("Curator"
   replaces "Power User"; replaces §10's GUEST/USER/POWER USER/ADMIN). MINOR bump.

## 2026-07-03 · ADR status
- **ADR-0001** — Write-control model (post-moderation: RBAC + audit + soft-delete +
  revert). Accepted, merged to master via PR. Master_Plan update PENDING (see drift #1).
- **ADR-0002** — Account↔Person link. DRAFTED + approved by Wes; commit via next BE prompt.
- GEDCOM-7 alignment does NOT need an ADR — already baseline in Master_Plan §3/§3.6/§6.

---

## 2026-07-01 · master is protected — all changes go through a PR
- `master` rejects direct pushes. Rule: *changes must be made through a pull request*,
  and **2 of 2 required status checks** must pass before merge.
- Land anything on master: push a branch → PR into `master` → 2 checks green → merge →
  (optionally) delete branch. Wes is repo owner and **may self-merge**.
- *Why it matters:* `git push origin master` fails with `GH013: Repository rule
  violations`. Expected, not a bug.

## 2026-07-01 · repository coordinates
- Repo: `github.com/pseudokoder/FamilyHub` (public). Default branch `master`; active
  `wp3-frontend-crud`. Source of truth = GitHub raw URLs, never a local copy.

## 2026-07-01 · branch-per-WP workflow
- Each WP on its own branch off master. Red tests OK on-branch. Merge to master only when
  CI green. **Wes pushes/merges.**

## 2026-07-01 · documentation ownership lanes
- Decisions (ADRs) + plans originate in the management lane (Wes + co-manager). Builders
  execute to the outcome via curated prompts; they don't author/approve docs. Doc commits
  are made by the owning builder (per §7 RACI) at Wes's direction. Three-part memory:
  ADRs = decisions · Parking Lots = ideas · Context Log = operational facts (this file).

## 2026-07-01 · Cowork does not auto-read CLAUDE.md
- The co-manager brief is pasted into each new thread by hand. Key docs are read on
  demand from GitHub, not assumed.
