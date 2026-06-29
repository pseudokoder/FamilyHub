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

_None._

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
