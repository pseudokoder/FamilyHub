# BLOCKERS — Cross-Builder Blocker Handoff Log

> **Two builders, one repo.** The **Backend Builder (BE)** owns the backend + the
> whole repo/infra; the **Frontend Builder (FE)** owns the front-end (Jinja templates,
> CSS, vanilla JS). A builder will sometimes hit a wall only the *other* builder can
> fix (the FE finds a missing or wrong endpoint; the BE finds the front-end needs a
> different data shape). This file is how that handoff happens without anyone faking a
> dependency. (Master Plan §7.)

## The protocol — read this, then the open items

1. **Start of every session:** read this file FIRST. If there's an `OPEN` item
   addressed to you, resolve it, mark it `RESOLVED` (keep the line — don't
   delete history), then start your normal work.
2. **Never fake or stub around a cross-boundary blocker.** That's what produced
   the hollow first build. Stop *that item*; continue other in-scope work if
   it's safe to.
3. **Log it here** as an `OPEN` entry with: date · raised-by (BE/FE) ·
   what's blocked · exactly what the other builder must do · status.
4. **Surface it in your end-of-session summary** so Wes sees it and knows which
   tool to spin up next.
5. **Distinct from "don't stop for permission":** a design *preference* → pick a
   reasonable option and keep going. A hard *dependency* on the other builder →
   log it here and flag it, never fake it.

Entry format:
```
### [OPEN|RESOLVED] <short title>
- Date: YYYY-MM-DD
- Raised by: BE | FE
- Blocks: <what can't proceed>
- Needs (the other builder must): <the exact action required>
- Status: <OPEN / RESOLVED on YYYY-MM-DD — how>
```

---

## Open items

