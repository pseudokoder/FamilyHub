# ADR-0003: White-Label — Neutral Language, No Personal Data in the App

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** Wes Leiter (project owner)
- **Scope:** All of FamilyHub (v1 and v2), source + templates + UI copy + docs.
- **Supersedes:** none

## Context

FamilyHub is built as a **generic, forkable project first** — a public GitHub repository
anyone (including the author) instantiates with *their own* family data at runtime. The
author's own family is just one deployment among many.

It follows that **no specific family's personal data may appear in the running app or in
the technical build description**: not in code, templates, UI copy, config defaults, or the
plan's "how it's built" language. A build surfaced the problem — a login screen read
*"Forgot your password? Call or text Wes…,"* hardcoding a real name and an out-of-band reset
that also contradicts the self-serve email reset. This protects PII (a real name/contact in
a public repo is a leak) and keeps the project forkable and portfolio-ready.

**Nuance (important):** crediting the author and telling the project's origin story is
*encouraged*, not forbidden — that's how open-source projects work. The line is between
*credit/inspiration narrative* (fine) and *the app's own voice + build details* (must be
neutral).

## Decision

**Prohibited — no personal names or contact details** (phone, email, address) in:
1. The **default site UI copy** — the running app's own voice.
2. **Config defaults** and seed-of-record shipped with the app.
3. The **technical/plan language** describing *how the app is built* (schema, endpoints,
   architecture prose).

**Allowed — a personal name MAY appear** as:
4. **Explicit author credit / attribution** (e.g., README author line, LICENSE, CONTRIBUTORS).
5. **Project-inspiration / origin narrative** in docs ("what inspired this project"), clearly
   framed as background, not as the app's operative copy.

**Rules:**
6. All family-specific and branding/contact values in the app are **configuration or runtime
   data** (`site_settings`: `site_name`, `family_name`, admin-contact; or user records) —
   never hardcoded.
7. UI copy is **neutral and generic** — "Reset your password by email," "Contact your family
   administrator" — never naming an individual.
8. **Demo/seed data** may use clearly *fictional* names for development; such names must never
   leak into shipped UI chrome, copy, or defaults.

## Consequences

### Positive
- The app is genuinely forkable/white-label and portfolio-clean; no PII leaks into the app or
  its build docs; branding changes need no code edits.
- The author still gets clear credit and can tell the project's story.

### Effort / Enforcement
- One-time copy audit of existing templates (the login-reset copy is the first fix).
- Every builder prompt (FE and BE) carries the neutral-language rule; phase-gate review greps
  for hardcoded names/contact in the app surface before merge.

## Alternatives Considered
- **Hardcode the author's family "for now," generalize later** — rejected: leaks PII into a
  public repo, isn't forkable, and "later" tends never to come.
- **Ban the author's name everywhere, including credits** — rejected: over-broad; author
  attribution and the inspiration story are legitimate and valuable.

## Related
- Master Plan: white-label / config-driven branding (`site_settings`).
- ADR-0002 (Account↔Person link) — user/contact data is runtime, not source.
