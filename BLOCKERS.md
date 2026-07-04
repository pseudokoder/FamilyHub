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

### [OPEN] WP4 nav brief says "Admin" is Curator+; the backend admin surface is Admin-only
- Date: 2026-07-03
- Raised by: FE
- Blocks: nothing critical — the app shell (`app/templates/base.html`) gates the
  user-menu "Admin" item on `current_user.is_admin` (true Admin), NOT Curator+ as
  the WP4 brief literally asked ("Admin (only if the current user is Curator/
  Admin per the role)"), so the link never 403s. That's the safe default, but it
  means Curators get no admin-menu entry at all right now, even though §10 makes
  Curator a real, elevated rung (it holds `revert`, i.e. the audit trail +
  restore/undo).
- Needs (BE must, or Wes must decide): pick one —
  1. Confirm the nav is right as built (Admin-only) and the brief's "Curator/
     Admin" phrasing was loose — nothing to change; OR
  2. Add a Curator-visible capability to gate a menu item on instead — most
     naturally the audit trail (`GET /api/activity`, already `role_required
     (Role.CURATOR)`) — so Curators get e.g. an "Activity" entry pointing at a
     real page, distinct from the Admin-only `/admin/*` panel.
  Every `/admin/*` HTML route and every `/api/admin/*` + `/api/suggestions`
  (GET/PUT) + `/api/role-requests` (GET/approve/deny) JSON route is hard-coded
  `@admin_required` (`app/services/authz.py`, `app/routes/admin.py`,
  `app/routes/api/admin_api.py`, `app/routes/api/inbox.py`) — loosening any of
  those to Curator+ is a §10 permissions-map change, not a template change, so
  it's BE's call either way.
- Status: OPEN.

### [OPEN] Home's "Recent Activity" needs a friendly, all-members feed; today it's Curator+ only
- Date: 2026-07-03
- Raised by: FE
- Blocks: nothing critical — `app/templates/dashboard.html` only renders the
  Recent Activity container for `current_user.has_role('curator')`; everyone
  else sees an honest static message instead of a feed that would 403. But the
  WP4 Home brief describes this section for every logged-in member ("Mom added
  a photo to …"), and the only endpoint that exists, `GET /api/activity`
  (`app/routes/api/activity.py`), is `@role_required(Role.CURATOR)` by design
  (ADR-0001 — it's the audit/write-control trail, which also carries
  restore/revert/security actions a Viewer or Contributor arguably shouldn't
  see). `app/static/js/home.js` already has the friendly action→verb /
  subject_type→noun phrasing ready (`ACTION_VERB`/`SUBJECT_NOUN`) — it just has
  nothing to call for non-Curators.
- Needs (BE must): add a `view`-permission-gated feed of *friendly, non-sensitive*
  creation/update events (new people, photos, stories — not deletes/reverts/
  security actions) that every logged-in member can call, OR confirm Curator+
  gating is the intended v1 answer and this is a documentation-only fix (update
  the Master Plan §4 Home description to say "Curator+" instead of "every
  member").
- Status: OPEN.

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
