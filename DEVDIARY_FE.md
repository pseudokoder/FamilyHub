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

---

## FE-2 — Person Page (Six Tabs, Native Chronicle)

**Branch:** `fe2-person-page`
**Date:** 2026-07-04
**Status:** Implementation complete; full suite green; pending owner review + merge.

### What FE-2 Delivered

`people/show.html`'s FE-1 placeholder ("this person's page is on its way") is
now the real Person Page: one route, six tabs (Story · Relationships ·
Timeline · Photos · Details · Sources), switched by URL hash so every tab is
deep-linkable and back/forward works. Everything is client-rendered by the new
`app/static/js/person.js` against the WP2 JSON API — no new Flask routes, no
`docs/openapi.yaml` changes (the `/people/{individual_id}` Views entry already
existed).

- **Story** — Life Sketch, Photos strip, Family summary, Name Meaning (only
  when one exists), Vitals, Sources, plus a condensed right-rail timeline. No
  "Latest Changes" card — see the BLOCKERS.md item below.
- **Relationships** — Parents/Spouses/Children/Siblings, each with a
  pedigree-type badge; add spouse/child, link parents, edit a child's
  pedigree_type/order, remove a link — all Contributor+.
- **Timeline** — age spine, life-chapter grouping, Life/Family/World
  color-coded events, a migration-thread place-change mark, "N sources"
  badges per event.
- **Photos** — a photo-wall grid, a CSP-safe lightbox, upload + link/unlink an
  existing photo (Contributor+).
- **Details** — the full CRUD workbench: Names (all fields), Person facts
  (sex/living/restriction, plain-language restriction help text), Events &
  attributes (any GEDCOM tag, fuzzy dates, find-or-create place).
- **Sources** — citations grouped by what they back (person/name/event),
  plain-language QUAY reliability labels, attach/edit/soft-delete
  (Contributor+).

Full decision log (tab-switching architecture, the memoized fetch cache, the
Relationships data-assembly path, Markdown rendering, the Timeline algorithm,
and a real flexbox bug found in the browser) is in
`docs/FRONTEND_DESIGN.md`'s 2026-07-04 entry — not duplicated here.

### Depth-Bar Decisions Worth Recording

- **Header portrait / relationship-card cameos** reuse `chronicle.js`'s own
  `photo()`/`applyTones()` globals (already loaded site-wide by `base.html`)
  for the toned-cameo placeholder, rather than inventing a new component —
  same CSP-safe data-p1/data-p2 mechanism, just applied to freshly-injected
  markup. Tones are picked deterministically from the person's id (decorative
  only — no such field exists on `Individual`).
- **"Follow" renders disabled, not faked.** The header's Follow button was
  wireframed and approved, but no backend endpoint exists. Logged as an OPEN
  `BLOCKERS.md` item asking whether it's in scope for v1 or cut.
- **No "Latest Changes" card on Story.** `GET /api/activity/feed` has no
  per-subject filter — showing it un-scoped would either leak site-wide
  activity onto one person's page or require re-deriving Curator+-only data.
  Omitted per §5A; OPEN `BLOCKERS.md` item asks BE for the filter.
- **Editing a child's pedigree_type/child_order** goes through DELETE then
  re-POST (the contract has no PUT for an active `family_children` row, but
  `family_service.add_child` already restores-with-new-values on a
  soft-deleted one) — a real code path, not a workaround. Logged as an OPEN
  *forward note* (not a blocker — it works today) asking for a dedicated PUT
  so the audit trail records one `update` instead of a delete/create pair.