### [OPEN] FE-6 rewrote `app/routes/admin.py` + touched a BE test file + `docs/openapi.yaml` — BE review at merge
- Date: 2026-07-06
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE must): review three things this session touched outside its own
  new files.
  1. **`app/routes/admin.py` — rewritten, thin-controller only.** No
     business logic moved: every mutation still goes through the existing
     `user_service`/`backup_service`/`settings_service`/`audit_service`
     calls verbatim, same as before. Seven view functions are new or
     changed (`dashboard`, `list_users`, `suggestions`, `role_requests`,
     `settings_console`, `backups`, `activity`); four are byte-for-byte the
     same logic as before, just re-ordered in the file (`create_user`,
     `edit_user`, `reset_password`, `site_settings`, `run_backup`,
     `download_backup`). The one BEHAVIOR change: `activity()`'s decorator
     moved from `admin_required` to `role_required(Role.CURATOR)` — brief-
     authorized (Curator holds `revert`; see the 2026-07-03 RESOLVED entry
     below that already pre-authorized this).
  2. **`tests/test_wp5_authz_alignment.py` — one BE-authored test file,
     touched, not a new FE file.** `/admin/activity` moved out of
     `ADMIN_ONLY_GET_ENDPOINTS` and into `CURATOR_PLUS_GET_ENDPOINTS`
     (alongside `/api/activity`, which that same list already tests
     identically) — a direct, necessary consequence of the Activity access
     change above, not incidental scope creep. Full suite re-run green
     (260/260) after the change.
  3. **`docs/openapi.yaml`** — the `Admin` tag block trimmed to the four
     legacy flows this session kept verbatim (`/admin/users/new`,
     `/admin/users/{user_id}/edit`, `/admin/users/{user_id}/reset-password`,
     `/admin/settings`, `/admin/backups/run`, `/admin/backups/{filename}/
     download`), each re-worded to note where it's superseded-but-still-
     reachable; seven `Views`-tag entries added/moved (`/admin`,
     `/admin/users`, `/admin/suggestions`, `/admin/role-requests`,
     `/admin/config`, `/admin/backups`, `/admin/activity`) — the brief-
     authorized "new/changed view routes → Views tag" rule.
  No schema, migration, or `/api/*` endpoint changed — every JSON call this
  console makes was already in the WP2 contract. Confirm none of this breaks
  any existing BE test (it doesn't — 260/260 green) and sign off at merge.
- Status: **RESOLVED 2026-07-06** — verified all three on `be-signoffs-pending-
  email` (off master, post-merge). (1) `app/routes/admin.py`: every mutating
  view (`create_user`, `edit_user`, `reset_password`, `site_settings`,
  `run_backup`) still calls only `user_service`/`backup_service`/
  `settings_service`/`audit_service`; the seven console views (`dashboard`,
  `list_users`, `suggestions`, `role_requests`, `settings_console`, `backups`,
  `activity`) are thin `render_template` shells with no direct DB access; the
  one behavior change, `activity()` gated by `role_required(Role.CURATOR)`
  instead of `admin_required`, matches the 2026-07-03 RESOLVED entry's
  pre-authorization. (2) `tests/test_wp5_authz_alignment.py`: `/admin/activity`
  is in `CURATOR_PLUS_GET_ENDPOINTS` alongside `/api/activity`, both covered by
  the same allow/deny parametrized tests. (3) `docs/openapi.yaml`: the `Admin`
  tag (lines 133-154) documents exactly the four kept legacy flows
  (`/admin/users/new`, `/admin/users/{user_id}/edit`,
  `/admin/users/{user_id}/reset-password`, `/admin/settings`,
  `/admin/backups/run`, `/admin/backups/{filename}/download`), each noting
  where it's superseded; the `Views` tag (lines 564-598) has the seven new/
  moved `/admin*` entries, `/admin/activity`'s response noting `403: Logged in
  below Curator`. Full suite green (260/260, confirmed this session). No
  follow-up needed.

### [OPEN] FE-5 added `app/routes/account.py` + `docs/openapi.yaml` Views entries — BE review at merge
- Date: 2026-07-06
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE must): review the new `account_bp` blueprint (`app/routes/
  account.py`: `GET /account` → Account & Security, `GET /account/
  contributions` → My Contributions) and its registration in
  `app/__init__.py`, plus the two matching `docs/openapi.yaml` Views-tag
  entries (and a third small edit: a `photo` query param added to the
  *existing* `/memories` Views entry, documenting the new `?photo=` deep-link
  support in `app/static/js/memories.js`) the FE-5 brief authorized FE to add
  on-branch. View-routing only — no business logic, schema, or `/api/*`
  endpoints changed; every field these pages read/write already shipped in
  the prior backend run (`ffe6cb1`). Two small additional touches, same
  transparency rule as prior sessions' one-line fixes: `app/forms/
  auth_forms.py` gained `render_kw` autocomplete attributes on
  `ChangePasswordForm`'s three password fields (brief-authorized,
  "template-only fix, allowed" — the only observable effect is the rendered
  HTML attribute) and `app/static/css/chronicle-app.css`'s shared
  `.chip-group` rule gained `flex-wrap: wrap` (a real 375px overflow bug this
  session's own 6-chip filter group exposed; re-verified People's existing
  3-chip filter still renders on one line). Confirm none of this breaks any
  existing BE test (it doesn't — 260/260 green) and sign off at merge time.
- Status: **RESOLVED 2026-07-06** — verified on `be-signoffs-pending-email`
  (off master, post-merge). `app/routes/account.py`'s `account_bp` (`GET
  /account`, `GET /account/contributions`) is view-routing only — both routes
  just `render_template` a shell, `@login_required`, no id in either URL;
  registered correctly in `app/__init__.py`. `docs/openapi.yaml`'s `/account`
  and `/account/contributions` Views entries match the routes exactly, and
  the `/memories` entry's `photo` query param documents the `?photo=` deep
  link `app/static/js/memories.js` supports. `app/forms/auth_forms.py`'s
  `ChangePasswordForm` has `render_kw={"autocomplete": ...}` on all three
  password fields (current-password/new-password x2) — template-only, no
  business-logic change. `app/static/css/chronicle-app.css`'s `.chip-group`
  rule has `flex-wrap: wrap` — layout-only. Full suite green (260/260,
  confirmed this session). No follow-up needed.

### [RESOLVED] FE-4 added `app/routes/memories.py` + `app/routes/search.py` + `docs/openapi.yaml` Views entries — BE review at merge
- Date: 2026-07-05
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE must): review the two new blueprints — `memories_bp`
  (`app/routes/memories.py`: `GET /memories`, `/memories/person`,
  `/memories/family`, `/memories/event`, `/memories/stories`,
  `/memories/stories/new`, `/memories/stories/<int:note_id>`) and `search_bp`
  (`app/routes/search.py`: `GET /search`) — and their registration in
  `app/__init__.py`, plus the matching `docs/openapi.yaml` Views-tag entries
  the FE-4 brief authorized FE to add on-branch. View-routing only — no
  business logic, schema, or `/api/*` endpoints changed. Confirm it doesn't
  break any existing BE tests (it doesn't — 239/239 green) and sign off at
  merge time.
- Status: **RESOLVED 2026-07-05** — reviewed at merge (already merged to
  master via PR #15). Both blueprints are view-routing only: every route just
  `render_template`s a shell page, no direct DB access, no new `/api/*`
  surface, no schema change. `app/__init__.py` registers both blueprints
  correctly; the seven `/memories*` + one `/search` OpenAPI Views-tag entries
  match the routes exactly. Full suite green post-merge. Sign-off complete;
  no follow-up needed.

### [RESOLVED] FE-4 added `app/static/css/style.css` cleanup — BE decides on deleting the file
- Date: 2026-07-05
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE should): per the FE-4 brief's Task 0 (owner directive, ADR-0004),
  the pre-Chronicle "elderly-first sizing" layer was stripped from
  `app/static/css/style.css` (oversized root font-size, jumbo buttons/inputs,
  a non-Chronicle hardcoded-blue focus ring/skip-link that duplicated
  `chronicle-main.css`'s own, plus several classes from the removed pre-WP1
  "Lite" photo/wiki app that had zero references left anywhere:
  `.btn-dashboard`, `.photo-card`, `.album-card`, `.photo-full`,
  `.infobox-card`, `.album-cover-placeholder`, `.photo-preview`,
  `.drag-ghost`). What's left (`.hero-banner`, `.hero-preview`, `.chip-group`,
  `#main-content:focus`) is everything still referenced by a current
  template. The file is now 40 lines, effectively a small residual file
  rather than a real stylesheet — BE's call whether to delete it outright
  and inline its remaining rules into `chronicle-app.css`, or leave it as is.
- Decision (BE, 2026-07-05): **delete it outright.** A 4-rule residual file
  that isn't even the app's main stylesheet earns its keep only as a place to
  find those 4 rules later — inlining them into `chronicle-app.css` (the one
  stylesheet every Chronicle template already loads) removes a whole file
  from the include graph for zero loss of clarity. Implemented this session:
  `app/static/css/style.css` deleted; `.hero-banner`, `.hero-preview`,
  `.chip-group`, `#main-content:focus` moved verbatim into
  `app/static/css/chronicle-app.css`; the one remaining `<link>` to
  `style.css` (`app/templates/base.html`) removed. Full suite still green.
- Status: **RESOLVED 2026-07-05** — deleted; rules relocated; sign-off above.

### [RESOLVED] FE-3 added `app/routes/tree.py` + `docs/openapi.yaml` Views entries — BE review at merge
- Date: 2026-07-05
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE must): review the new `tree_bp` blueprint (`app/routes/tree.py` —
  three thin view routes: `GET /tree`, `GET /tree/family/<int:family_id>`,
  `GET /tree/relationship`, each just rendering a shell template, same
  pattern as `app/routes/people.py`) and its registration in `app/__init__.py`,
  plus the three matching `docs/openapi.yaml` Views-tag entries the FE-3 brief
  authorized FE to add on-branch. View-routing only — no business logic,
  schema, or `/api/*` endpoints changed. Confirm it doesn't break any existing
  BE tests (it doesn't — 239/239 green) and sign off at merge time.
- Status: **RESOLVED 2026-07-05** — reviewed at merge (already merged to
  master via PR #13). `tree_bp`'s three routes are view-routing only —
  each renders a shell template and passes through query params
  (`family_id`, `a`/`b` for the relationship view) with no direct DB access,
  no new `/api/*` surface, and no schema change. The three Views-tag OpenAPI
  entries match the routes exactly. Full suite green post-merge. Sign-off
  complete; no follow-up needed.

### [RESOLVED] Person Page "Follow" action has no backend endpoint
- Date: 2026-07-04
- Raised by: FE
- Was blocking: nothing critical — the Person Page header's "Follow" button
  (wireframed and approved per the FE-2 brief) renders **disabled**, with a
  "coming soon" title attribute, per §5A's "never fake a control" rule. It is
  not wired to anything.
- Needs (BE should): decide whether "Follow a person" (a per-member subscription
  to updates on one individual) is in scope for v1 or deferred/cut. If it's in:
  a `POST/DELETE /api/individuals/{id}/follow` (or similar) endpoint + a
  `follows` join table (user_id, individual_id). If it's out: say so and FE will
  drop the button and its BLOCKERS reference instead of leaving it disabled
  forever.
- Decision (Wes, 2026-07-04): **park to v1.x.** Follow-a-person pairs naturally
  with the v2 notification-email system (Master Plan §11 v2 captures) and isn't
  useful on its own without it — out of v1 scope. No endpoint, no `follows`
  table, this session. Captured in the Master Plan §11 parking lot (Revision
  2.5.0).
- Status: **RESOLVED 2026-07-04** — parked, not built. Needs (FE, next
  session): remove the disabled "Follow" button and this BLOCKERS reference
  from the Person Page header.

### [RESOLVED] Home's "Latest Changes" needs a per-subject activity filter
- Date: 2026-07-04
- Raised by: FE
- Was blocking: nothing critical — the Person Page's Story tab has no "Latest
  Changes" card. `GET /api/activity/feed` (the friendly, all-members feed
  BE built for Home, BLOCKERS.md 2026-07-03) only accepts `?limit=`; it has no
  `subject_type`/`subject_id` filter, so there is no way to ask "recent
  activity about THIS person" without re-deriving Curator+-only data the
  member feed deliberately doesn't expose. Per §5A, the card is omitted
  entirely rather than showing an unfiltered or faked feed.
- Needs (BE should): add optional `subject_type`/`subject_id` query params to
  `GET /api/activity/feed` (same safe-creates-only filter as today, just
  additionally scoped to one subject) — mirrors the pattern every other list
  endpoint already uses (`/api/events`, `/api/notes`, `/api/media`,
  `/api/citations`). Once it exists, FE adds the Story-tab card back — no other
  change needed.
- Status: **RESOLVED 2026-07-04** — `GET /api/activity/feed` now accepts
  optional `subject_type`+`subject_id` (both or neither; 400 if only one is
  given or the type is unknown), additionally scoping `write_control.member_feed`
  to one subject while keeping the same safe-creates-only filter. Documented in
  `docs/openapi.yaml`; covered in `tests/test_wp5_member_feed.py` (filtered vs.
  unfiltered counts, excluded actions stay excluded when filtered, both
  validation-error cases). Needs (FE, next session): add the Story-tab "Latest
  Changes" card pointed at `?subject_type=individual&subject_id={id}` — no
  further backend work needed.

### [RESOLVED] WP4 nav brief says "Admin" is Curator+; the backend admin surface is Admin-only
- Date: 2026-07-03 (raised) → 2026-07-03 (resolved)
- Raised by: FE
- Was blocking: nothing critical — `app/templates/base.html` gated the user-menu
  "Admin" item on `current_user.is_admin` (true Admin), not Curator+ as the WP4
  brief literally asked, so the link never 403'd; it just meant Curators saw no
  admin-menu entry at all, even though §10 makes Curator a real, elevated rung
  (it holds `revert`).
- Decision (BE, option 1 of the two offered): **the Admin-only nav item is
  correct as built — leave it Admin-only.** Every capability behind `/admin/*`
  and `/api/admin/*` (user management, settings, backups, suggestion/role-request
  triage) is genuinely `administer`-scoped per the permissions map
  (`app/services/permissions.py`) — Curator does NOT hold `administer`, only
  `revert`. Loosening the panel to Curator+ would be wrong, not just untidy.
- What DID change (so the gate is no longer even loosely tied to the legacy
  boolean): `admin_required` in `app/services/authz.py` is now
  `permission_required(permissions.ADMINISTER)` — the same permissions-as-data
  layer as everything else — instead of a bespoke `role_required(Role.ADMIN)`.
  `current_user.is_admin` still exists (template display / back-compat) but no
  route gates on it. See `tests/test_wp5_authz_alignment.py` for the full
  allow/deny matrix.
- Curator's distinct capability is real and already exposed: `GET /api/activity`
  (the full audit trail), `POST /api/restore`, `POST /api/audit/<id>/revert` —
  all `permission_required(permissions.REVERT)`, Curator+. **FE may add a
  Curator-visible nav entry pointing at these** whenever it builds an activity/
  audit HTML page — no backend work needed, the endpoints already exist and are
  correctly gated. Not blocking; template-only whenever FE gets to it.
- Status: **RESOLVED 2026-07-03.**

### [RESOLVED] Home's "Recent Activity" needs a friendly, all-members feed; today it's Curator+ only
- Date: 2026-07-03 (raised) → 2026-07-03 (resolved)
- Raised by: FE
- Was blocking: nothing critical — `app/templates/dashboard.html` only rendered
  the Recent Activity container for `current_user.has_role('curator')`; everyone
  else saw a static message instead of a feed that would 403. The only endpoint
  that existed, `GET /api/activity`, is `@role_required(Role.CURATOR)` by design
  (ADR-0001 — the audit/write-control trail, which also carries security actions
  a Viewer or Contributor shouldn't see).
- Fix (BE): new `GET /api/activity/feed` (`app/routes/api/activity.py`,
  `permission_required(permissions.VIEW)` — any logged-in member). Backed by
  `write_control.member_feed()`: a DIFFERENT, narrower view over the SAME
  `audit_log` table — only `create` events on `individual`/`media`/`note`
  (new people/photos/stories), rendered as a friendly sentence ("Jane added a
  photo: Family reunion 1962"), with since-(soft-)deleted subjects silently
  skipped. Deletes, reverts, updates, and every account/security action
  (`user`/`backup` subject types) never appear — proven in
  `tests/test_wp5_member_feed.py`, including a check that the full Curator+
  trail still sees what the friendly feed excludes. Documented in
  `docs/openapi.yaml` (`MemberActivityEntry` schema).
- Needs (FE, next front-end session): point `app/static/js/home.js`'s existing
  `ACTION_VERB`/`SUBJECT_NOUN` rendering at `GET /api/activity/feed` (it already
  returns pre-formatted `text` per row, so the JS may not even need the noun/verb
  maps anymore — FE's call), and loosen `dashboard.html`'s Recent Activity
  container from `current_user.has_role('curator')` to any authenticated member.
  Template/JS-only; no further backend work required.
- Status: **RESOLVED 2026-07-03.**

### [RESOLVED] Found + fixed: Bootstrap was silently CDN-only, dead on arrival under the CSP
- Date: 2026-07-03
- Raised by: FE
- Was blocking: nothing filed an issue — this was a **pre-existing bug** WP4
  testing surfaced, not something introduced this session. Manually loading any
  authenticated Bootstrap page in a real browser (not pytest, which never
  fetches `<link>`/`<script>` tags) showed Bootstrap's CSS/JS failing to load
  from `cdn.jsdelivr.net`, blocked by the strict CSP (`style-src`/`script-src
  'self'`, `app/__init__.py`). Every Bootstrap page — admin panel included —
  was unstyled and had no working dropdowns/collapse for anyone testing in a
  browser, contradicting `base.html`'s own comment ("served from the installed
  package — no CDN").
- Root cause: `BOOTSTRAP_SERVE_LOCAL` was never set, so Bootstrap-Flask
  defaulted to `False` (CDN mode).
- Fix (FE, this session): added `BOOTSTRAP_SERVE_LOCAL = True` to
  `app/config.py`, with a comment explaining why. Verified in a real browser
  (Bootstrap CSS/JS/Popper now load from `/bootstrap/static/...`, same-origin)
  and the full suite stays green (207/207).
- Also touched, same session, same transparency rule as the FE `main.py` entry
  above — small, mechanical, needed for the WP4 nav to work at all, not a
  design decision:
  - `app/__init__.py` — added an `app.context_processor` injecting `brand`
    (site_name/family_name) into every template, so the navbar brand doesn't
    require every route to pass it in explicitly.
  - `run.py` — reads `PORT` from the environment (default 5000 unchanged)
    purely so local dev can pick a free port; no behavior change when unset.
- Needs (BE should): spot-check `BOOTSTRAP_SERVE_LOCAL` at PR review — it's a
  one-line config fix, but it changes what every existing Bootstrap page (incl.
  admin) actually looks like in a browser for the first time.
- Status: **RESOLVED 2026-07-03** — fixed, tested (pytest green + manual
  browser verification via the preview tool).

### [RESOLVED] FE touched `app/routes/main.py` — BE review at merge

- Date: 2026-06-28
- Raised by: FE
- Blocks: nothing (safe to merge once BE reviews)
- Needs (BE must): review the one-line routing change in `app/routes/main.py`
  (`render_template("index.html", ...)` → `render_template("dashboard.html", ...)`
  inside the `if current_user.is_authenticated:` branch). This is view-routing
  only — no business logic, no schema, no endpoints changed. Confirm it doesn't
  break any existing BE tests and sign off at merge time.
- Status: RESOLVED 2026-06-29 — tests green (139/139); view-routing only, no
  business logic/schema/endpoints changed; BE sign-off complete.

### [RESOLVED] Provided files for the docs reconciliation were missing from the tree
- Date: 2026-07-03 (raised) → 2026-07-03 (resolved)
- Raised by: Code
- Was blocking: **Task A** of the docs-reconciliation run — committing the two
  Wes-authored files **as-is** (the brief says *do not rewrite* them, so Code did
  not author them):
  1. `docs/adr/0002-account-person-link.md` (ADR-0002, Accepted)
  2. `docs/CONTEXT_LOG.md` (cross-thread operational log)
- Status: **RESOLVED 2026-07-03** — Wes placed both files; Code committed them
  unmodified. The ADR index and Master Plan v2.0.0 references to ADR-0002 now
  resolve; the CONTEXT_LOG's drift list (#1–4) matches the applied reconciliation.

### [RESOLVED] wp3-frontend-crud (Chronicle FE work) merged forward onto master
- Date: 2026-07-03
- Raised by: FE
- Was blocking: starting **WP4** — the FE builder was told to branch `wp4-fe-shell`
  off `master`, but the prior WP3 Chronicle front-end work (public `index.html`,
  `dashboard.html`, `chronicle.js`, self-hosted fonts/images, `FRONTEND_DESIGN.md`)
  was sitting unmerged on `wp3-frontend-crud`, branched before the WP3 backend-gaps
  and WP3 backend-admin work landed on master.
- Needs (BE should): spot-check the merge at PR review — `docs/MASTER_PLAN.md` and
  this file were the only textual conflicts (both doc-only; resolved by keeping
  master's reconciled v2.0.0 plan and carrying forward the one Wes-approved parking-lot
  entry the FE branch had added). No app code conflicted.
- Status: **RESOLVED 2026-07-03** — merged `origin/master` into a new `wp4-fe-shell`
  branch created from `origin/wp3-frontend-crud`; conflicts resolved as above; full
  suite still green post-merge (see DEVDIARY_FE.md).

---

## Forward notes (not blocking today, but the next builder must know)

### [RESOLVED] No PUT for an active `family_children` row — editing pedigree_type/child_order works, but leaves a two-entry audit trail
- Date: 2026-07-04
- Raised by: FE
- Was blocking: nothing — the Relationships tab's "Edit" action on a child link
  (change pedigree_type or birth order) worked correctly, just via DELETE +
  re-POST (a real, intended `family_service.add_child` restore path, not a
  stub), leaving a two-entry audit trail for what is, from the member's point
  of view, a single edit.
- Needs (BE, whenever convenient): a `PUT /api/families/{family_id}/children/{child_id}`
  that updates `pedigree_type`/`child_order` on an active link directly, so the
  audit trail records one `update` instead of a `delete` + `create` pair.
- Status: **RESOLVED 2026-07-04** — added `PUT /api/families/{family_id}/children/{child_id}`
  (`family_service.update_child`, Contributor+): updates an ACTIVE link in
  place, producing exactly one `update` audit row with a real before -> after
  snapshot (`write_control.log_update` gained an optional `subject_id` override
  for composite-key rows like this one, which have no single `.id` column).
  404 on a link that's missing or already soft-deleted. Documented in
  `docs/openapi.yaml`; covered in `tests/test_api_families.py` (happy path +
  audit-row shape, 404 missing/deleted, RBAC deny). Needs (FE, next session):
  swap the Relationships tab's edit flow from DELETE+POST to this one PUT call.

### [RESOLVED] `users` table aligned to Master Plan §3.5 + §10 RBAC
- Date: 2026-06-16 (raised) → 2026-06-17 (resolved)
- Raised by: Code
- Was blocking: the WP2 auth/RBAC layer.
- Context: §3.5 specifies `users` with **email-as-login**, a `role`, and
  `is_active`. WP1 deliberately kept the old username-login + `is_admin` shape to
  preserve the tested Tier-1 hardening (§7), deferring the change to WP2 per §10.
- Status: **RESOLVED 2026-06-17 (WP2).** `users` now has `email NOT NULL UNIQUE`
  (the login key), a four-rung `role` (GUEST/USER/POWER_USER/ADMIN — §10), and
  `is_active`; `username` + the `is_admin` column are dropped (`is_admin` lives on
  as a computed property so existing checks keep working). The data migration maps
  `is_admin=1 → 'admin'`, else `'user'`. All permission checks now route through
  the single `app/services/authz.py` layer (§10 anti-lock-in). The hardening
  (bcrypt, CSRF, rate limiting, signed single-use reset tokens, vague errors,
  open-redirect guard) is unchanged and its tests stay green — only the login
  *identifier* moved from username to email. Migration:
  `8f1e6fa904a3_users_email_login_role_is_active_wp2_.py`.

---

## Decision / deviation log (Master Plan reconciliation)

Recorded here per the WP1 instruction to "note any conflicts with the Master
Plan." These are **resolved decisions**, not blockers.

### [RESOLVED] Adopted feature-branch-per-WP workflow
- Date: 2026-06-18 · Raised by: Wes (management)
- Change: per-WP branches off master; red tests allowed on-branch; merge to master
  only when green (CI gate); FE may edit docs/openapi.yaml on-branch w/ Code approval
  at merge; Wes integrates.
- Rationale: contract-first + trunk-protection best practice; contains WIP red tests
  without weakening the Definition of Done on master.
- Status: RESOLVED 2026-06-18 — docs updated; wp3-frontend-crud branch created.

### [RESOLVED] `audit_log` kept even though it's not in the §3 table list
- Date: 2026-06-16 · Raised by: Code
- The §3 schema lists 15 tables; `audit_log` isn't one of them. It was kept as
  preserved security infrastructure (it backs the admin activity trail and the
  user_service audit rows, and it's the §9 Tier-2 "audit logging" rung). It is
  additive and MySQL-portable, so it locks nothing in.
- Status: RESOLVED 2026-06-16 — kept by design; documented in DEVDIARY_BE.

### [RESOLVED] `site_settings` columns renamed to the §3.5 names
- Date: 2026-06-16 · Raised by: Code
- The old table used `key`/`value`; §3.5 specifies `setting_key`/`setting_value`.
  Renamed to match the spec exactly (one-line change in `settings_service`),
  since there was no preserved-auth reason to keep the old names. Clean baseline,
  no data to migrate.
- Status: RESOLVED 2026-06-16.

### [RESOLVED] CLAUDE.md reconciled to the Master Plan
- Date: 2026-06-16 · Raised by: Code
- `CLAUDE.md` still described the superseded "Lite" photo/blog/wiki app and
  claimed all features were built. Conflicts found and fixed in this session:
  the "Lite" name (Master Plan: never "Lite"; v1 = "Full"); the photo/blog scope
  (→ GEDCOM-7 "one database, many views"); the "all six features built" status
  (→ WP1 re-foundation); "Claude Code builds the app" (→ two builders: Code +
  Cowork); single `DEVDIARY.md` (→ BE/FE split); "Next: deploy to Lightsail"
  (→ WP roadmap; deploy is WP5); "push to GitHub" (→ commit only, Wes pushes).
  The Master Plan governs; CLAUDE.md now points to it as the source of truth and
  encodes this blocker protocol.
- Status: RESOLVED 2026-06-16.
