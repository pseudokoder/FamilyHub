# ADR-0004: Defer All Front-End Design Constraints Until the Front End Is Stable

- **Status:** Accepted
- **Date:** 2026-06-28 *(decision made at Master Plan v1.4; recorded retroactively 2026-07-04)*
- **Deciders:** Wes Leiter (project owner)
- **Scope:** v1 front-end build; Master Plan §5B; `docs/FRONTEND_DESIGN.md`.
- **Supersedes:** the §5B "durable visual constraints" approach of Master Plan v1.3.

## Context

Early Frontend Builder runs, executed under the Master Plan's hard visual constraints,
repeatedly produced broken, extremely generic HTML/CSS — far below the project's
quality bar. To isolate the cause, an unconstrained design session was run with carte
blanche over design criteria. It produced high-quality, creative work (the design that
became **Chronicle**), demonstrating that the **constraint load in the baseline — not
builder capability — was suppressing design quality**.

The response was staged: Master Plan v1.3 moved the living design language out of the
baseline into FE-owned `docs/FRONTEND_DESIGN.md`; when that proved insufficient, v1.4
went further and **emptied §5B entirely**, parking even the "durable" constraints
(WCAG-AA contrast, elderly-friendly type/tap targets, calm-by-design rules) in
FRONTEND_DESIGN's Design Parking Lot.

## Decision

1. **No design constraints live in the baseline during the v1 build.** Master Plan §5B
   stays an intentionally empty placeholder; anything that even remotely constrains
   front-end visual expression is deferred.
2. Constraint candidates are **captured, not enforced**, in `docs/FRONTEND_DESIGN.md`
   → Design Parking Lot.
3. Constraints are re-introduced into §5B as a **validation/tuning pass at the END of
   v1** — after the front end is built, stable, and visually right — and gate the
   public launch (accessibility, elderly-usability, calm-by-design).

## Consequences

### Positive
- Design quality restored (Chronicle is the direct product of this decision).
- The FE iterates freely under §11 Tier-2 without baseline revisions.

### Negative / accepted risk
- Accessibility and elderly-usability are unverified until the end-of-v1 pass; that
  pass is a **pre-launch gate**, not optional polish.

### Enforcement note
This decision was silently reverted once (Revision 2.3.0 re-populated §5B from v1.3
because this rationale was unrecorded). **§5B must not be re-populated before the
end-of-v1 pass; cite this ADR when tempted.**

## Alternatives Considered
- **Keep constraints and iterate prompts** — failed in practice across multiple runs.
- **Partial constraint set** — still degraded output; the test showed only full
  removal restored quality.

## Related
- Master Plan v1.3/v1.4 revision entries; §11 two-tier change control; §5B placeholder.
- `docs/FRONTEND_DESIGN.md` Design Parking Lot (the parked constraint candidates).