- **Markdown rendering is a small, safe, hand-written subset** (paragraphs,
  headings, bold/italic/code, "- " lists) — no CDN markdown library is
  allowed under the strict CSP, and adding a Python one would cross into BE's
  lane (`app/requirements.txt` is BE's file). Escaping happens on the raw text
  BEFORE any Markdown syntax is applied, so no amount of Markdown can smuggle
  real HTML through (D315).
- **Relationships' add-spouse/add-child/link-parents pickers** search only
  existing individuals via `/api/search` (never inline "create a new person"),
  keeping this page's scope to *linking*, not authoring — a new person is
  still made at `/people/new`.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/templates/people/show.html` | Modified | Real content; thin shell, all rendering is client-side |
| `app/static/js/person.js` | Created | All six tabs, ~1,700 lines, sectioned and commented |
| `app/static/css/chronicle-app.css` | Modified | New Person Page component classes (§9 of that file) |
| `BLOCKERS.md` | Modified | Two OPEN items (Follow endpoint, activity/feed subject filter) + one OPEN forward note (family_children PUT) |
| `docs/FRONTEND_DESIGN.md` | Modified | 2026-07-04 decision-log entry |

### Manual Testing Checklist

> Clear this section once the owner has done a browser pass and confirmed green.

- [x] Logged in as a seeded Contributor (`jo@example.com`) against
      `flask seed`'s Hartwell data (`/people/3`, John Thomas Hartwell — every
      polymorphic link kind the seed data exercises: names, events, a family as
      both child and parent, media, a note, a citation) — all six tabs render
      real data, nothing hollow.
- [x] Created an event (Residence, fuzzy year, find-or-create place) and a
      citation (existing source via search) live in the browser — both
      persisted, re-rendered correctly, and propagated into the Story tab's
      Vitals/Sources cards and the Timeline without a page reload.
- [x] Logged in as the seeded Viewer (`pat@example.com`) — confirmed zero
      Add/Edit/Delete/Remove controls render anywhere across Relationships,
      Details, Photos, or Sources (Person facts falls back to plain read-only
      text instead of a disabled form).
- [x] 375px viewport: header stacks, tabs scroll horizontally, relationship
      cards go full-width — no horizontal page overflow.
- [x] Zero browser console errors / CSP violations across every tab and role
      tested.
- [x] `flask db upgrade` had nothing pending; 232/232 tests green before and
      after (no new routes — the `test_openapi.py` route-map sync test needed
      no changes).

### A Bug Found and Fixed in the Browser

The first real-browser pass on Relationships showed every card's "Remove"
button overlapping the person's name — a flexbox sizing bug (`.rel-card__body`
had no `flex-grow`, so a fixed-width card's default shrink behavior squeezed
it down to ~24px while the sibling actions block, protected with
`flex: none`, kept full size and rendered over it) that pytest's HTML-only
test client had no way to catch. Fixed by giving the actions block its own
row (`flex: 0 0 100%`) instead of fighting for space beside a long name.
Full root-cause writeup in `docs/FRONTEND_DESIGN.md`.

### Cross-Boundary Touches

None. No Flask routes, models, services, or `docs/openapi.yaml` paths changed
this branch — client-side templates/CSS/JS only, against the existing WP2
contract.

### WGU Connections

- **D280 JavaScript Programming** — a hash-router with lazy tab loading and a
  memoized fetch cache (`once`/`invalidate`), built from scratch in vanilla JS
  (no framework); a small hand-rolled Markdown-to-safe-HTML renderer.
- **D278/D279 Front-End, D281 UI Design** — six distinct information
  densities (a read-only Story digest vs. a full CRUD workbench in Details)
  sharing one design language; a real flexbox debugging session (automatic
  minimum size vs. `flex-grow`/`flex-shrink` interaction).
- **D315 Security** — every dynamically-injected string goes through
  `escapeHtml()` before becoming `innerHTML`, including inside the Markdown
  renderer (escape-then-decorate, never decorate-then-escape); CSP-strict
  throughout (no inline styles/handlers anywhere in ~1,700 new lines).
- **D426/D427 Data Management** — the Relationships tab is a hands-on graph
  traversal exercise: discovering "families where I'm a child" has no direct
  endpoint, so it's derived from a bounded pedigree walk, the same BFS
  structure `tree_service.py` uses server-side.

### v2 Spring Boot Migration Notes

Nothing here changes the v2 route/contract mapping — this branch is
templates/CSS/JS only. The Person Page's client-side memoized cache
(`cache`/`once`/`invalidate`) is the same shape an Angular `PersonService`
would want as a `shareReplay(1)`-backed observable per data key; the
lazy-tab-load pattern maps directly to Angular's lazy-loaded feature modules
or a `*ngIf`-gated child component that only calls its own API on first
activation.

---

## FE-3 — Tree: Vertical Pedigree, Family Group, Relationship Finder

**Branch:** `fe3-tree`
**Date:** 2026-07-05
**Status:** Implementation complete; full suite green; pending owner review + merge.

### What FE-3 Delivered

The nav's Tree `coming-soon` link is now a real section: three pages, one new
`app/routes/tree.py` blueprint (`GET /tree`, `GET /tree/family/<id>`,
`GET /tree/relationship`), all client-rendered by the new `app/static/js/
tree.js` against the WP2 JSON API. `docs/openapi.yaml`'s Views tag grew the
three paths (the one on-branch cross-lane edit this run needed — logged in
`BLOCKERS.md` for BE's merge-time review per the branch-per-WP protocol).

- **Pedigree** (the default) — a vertical ancestor tree from
  `GET /api/tree/root` / `?root=` recentering, rendered as a pure-CSS nested
  `<ul>/<li>` "org chart" (flexbox + `::before`/`::after` border connectors —
  zero JS position math, unlike `chronicle.js`'s absolutely-positioned hero
  tree). Each node: toned cameo, name (links to the Person Page), lifespan, a
  `pedigree_type` badge when a branch is adopted/foster/step, a **Center**
  button (recenter, `history.pushState` + `popstate`, distinct from the name
  link's **navigate**), and lazy-fetches 4 more generations from any leaf via
  `GET /api/individuals/{id}/pedigree?direction=ancestors&depth=4`. Empty
  parent slots render an honest "+ Add parent" invite into the Person Page's
  Relationships tab for Contributor+, or nothing at all otherwise (§5A: never
  a hollow shell).
- **Family Group sheet** — one family, read-only: both partners (reusing
  `.rel-card` verbatim from FE-2), marriage/divorce events, children in
  `child_order` with pedigree badges. Reachable from any pedigree node's
  "Family" link or a direct `/tree/family/<id>` URL; "Edit this family" links
  to the Person Page's Relationships tab for Contributor+ — no CRUD
  duplicated here, same rule as the pedigree invite.
- **Relationship Finder** — two search-as-you-type person pickers
  (`/api/search`, person A defaults from `GET /api/me/person` when linked);
  `GET /api/individuals/{a}/relationship/{b}`'s plain-English label plus a
  person-by-person chain (portrait + name + the parent/child/spouse hop
  between each pair), derived from `distance_a`/`distance_b`/`path` client-
  side (the contract gives the path's node ids, not a per-hop type). Self,
  no-known-relationship, and unlinked-member states each render their own
  honest message — never a fake chain.

Full decision log (the org-chart layout system, the orientation seam, the
mobile outline degrade, and two real bugs found in the browser) is in
`docs/FRONTEND_DESIGN.md`'s 2026-07-05 entry — not duplicated here.

### Depth-Bar / Design Decisions Worth Recording

- **Three resource-oriented routes, not one hash-switched page.** Pedigree
  recenters via a query string (`?root=`); Family Group and Relationship each
  get their own path so a family sheet and a specific relationship query are
  both directly linkable/bookmarkable, matching the brief's "no rule against
  separate routes."
- **`pedigree_type` isn't on a pedigree edge** (`PedigreeGraph.edges` only
  names the family id linking parent to child) — it lives on that family's
  `children[]` row. `tree.js` fetches each newly-seen family once
  (`ensurePedigreeTypes`) and patches the real badge value in before the first
  paint, so there's never a flash of the wrong badge.
- **Portraits across many tree nodes are one `GET /api/media` call, filtered
  client-side by scanning each item's `links[]`** — `Media` has no direct
  `subject_id` (one photo can attach to more than one subject), so this is
  the tree-section equivalent of FE-2's "fetch it all, filter client-side"
  call for family-scale data.
- **The relationship chain's hop type is computed, not returned.** The API
  gives `distance_a`/`distance_b` (A's/B's generations to the nearest common
  ancestor) and `path` (ids from A through the NCA to B); a hop is "parent" if
  its index is before `distance_a` in the path, "child" after — the same
  ascent/descent split `tree_service.py`'s `_relationship_label` already
  computes server-side for the English label, just re-derived client-side for
  the per-hop chain.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/routes/tree.py` | Created | `tree_bp`: pedigree/family/relationship view routes |
| `app/__init__.py` | Modified | Registered `tree_bp` |
| `app/templates/tree/{pedigree,family,relationship}.html` | Created | Thin shells; all rendering is client-side |
| `app/templates/base.html` | Modified | Tree nav link now points at `tree.pedigree` |
| `app/static/js/tree.js` | Created | All three views, sectioned and commented |
| `app/static/js/person.js` | Modified | Task 0: dropped Follow; real View Tree/Relationship links; Story's Latest Changes card |
| `app/static/css/chronicle-app.css` | Modified | New Tree section component classes (§11 of that file) |
| `app/static/js/sw.js` | Modified | Bumped the PWA shell cache version — see below |
| `docs/openapi.yaml` | Modified | Three new Views-tag paths (`/tree`, `/tree/family/{family_id}`, `/tree/relationship`) |
| `docs/FRONTEND_DESIGN.md` | Modified | 2026-07-05 decision-log entry |

### Manual Testing Checklist

> Clear this section once the owner has done a browser pass and confirmed green.

- [x] Logged in as the seeded Contributor (`jo@example.com`): Pedigree from
      Maya Jane Hartwell (4 generations of real Hartwell seed data) —
      recenter on an ancestor updates the URL and re-renders; back/forward
      (`popstate`) restores the prior root; leaf nodes with no recorded
      parents show "+ Add parent" linking into `#relationships`.
- [x] Family Group sheet (`/tree/family/3`) — both partners, children,
      "Edit this family" link, all correct for Contributor.
- [x] Relationship Finder — blood relationship (grandparent, 2-hop chain),
      spouse (1-hop), self-to-self, and two unrelated people (seed data's
      separate Hartwell/Vega lines) — each rendered its own honest message;
      no fake chain when `path` was empty.
- [x] Logged in as the seeded Viewer (`pat@example.com`) — zero "+ Add
      parent" invites and no "Edit this family" link anywhere; read/navigate
      still works everywhere.
- [x] 375px viewport: Pedigree's org chart degrades to an indented, scrollable
      outline (no horizontal page overflow); Family Group and Relationship
      Finder stack full-width, same as FE-2's existing mobile rules.
- [x] Zero browser console errors / CSP violations across all three views and
      both roles tested.
- [x] 239/239 tests green before and after (three new routes; the
      `test_openapi.py` route-map sync test needed the matching
      `docs/openapi.yaml` entries, added on this branch).

### Two Bugs Found and Fixed in the Browser

1. **Mobile name-text overflow.** At the ≤640px indented-outline breakpoint, a
   flex child (`.pedigree-node__body`) has no `min-width: 0`, so its default
   auto minimum size (its unwrapped content width) let long names push past
   the card's right edge instead of wrapping — the exact same flexbox gotcha
   FE-2's decision log already found once on `.rel-card__body`. Fixed by
   adding `min-width: 0`.
2. **Mobile action buttons overlapping a wrapped name.** Once names could wrap
   to 2-3 lines, `.pedigree-node__actions`' `flex: 0 0 100%` (meant to push
   Center/Family onto their own row) had no effect because the mobile
   `.pedigree-node` row was still `flex-wrap: nowrap` — added `flex-wrap:
   wrap` so the actions block actually drops below a multi-line name instead
   of rendering on top of it.

