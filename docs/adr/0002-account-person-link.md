# ADR-0002: Account ↔ Person Link

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** Wes Leiter (project owner)
- **Scope:** FamilyHub v1 "Full" (Flask/SQLite/SQLAlchemy); notes for v2 "Enterprise".
- **Supersedes:** none

---

## Context

FamilyHub has two separate record types that both describe people:

- **`users`** — the application-layer authentication record (login, password hash,
  role). Per Master Plan §3.5 this is deliberately *not* GEDCOM; it serves the website's
  own needs.
- **`individuals`** — the GEDCOM-7 INDI record (§3.1): a person in the family tree.

A living family member is normally *both*: they log in (a `user`) **and** they are a
person in the tree (an `individual`). Nothing currently connects the two records. That
gap blocks several decided features:

- The Tree can't default its root to "you."
- A member can't be scoped to **edit their own record**.
- The **Family Address Book** (v1.x) can't join a member's shareable contact info to
  their person.
- Living members can't author their **own enduring genealogy record** (profession,
  achievements, "how I want to be remembered").
- There is no clean identity seam for a future **Family Bunch** companion app.

## Decision

Add a **nullable one-to-one link** from a user account to its person node:

- `users.individual_id` → `individuals.id` (nullable FK), **or** a dedicated link table
  if a cleaner separation is preferred at build time.
- **Cardinality:** one `user` links to at most one `individual`; an `individual` has zero
  or one linked `user` (most persons — the deceased — have none).
- The link is **nullable**: a brand-new member (or a view-only relative/friend) may have
  no linked person yet. When unlinked, the Tree falls back to the site default root
  (**oldest ancestor**, per the Settings decision).
- **Admin can set/verify** the link; **changes are written to `audit_log`** (per ADR-0001).

## Consequences

### Positive
- Tree defaults to the logged-in member's own person as root.
- Enables per-user "edit your own record" scoping.
- Powers the Family Address Book (join member profile/contact prefs to their person).
- Enables living members to author their own enduring facts — high-value, hard-to-
  recover data.
- Provides the stable identity seam a future Family Bunch app links against.

### Negative / Risks
- A wrong link mis-attributes edits/contact info to the wrong person → mitigated by
  admin verification + audit trail.
- Living-person PII rules (§9, `living` flag) still gate what a linked profile exposes.

### Neutral
- **Keeps the GEDCOM-7 separation intact** — `users` stays app-layer, `individuals` stays
  GEDCOM. We do NOT merge them.

## Alternatives Considered

- **No link** — rejected: breaks all four dependent features.
- **Merge `users` into `individuals`** — rejected: conflates authentication with the
  GEDCOM data model, violates §3.5 separation and the GEDCOM-7 alignment (ADR-worthy
  schema hygiene), and would not map cleanly to v2.

## Migration / v2

The nullable FK (or link table) is **additive** — Flask-Migrate adds it without
disturbing existing data, and it maps cleanly to the v2 Spring Boot/MySQL model.

## Related
- **ADR-0001** (audit of link changes; self-edit rides on the post-moderation model).
- Master Plan §3.1/§3.5 (INDI vs users), §10 (RBAC scoping of self-edit), §11 parking
  lot (per-member dashboard, address book, public surface).
