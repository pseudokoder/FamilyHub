# ADR-0001: Write-Control Model for the FamilyHub Database

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Wes Leiter (project owner)
- **Scope:** FamilyHub v1 "Full" (Flask/SQLite/SQLAlchemy). Notes on v2 "Enterprise" (Java/Spring Boot) where relevant.
- **Supersedes:** none

---

## Context

FamilyHub is a single GEDCOM-7 genealogy database presented through many curated
**views** (one database, many views — no data is duplicated per view). Logged-in
family members perform full CRUD against the WP2 JSON API (`/api/*`), which
already ships RBAC and an `audit_log`, with 139 tests green.

We need a policy for **how writes are controlled** so that shared editing does not
degrade data quality. Two data-integrity principles are in tension with editing
convenience:

- **Provenance / data fidelity** — every fact should be traceable to *who*
  changed it, *when*, and *from what source*, and every change should be
  reversible.
- **Maker–checker (the "four-eyes principle")** — a segregation-of-duties control
  where the person who makes a change is not the one who approves it.

Genealogy has its own version of this: the **Genealogical Proof Standard**, which
holds that conclusions must be evidence-based rather than merely asserted.

The editing population is **small and high-trust** (a family), and a bad edit
(e.g., a wrong birth date) is **recoverable**, not catastrophic or irreversible.

## Decision

For v1, adopt **post-moderation write-control**:

1. **Direct writes**, gated by existing **RBAC** roles
   (Viewer / Contributor / Power User / Admin).
2. **Full `audit_log` capturing before -> after values** on every mutating
   operation (provenance).
3. **Soft deletes only** — records are never hard-deleted, so any state is
   recoverable.
4. **Power-User revert** — a one-click undo of any change, driven from the audit
   trail.

We will **not** build a pre-moderation approval queue in v1.

## Rationale

- Pre-moderation (holding edits until approved) is the correct control when a bad
  write is **expensive and irreversible** — money, medical, PII exposure. A wrong
  genealogical fact is neither; it is recoverable. Post-moderation is therefore
  the industry-appropriate choice for a small, high-trust family database, and is
  how comparable systems (Wikipedia, FamilySearch) operate.
- It **reuses what WP2 already built** (RBAC + `audit_log` + direct-write API),
  keeping cost near zero and avoiding a rewrite of a tested API.
- A moderation queue is **additive, not a retrofit** — it can be layered on later
  as a separate `change_request` table without disturbing the core schema, so
  there is no "build now or pay 10x later" penalty that would justify early work.
- Respects the project constraint to **execute rather than over-plan**.

## Consequences

### Positive
- Low editing friction; low build cost; recoverable at all times.
- Strong provenance and accountability via before/after audit trail.
- Migration-friendly toward v2 (the queue, if added, is an additive table).

### Negative / Risks
- Bad or careless edits are **live until noticed**; the model relies on the audit
  trail and Power-User revert rather than prevention.
- No **enforced second approver** in v1 (accepted, given scale and trust).

### Future / v2 (reserved, not built now)
- **Pre-moderation via maker–checker**: an additive `change_request` table where
  a normal user's edit sits in a *transparent* "pending review" state (never a
  silent hold) until a Power User or Admin approves it.
- **Two-approver / four-eyes policy** as a configurable toggle (SOX/banking-grade;
  overkill for a family site). Planned as **v2 portfolio practice**, not v1
  production.

## Alternatives Considered

- **Pre-moderation approval queue in v1** — rejected: high friction, high build
  cost, doubles the state model on every editable entity, and fights the existing
  WP2 direct-write API. No offsetting benefit at family scale.
- **Open editing with no audit/revert** — rejected: violates the provenance /
  fidelity principle; makes bad edits unrecoverable.

## Related / Notes

- **Public exposure is out of scope here.** The site and database are
  **locked-down by default (default-deny)**; only data an Admin explicitly
  selects appears on the public page, edited through a dedicated Admin-only tool.
  This is standard PII best practice and will be captured in a separate ADR when
  the public/curated site is built.
