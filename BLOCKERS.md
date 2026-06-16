# BLOCKERS — Cross-Builder Blocker Handoff Log

> **Two builders, one repo.** **Claude Code** owns the backend + the whole
> repo/infra; **Cowork** owns the front-end (Jinja templates, CSS, vanilla JS).
> A builder will sometimes hit a wall only the *other* builder can fix (Cowork
> finds a missing or wrong endpoint; Code finds the front-end needs a different
> data shape). This file is how that handoff happens without anyone faking a
> dependency. (Master Plan §7.)

## The protocol — read this, then the open items

1. **Start of every session:** read this file FIRST. If there's an `OPEN` item
   addressed to you, resolve it, mark it `RESOLVED` (keep the line — don't
   delete history), then start your normal work.
2. **Never fake or stub around a cross-boundary blocker.** That's what produced
   the hollow first build. Stop *that item*; continue other in-scope work if
   it's safe to.
3. **Log it here** as an `OPEN` entry with: date · raised-by (Code/Cowork) ·
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
- Raised by: Code | Cowork
- Blocks: <what can't proceed>
- Needs (the other builder must): <the exact action required>
- Status: <OPEN / RESOLVED on YYYY-MM-DD — how>
```

---

## Open items

_None._ WP1 is a backend-only work package (database foundation); **Cowork is
idle until the WP2 API contract is published** (Master Plan §7 build sequence),
so there are no cross-builder blockers right now.

---

## Forward notes (not blocking today, but the next builder must know)

### [OPEN] `users` table not yet aligned to Master Plan §3.5
- Date: 2026-06-16
- Raised by: Code
- Blocks: Nothing today. A future reconciliation in **WP2** (the auth/RBAC layer).
- Context: §3.5 specifies `users` with **email-as-login**, a `role` enum
  (`admin`|`member`), and `is_active`. WP1 deliberately **kept the existing
  table as-is** — username-login + an `is_admin` boolean — because that auth /
  admin / password-reset code is already built, tested, and is the Tier-1
  security hardening §7 says to *preserve*, and because §10 schedules the
  role/auth layer for WP2. (Decision confirmed with Wes during WP1 planning.)
- Needs (Code, in WP2): when building the §10 role scaffolding, decide
  username-vs-email login and migrate `users` to the §3.5 shape (add `role` +
  `is_active`, fold `is_admin` into `role`), updating auth/admin/user_service/
  the create-admin CLI/test fixtures together. Then mark this RESOLVED.

---

## Decision / deviation log (Master Plan reconciliation)

Recorded here per the WP1 instruction to "note any conflicts with the Master
Plan." These are **resolved decisions**, not blockers.

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