### A Non-Bug Worth Recording: the PWA Service Worker Cache

Manual verification kept showing stale JS/CSS (an already-removed "Follow"
button, unstyled Pedigree cards) even after confirming the served **files**
were correct byte-for-byte. Root cause: `app/static/js/sw.js`'s fetch handler
is cache-first for everything under `/static/` — once a browser has fetched
`/static/js/person.js` even once, it's served from the Cache Storage
indefinitely, regardless of the server's `Cache-Control` headers, until the
`CACHE` constant's version bumps (the file's own documented "refresh lever").
This isn't a bug in this branch's code, but it IS a real consequence of it:
any returning member's browser would keep serving the pre-FE-3 shell after
this ships. Fixed by bumping `CACHE` to `"familyhub-shell-v2"` in `sw.js` —
the one-line, already-documented fix for exactly this situation.

### Cross-Boundary Touches

`docs/openapi.yaml`'s Views tag gained three paths (`/tree`,
`/tree/family/{family_id}`, `/tree/relationship`) — no other section of the
spec changed, and no Flask routes/models/services outside `app/routes/
tree.py` (a new, FE-owned file) were touched. Per the branch-per-WP protocol,
this is a doc-only cross-lane edit for BE to spot-check at merge, not logged
as a `BLOCKERS.md` item (no dependency on BE, nothing blocked).

### WGU Connections

- **D286 Discrete Mathematics II** — the Pedigree/Relationship views are a
  hands-on rendering of the same BFS-over-a-graph structure `tree_service.py`
  implements server-side: nodes + edges, bounded depth, nearest-common-
  ancestor path reconstruction.
- **D280 JavaScript Programming** — a client-side graph merge (`mergeGraph`)
  that accumulates state across multiple lazy-fetches without ever re-fetching
  data already in hand; `history.pushState`/`popstate` for shareable,
  back-navigable client-side state that never round-trips the server.
- **D278/D279 Front-End, D281 UI Design** — a pure-CSS nested-list layout
  (no JS position math) that degrades from a widening org chart to a
  scrollable indented outline at one breakpoint; a real flexbox debugging
  session (`min-width: 0` and `flex-wrap` both needed for a wrapped multi-line
  flex child to lay out correctly).
- **D315 Security** — same `escapeHtml()`-before-`innerHTML` discipline as
  every other page; CSP-strict throughout (SVG was an allowed option for the
  connector lines but wasn't needed — pure CSS did the whole job).

### v2 Spring Boot Migration Notes

The pedigree graph traversal (`mergeGraph`/`renderAncestor`) has no notion of
"vertical" anywhere in its logic — only the CSS class controls layout
direction, which is exactly the seam a v2 Angular pan/zoom canvas component
would want: swap the rendering layer, keep the same graph-slice consumption
contract (`GET /api/individuals/{id}/pedigree`, lazy-fetched per node). The
Relationship Finder's two independent picker components are a natural mapping
to two instances of one Angular `PersonPickerComponent`.

---

## FE-4 — Memories (Album Views + Stories), Search, and the Elderly-First Sizing Strip

**Branch:** `fe4-memories-search`
**Date:** 2026-07-05
**Status:** Implementation complete; full suite green; pending owner review + merge.

### What FE-4 Delivered

**Task 0 (owner directive, ADR-0004):** stripped the leftover pre-Chronicle
"elderly-first" sizing layer out of `app/static/css/style.css` — it was
loading AFTER `chronicle-app.css` and silently winning the cascade on every
authenticated page since WP5 shipped. Dropped `.display-6` from the three
error pages (the known one-line fix from the FE-3 log).

**Memories** — the nav's `coming-soon` link is now a real section: a new
`app/routes/memories.py` blueprint (`GET /memories`, `/memories/person`,
`/memories/family`, `/memories/event`, `/memories/stories`,
`/memories/stories/new`, `/memories/stories/<id>`), all client-rendered by
two new scripts against the WP2 JSON API.

- **Chronological** (the default) — every photo by capture date, falling
  back to upload date (visibly labeled) via `GET /api/media?order_by=
  capture`; the section's "+ Upload a photo" entry point (unlinked uploads —
  link them to someone later).
- **By Person** — a person picker, then `GET /api/media?subject_type=
  individual&subject_id=` (the exact call the Person Page's own Photos tab
  already uses).
- **By Family** — a family picker, then a client-side aggregation over the
  family itself, its own events, and its members' events (defined and
  justified in `docs/FRONTEND_DESIGN.md`'s 2026-07-05 entry — no missing
  backend capability, no blocker filed).
- **By Event** — every event with a linked photo, grouped, no picker (a
  whole-archive view, same spirit as Chronological).
- **Photo Detail** — extends FE-2's simple lightbox: full metadata, every
  link as a navigable chip (an event link resolves to ITS subject, since
  events have no page of their own), Contributor+ edit metadata/manage
  links/soft-delete.
