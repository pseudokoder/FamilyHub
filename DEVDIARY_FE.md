# FamilyHub v1 — Frontend Builder Dev Diary

> **Who writes this:** the **Frontend Builder (FE)** only. The Backend Builder
> (BE) has its own `DEVDIARY_BE.md`. Keeping them separate means the two builders
> never clobber each other's diary on the same branch. See `DEVDIARY.md` for the
> thin index that points here.

---

## WP3 — Chronicle Public Home Page

**Branch:** `wp3-frontend-crud`
**Date:** 2026-06-28
**Status:** Implementation complete; pending Wes review + merge to master.

### What WP3 Delivered

The logged-out public home page (`/`) is now the **Chronicle** design — an
antique expedition journal aesthetic with self-hosted fonts, a splash video,
animated family tree, dossier, people sheet, photo wall, and map-route timeline.
All sections are driven by `SAMPLE_DATA` (mock Rivera/Okafor/Vega family) pending
real API integration in a later WP.

The logged-in dashboard is unchanged in content; it was split to its own file
(`dashboard.html`) so `index.html` could become a fully standalone template.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/templates/index.html` | Modified | Replaced with Chronicle standalone template |
| `app/templates/dashboard.html` | Created | Carries the authenticated Bootstrap dashboard |
| `app/routes/main.py` | Modified (cross-boundary) | One-line routing change — see below |
| `app/static/css/chronicle-main.css` | Created | Design tokens, layout, atmosphere |
| `app/static/css/chronicle-components.css` | Created | Component styles (tree, dossier, etc.) |
| `app/static/css/fonts.css` | Created | 37 @font-face rules for self-hosted woff2 fonts |
| `app/static/js/chronicle.js` | Created | CSP-compliant JS; SAMPLE_DATA intact |
| `app/static/fonts/*.woff2` | Created (37 files) | Old Standard TT, Spectral, Special Elite |
| `app/static/img/` | Created (5 files) | antique-map, world-map-vintage, logo, favicons |
| `app/static/videos/animation_2.mp4` | Created | Intro splash animation |
| `docs/FRONTEND_DESIGN.md` | Modified | Design Language, Decision Log, Parking Lot |
| `BLOCKERS.md` | Modified | Logged FE touch of main.py for BE review |

### Decisions Made Without Wes

#### 1. Auth split: `dashboard.html` + one-line `main.py` route change

**Problem:** The task said make `index.html` standalone (no `{% extends %}`),
but the original `index.html` used `{% if current_user.is_authenticated %}` to
serve two different pages from the same file. A standalone template can't also
extend `base.html`.

**Decision:** Created `app/templates/dashboard.html` (extends `base.html`,
carries the authenticated content) and changed one line in `main.py`:

```python
# Before
return render_template("index.html", ...)
# After
return render_template("dashboard.html", ...)
```

This is view-routing only — no business logic, no schema, no endpoints changed.
Logged in `BLOCKERS.md` as a cross-boundary touch for BE review.

**Why this is right:** The alternative (checking `current_user.is_authenticated`
inside a standalone template) would mean the template conditionally produces
valid HTML or gibberish depending on auth state — that's fragile and untestable.
Clean separation (public template / dashboard template) is how Flask apps should
work. The route stays in `main.py` where it belongs.

#### 2. CSP compliance: no inline styles whatsoever

The app has a strict CSP (`style-src 'self'`) — no `'unsafe-inline'`. The
Chronicle source used inline `style="..."` extensively for:
- CSS custom properties on `.photo` elements (`--p1`, `--p2` duotone palette)
- Tree node positions (`left`, `top`)
- One-off spacing on the catalog `<h2>`
- A screen-reader label
- A `<noscript>` message

**Approach:**
- Photo tone values → `data-p1`/`data-p2` attributes; applied by `applyTones()`
  helper via `el.style.setProperty('--p1', el.dataset.p1)` (JS property writes
  are NOT blocked by CSP — only HTML attribute `style=""` is blocked).
- Tree node positions → `data-x`/`data-y`; applied at DOMContentLoaded via
  `el.style.left = el.dataset.x`.
- Catalog h2 margin → `.catalog h2 { margin-top: var(--space-2); }` in CSS.
- Screen-reader label → `.sr-only { position: absolute; left: -9999px; }`.
- Noscript message → `.noscript-msg { text-align: center; ... }`.

Zero inline `style` attributes in the rendered HTML — confirmed by PowerShell
`Invoke-WebRequest` check after Flask server startup.

#### 3. Self-hosted fonts (no Google Fonts CDN)

The strict CSP also forbids external `font-src`. Google Fonts `<link>` tags were
removed. Fonts were downloaded as woff2 files using PowerShell
`Invoke-WebRequest` with a Chrome User-Agent (required to get woff2 instead of
TTF from Google's API). 37 files covering all unicode ranges for:
- Old Standard TT (italic 400, normal 400, normal 700) — 5 ranges × 3 variants
- Special Elite (normal 400) — 2 ranges
- Spectral (normal 300/400/500/600) — 5 ranges × 4 weights

All placed in `app/static/fonts/`; `fonts.css` loads them with `@font-face`.

#### 4. CSS image paths — no change needed

Chronicle's CSS uses `url("../img/...")` which resolves correctly from
`app/static/css/` → `app/static/img/` — the same relative directory structure
that Flask's static folder uses. No CSS edits were needed for image paths.

#### 5. SAMPLE_DATA kept exactly as-is

The task brief required keeping the mock data unchanged. `SAMPLE_DATA` in
`chronicle.js` is verbatim from the Chronicle source (Rivera/Okafor/Vega family).
It will be replaced by real `/api/*` calls in a later WP when the tree/dossier/
timeline sections are wired to the WP2 REST API.

### Manual Testing Checklist

> Clear this section once Wes has done a browser pass and confirmed green.

- [ ] Open `http://localhost:5000/` in a browser — logged out.
- [ ] Splash animation plays, fades to body.
- [ ] All Chronicle sections visible: masthead, hero tree, meta strip, dossier,
      people sheet, collections, photo wall, timeline, catalog search, footer.
- [ ] Zero console errors (CSP violations, 404s, JS exceptions).
- [ ] Open DevTools → Network → reload; confirm all fonts load from `/static/fonts/`.
- [ ] Open DevTools → Application → Security; no mixed content.
- [ ] Log in → redirected to Bootstrap dashboard (not Chronicle).
- [ ] Log out → back to Chronicle page.
- [ ] Resize to mobile (~375px) — layout responds, no overflow.
- [ ] Check with `prefers-reduced-motion: reduce` emulation — splash hidden,
      animations disabled.

### Cross-Boundary Touch: `app/routes/main.py`

This file is normally BE territory. The FE touched it for the auth-split routing
(one line: `"index.html"` → `"dashboard.html"`). Logged in `BLOCKERS.md` so the
BE can review at merge time. No business logic changed.

### WGU Connections

- **D276 Web Development Foundations** — Jinja2 template inheritance (`dashboard.html`
  extending `base.html`); standalone template structure.
- **D277 JavaScript Programming Essentials** — The `applyTones()` helper and the
  DOMContentLoaded node-position pattern; IntersectionObserver for scroll-reveal
  and SVG path animation.
- **D280 Introduction to Web Development** — Flask route rendering; static file
  serving via `url_for('static', filename='...')`.
- **D287 Full Stack Web Development** — Content Security Policy; `font-src 'self'`;
  why inline styles are blocked and how to work within the constraint.

### v2 Spring Boot Migration Notes

The Chronicle public page is **pure front-end** — no Spring Boot equivalent is
needed. When v2 is built:
- `index.html` becomes a static Angular component (no server-side rendering).
- `dashboard.html` becomes the authenticated default route in Angular Router.
- Font files move to `src/assets/fonts/`; `fonts.css` → Angular `styles.scss`.
- Chronicle's `SAMPLE_DATA` is replaced by HTTP calls to the v2 Spring Boot REST API.

The CSP and static-asset patterns are framework-agnostic best practices —
everything learned here transfers directly to v2 (D287/D288).

---

## WP4 — Authenticated App Shell, Home, and People

**Branch:** `wp4-fe-shell` (created from `wp3-frontend-crud`, merged forward
onto `master` — see "Branch housekeeping" below)
**Date:** 2026-07-03
**Status:** Pieces 1–3 complete and manually verified in a real browser; pending
Wes review + merge to master.

### What WP4 Delivered

Three pieces, all wired to the live WP2/WP3 JSON API (`docs/openapi.yaml`) —
nothing here renders mock data:

1. **The app shell** (`app/templates/base.html`) — primary nav (Home · Tree ·
   People · Memories · Search) and a user-menu dropdown (Account & Security ·
   Suggest an idea · Admin[gated] · Log Out). The brand shows the family's own
   name if one's been set in Settings, else "FamilyHub" (`app.context_processor`
   in `app/__init__.py`, reading `settings_service.branding()`).
2. **Home** (`app/templates/dashboard.html` + `app/static/js/home.js`) — a Quick
   Add row (gated on the `contribute` permission), a warm "On This Day" feed
   (`GET /api/on-this-day`), a small stat strip (`GET /api/stats`), and Recent
   Activity (`GET /api/activity`, Curator+ only — see Decisions below).
3. **People** (`app/routes/people.py`, `app/templates/people/*`,
   `app/static/js/people.js`) — a find bar + status/surname filter chips + sort,
   all against `GET /api/search`; and a depth-complete Register form that
   creates an individual, a primary name, and (optionally) birth/death events
   with fuzzy dates and places, via `POST /api/individuals` → `/api/places` →
   `/api/events`.

Everything else the brief called out as later work (Tree, Memories, global
Search, the fuller "User area," Suggest-an-idea, the Person Page, and the
Photo/Source/Story Quick Add tiles) points at one shared placeholder route,
`GET /coming-soon?feature=...` (`app/templates/coming_soon.html`) — except the
Person Page (`/people/<id>`), which is a real per-id route with placeholder
content so every People-list link is already stable for FE-2.

### Branch Housekeeping (read this before anything else on this branch)

`wp4-fe-shell` was created FROM `wp3-frontend-crud` (not from a fresh `master`)
because the brief's Piece 1 assumes `dashboard.html`, `chronicle.js`, and
`docs/FRONTEND_DESIGN.md` already exist — they only existed on the unmerged
WP3 branch, not on `master`. `origin/master` (containing the merged WP3
backend-gaps + backend-admin work) was then merged INTO this branch. Only two
files conflicted — `docs/MASTER_PLAN.md` and `BLOCKERS.md`, both doc-only —
resolved by keeping master's newer, reconciled content and carrying forward one
Wes-approved parking-lot entry (the "public surface + PII guardrail" idea) that
only existed on the WP3 branch. No application code conflicted; the full suite
was green (207/207) immediately after the merge, before any WP4 code was
written. Logged in `BLOCKERS.md` as a RESOLVED item for BE to spot-check.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/templates/base.html` | Modified | New nav + user menu; brand from settings |
| `app/templates/dashboard.html` | Modified | Home: Quick Add, On This Day, stats, activity |
| `app/templates/coming_soon.html` | Created | Shared placeholder for unbuilt nav destinations |
| `app/templates/people/index.html` | Created | Find/filter/sort/paginate |
| `app/templates/people/new.html` | Created | Register-a-person form |
| `app/templates/people/_fuzzy_date_fields.html` | Created | Shared birth/death date+place fields |
| `app/templates/people/show.html` | Created | Person Page placeholder (real per-id route) |
| `app/routes/people.py` | Created | `people_bp`: index / new / show |
| `app/routes/main.py` | Modified | Added `coming_soon` view |
| `app/__init__.py` | Modified (cross-boundary) | Registered `people_bp`; added branding context processor |
| `app/config.py` | Modified (cross-boundary, bugfix) | `BOOTSTRAP_SERVE_LOCAL = True` — see below |
| `run.py` | Modified (cross-boundary, minor) | `PORT` env var for local dev |
| `app/static/js/api.js` | Created | Shared `apiFetch()` (CSRF header + JSON body) |
| `app/static/js/home.js` | Created | Home page data wiring |
| `app/static/js/people.js` | Created | People list + Register form logic |
| `app/static/css/style.css` | Modified | Quick-add tiles, chips, stat strip, person rows (additions only) |
| `docs/openapi.yaml` | Modified | New `Views` tag: `/coming-soon`, `/people`, `/people/new`, `/people/{individual_id}` |
| `docs/FRONTEND_DESIGN.md` | Modified | Decision log entry for this WP |
| `BLOCKERS.md` | Modified | 2 new OPEN items + 2 RESOLVED (merge, Bootstrap bug) |

### Decisions Made Without Wes

See `docs/FRONTEND_DESIGN.md`'s 2026-07-03 decision-log entry for the full
list (JS-orchestrated multi-step create, fuzzy-date encoding, why sort has no
"by surname," the Surname chip's match-any-name behavior). Summarized here:

1. **Admin nav gating uses `is_admin`, not Curator+** as the brief literally
   said — every `/admin/*` and `/api/admin/*` route is hard-coded Admin-only,
   so gating on Curator would 403. Logged OPEN in `BLOCKERS.md`.
2. **Recent Activity is Curator+-only on Home** — the only endpoint,
   `GET /api/activity`, is the Curator+ audit trail (ADR-0001), not a friendly
   all-members feed. Non-Curators see an honest static message, never a
   silently-broken fetch. Logged OPEN in `BLOCKERS.md`.
3. **"Suggest an idea" is a placeholder**, even though `POST /api/suggestions`
   already exists and is trivial to wire — kept this WP scoped to exactly the
   three specified pieces (Home, People, the shell) rather than quietly
   growing a fourth.
4. **"About" dropped from the primary nav** (the brief lists exactly five
   items); the page still renders at `/about`, just unlinked until there's a
   footer to put it in.

### Bug Found + Fixed: Bootstrap was CDN-only, dead under the CSP

Manually loading any authenticated page in a real browser (not `pytest`, which
never fetches `<link>`/`<script>` tags) showed Bootstrap's CSS/JS failing to
load from `cdn.jsdelivr.net` — blocked outright by the strict CSP
(`script-src`/`style-src 'self'`). This predates WP4; it means every existing
Bootstrap page, including the WP3-admin panel, has never actually rendered
correctly in a CSP-honoring browser. Root cause: `BOOTSTRAP_SERVE_LOCAL` was
never set, so Bootstrap-Flask defaulted to CDN mode. Fixed with one line in
`app/config.py`; verified both ways (CDN requests now `[FAILED]`-then-absent,
`/bootstrap/static/...` requests `200 OK`) and confirmed the full suite stays
green. Full writeup + the exact verification steps are in `BLOCKERS.md`
(2026-07-03, RESOLVED).

### Manual Testing Checklist

> Clear this section once Wes has done a browser pass and confirmed green.
> Note: this app registers a service worker (`sw.js`) that precaches static
> JS/CSS for offline use — if you're iterating on a `.js`/`.css` file and the
> browser won't show your change, unregister the service worker (DevTools →
> Application → Service Workers) or hard-reload; this bit FE mid-WP4 and cost
> real debugging time before the cause was found.

- [ ] Log in as each seeded role (`flask seed` gives Viewer/Contributor/Curator;
      `flask create-admin` for Admin) and confirm: Quick Add and "+ Add a
      person" show only for Contributor+; Admin menu item shows only for Admin;
      Recent Activity shows real data for Curator/Admin, the honest fallback
      message for everyone else.
- [ ] Home: On This Day, stat strip, and Recent Activity all load without
      console errors; the empty states ("no milestones today," etc.) read
      naturally.
- [ ] People: type in the find bar (debounced), toggle Living/Deceased/All,
      toggle the Surname chip and type a surname, change the sort — list
      updates each time without a page reload.
- [ ] Register a person with only a given name — succeeds. Register one with
      neither given nor surname — inline error, no request sent. Register one
      with a birth year + place — confirm via `GET /api/individuals/<id>` and
      `GET /api/events?subject_type=individual&subject_id=<id>` that the name
      and BIRT event both saved with the right `date_original`/`date_sort`.
- [ ] Every nav item and user-menu item resolves to either a real page or the
      "coming soon" placeholder — no 404s, no dead links.
- [ ] Resize to mobile (~375px) — nav collapses behind the hamburger, the
      Register form's fields stack full-width and stay tappable.
- [ ] Zero CSP violations in the console on any of the above (checked via the
      browser console, not just `curl`).

### Cross-Boundary Touches

- `app/__init__.py` — registered `people_bp`; added the branding context
  processor. Additive, no existing behavior changed.
- `app/config.py` — `BOOTSTRAP_SERVE_LOCAL = True` (bugfix, see above).
- `run.py` — `PORT` env var, defaults to the unchanged 5000.
- `docs/openapi.yaml` — added the new `Views` tag/paths for the HTML routes
  this WP introduced, per the branch-per-WP rule that cross-lane contract
  edits are allowed on-branch with the owning builder's approval at merge.

All logged in `BLOCKERS.md` for BE review, same pattern as WP3's `main.py` touch.

### WGU Connections

- **D276 Web Development Foundations** — Jinja2 `{% include %}` with `{% with
  %}`-scoped variables (`_fuzzy_date_fields.html` reused for birth AND death by
  parameterizing element ids on one `prefix` variable).
- **D277 JavaScript Programming Essentials** — `apiFetch()`'s CSRF-header
  pattern; debounced input handlers; client-side sort/paginate over a fetched
  array (justified here by "family scale," not hand-waved).
- **D280 Introduction to Web Development** — a Flask Blueprint per feature area
  (`people_bp`) with thin, template-rendering-only views — the Controller half
  of the layered architecture CLAUDE.md asks for; the Service/Repository halves
  (already built in WP2/WP3) are untouched.
- **D287 Full Stack Web Development / D315 Security** — the CSRF-token-via-
  meta-tag + `X-CSRFToken` header pattern for JSON `fetch()` calls (forms
  aren't the only thing CSRF protection has to cover); the Bootstrap CDN/CSP
  bug is a live example of defense-in-depth catching a real misconfiguration.

### v2 Spring Boot Migration Notes

- `people_bp`'s three views map to `PeopleController.java` `@GetMapping`s
  returning view names for Angular's router to mount components on — no
  business logic to port, since there isn't any here (it all lives in the
  already-built `@Service` layer).
- `api.js`'s `apiFetch()` is exactly the shape of an Angular `HttpClient`
  interceptor that attaches a CSRF header — same contract, same header name,
  ports directly.
- The Register form's multi-step client orchestration (create individual →
  find-or-create place → create event) is the same sequence a v2 Angular
  reactive form's submit handler would run against the identical REST
  endpoints — nothing here is Flask/Jinja-specific.
- `app.context_processor` (the branding injection) has no direct Spring
  equivalent needed — v2's Angular app would just call a `/api/settings`-style
  endpoint once at bootstrap and hold it in a shared service.

---

## WP5 — Chronicle Reaches the Authenticated App + Copy Neutralization

**Branch:** `wp5-fe-chronicle`
**Date:** 2026-07-04
**Status:** Complete; manually verified across all four roles; pending Wes
review + merge to master.

### What WP5 Delivered

Two tasks, both scoped tightly per the brief (no new pages this WP):

1. **Chronicle reskin of the authenticated app.** A new stylesheet,
   `app/static/css/chronicle-app.css`, repaints Bootstrap's own component
   classes (buttons, forms, dropdowns, list groups, tables, badges) in the
   same tokens/fonts as the public Chronicle page, and `base.html` now uses
   the *actual* `.site-header`/`.brand`/`.nav__links` markup from
   `index.html` — not just similar colors, the same component. Only three
   template files were touched (`base.html`, `dashboard.html`,
   `people/*.html` — Task 2's exact scope) but the whole authenticated app
   (admin panel, auth pages, error pages) inherited the look for free, because
   they already used Bootstrap's own classes and this WP repaints those
   classes globally.
2. **Copy neutralization sweep (ADR-0003).** Grepped the app surface for the
   author's name and personal contact details. Found and fixed one real bug
   (`/.well-known/security.txt` hardcoded a personal email — now reads
   `MAIL_DEFAULT_SENDER` config) and one source comment. BE had already fixed
   the login/error-page copy in a prior commit (`4bd1182`) — verified, not
   re-touched.

Full decision log (mechanism, the header-reuse approach, the mobile dropdown
conflict and its fix, the palette-table correction) is in
`docs/FRONTEND_DESIGN.md`'s 2026-07-04 entry — not duplicated here.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/static/css/chronicle-app.css` | Created | The Bootstrap-repaint layer + new app-only components |
| `app/templates/base.html` | Modified | Chronicle header/dropdown/flash markup, brand in `<title>` |
| `app/templates/dashboard.html` | Modified | Recent Activity ungated; `.section-title` labels |
| `app/templates/people/index.html` | Modified | `.chip` → `.filter-chip` |
| `app/templates/people/show.html`, `coming_soon.html` | Modified | Dropped `.display-6` (see "known inconsistency" below) |
| `app/static/js/home.js` | Modified | Recent Activity calls `/api/activity/feed`; verb/noun maps removed |
| `app/static/js/people.js` | Modified | `.chip` → `.filter-chip` selector |
| `app/static/css/style.css` | Modified | WP4 app-shell rules removed (moved to chronicle-app.css) |
| `app/routes/main.py` | Modified | `security_txt` reads `MAIL_DEFAULT_SENDER` instead of a hardcoded address |
| `app/templates/index.html` | Modified | One comment reworded (ADR-0003) |
| `docs/FRONTEND_DESIGN.md` | Modified | Palette table corrected to match shipped CSS; WP5 decision log |

### A Bug Fixed That Wasn't New Scope

Confirmed the WP4 brief's own framing was wrong about *when* Chronicle
styling was supposed to land: it deferred the whole visual pass to
"end-of-v1," but `docs/CONTEXT_LOG.md`'s 2026-07-03 CLARIFICATIONS block
(written the same day, after WP4 shipped) says styling applies *during* the
build — only the accessibility/elderly/§5B *constraints* are the end-of-v1
gate. This WP's brief matches the clarified rule; the FRONTEND_DESIGN.md WP4
entry has a correction note pointing here.

### Manual Testing Checklist

> Clear this section once Wes has done a browser pass and confirmed green.

- [x] Home, People (find/filter/sort), and Register-a-person all render in
      Chronicle across Viewer/Contributor/Curator/Admin — screenshotted each.
- [x] Recent Activity shows the real friendly feed for a Viewer (not the old
      "ask a Curator" message) — confirmed via `pat@example.com`.
- [x] Admin menu item appears only for Admin; admin's user table (untouched
      template) picked up the Chronicle look for free.
- [x] Mobile (375px): hamburger opens/closes the primary nav; the user-menu
      dropdown opens independently without the mobile nav interfering, in
      either order.
- [x] Zero console errors / CSP violations on any page tested.
- [x] `flask db upgrade` had nothing pending; 232/232 tests green before and
      after.
- [ ] Wes: sanity-check the palette against real daylight / a phone screen —
      the WCAG-AA audit itself is still the deferred parking-lot item, but a
      gut-check now is cheap.

### Cross-Boundary Touches

- `app/routes/main.py` — `security_txt()` now reads `current_app.config
  ["MAIL_DEFAULT_SENDER"]`. Same transparency pattern as WP3/WP4's touches to
  this file; logged in `BLOCKERS.md` is not needed this time (bugfix within
  FE's existing footprint in this file, no new cross-boundary dependency).

### WGU Connections

- **D278/D279 Front-End Web Development, D281 UI Design** — the "repaint a
  component library's own classes with new tokens" pattern (a custom
  Bootstrap theme) instead of hand-rolling new markup everywhere; CSS
  cascade/specificity reasoning (why `.display-6` beats a bare `h1` selector
  regardless of stylesheet load order — class beats element every time).
- **D280 JavaScript Programming** — diagnosing an event-handling conflict
  between two independent scripts sharing a DOM region (chronicle.js's
  "close on any link click" vs. Bootstrap's dropdown toggle) and resolving it
  with markup structure (moving the dropdown out of the shared region) rather
  than patching either script.
- **D315 Security** — ADR-0003's config-not-code rule for the security-contact
  address is the same "secrets/identity live in config" principle as
  `MAIL_PASSWORD` living in `.env`, applied to a non-secret but still
  personal value.

### v2 Spring Boot Migration Notes

Nothing here changes the v2 mapping already recorded for WP4 — this WP was
CSS + a handful of template/JS edits, no new routes or contract surface. The
one durable lesson: Angular's component-scoped styles would have made the
"repaint Bootstrap's classes" mechanism unnecessary (each component brings its
own styles) — worth remembering when v2 designs its Material/Angular theme
instead of trying to port `chronicle-app.css` line-for-line.
