# ADR-0003: Branding and Family Data Are Runtime Configuration

- **Status:** Accepted
- **Date:** 2026-07-03 *(rewritten for clarity 2026-07-05; decision unchanged)*
- **Deciders:** Wes Leiter (project owner)
- **Scope:** all deployment-specific values, v1 and v2.

## Context

FamilyHub is a white-label genealogy application: any family can deploy it with
their own data. During early builds, deployment-specific values — a family's
name and contact details — were found hardcoded in templates and configuration
defaults, coupling the codebase to a single deployment and placing personal
data in a public repository.

## Decision

All deployment-specific values are **runtime data, never source code**:

1. Branding (`site_name`, `family_name`) and the administrative contact address
   live in `site_settings` or instance configuration (e.g.,
   `MAIL_DEFAULT_SENDER`).
2. The application's UI copy is deployment-neutral (e.g., "contact your family
   administrator" rather than naming an individual).
3. Seed and demo data use clearly fictional names only.

## Consequences

- Any family can fork and deploy without code changes; rebranding is an
  administrative action, not a development task.
- The public repository carries no family's personal data; a copy audit at each
  phase gate keeps it that way.
- Minor indirection cost: templates and routes read branding from
  settings/configuration rather than literals.

## Alternatives Considered

- **Hardcode one family's values and generalize later** — rejected: couples the
  code to one deployment, leaks personal data into a public repository, and
  "later" reliably never comes.

## Related

- Master Plan §8 (decision 11), §3.5 (`site_settings`), §5 (admin branding).
- ADR-0002 (Account↔Person link) — user data is likewise runtime, not source.