- **Stories** — the memory-blog lane over the same `notes` table: a list
  (newest first), a read view (rendered Markdown, "About" links, Contributor+
  edit/manage-links/delete), and a "Write a Story" flow (title, content,
  format, shared-note flag, an optional who/what-it's-about picker) —
  Contributor+ gated the `people/show.html` way (an honest message for a
  Viewer who lands there directly, not a form that would just 403).

**Search** — the nav's `coming-soon` link is now `app/routes/search.py`
(`GET /search`), Quick and Advanced hash-switched on one page (`#quick`/
`#advanced`, the Person Page's own tab pattern), plus a header quick-search
overlay reachable from any authenticated page (a Tier-2 design call, logged
in `docs/FRONTEND_DESIGN.md`).

- **Quick** — search-as-you-type across people AND families (families have
  no name of their own; matched against the `partner1`/`partner2` strings
  `GET /api/families` already computes), keyboard-navigable (arrow keys +
  Enter), each result navigates straight to its page.
- **Advanced** — every field Master Plan §12 promises: given/surname
  (partial), sex, living/deceased, birth AND death year ranges, place, plus
  full-text over notes/bios (the `q` parameter already does double duty —
  see the design-log entry for why death-year-range needed no blocker).

Full decision log (the `fh-common.js` extraction and why it's scoped to only
the new pages, the "one photo store" upload-then-link philosophy, the
capture-date depth-bar fix, the Search design calls, and two real bugs found
in the browser) is in `docs/FRONTEND_DESIGN.md`'s 2026-07-05 entry — not
duplicated here.

### Depth-Bar / Design Decisions Worth Recording

- **A photo can be uploaded with no subject at all** (`POST /api/media` only
  requires `file`) — the Memories upload form takes advantage of this on
  purpose; "who this is of" is a Photo Detail "manage links" action, not a
  required upload field, matching how a real family actually digitizes a box
  of old prints.
- **The Memories upload/edit forms are the first to populate
  `capture_date_sort`**, not just `capture_date` — using the same fuzzy-date
  group (Precision/Year/Month/Day) events/vitals already use, generalized
  into `fh-common.js`. Photos uploaded through FE-2's older, simpler form
  keep falling back to upload-date ordering; that's the documented fallback
  behavior working as designed, not a regression.
- **`fh-common.js` is new, but `person.js`/`tree.js`/`people.js` are
  untouched.** Extracting shared helpers into a refactor of three already-
  shipped, browser-verified files was judged out of this brief's scope
  (unrequested, and riskier than the duplication it would remove); the new
  module exists so the THREE NEW files this WP adds don't duplicate each
  other instead.
- **Death-year range is a client-side filter, not a `BLOCKERS.md` entry** —
  `GET /api/search` has no `death_from`/`death_to` parameter, but
  `PersonListItem.death_year` is a real field on every row the server
  already returns, so filtering the already-filtered result set client-side
  is a design/implementation choice (same shape as People's client-side
  sort), not a missing capability.

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/routes/memories.py`, `app/routes/search.py` | Created | New blueprints, thin view routes |
| `app/__init__.py` | Modified | Registered both blueprints |
| `app/templates/memories/*.html`, `app/templates/search/index.html` | Created | Thin shells; all rendering is client-side |
| `app/templates/base.html` | Modified | Nav links now real; header search button + overlay; `api.js`/`fh-common.js`/`search.js` now load app-wide |
| `app/templates/dashboard.html` | Modified | Quick Add Photo/Story tiles wired to real routes |
| `app/templates/errors/{403,429,500}.html` | Modified | Task 0: dropped `.display-6` |
| `app/static/js/{memories,stories,search,fh-common}.js` | Created | New section scripts + the shared helper module |
| `app/static/css/style.css` | Modified | Task 0 strip (see design log) |
| `app/static/css/chronicle-app.css` | Modified | `.tree-subnav` generalized to `.subnav`/`.tree-subnav`; new Memories/Photo-Detail/Stories/Search sections; two browser-bug fixes (see below) |
| `app/static/js/sw.js` | Modified | Bumped the PWA shell cache version |
| `docs/openapi.yaml` | Modified | Nine new Views-tag paths |
| `docs/FRONTEND_DESIGN.md` | Modified | 2026-07-05 decision-log entry |

### Manual Testing Checklist

> Clear this section once the owner has done a browser pass and confirmed green.

- [x] Logged in as the seeded Contributor (`jo@example.com`): uploaded a
      photo with a fuzzy capture date (Chronological), confirmed it sorts
      correctly; opened Photo Detail on a seeded photo — edited metadata,
      added a link (search-as-you-type to a person), removed a link, all
      persisted and re-rendered correctly.
- [x] By Person / By Family / By Event — picker-driven views resolve to the
      right album; By Family's aggregation correctly pulled in a photo linked
      to a member's own event, not just the family's own direct links.
- [x] Stories — list, read view, "Write a Story" (title/Markdown content with
      live preview/format/shared flag/subject picker) end-to-end, then
      Edit and Delete on the same story — all correct.
- [x] Quick search (header overlay AND the `/search` page) — people and
      families both appear, arrow-key navigation highlights rows, Enter/click
      navigates to the right page.
- [x] Advanced search — every §12 field, including a death-year-range query
      and a full-text keyword query that correctly matched and linked to a
      story.
- [x] Logged in as the seeded Viewer (`pat@example.com`) — no upload forms,
      no Edit/Add-a-link/Delete anywhere in Memories or Stories, "Write a
      Story" shows the honest access message instead of a form; read/browse/
      search still fully work.
- [x] 375px viewport: Memories subnav wraps to two rows; the fuzzy-date group
      shows 2-up instead of squeezed 4-up; Photo Detail stacks image-above-
      panel; Search's Quick/Advanced tabs and every form field stack cleanly.
- [x] Zero browser console errors / CSP violations across every new page and
      both roles tested.
- [x] 239/239 tests green (nine new routes; `test_openapi.py`'s route-map
      sync test needed the matching `docs/openapi.yaml` entries, added on
      this branch).

### Two Bugs Found and Fixed in the Browser

1. **Bootstrap's breakpoint columns key off viewport width, not the
   immediate container's width.** The fuzzy-date fields squeezed unreadably
   into one row inside the 340px Photo Detail panel even on a wide desktop
   viewport, because `col-md-3` computes 25% against whatever satisfies the
   `≥768px` media query — the *viewport* — not the actual 340px container
   holding it. Fixed with `col-6 col-md-3` in the shared component (helps
   real narrow phones) plus a scoped override forcing full-width stacking
   inside `.photo-detail__panel` specifically (which is narrow
   unconditionally, regardless of viewport).
2. **The new header search button overlapped the brand wordmark at 375px.**
   `.header-actions` gained one more fixed-width child; `.brand`'s text
   doesn't shrink just from being a flex item without `min-width: 0`. Fixed
   with a `body.app-shell`-scoped media rule (shrinks the wordmark, hides the
   tagline below 400px) that leaves the public page's header (no search
   button there) completely untouched.

### A Non-Bug Worth Recording (Again): the PWA Service Worker Cache

FE-3's diary already documented `sw.js`'s cache-first `/static/` strategy as
the reason a served file being byte-correct doesn't prove the browser is
running it. This session hit the exact same trap repeatedly while iterating
on the two bugs above — `pwa.js` re-registers the service worker on every
page load, so even after manually unregistering it mid-session to force a
fresh fetch, the NEXT reload silently re-registered it and re-cached
whatever was being served at that moment. Confirming a fix required clearing
Cache Storage (or bumping `CACHE`) before every single re-check. Not a new
finding — a repeat encounter that reinforces FE-3's one. `CACHE` bumped to
`"familyhub-shell-v3"`.

### Cross-Boundary Touches

`docs/openapi.yaml`'s Views tag gained nine paths (the Memories + Search view
routes) — no other section of the spec changed, and no Flask routes/models/
services outside the two new, FE-owned blueprint files were touched. Per the
branch-per-WP protocol, this is a doc-only cross-lane edit for BE to
spot-check at merge; logged in `BLOCKERS.md` alongside a second entry noting
the `style.css` cleanup, since BE owns the call on whether to delete that
file now that it's down to four rules.

### WGU Connections

- **D276/D280** — `fh-common.js` is Jinja/JS component extraction applied to
  vanilla script files instead of a framework: one canonical
  `subjectPicker()`/`renderNoteContent()`/fuzzy-date group used by three
  pages instead of three copies.
- **D278/D279 Front-End, D281 UI Design** — the Bootstrap breakpoint bug is a
  concrete lesson in the difference between viewport-relative and
  container-relative responsive design (the "container query" gap), and the
  header-overlap bug is a concrete lesson in why flex items need
  `min-width: 0` to actually shrink instead of overflowing.
- **D286 Discrete Mathematics II / D287 Database** — By Family's aggregation
  is a small, explicit set-union computed client-side (family's direct links
  ∪ family-event links ∪ member-event links, deduplicated by media id) over
  data the server already exposes per-subject, rather than a new query.
- **D315 Security** — `renderNoteContent()` escapes raw Markdown BEFORE any
  HTML is built, same discipline as every other rendered field in this app;
  CSP-strict throughout, no inline styles/scripts anywhere in the new code.

### v2 Spring Boot Migration Notes

Every new page still follows the "Flask renders a shell, JS calls the JSON
API" split, so nothing here is thrown away in the rewrite: `MemoriesController`
and `SearchController` map directly to the two new blueprints, and
`fh-common.js`'s helpers (the subject picker, the Markdown renderer, the
fuzzy-date group) are natural candidates for shared Angular components/
pipes rather than page-specific code, since v1 already proved they're needed
in more than one place.

## FE-5 — User area: My Contributions + Account & Security

**Branch:** `fe5-user-area`
**Date:** 2026-07-06
**Status:** Implementation complete; full suite green; pending owner review + merge.

### What FE-5 Delivered

Two new pages under a new `app/routes/account.py` blueprint (`GET /account`,
`GET /account/contributions`), both client-rendered by one new script,
`app/static/js/account.js`, against the Account tag the backend shipped in
`ffe6cb1`. The user menu's "Account & Security" entry now points here instead
of straight at `/auth/change-password`, and gained a new "My Contributions"
entry (`app/templates/base.html`).

**My Contributions** (`/account/contributions`) — a member's own audit rows,
never anyone else's (`GET /api/me/contributions` takes no `actor_id`
parameter anywhere in this file, by construction — that side door is the
Curator-only `/api/activity`):

- **Summary cards** (`.stat-strip`) — Total contributions, then People/
  Families/Events/Photos/Sources groups, each a straight sum of real
  `summary.by_subject_type` buckets (no per-cell action×type fetch, no
  invented numbers — the brief's "every count must come from the real
  summary" read literally). Cards hide entirely for a member who's never
  contributed; the list shows an honest "You haven't added anything yet" +
  Quick Add invite instead, rather than a wall of zeroes.
- **The list** — paginated (`page`/`per_page`, Prev/Next, same shape as
  `people.js`'s pager) and filterable by action and subject type
  (`.chip-group`, same idiom as People's living-status filter). Each row
  resolves its subject by fetching the real record — `GET /api/individuals`,
  `/api/families`, `/api/media`, `/api/notes`, `/api/events` all already
  soft-delete-aware (`get_or_404` 404s a deleted row) — so a link only ever
  appears for a subject that's still there, and a since-deleted one renders
  unlinked with "(since removed)" instead of a dead link or a 404. An event
  has no page of its own, so it resolves to ITS OWN subject (person or
  family), the same idea `fh-common.js`'s `resolveLinkTarget` already uses
  for a photo's "linked to" chips. Subject types with no page at all
  (source/citation/name/user/backup/family_child) get a friendly label and
  no link — named, not faked.
- **Media rows needed a real "Memories detail" destination that didn't quite
  exist yet** — `memories.js`'s Photo Detail overlay only ever opened from a
  click inside an already-loaded album grid, no shareable URL. Added a small,
  additive `?photo=` query param to `/memories` (`app/static/js/memories.js`'s
  `DOMContentLoaded` handler) that calls the SAME `openPhotoDetail(id)` the
  grid's own click handler uses — it fetches by id directly, so it works
  regardless of which album view is the page default. Documented as a
  parameter on the existing `/memories` Views entry, not a new route.

**Account & Security** (`/account`) — five independently-rendered sections
over one `GET /api/me` snapshot (progressive disclosure, not a settings
dump):

- **Profile** — display name + a searchable timezone picker. The picker uses
  `Intl.supportedValuesOf('timeZone')` — the BROWSER's own IANA database,
  the same source `zoneinfo.available_timezones()` validates against
  server-side (`account_service.update_me`) — so there's no bundled zone
  list to keep in sync; a short hand-picked fallback list covers browsers
  without that API (Safari <15.4). "Site default" is a real chip, not a
  blank field. Saves via `PUT /api/me`.
- **Role** — a badge (same admin/curator/contributor/viewer → color mapping
  as the admin Users tab) + "Request a role change," a picker that excludes
  the member's OWN current role (avoids a guaranteed 400) and renders the
  409 "already have a pending request" state as calm text, not a form error.
- **Email** — address + verified/unverified badge, resend-verification,
  and change-email (new address + current password). `GET /api/me` has no
  persistent "pending change" field — only the change-email POST response
  carries `pending_email` — so rather than fake one, the pending address is
  remembered client-side (`localStorage`, keyed by user id) and cleared the
  moment a later `/api/me` snapshot shows `email` actually caught up to it
  (the verification link was clicked). An honest derivation from data the
  API really returns, not a guessed field.
- **Password** — links to the existing `/auth/change-password` flow rather
  than rebuilding it. That form had NO `autocomplete` attributes on any of
  its three password fields — a password manager can't tell "current" from
  "new" without them. Fixed via WTForms `render_kw` on `ChangePasswordForm`
  (`app/forms/auth_forms.py`) — the brief's "template-only fix, allowed"
  covers this: the only observable effect is the rendered HTML attribute,
  same as any other Jinja-side tweak.
- **Delete account** — "delete = anonymize," stated plainly before the
  password field, not after. Success replaces the confirm form with a brief
  "signing you out…" message before redirecting to `/` (which renders fine
  logged-out) — no page ever tries to render as an authenticated user with
  no session.

### Depth-Bar / Design Decisions Worth Recording

- **Family gets a real link too, not just person/media/note.** The brief's
  examples only named those three, but `/tree/family/{id}` (the FE-3 Family
  Group sheet) is exactly the same kind of real, already-shipped page — "a
  page exists" is the actual rule, and family clears it. No family-subject
  audit row existed in seed data to click through in the browser, but the
  resolver is the identical fetch-then-catch shape already proven for
  individual/media/note.
- **`window.alert()` / blocking dialogs, deliberately avoided on this page.**
  Several existing pages (`memories.js`'s unlink/delete-photo failures) use
  `window.alert()` for button-triggered errors, and it would have been the
  path of least resistance here too. Found in the browser, not in review: an
  alert for the resend-verification 503 blocked the automated preview tool
  completely (a real modal, same as it would a real user mid-task) on a page
  the brief explicitly wants to "feel calm, not like a settings dump." Every
  error path on this page now uses the SAME inline `.alert-danger`
  (`showInlineError`/`alertFormError`, both already in `fh-common.js`) the
  form-submit paths already used — one consistent error idiom for the whole
  page instead of two. `window.confirm()` for the final delete gate is kept
  (a deliberate blocking yes/no, not a dismissable notice, and matches the
  existing delete-photo precedent).
- **`.chip-group` needed `flex-wrap: wrap`.** The existing rule (People's
  3-chip living-status filter) never needed to wrap at any real width. My
  Contributions' subject-type group has 6 chips, which overflowed off a
  375px viewport instead of dropping to a second row — a real bug the
  browser pass caught that a wider desktop check wouldn't have. Fixed in the
  shared class (`chronicle-app.css`), verified People's own filter still
  renders on one line afterward (no regression).
- **A `label` immediately before a `.chip-group` sits on the same line.**
  Bootstrap's `.form-label` is `display: inline-block`; `.chip-group` is
  `inline-flex` — nothing forces a line break between them unless something
  else in the pair is block-level. Every other `.chip-group` in the app is
  preceded by a plain `<div>`, not a `<label>`, so this never surfaced
  before the Timezone field. Fixed with `d-block` on that one label rather
  than changing `.form-label` globally (Bootstrap fields elsewhere may rely
  on the inline-block default).

### Files Created or Modified

| File | Status | Notes |
|---|---|---|
| `app/routes/account.py` | Created | New blueprint, two thin view routes |
| `app/__init__.py` | Modified | Registered the blueprint |
| `app/templates/account/{security,contributions,_subnav}.html` | Created | Thin shells; all rendering is client-side |
| `app/static/js/account.js` | Created | Both pages' logic (DOM-guarded, one file) |
| `app/templates/base.html` | Modified | User menu: "Account & Security" repointed, "My Contributions" added |
| `app/forms/auth_forms.py` | Modified | `ChangePasswordForm` render_kw autocomplete attributes |
| `app/static/js/memories.js` | Modified | `?photo=` deep-link support (DOMContentLoaded) |
| `app/static/css/chronicle-app.css` | Modified | New Account & Security section; `.chip-group` flex-wrap fix |
| `app/static/js/sw.js` | Modified | Bumped the PWA shell cache version |
| `docs/openapi.yaml` | Modified | Two new Views-tag paths; `?photo=` param on the existing `/memories` entry |
| `docs/FRONTEND_DESIGN.md` | Modified | 2026-07-06 decision-log entry |
| `BLOCKERS.md` | Modified | Style.css entry header label fixed (`[OPEN]` → `[RESOLVED]`, body already said resolved); new FE-5 cross-lane entry |

### Manual Testing Checklist

> Clear this section once the owner has done a browser pass and confirmed green.

- [x] Profile: changed display name + timezone (searched "chicago" → picked
      `America/Chicago`) as a throwaway seeded user; `GET /api/me` confirmed
      the save persisted.
- [x] Role: requested a role change, saw the success state; requested again
      without reloading — the 409 "already have a pending request" state
      rendered correctly.
- [x] Email: resend-verification against a dev server with no mail
      configured rendered the 503 as an inline error, not a crash or an
      alert; change-email likewise. Simulated the pending → verified
      transition directly against the dev DB (set `pending_email`
      client-side, then flipped `email` server-side to match) — the pending
      banner appeared, then correctly cleared itself on the next load once
      `email` caught up.
- [x] Delete account: on a disposable seeded user (not `jo`/`robert`/`pat`,
      never the admin) — wrong password showed an inline 403, correct
      password anonymized the row (verified in the DB: display_name "Former
      member", email `deleted-user-<id>@familyhub.invalid`, `is_active`
      false), the session ended (`GET /api/me` → 401 after), and the browser
      landed on the public `/` without error.
- [x] My Contributions: real seeded audit rows for three different accounts
      exercised every resolver branch — a live photo (linked, opened via the
      new `?photo=` deep link and confirmed the Photo Detail overlay opens),
      a live person + a `Birth: <name>` event (both linked to the Person
      Page), a citation (named, unlinked — no page exists), and a
      create-then-delete note pair (BOTH rows rendered "(since removed)",
      including the original "Added" row for the now-gone story). Filters
      (action + subject type) and pagination (24 rows, default 20/page)
      confirmed against real data; the true empty state (a Viewer with zero
      rows) showed the honest "haven't added anything yet" + Quick Add
      invite with no summary cards, not a wall of zeroes.
- [x] 375px viewport: both pages checked full-page (a taller-than-viewport
      resize, since this environment's page scroll didn't respond to
      `window.scrollTo`/`body.scrollTop` from injected script — a tooling
      quirk, not an app bug). Found and fixed the `.chip-group` wrap bug and
      the Timezone label/chip collision above during this pass.
- [x] Zero browser console errors across every page/role tested. The only
      failed network requests observed were the EXPECTED ones — soft-deleted
      subjects' `GET /api/notes/{id}` 404s (caught, rendered "(since
      removed)") and two seeded media rows with no real file on disk
      (`/file`/`/thumb` 404s, a pre-existing seed-data gap, not something
      this branch touched).
- [x] 260/260 tests green (no backend logic touched; the two new Views-tag
      paths keep `test_openapi.py`'s route↔spec sync test passing).

### Cross-Boundary Touches

`docs/openapi.yaml` gained two Views-tag paths (`/account`,
`/account/contributions`) plus a `photo` query param on the existing
`/memories` entry — no Flask routes/models/services outside the one new,
FE-owned blueprint file were touched. Logged in `BLOCKERS.md` for BE to
spot-check at merge, same protocol as FE-3/FE-4.

### WGU Connections

- **D315 Security** — the `autocomplete` fix on `ChangePasswordForm` is a
  concrete password-manager-interoperability lesson: browsers/managers key
  "which field is the NEW password" off this attribute, not label text,
  field name, or field order.
- **D278/D279 Front-End, D281 UI Design** — the `.chip-group` wrap bug and
  the label/chip collision are both instances of the same lesson FE-3/FE-4
  already logged once each: a component that's only ever been tested with a
  short list of items, or a specific preceding sibling, can hide a layout
  assumption that a wider real-world case (more chips, a `<label>` instead
  of a `<div>`) breaks.
- **D287 Database / ADR-0001** — the "since removed" resolution leans
  directly on `get_or_404`'s soft-delete filtering being applied uniformly
  across every resource GET-by-id endpoint; the front end never has to know
  a row is soft-deleted vs. hard-gone, it just gets the same 404 either way.
- **D286 Back-End (client/server contract)** — the pending-email
  client-side derivation is a small case study in working WITH an API
  contract's actual shape instead of wishing for a field it doesn't have:
  `pending_email` only ever appears on the POST response, so the client
  remembers it and reconciles against the next GET rather than inventing a
  GET-side field the backend was never asked to add.

### v2 Spring Boot Migration Notes

Same split as every prior WP: `AccountController.java`, two `@GetMapping`s
returning view names for Angular's router. The one piece worth flagging for
the rewrite is the pending-email client-side reconciliation — a v2 built on
a real notification/event system (Master Plan §11) would likely push a
server-driven "email changed" event instead, making this localStorage trick
unnecessary. Not a lock-in either way: v1's approach only reads
already-public fields (`email`) and writes to no server state.

---

## FE-6 — Admin Console (Dashboard, Users, Inboxes, Settings, Backups, Activity)

**Branch:** `fe6-admin-console`
**Date:** 2026-07-06
**Status:** Implementation complete; full suite green; pending owner review + merge.

### What FE-6 Delivered

The `/admin/*` surface predates Chronicle — every page was a plain Bootstrap
template with server-fetched data. This run rebuilds it as a native-Chronicle,
client-rendered console (one new script, `app/static/js/admin.js`, DOM-guarded
per page like every prior FE script) over the AdminApi/Inbox/WriteControl
tags, while keeping four already-working server-rendered forms exactly as they
were (see "A Deliberate Split," below).

**Seven pages, one shared `admin/_subnav.html`** (role-gated: every tab but
Activity only renders `{% if current_user.is_admin %}`; Activity renders
`{% if current_user.has_role('curator') %}` — so a Curator who isn't also an
Admin sees a ONE-tab subnav, never a menu of links that would 403):

- **Dashboard** (`/admin`) — `GET /api/stats` (all ten counts + storage,
  formatted with a new `formatBytes` helper), `GET /api/admin/backups`
  (last/next run, disk-free percentage), and the two queues that need eyes
  (`GET /api/suggestions?status=new`, `GET /api/role-requests?status=pending`),
  each showing a count + newest few + a one-click jump link to its own page.
- **Users** (`/admin/users`) — `GET /api/admin/users` rendered as a table
  (role/linked-person/status/member-since badges), with three real actions per
  row: email-a-reset-link (`POST /api/admin/users/{id}/reset-password`),
  secure change-email with step-up (`POST /api/admin/users/{id}/change-email`,
  an inline drawer under the row), and link/unlink to a person
  (`PUT`/`DELETE /api/users/{id}/individual`, `subjectPicker()` reused from
  `fh-common.js`, a 409 rendered as "already linked to another account," not a
  generic error). The read-only role→permission matrix
  (`GET /api/permissions/matrix`) renders below as a small table — legible,
  not editable, no v2 tease.
- **Suggestions Inbox** (`/admin/suggestions`) — filterable
  (`status`/`topic`/`prioritized` chips) over `GET /api/suggestions`; each row
  is its own inline triage form (`PUT /api/suggestions/{id}`) with a "Saved ✓"
  flash, not a separate edit page.
- **Role Requests** (`/admin/role-requests`) — one unfiltered
  `GET /api/role-requests` fetch, split client-side into a Pending block
  (Approve/Deny buttons) and a Decided History block (chip-filterable
  approved/denied) — the brief's "pending queue... show already-decided
  history" read as two sections, not one filtered list.
- **Settings** (`/admin/config`) — the grouped, config-as-data settings
  (branding/defaults/security/email) over `GET`/`PUT /api/settings`, as FOUR
  independent per-group forms rather than one big form, since
  `settings_service.update_settings` genuinely supports a partial `{key:
  value}` patch — a mistake in Security never blocks saving Branding. See "A
  Deliberate Split" for why this is a new URL, not `/admin/settings`.
- **Backups** (`/admin/backups`) — overview, back-up-now with its inline
  verification report, a schedule editor, and the restore flow rendered as
  the gravest action in the app (`.panel--danger`, step-up password + an
  explicit confirm checkbox, copy stating a safety backup is taken first).
  Downloading a zip stays a plain `<a href>` to the existing
  `admin.download_backup` route — a file download needs no JSON round trip.
- **Activity** (`/admin/activity`) — the full audit trail, paginated and
  filterable (action/subject-type chips, an Admin-only actor dropdown, date
  range), with ONE contextual action per row: `Restore` on a `delete`-action
  row (`POST /api/restore`), `Revert` on everything else revertible
  (`POST /api/audit/{id}/revert`) — showing both on the same row would do
  near-identical things for little benefit. **Curator+, not Admin-only** — see
  "The Activity Access Change," below.

### A Deliberate Split: Two Settings Pages, Not One

`GET /api/settings` (branding/defaults/security/email) and the PRE-EXISTING
`/admin/settings` HTML form (tagline/about_text/contact_text/the dashboard
hero image) are two independent surfaces in the backend today —
`settings_service.py` has always had two parallel systems (`KNOWN_KEYS` +
`get_all()` for the legacy one, `SETTING_GROUPS` + `editable_settings()` for
the new one) that share no keys and no endpoint. Rather than strand the
legacy form's real, still-used capability (the About page and the dashboard
banner both read it) by relocating it, or bury the new grouped console
inside its page, the new console lives at a fresh URL (`/admin/config`,
labeled "Settings" in the subnav) with a one-line link to the legacy page
(relabeled "Site Text" in the subnav) — **and the legacy page's URL, form,
and behavior are completely untouched**, which is also why
`tests/test_admin.py`'s `test_site_settings_save_and_show` and
`test_hero_upload_processed_and_walled` (both POST to `/admin/settings`)
needed no changes at all. The legacy Users forms (`/admin/users/new`,
`/admin/users/{id}/edit`, `/admin/users/{id}/reset-password`) got the same
"restyle, don't relocate" treatment — restyled for free by the shared
Chronicle stylesheet cascade (same mechanism WP5 used app-wide), plus a new
`{% include "admin/_subnav.html" %}` on each so navigating in and back out
of them feels like one console, not a detour.

Two legacy routes are now unlinked from the console's nav (superseded by a
better version, not deleted): `/admin/users/{id}/reset-password` (set a
password directly, by hand) is superseded by the Users page's emailed
reset-link action; `/admin/backups/run` (a flash-redirect POST) is superseded
by the Backups page's `POST /api/admin/backups/run` with an inline report.
Both routes still work if visited directly — removing a working feature
nobody asked to remove would be a bigger change than this brief called for.

### The Activity Access Change

`app/routes/admin.py`'s `activity()` route moved from `@admin_required` to
`@role_required(Role.CURATOR)` — the brief's explicit instruction, backed by
the 2026-07-03 BLOCKERS resolution that already authorized a Curator-visible
Activity nav entry once FE built this page. `base.html`'s user menu now shows
"Activity" (not "Admin") to a Curator who isn't also an Admin. This DID
require updating one pre-existing test:
`tests/test_wp5_authz_alignment.py`'s `ADMIN_ONLY_GET_ENDPOINTS` had
`/admin/activity` listed as admin-only (written before this page existed in
its Curator+ form) — moved to `CURATOR_PLUS_GET_ENDPOINTS` alongside its own
API (`/api/activity`), which the same file already tests the exact same way.
Logged transparently in `BLOCKERS.md`'s review entry, same rule as any other
touch outside this session's own new files.

### Two Bugs Found and Fixed in the Browser (Not Caught by pytest)

1. **The guarded restore's success message was invisible.** The restore
   handler set `form.outerHTML` to a "Restored ✓ — safety backup saved as…"
   confirmation, then immediately called `load()` to refresh the rest of the
   page — but `load()` unconditionally re-rendered the restore area too,
   silently overwriting the confirmation with a fresh form in the SAME
   synchronous callback, so a real admin would never see it. Fixed by giving
   `load()` a `{ skipRestoreArea: true }` option the restore handler passes,
   so the overview/schedule/backup-list refresh normally while the
   confirmation message persists until the next real page load. Caught by
   scripting the actual restore flow against the dev server, not by reading
   the code — the bug was invisible in isolation (`renderRestoreArea` looked
   correct on its own) and only showed up watching the two calls run back to
   back.
2. **A restored/reverted subject kept showing "(since removed)" after the
   very action that un-deleted it.** The Activity page's `resolveSubject()`
   memoizes each `subject_type:subject_id` lookup in `resolveCache` so a
   subject referenced by multiple rows is only fetched once — but the cache
   never expired, so once a subject resolved as `{removed: true}` (its normal
   deleted state), clicking Restore or Revert on that very row changed the
   real data but not the cached client-side verdict, and the row (now current)
   kept reading "since removed" until a full page reload. Fixed by deleting
   the specific `resolveCache` entry right after a successful restore/revert,
   which needed the Revert button to also carry `data-subject-type`/
   `data-subject-id` (previously it only had `data-audit-id`, since the
   revert endpoint's response doesn't include the subject type). Verified by
   restoring, then re-deleting, then re-restoring the same test row in one
   browser session and confirming each state showed correctly without a
   reload — the bug only shows up on a SECOND action against the same
   subject in one session, which is exactly the kind of thing pytest's
   single-request-per-test shape doesn't naturally exercise.

Also re-encountered, not re-caused: the same PWA service-worker cache trap
FE-3/FE-4 already documented — a fix on disk doesn't reach the running page
until the Cache Storage entry is cleared or `CACHE` is bumped again, even
"live-reloading" via `window.location.reload()`. Cleared the cache manually
mid-session while iterating on the two bugs above; the version bump below
covers real returning members.

### Files Created or Modified

`app/routes/admin.py` (rewritten — seven new/changed thin views, four legacy
views kept verbatim); `app/templates/admin/_subnav.html`,
`admin/{dashboard,suggestions,role_requests,config}.html` (new);
`admin/{users,backups,activity}.html` (rebuilt); `admin/{new_user,edit_user,
reset_password,settings}.html` (subnav include added, nothing else changed);
`app/static/js/admin.js` (new — all seven pages); `app/static/css/
chronicle-app.css` (new §16: `.btn-danger`/`.text-bg-warning`/
`.text-bg-danger` repaints, a detail-row background rule); `app/templates/
base.html` (Admin nav link repointed to the dashboard; new Curator-only
Activity nav entry); `app/static/js/sw.js` (cache version bump);
`tests/test_wp5_authz_alignment.py` (`/admin/activity` moved lists — see "The
Activity Access Change"); `docs/openapi.yaml` (Admin tag trimmed to the four
kept legacy flows + notes on the two superseded-but-reachable ones; seven
Views-tag entries, new + moved).

### Manual Testing Checklist

- [x] Dashboard: real stats/backup-health/queues rendered correctly against
      the dev DB (10 people, a pending role request, an empty suggestions
      inbox before one was filed).
- [x] Users: linked a real person via the picker, confirmed the 409 path by
      trying to link the SAME person to a second account ("already linked to
      another account"), then unlinked — all three states re-rendered
      correctly with no page reload.
- [x] Suggestions: filed a real suggestion via the API, triaged it
      (status → in_progress, priority → 1) inline, confirmed via a fresh
      `GET /api/suggestions`.
- [x] Role Requests: approved the real seeded pending request; it moved from
      Pending into Decided History with the correct actor/timestamp.
- [x] Settings: a sub-6 `min_password_length` was actually blocked TWICE —
      first by the number input's own `min="6"` (native HTML5 validation,
      never even reaches the server), and, after deliberately removing that
      attribute to test the fallback, by the server's 400 with the
      field-highlighting heuristic working correctly (`is-invalid` class +
      inline message). A valid save showed "Saved ✓".
- [x] Backups: ran a real backup (report showed table/file counts), edited
      the schedule, and ran a real guarded restore twice (wrong password path
      not separately re-tested this session — covered by `admin_service`'s
      own `_step_up` pytest coverage) — found and fixed the invisible-
      success-message bug above in the process.
- [x] Activity: filtered by action/subject-type/date, exercised both Restore
      and Revert on real rows (a story create → delete → restore → revert →
      revert chain), confirmed the actor dropdown appears for Admin and is
      ABSENT for Curator (fetching `/api/admin/users` would 403 for them) —
      found and fixed the stale-cache bug above in the process.
- [x] Role matrix: Admin sees Curator holding `revert` but not `administer`,
      matching `permissions.ROLE_PERMISSIONS` exactly.
- [x] Role gating, scripted end to end: as Curator, every `/admin/*` path
      403'd except `/admin/activity` (200); the user menu showed "Activity,"
      not "Admin." As Contributor, EVERY `/admin/*` path 403'd including
      `/admin/activity`, and the user menu showed neither link.
- [x] 375px viewport: the seven-tab subnav wraps to three rows cleanly; the
      Users table scrolls horizontally with Reset Link/Change Email fully
      reachable past the fold (`scrollWidth` 1134px vs. `clientWidth` 327px,
      confirmed reachable by scrolling all the way right); the Backups
      restore panel's form fields stack full-width with no overflow.
- [x] Zero browser console errors across every page and role tested.
- [x] 260/260 tests green, including the one pre-existing test this branch
      had to update (see "The Activity Access Change").

### Cross-Boundary Touches

`app/routes/admin.py` (rewritten, thin views only — no business logic moved;
every mutation still goes through the existing `user_service`/
`backup_service`/`settings_service`/`audit_service` calls verbatim) and
`docs/openapi.yaml` (Admin tag trimmed + reworded, seven Views-tag entries
new/moved) are the expected FE-owned route/doc touches, same protocol as
FE-3/FE-4/FE-5. The one touch outside that pattern —
`tests/test_wp5_authz_alignment.py`, a BE-authored test file — is logged in
`BLOCKERS.md`'s review entry in full, since it's a direct, necessary
consequence of the brief's own explicitly-authorized Activity access change,
not incidental scope creep: the alternative would have been leaving a stale
test permanently red or silently wrong.

### WGU Connections

- **D315 Security** — the permission-matrix rendering and the Curator-only
  Activity nav gate are both `permissions.py`'s "role = a bundle of
  permission flags" made visible in the UI; the actor filter's admin-only
  gate is the same principle applied to a UI AFFORDANCE, not just a route
  (offering a control whose data source would 403 for the viewer is its own
  small access-control bug class, distinct from gating the page itself).
- **D276 Web Development Foundations** — the four-form Settings page is a
  concrete lesson in matching UI granularity to the server's actual
  transaction boundary: `update_settings` supports a partial patch, so four
  small forms are MORE correct than one big one, not just a stylistic choice.
- **D287 Database / ADR-0001** — the Restore-vs-Revert row action split
  mirrors `write_control.py`'s own two distinct code paths (`restore`: un-
  delete a currently-soft-deleted row by id; `revert`: replay a specific
  audit entry's `before_json`) — the UI reflects a real semantic difference
  in the data model, not an arbitrary UX choice.
- **D280 JavaScript Programming** — both browser-found bugs this session are
  the same class of lesson: a synchronous "set success message, then
  refresh everything" sequence can silently clobber its own output, and a
  memoization cache is only as correct as its invalidation story — "cache the
  result" and "the result can become stale" have to be designed together,
  not the first one alone.

### v2 Spring Boot Migration Notes

`AdminController.java` (dashboard/users/suggestions/role-requests/settings/
backups/activity — seven thin `@GetMapping`s) plus small sibling
`@Controller`s for the four kept legacy forms, exactly the same split as
every prior WP. The permission matrix's read-only rendering is a direct
preview of v2's `role_permissions` table + an editable admin UI over it —
v1 intentionally ships the READ half only, per the brief. Nothing about the
"two settings systems" split needs to survive into v2; that's a natural
place for the Java rewrite to unify `site_settings` into one coherent
schema, since v2 has no legacy HTML form dragging a naming/shape convention
forward from WP1.

---

## FE — Punch-list fix run (404 heading, pending_email swap, BLOCKERS labels)

**Branch:** `fe-fix-punchlist`
**Date:** 2026-07-06
**Status:** Complete; full suite green.

Three small items from the 2026-07-05 punch list plus the backend's new
`GET /api/me` field:

1. `app/templates/errors/404.html` — removed the leftover `display-6` class
   from the `<h1>`, matching 403/429/500 (stripped from those three on FE-4,
   404 just wasn't on that run's list).
2. `app/static/js/account.js` — `GET /api/me` now returns `pending_email`
   (set by `POST /api/me/change-email`, cleared on verification), so the
   FE-5 localStorage stopgap (`pendingEmailKey`, the per-browser cache) is
   gone. `renderEmail(me)` reads `me.pending_email` directly; the change-
   email submit handler re-fetches `GET /api/me` after a successful POST and
   re-renders from that fresh snapshot instead of hand-patching local state.
   Same user-visible behavior, except the pending notice now survives
   across browsers/devices instead of living in one browser's localStorage.
   Any orphaned `fh_pending_email_*` keys in existing browsers are harmless
   dead weight — not worth a migration.
3. `BLOCKERS.md` — two entries (FE-6's and FE-5's BE-review items) had
   Status lines already saying RESOLVED 2026-07-06 but the `###` header
   still said `[OPEN]`; fixed both header labels only, no other line
   touched.
4. `app/static/js/sw.js` — cache bump (`familyhub-shell-v6` → `v7`) for the
   `account.js` change.

### v2 Spring Boot Migration Notes

The FE-5 diary entry above already flagged the localStorage reconciliation
as the one piece not worth carrying into v2 — this session removes it a
build early, once the backend field existed, rather than waiting for a v2
rewrite to make it obsolete. Nothing else new here.
