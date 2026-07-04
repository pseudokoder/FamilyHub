# Architecture Decision Records (ADRs)

Point-in-time architecture decisions for FamilyHub. Each ADR captures the **context**,
the **decision**, and its **consequences** so a future thread (or the v2 rewrite) can see
*why* a thing is the way it is without re-litigating it. The [Master Plan](../MASTER_PLAN.md)
is the living spec; ADRs are the immutable record of the calls behind it.

| ADR | Title | Status | Summary |
|---|---|---|---|
| [0001](0001-write-control-model.md) | Write-control model | Accepted | Post-moderation: direct writes gated by RBAC + full `audit_log` (before→after) + soft-delete + Curator revert. No pre-moderation queue in v1. |
| [0002](0002-account-person-link.md) | Account↔Person link | Accepted | Nullable `users.individual_id` FK ties an account to its INDI record; unlinked users fall back to the oldest-ancestor tree root. |
| [0003](0003-white-label-neutral-language.md) | White-label / neutral language | Accepted | No personal names/contact in the app's UI copy, config defaults, or build-detail docs; author credit and origin narrative remain allowed. |

**Convention:** files are `NNNN-short-slug.md`, numbered sequentially and never renumbered.
Once **Accepted**, an ADR is not edited to reverse it — a *new* ADR supersedes it (noted in
both). Add new rows to this table when an ADR lands.
