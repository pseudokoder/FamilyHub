# FamilyHub — Frontend Design

> **Owned by Cowork.** This is the living visual + UX design language for the v1
> ("Full") site — palette, typography, dark/light, motion, components, and the
> design-decision record behind them. Cowork evolves it freely **within** the
> durable visual constraints in **Master Plan §5B**, under §11 **Tier-2** change
> control (change directly, log it here, no Master Plan revision). A change that
> would breach a §5B constraint, or that needs new functionality/endpoints,
> **escalates to Tier 1** (Master Plan) — see §11. Code does not write this file.

## Design Language

**Chronicle** — an antique expedition journal brought to life.

### Palette

> **Corrected 2026-07-04 (WP5):** this table had drifted from the actual
> shipped tokens in `app/static/css/chronicle-main.css` — it described an
> earlier iteration. The table below is the real `:root` block; treat the CSS
> file as the source of truth going forward and fix this table if it drifts
> again.

| Token          | Hex       | Role                                         |
|----------------|-----------|-----------------------------------------------|
| `--paper`      | `#efe1c6` | Page background — aged parchment              |
| `--paper-2`    | `#e6d6b6` | Deeper parchment — banded sections, hover     |
| `--card`       | `#f6edd6` | Card/panel fill (dossier, frame-card, panels) |
| `--frame`      | `#211a13` | Near-black — dark plates (catalog, title card)|
| `--ink`        | `#2a2014` | Primary text                                  |
| `--ink-soft`   | `#5f5037` | Secondary text, body copy                     |
| `--ink-faint`  | `#6f5b40` | Tertiary text — meta, labels                  |
| `--rust`       | `#9d3b2c` | Archival red — primary accent, CTAs           |
| `--rust-dk`    | `#7d2c20` | Rust hover/active state                       |
| `--amber`      | `#bd7a2a` | Sepia gold — decorative accents, 2nd accent   |
| `--sepia`      | `#a9763f` | Warm neutral accent                           |
| `--blue`       | `#355e7c` | Antique map blue — cool trim accent (AA)      |
| `--blue-lt`    | `#7ea9c6` | Lighter blue — text/lines on dark frames      |

`--on-frame` (`#f0e4cf`) / `--on-frame-soft` (`#c9b896`) are the near-white
text tones used on dark (`--frame`) backgrounds. Dark section backgrounds use
`--frame`; the catalog plate and closing title card are the main examples.

### Typography

All fonts are **self-hosted** (woff2, `app/static/fonts/`) — no CDN calls.

| Face              | Weight(s)    | Role                                     |
|-------------------|--------------|------------------------------------------|
| **Old Standard TT** | 400, 700, italic 400 | Display headings, masthead title |
| **Spectral**      | 300, 400, 500, 600 | Body text, long-form captions        |
| **Special Elite** | 400          | Typewriter / "stamp" accent labels       |

All unicode ranges covered (cyrillic-ext, cyrillic, vietnamese, latin-ext,
latin) for Old Standard TT and Special Elite; Spectral covers the same five
ranges at all four weights.

### Motion & Atmosphere

- **Intro splash**: full-viewport MP4 (`animation_2.mp4`) auto-plays muted on
  first visit; fades to the body once the animation ends.
- **Scroll-reveal**: `.reveal` elements transition from `opacity: 0; translateY(30px)`
  to visible over 0.6 s as they enter the viewport (IntersectionObserver).
- **Map-route timeline**: SVG path draws itself from start → end as the section
  enters the viewport; nodes pop in sequentially; hovering a node shows a photo
  card that appears from below.
- `@media (prefers-reduced-motion: reduce)` disables all transitions and
  auto-plays; the splash video is hidden.

### Visual Motifs

- **Rubber-stamp badges**: "VERIFIED", "RESTRICTED", "FAMILY ARCHIVE" etc.,
  rendered with SVG clip-path or CSS + Special Elite; rotated slightly off-axis.
- **Photo placeholders / toned cameos**: photos carry CSS custom properties
  `--p1`/`--p2` (duotone palette) applied via JS `el.style.setProperty()` so
  they obey the strict CSP without any inline `style` attributes.
- **Dossier card**: antique file-folder aesthetic — tab header, rope-and-seal
  stamp, "CLASSIFIED" ribbon.
- **Hero genealogy tree**: positioned nodes with photo cameos and ink-line
  connectors, rendered absolutely within a fixed-size canvas element.
- **Aged paper texture**: achieved purely via CSS gradient overlays and
  `background-color`; no texture image required.

---

## Design Decision Log

### 2026-06-28 — Chronicle design language adopted as FamilyHub v1 theme

**What changed:** The public home page (`/`) uses the Chronicle HTML/CSS/JS
design as a standalone Jinja template (`app/templates/index.html`) that does not
extend `base.html`. The authenticated dashboard continues to use Bootstrap via
`base.html`. Chronicle is the public face; Bootstrap is the logged-in workspace.

**Why:** Chronicle's antique-expedition aesthetic maps directly to the §5B
design brief ("cross-generational warmth, characterful, Cinephile/Datumology
quality bar, calm by design, generous whitespace"). It is not a clone —
it has its own strong visual identity. The decision was judged a Tier-2
design choice (within §5B constraints; no new endpoints; no Master Plan scope
change) and is recorded here accordingly.

**Files created/changed:**
- `app/templates/index.html` — replaced with Chronicle standalone template
- `app/templates/dashboard.html` — new; carries authenticated Bootstrap dashboard
- `app/routes/main.py` — one-line routing change (FE cross-boundary touch,
  logged in BLOCKERS.md for BE review)
- `app/static/css/chronicle-main.css` — Chronicle design tokens + layout
- `app/static/css/chronicle-components.css` — Chronicle component styles
- `app/static/css/fonts.css` — 37 @font-face rules for self-hosted woff2 fonts
- `app/static/js/chronicle.js` — CSP-compliant JS (inline styles removed,
  CSS custom properties applied via `el.style.setProperty()`)
- `app/static/fonts/` — 37 woff2 font files (Old Standard TT, Spectral,
  Special Elite)
- `app/static/img/` — antique-map.jpg, world-map-vintage.jpg, logo.jpg,
  favicon.png, apple-touch-icon.png
- `app/static/videos/animation_2.mp4` — intro splash

**CSP compliance approach:** The strict CSP (`style-src 'self'`) forbids inline
`style="..."` attributes. All inline styles in the original Chronicle template
were converted to either (a) a CSS class in `chronicle-main.css` /
`chronicle-components.css`, or (b) `data-p1`/`data-p2` attributes read by the
`applyTones()` JS helper. Tree-node positions (`left`/`top`) were converted to
`data-x`/`data-y` and applied via `el.style.left = el.dataset.x` at
DOMContentLoaded — JS property writes are not blocked by CSP.

**Mock data:** `SAMPLE_DATA` in `chronicle.js` (Rivera/Okafor/Vega family)
is kept exactly as-is; it drives all rendered sections (tree, dossier, people
sheet, collections, photo wall, timeline, catalog). It will be replaced by real
API calls in a future WP.

---

### 2026-07-03 — WP4: authenticated app shell, Home, and People (Bootstrap workspace)

**What changed:** built the logged-in app shell per the WP4 brief:
- `app/templates/base.html` — new primary nav (Home · Tree · People · Memories ·
  Search) + a user-menu dropdown (Account & Security · Suggest an idea ·
  Admin[gated] · Log Out), brand pulled from `site_settings` via a new
  `app.context_processor` (`app/__init__.py`).
- `app/templates/dashboard.html` (Home) — Quick Add row, On This Day, a small
  stat strip, and Recent Activity, all client-fetched from the WP2 JSON API by
  `app/static/js/home.js`.
- `app/routes/people.py` (new blueprint) + `app/templates/people/*` — Find/
  filter/sort/paginate (`people/index.html`) and a depth-complete Register
  form (`people/new.html`, `people/_fuzzy_date_fields.html`), both driven by
  `app/static/js/people.js`.
- `app/static/js/api.js` — the one shared `apiFetch()` helper (CSRF header +
  `credentials: same-origin` + JSON body handling) every authenticated page's
  JS now uses.
- `app/templates/coming_soon.html` + `main.coming_soon` — one shared
  placeholder route for every nav/menu destination this WP doesn't build
  (Tree, Memories, global Search, Account & Security's fuller "User area",
  Suggest an idea, the Person Page's "See all activity" link, and the Quick
  Add Photo/Source/Story tiles). Person creation (`/people/new`) and the
  People list (`/people`) are real; the Person Page (`/people/<id>`) is a real,
  stable, per-id route with placeholder content (FE-2 fills it in).

**This continues Bootstrap, not Chronicle, on purpose.** §5B's design-brief
constraints (elderly-accessible, cross-generational warmth, "calm by design")
are explicitly **deferred to the end of v1** for this WP per the build brief —
functional, contract-wired pages now, visual polish later. `style.css` picked
up a small, plain set of classes (quick-add tiles, on-this-day rows, the stat
strip, filter chips, person rows) using the existing elderly-first tokens
(big type, big tap targets, obvious focus rings) already in that file — no
Chronicle tokens, motifs, or fonts were touched. The "Calm-by-design on
interior pages" and "Cross-generational tone" parking-lot items below still
apply to a *future* visual pass over these same templates.

**Depth-bar decisions (§5A) worth recording:**
- **Register Person is JS-orchestrated, not a Flask POST route.** The form
  posts nothing itself; `people.js` calls `POST /api/individuals` (name +
  sex + living), then — only if a year was entered — find-or-creates a
  `Place` (`POST /api/places`, matched case-insensitively against the already-
  loaded list) and `POST /api/events` for BIRT/DEAT. This is the same JSON
  contract a v2 Angular reactive form calls, so nothing here is throwaway.
- **Fuzzy dates** are a Precision (Exact/About/Before/After) + Year + optional
  Month + optional Day group, converted client-side into the schema's
  `date_original` ("ABT May 1951") / `date_sort` ("1951-05-00") pair — full
  GEDCOM date grammar is out of scope; this covers the common cases §5A asks
  for without inventing an endpoint.
- **The People list's sort control omits "by surname."** `PersonListItem`
  (the shape `GET /api/search` and `GET /api/individuals` both return) only
  carries `primary_name`, not discrete given/surname fields, so a reliable
  client-side surname sort isn't possible without a contract change. Sort is
  Name (A–Z) and Birth year (oldest/newest) only. The **Surname filter chip**
  is unaffected — it's a *server-side* `GET /api/search?surname=` filter
  (matches ANY of a person's names, not just their primary/display one — this
  is correct behavior for genealogy: a person with a married-name row keeps
  showing up under their married surname even though their primary name is
  their birth name; verified against the seed data).
- **"Admin" nav gating uses `is_admin`, not Curator+,** despite the WP4 brief's
  literal wording — every `/admin/*` and `/api/admin/*` route is hard-coded
  Admin-only (§10), so gating on Curator would render a menu item that 403s.
  Logged as an OPEN item in `BLOCKERS.md` (2026-07-03) rather than silently
  reinterpreting the brief.
- **Recent Activity is Curator+-only on Home**, for the same reason: the only
  existing endpoint (`GET /api/activity`) is the Curator+ audit trail
  (ADR-0001), not a friendly all-members feed. Viewers/Contributors see an
  honest static message instead of a feed that would 403. Also logged as an
  OPEN item in `BLOCKERS.md`.
- **"About" dropped from the primary nav.** The WP4 brief specifies exactly
  five primary items (Home/Tree/People/Memories/Search); the pre-existing
  `/about` page (admin-editable site text) still renders at its URL but has no
  nav link in this build. A footer is the natural home for it once there is a
  footer (later visual pass).

**Bug found + fixed in the process (not new scope, logged in `BLOCKERS.md`):**
Bootstrap was loading from a CDN and silently failing under the strict CSP in
every real browser (pytest never caught it — the test client doesn't fetch
`<script>`/`<link>` tags). Fixed with one config line
(`BOOTSTRAP_SERVE_LOCAL = True` in `app/config.py`); every existing Bootstrap
page (including the WP3 admin panel) is now actually styled and interactive
for the first time in a real browser.

**Files created/changed:** `app/templates/base.html`, `app/templates/
dashboard.html`, `app/templates/coming_soon.html`, `app/templates/people/
{index,new,show,_fuzzy_date_fields}.html`, `app/routes/people.py`,
`app/routes/main.py` (added `coming_soon`), `app/__init__.py` (registered the
blueprint + the branding context processor), `app/config.py`
(`BOOTSTRAP_SERVE_LOCAL`), `run.py` (`PORT` env var), `app/static/js/
{api,home,people}.js`, `app/static/css/style.css` (additions only),
`docs/openapi.yaml` (new `Views` tag: `/coming-soon`, `/people`, `/people/new`,
`/people/{individual_id}`).

---

### 2026-07-04 — WP5: Chronicle reaches the authenticated app

**What changed:** the app shell, Home, and People now read as Chronicle, not
plain Bootstrap — the WP4 deferral ends here. Per the WP5 brief, **styling
lands now; only §5B's accessibility/elderly *constraints* stay deferred**
(the WP4 entry above got this wrong — Chronicle styling itself was never
meant to wait for end-of-v1, only the WCAG/tap-target/elderly pass was).

**Mechanism: "layer Chronicle tokens over Bootstrap structure."** Bootstrap
keeps doing its job — grid, dropdown JS, form validation states, `.table`
markup in admin's untouched templates. A new stylesheet,
`app/static/css/chronicle-app.css`, loads after `chronicle-main.css` +
`chronicle-components.css` and repaints Bootstrap's own component classes
(`.btn`, `.btn-primary`, `.form-control`, `.form-select`, `.dropdown-menu`,
`.list-group-item`, `.table`, `.badge`/`.text-bg-*`) in the same tokens,
fonts, and idioms as the public page. **This is why admin's user table and
the login/error pages now look Chronicle too, with zero edits to their
template files** — only `base.html`, `dashboard.html`, and `people/*.html`
were touched (Task 2's actual scope); everything else inherited the look for
free because it already used Bootstrap's own classes. Two new component
classes were needed where Bootstrap had nothing to repaint: `.panel`/
`.quick-add-tile`/`.on-this-day`/`.stat-strip`/`.person-row` (Home + People,
moved out of `style.css` into `chronicle-app.css`) and `.filter-chip` (People's
status/surname chips — a NEW class, not chronicle-components.css's `.chip`,
which is styled for the public page's dark `.catalog` plate and would have
had the wrong contrast on a light parchment page; the two now coexist without
collision).

**The header is reused verbatim, not reinvented.** `base.html`'s `<header
class="site-header" id="siteHeader">`/`.brand`/`.nav__links` is the *same*
markup and ids as the public `index.html`, so `chronicle.js` (already loaded
publicly, already CSP-safe, already tested) drives the sticky-header class
and the mobile hamburger toggle for the app too — nothing new was written for
either. Every other section of that file no-ops safely on pages without its
matching element (splash, tree, timeline, catalog — see its own CSP
compliance note), which is what makes loading the whole file app-wide safe.
One adaptation was necessary: the public header is deliberately *transparent*
at the top (it reads over a hero image); app pages have no hero behind it, so
`body.app-shell .site-header` is pinned to the solid "scrolled" look
unconditionally, regardless of which way `chronicle.js`'s scroll listener
toggles `.is-scrolled`.

**A real conflict found and designed around: the user-menu dropdown lives
OUTSIDE `#navLinks`.** `chronicle.js`'s mobile menu closes on ANY click inside
`#navLinks` (reasonable for a page with no submenus). Nesting the user-menu
dropdown inside it, as a first draft did, meant tapping "Robert Hartwell ▾" on
mobile fired two handlers at once: Bootstrap's dropdown JS opening the menu,
and `chronicle.js` immediately hiding the whole nav panel it lives inside —
the menu would open and instantly become unreachable. Fixed by moving the
dropdown to a sibling `.header-actions` wrapper next to the hamburger button,
outside the collapsible nav entirely; verified in the browser on a 375px
viewport that the dropdown opens and the primary nav's mobile state is
untouched either way.

**Recent Activity is no longer Curator+-only.** BLOCKERS.md's WP4 items were
resolved by BE before this WP started: `GET /api/activity/feed` (permission
`view`, any member) returns a pre-formatted friendly sentence per row, so
`dashboard.html`'s Recent Activity container now renders for every logged-in
member, and `home.js` dropped the client-side verb/noun mapping it used to
need (the backend does that now). Verified as Viewer, Contributor, Curator,
and Admin — a Viewer sees the real feed, not the old "ask a Curator" message.

**Task 3 — copy neutralization (ADR-0003):** grepped the whole app surface
(`app/templates/`, `app/routes/`, `app/services/`) for the author's name and
any phone/email/address. Two hits, both fixed:
- `/.well-known/security.txt` (`app/routes/main.py`) hardcoded a personal
  Gmail address as the RFC 9116 security contact. Now reads
  `current_app.config["MAIL_DEFAULT_SENDER"]` — config, not source, per ADR-0003
  rule 6. (`login.html`, `forgot_password.html`, and the 403/429/500 pages were
  already fixed by BE's `4bd1182` before this WP — verified, not re-touched.)
- A Jinja *comment* in `index.html` ("FE decisions made without Wes") named the
  owner in what ADR-0003 rule 3 treats as technical/build-detail language;
  reworded to "without owner sign-off." Not rendered output, but for
  consistency with BE's equivalent comment cleanup in `4bd1182`.

**Known minor inconsistency, deliberately not fixed this WP:** `errors/
403.html`, `429.html`, and `500.html` still use Bootstrap's `.display-6` class
on their `<h1>`, which (being a class selector) outranks chronicle-main.css's
plain `h1 { font-size: clamp(...) }` rule regardless of load order — so those
three headings render at Bootstrap's fixed size rather than the Chronicle
scale, even though the surrounding page (nav, buttons, body text) is fully
reskinned. `coming_soon.html` and `people/show.html` had the same class and
were fixed (they're reachable from the nav built this WP); the error pages
were out of Task 2's explicit scope (app shell + Home + People) and are left
for the next template pass — same one-line fix (drop `.display-6`) when
someone's there anyway.

**Files created/changed:** `app/static/css/chronicle-app.css` (new); `app/
templates/base.html` (Chronicle header/dropdown/flash markup); `app/templates/
dashboard.html` (Recent Activity ungated, section labels use `.section-title`);
`app/templates/people/index.html` (`.chip` → `.filter-chip`); `app/templates/
people/show.html`, `app/templates/coming_soon.html` (dropped `.display-6`);
`app/static/js/home.js` (Recent Activity now calls `/api/activity/feed`, no
verb/noun maps); `app/static/js/people.js` (`.chip` → `.filter-chip` selector);
`app/static/css/style.css` (WP4 app-shell rules removed — superseded);
`app/routes/main.py` (`security_txt` reads `MAIL_DEFAULT_SENDER`); `app/
templates/index.html` (comment reworded, ADR-0003).

---

### 2026-07-04 — FE-2: the Person Page (six tabs, native Chronicle)

**What changed:** `people/show.html`'s placeholder became the real Person
Page — one route, six hash-switched tabs (Story · Relationships · Timeline ·
Photos · Details · Sources), entirely client-rendered by the new
`app/static/js/person.js` against the WP2 JSON API. No new Flask routes; no
change to `docs/openapi.yaml`'s paths (the `/people/{individual_id}` Views
entry already existed for this route).

**Tab pattern:** URL hash (`#story`, `#relationships`, …) drives which panel
shows, so every tab is deep-linkable and back/forward works; each tab's data
loads lazily on first visit (`loadedTabs`), and a single memoized fetch cache
(`cache`/`once`/`invalidate`) means data shared across tabs — Relationships'
family graph, Story's Family card, Timeline's Family-class events — is only
ever fetched once per page load. Mutations reset the relevant cache keys and
mark dependent tabs as "not yet reloaded," so switching tabs after an edit
always shows fresh data without a full page reload.

**Header/cameo:** reuses chronicle.js's own `photo()`/`applyTones()`/`initials()`
globals (already loaded by `base.html`) for the sepia toned-cameo placeholder
every relationship card and the header portrait fall back to when a person has
no linked photo — the exact CSP-safe data-p1/data-p2 mechanism the public page
already established, just applied to new dynamically-injected markup instead
of static HTML. Tones are picked deterministically from the person's id (no
"tone" field exists on `Individual` — purely a front-end decorative choice).

**Relationships tab data assembly:** `GET /api/families` never returns child
rows in its list shape (only a single family's detail GET does), and there is
no "families I'm a child in" endpoint — so parent-family discovery goes
through `GET /api/individuals/{id}/pedigree?direction=ancestors&depth=1`,
whose edges name the family id(s) where this person is the child. Every
related person's vitals (birth/death year, living) come from one
`GET /api/individuals` call, mapped by id — the same "fetch it all, filter
client-side" call already made for the People list's sort (family-scale
dataset, Master Plan §12).

**Editing an existing child link (pedigree_type/child_order):** the contract
has no `PUT` for an active `family_children` row, only `POST` (create-or-
restore) and `DELETE`. The edit action calls `DELETE` then immediately
re-`POST`s with the new values — `family_service.add_child` already treats a
just-soft-deleted link as "restore with updated fields," a real code path, not
a stub. The only cost is a two-row (delete + create) audit trail instead of
one `update` row; logged as an OPEN forward note in `BLOCKERS.md` asking for a
dedicated `PUT` when convenient. Not blocking — the feature works correctly
today.

**Life Sketch vs. Name Meaning:** `Note` has no `is_primary` flag (unlike
`Name`), so "the person's primary attached note" for the Story tab's Life
Sketch card is defined as "the first attached note whose title doesn't start
with 'Name Meaning'" — a title-string convention, not a schema field. The Name
Meaning card renders only when such a note exists, per the brief.

**Markdown rendering:** `Note.content` is raw Markdown by contract
(`note_service.py`: "rendering to safe HTML is a VIEW concern"). No Markdown
library is vendored (no CDN allowed under the strict CSP; Python dependencies
are BE's lane, not FE's) — `person.js` implements a small, deliberately
limited subset (paragraphs, headings, bold/italic/code spans, "- " lists),
escaping the raw text FIRST so no Markdown syntax can smuggle real HTML
through. Full CommonMark is out of scope, the same call already made for
fuzzy-date grammar.

**Timeline tab:** life-chapter buckets (Childhood/Adolescence/Young
Adult/Adult/Senior) and the "migration thread" (a place-change mark between
consecutive dated events) are computed client-side from `date_sort` + `place`
— no schema support needed. Family-class events are deliberately narrow per
the brief: children's *births* and spouse/parent *deaths* only (not the
reverse), fetched as two separate id sets rather than one blanket BIRT-or-DEAT
filter. World events blend in via `GET /api/historical-events` bounded to the
person's birth year through their death year (or the current year if living).
"N sources" badges and the whole Sources tab both read from ONE unfiltered
`GET /api/citations` call, filtered client-side by subject id — avoids an
N-events, N-requests fan-out at family scale.

**Event-tag picker (Details tab):** `event_tag` is a free string server-side
(no enum — `event.py`'s column is a plain `VARCHAR(10)`), so the curated
Life-Events/Attributes dropdown is a UI convenience, not a schema limit — an
"Other (type a GEDCOM tag)…" option reveals a free-text field, so §5A's "every
user-meaningful field capturable" holds even for a tag the curated list
doesn't name.

**A real CSS bug found in the browser, not caught by pytest:** the first
Relationships-tab render had every `.rel-card`'s "Remove" button overlapping
the person's name. Cause: `.rel-card__body` had no `flex-grow`, so when the
fixed-width card ran short on space, flexbox's default shrink behavior forced
ALL the missing space out of `.rel-card__body` (down to ~24px) while
`.rel-card__actions` (given `flex: none` to protect it from disappearing)
kept its full size — the button's own content then rendered past its
box's shrunken neighbor. Fixed by giving the actions block `flex: 0 0 100%`
(its own row, under the photo/name) instead of trying to keep it beside a
long name in a 260px card. A good example of why `<when_to_verify>` real-
browser checks catch things pytest's HTML-only test client cannot.

**Files created/changed:** `app/templates/people/show.html` (real content,
replacing the FE-1 placeholder); `app/static/js/person.js` (new — all six
tabs); `app/static/css/chronicle-app.css` (new Person Page component classes:
`.person-header`, `.person-tabs`, `.story-layout`/`.story-rail`,
`.rel-card`/`.rel-family-card`, `.timeline-chapter`/`.tl-event`,
`.gallery-wall`, `.lightbox`, `.inline-form-slot`, `.vitals-list`). Two OPEN
items and one OPEN forward note logged in `BLOCKERS.md` (Follow endpoint,
per-subject activity filter, the family-children PUT).

---

### 2026-07-05 — FE-3: Tree (vertical Pedigree, Family Group, Relationship Finder)

**What changed:** the nav's Tree `coming-soon` link is now three real pages
— Pedigree (default, `/tree`), Family Group (`/tree/family/<id>`), and
Relationship Finder (`/tree/relationship`) — a new `app/routes/tree.py`
blueprint + `app/static/js/tree.js`. Person Page carry-overs from the prior
BE gap-fill run landed too: the disabled "Follow" button is gone, the header's
View Tree/View Relationship buttons point at these real pages, and the Story
tab has its "Latest Changes" card back.

**Pedigree layout system: a pure-CSS nested-list "org chart," upside down.**
The classic org-chart CSS recipe (`<ul>`/`<li>` nesting, flexbox rows,
`::before`/`::after` border-drawn connectors) normally grows an org chart
DOWNWARD from one root into more nodes — CEO at top, reports below. That's
*exactly* the shape a genealogy pedigree wants for the "ancestors" direction:
root person at the top (one node), parents below (two), grandparents below
that (four), doubling each generation. Zero JS position math anywhere —
unlike `chronicle.js`'s absolutely-positioned hero tree (which needs the
data-x/data-y + `el.style` trick to place nodes under the strict CSP), this
layout is 100% flexbox + CSS pseudo-elements. `tree.js` never computes a
pixel position; it only ever asks "does this person have parents in the
loaded slice, more beyond it, or none on record" and emits plain nested
markup.

**Node design:** a toned cameo (chronicle.js's `photo()`/`applyTones()`
globals, same as every other page), name (links to the Person Page — the
*navigate* affordance), lifespan, and a `pedigree_type` badge when a branch
is adopted/foster/step. A separate **Center** button is the *recenter*
affordance — deliberately a different control from the name link, per the
brief's "make both obvious." Recentering updates `?root=` via
`history.pushState` (and a `popstate` listener restores it on back/forward),
so every view is shareable and bookmarkable without a server round trip.

**The graph-not-linked-list requirement, concretely:** `PedigreeGraph.edges`
can name MORE than one parent-family for the same child (a live birth-family
link and a live adoptive-family link can coexist — `tree_service._parent_
families` returns every live family where a person is a child, not just one).
Rather than inventing a UI to group "birth branch" vs. "adoptive branch"
separately, every parent from every parent-family becomes a sibling `<li>` in
the same nested `<ul>`, each individually badged with ITS OWN family's
`pedigree_type` — simpler than a dual-branch UI and correct for the data
model without a special case.

**ORIENTATION SEAM — the v2 pan/zoom-canvas reserved toggle, not built here.**
Every rule keys off `.pedigree-canvas--vertical`, and the graph-merge/render
logic in `tree.js` has no concept of "vertical" at all — it only emits nested
markup. A future `--horizontal` sibling class is a single CSS block (flip the
flex axis, flip the connector pseudo-elements' left/top math) with zero JS
changes. The brief asked for the seam to exist, not for the toggle itself, so
that's where this stops.

**Mobile degrade (≤640px): the org chart becomes an indented, scrollable
outline**, not a shrunk version of the same layout — an ever-widening chart
genuinely doesn't work on a phone (by 4 generations there can be up to 16
great-great-grandparent cards in one row), but "one ancestor per line, each
generation indented further, connected by a plain left border" carries the
same information at any width with no horizontal scrolling. Same markup,
different CSS at one breakpoint; nothing computed differently in JS.

**Two real flexbox bugs found in the browser** (not caught by pytest, which
never lays out CSS): a long name at deep mobile indentation overflowed its
own card because the flex body child had no `min-width: 0` (its default auto
minimum size is its unwrapped content width) — the identical class of bug
FE-2's decision log already found once on `.rel-card__body`, now fixed the
same way on `.pedigree-node__body`. Once names could wrap to multiple lines,
the Center/Family action buttons (given `flex: 0 0 100%` to force them onto
their own row) still rendered on top of the wrapped name, because the mobile
`.pedigree-node` row itself was `flex-wrap: nowrap` — added `flex-wrap: wrap`
so the 100%-basis child actually gets to drop to a new line.

**Family Group sheet reuses `.rel-card`/`.rel-cards` verbatim** (FE-2's
Relationships-tab component) for both partners and children — a family sheet
and a person's own relationship cards should look like the same product, and
there was nothing about a family-scoped read view that needed different
markup.

**Relationship Finder's hop-by-hop chain is a client-side re-derivation**,
not new backend data: `RelationshipResult` gives `distance_a`/`distance_b`
(generations from each person to the nearest common ancestor) and `path`
(individual ids from A through the NCA to B), but no per-hop type. Since
`path`'s first `distance_a + 1` entries are the ascent from A to the NCA and
the rest are the descent to B, a hop's type is simply "parent" before that
boundary index and "child" after — mirroring the same ascent/descent split
`tree_service.py`'s own `_relationship_label` already computes server-side
for the English label. Self, no-known-relationship (or in-law, which the
service also returns an empty `path` for), and "this member has no linked
person" each render their own plain-language message instead of a fake or
partial chain.

**A real, non-bug finding: the PWA service worker's cache-first `/static/`
strategy (`app/static/js/sw.js`) meant manual verification kept showing
stale JS/CSS even from fetches that bypassed the browser's own HTTP cache** —
the service worker intercepts the request before the browser's cache is even
consulted, and its own Cache Storage entry for a given URL persists
indefinitely until `sw.js`'s own `CACHE` constant changes (its documented
"refresh lever"). Confirmed the served bytes were correct all along via a
cache-busting query string; then bumped `CACHE` to `"familyhub-shell-v2"` so
real returning members actually receive this branch's changed static files
instead of an indefinitely-stale shell.

**Files created/changed:** `app/routes/tree.py` (new blueprint); `app/
__init__.py` (registered it); `app/templates/tree/{pedigree,family,
relationship}.html` (new, thin shells); `app/templates/base.html` (Tree nav
link); `app/static/js/tree.js` (new — all three views); `app/static/js/
person.js` (Task 0 carry-overs); `app/static/css/chronicle-app.css` (new §11
Tree section: `.tree-subnav`, `.pedigree-tree`/`.pedigree-node`, `.family-
sheet__partners`, `.relationship-chain`, plus the mobile outline degrade);
`app/static/js/sw.js` (cache version bump); `docs/openapi.yaml` (three new
Views-tag paths).

---

### 2026-07-05 — FE-4: Memories (album views + Stories), Search, and the elderly-first sizing strip

**Task 0 — why the strip was a real fix, not just tidying.** `style.css`
loaded AFTER `chronicle-app.css` in `base.html`, so its oversized `.btn`/
`.form-control`/`.form-label` rules were winning the cascade and silently
overriding Chronicle's intended scale on every authenticated page since WP5
shipped — nobody had noticed because the two looked similar enough at a
glance. Worse, `html { font-size: 18px }` changed what `1rem` MEANS
app-wide: `chronicle-main.css`'s entire `--space-*`/`clamp()` token system
assumes the browser default (16px) root, so that one line was quietly
scaling the *whole app* up ~12%. Removed rather than migrated, per the owner
directive (ADR-0004): large-print support is the browser/OS's job (pinch-
zoom, `Ctrl`+`+`, OS text scaling), not something the app forces on every
visitor. What survived because a current template still references it:
`.hero-banner`, `.hero-preview`, `.chip-group`, `#main-content:focus`. Seven
other classes (`.btn-dashboard`, `.photo-card`, `.album-card`, `.photo-full`,
`.infobox-card`, `.album-cover-placeholder`, `.photo-preview`, `.drag-ghost`)
had zero references anywhere in the tree — leftovers from the removed
pre-WP1 "Lite" photo/wiki app — so they came out too rather than migrating
dead code. `style.css` is now 40 lines; logged in `BLOCKERS.md` for BE to
decide whether it's worth deleting outright.

**"One photo store, album views," made literal.** Chronological/By Person/
By Family/By Event are four different client-side filters over the SAME
`GET /api/media` — none of them is a separate store, and a photo can be
uploaded with NO subject at all (`POST /api/media` only requires the file)
and linked afterward from the Photo Detail panel. This mirrors how a real
family archive actually gets built: someone dumps a box of scanned photos in
first, then tags who's in them over time.

**By Family's aggregation is a defined, honest scope — not a missing
endpoint.** "Photos from a family's life together" is defined as: media
linked directly to the family, media linked to the family's own events
(marriage, divorce…), and media linked to any of its members' own individual
events. Every one of those is a real, already-existing `GET /api/media?
subject_type=…&subject_id=…` call (`individual`/`family`/`event` are all in
the Media Link schema); the only cost is a client-side fan-out (one media
call per relevant target: the family, its events, each member's events), the
same "one call per target, not per leaf record" shape `person.js`'s Timeline
tab already uses for family-scale event aggregation. No blocker filed —
nothing here is a capability the API lacks.

**Photo Detail extends, not reuses, FE-2's lightbox.** Person Page's
`.lightbox` (person.js) is a caption + one unlink button — enough for "this
person's own photos." Memories' photo detail needs full metadata, EVERY
link as a navigable chip (an event link has no page of its own, so it
resolves to the event's OWN subject — a person or family — via one extra
`GET /api/events/{id}`), and Contributor+ edit/manage-links/delete. Built as
its own component (`.photo-detail`, `memories.js`) rather than bolting all of
that onto person.js's simpler one, which stays exactly as FE-2 shipped it.

**Capture-date depth bar: the new upload form is the first to populate
`capture_date_sort`.** person.js's existing Photos-tab upload only ever sent
`capture_date` (raw text like "Summer 1952"), leaving `capture_date_sort`
null forever — fine for a caption, useless for the Chronological view's
actual sort order. The Memories upload/edit forms use the same Precision +
Year + Month + Day fuzzy-date group already established for events/vitals,
now generalized into `fh-common.js`, so newly uploaded photos sort correctly
by when they were taken; older photos uploaded before this form existed
correctly fall back to upload-date ordering (visibly labeled "Uploaded …"),
exactly the behavior the brief asked for, not a bug.

**A new shared module, scoped on purpose: `app/static/js/fh-common.js`.**
Three new pages in one work package would otherwise each re-type
`escapeHtml`/`debounce`/the search-as-you-type picker/the Markdown renderer/
the photo-cameo helpers — exactly the duplication the brief asks to avoid.
Rather than refactor `person.js`/`tree.js`/`people.js` (already shipped,
browser-verified in prior WPs, never touched by this brief) to also consume
it — a riskier, unrequested refactor of working code — `fh-common.js` is a
clean extraction point for the NEW code only (`memories.js`, `stories.js`,
`search.js`). Its `subjectPicker()` generalizes `person.js`'s person-only
picker to optionally include families too (a note or photo can be linked to
either), fetching `GET /api/families` once and matching client-side against
the same `partner1`/`partner2` display strings the API already computes —
the same "family-scale, brute force is fine" precedent as People's sort.

**Search: quick search in the header is a Tier-2 design call.** The brief
invited "consider surfacing this in the header" and left the call to FE. A
permanently-visible wide input would crowd the header at 375px, so it's a
toggleable overlay (`#headerSearchBtn`/`#headerSearchOverlay`) reusing the
exact same `subjectPicker()` the `/search` page's Quick tab uses — one
implementation, two presentations. Loaded app-wide via `base.html` (not
per-page) since the button lives in the shared header.

**Death-year range: implemented client-side, not filed as a blocker.**
Master Plan §12 promises a birth/death year range filter; `GET /api/search`
only has `birth_from`/`birth_to` (confirmed by reading `search_service.py` —
no `death_from`/`death_to` parameter exists). But `PersonListItem.death_year`
IS already a real field on every row the server returns regardless — so
filtering the already-server-filtered result set by death year client-side
produces the exact correct final answer, not an approximation of a missing
capability. This is the identical shape of call the codebase already made
for People's birth-year sort (achievable, just executed client-side because
the server doesn't offer it as a parameter) — a design/implementation
choice, not a hard dependency on BE, so no `BLOCKERS.md` entry.

**Two real bugs found only in the browser (not caught by pytest):**
1. **Bootstrap's breakpoint columns key off VIEWPORT width, not the
   immediate container's width.** The fuzzy-date group's `col-md-3` fields
   rendered fine full-width, but squeezed unreadably into one row inside the
   Photo Detail panel (a 340px sidebar) even on a 1280px-wide desktop,
   because `col-md-3`'s 25%-width rule keys off the *viewport* breakpoint
   (≥768px), not the 340px container actually holding it — a "container
   query" gap plain Bootstrap doesn't cover. Fixed two ways: `fh-common.js`'s
   `fuzzyDateFieldsHtml` now uses `col-6 col-md-3` (helps genuinely narrow
   phone viewports), and `.photo-detail__panel .row > [class*="col-"]` forces
   full-width stacking regardless of viewport, since that panel is narrow
   *unconditionally*.
2. **The new header search button overlapped the brand wordmark at a real
   375px width.** `.header-actions` gained one more fixed-width (44px) child;
   `.brand`'s text content doesn't actually shrink just because it's a flex
   item (no `min-width: 0`), so at 375px the two overlapped instead of
   wrapping. Fixed with a scoped `body.app-shell` media rule (shrinks the
   wordmark, hides the tagline below 400px) — deliberately NOT touched in
   `chronicle-main.css`, so the public page's header (no search button) is
   completely unaffected.

**Re-encountered, not re-caused: the service worker cache trap.** FE-3's
diary already documented `sw.js`'s cache-first `/static/` strategy as the
reason a served file being byte-correct doesn't mean the browser is running
it. This session hit it repeatedly while iterating on the two bugs above —
each edit needed the Cache Storage cleared (or the `CACHE` constant bumped)
before the fix was visible, confirming FE-3's finding rather than being a
new one. Bumped `CACHE` to `"familyhub-shell-v3"`.

**Files created/changed:** `app/routes/memories.py`, `app/routes/search.py`
(new blueprints); `app/__init__.py` (registered both); `app/templates/
memories/{index,by_person,by_family,by_event,stories,story_new,story_show,
_subnav}.html`, `app/templates/search/index.html` (new); `app/templates/
base.html` (nav links, header search button + overlay, app-wide `api.js`/
`fh-common.js`/`search.js`); `app/templates/dashboard.html` (Quick Add
Photo/Story tiles wired to real routes); `app/templates/errors/
{403,429,500}.html` (dropped `.display-6`); `app/static/js/{memories,
stories,search,fh-common}.js` (new); `app/static/css/style.css` (Task 0
strip, see above); `app/static/css/chronicle-app.css` (generalized
`.tree-subnav` → `.subnav`/`.tree-subnav` alias; new Memories/Photo-Detail/
Stories/Search sections; the two browser-bug fixes above); `app/static/js/
sw.js` (cache version bump); `docs/openapi.yaml` (nine new Views-tag paths).

### 2026-07-06 — FE-5: User area (My Contributions + Account & Security)

**Family gets a real link too, not just person/media/note.** The brief's own
examples named only those three subject types for My Contributions' row
linking, but `/tree/family/{id}` (FE-3's Family Group sheet) is exactly the
same kind of already-shipped, real page — "links to it where a page exists"
is the actual rule, and family clears it just as cleanly. Implemented with
the identical fetch-then-catch shape already proven for individual/media/
note (`GET /api/families/{id}`, partner names joined with "&", falls back to
"a family" if both are missing).

**Media rows needed a real "Memories detail" destination that didn't quite
exist.** `memories.js`'s Photo Detail overlay only ever opened from a click
inside an already-loaded album grid — no shareable URL to link a contribution
row at. Rather than file a blocker (nothing backend is missing; `GET
/api/media/{id}` already returns everything the overlay needs), added a
small, additive `?photo=` query param to `/memories` that calls the exact
same `openPhotoDetail(id)` the grid's own click handler already uses — it
fetches by id directly, so it's independent of which album view happens to
be the page default. One line in `memories.js`'s `DOMContentLoaded`, one new
query param documented on the existing `/memories` Views entry.

**Summary cards are grouped labels over real numbers, not a richer query.**
`GET /api/me/contributions`'s `summary` object gives two independent
breakdowns — counts by action, counts by subject type — but no
action×subject_type cross-tab (e.g., no single number for "photos I
personally added" vs. "photos I edited"). Rather than issue N extra filtered
fetches per card just to get an exact cross-tab (a real but needless
N+1 for a personal dashboard), the cards sum real `by_subject_type` buckets
into friendlier groups (People = individual+name, Sources = source+citation,
etc.) and a Total card sums `by_action`. Every number is still a straight sum
of real API-returned counts — grouping/relabeling, not estimation — which is
what the brief's "your grouping call, but every count must come from the
real summary" actually asks for.

**The pending-email state is a client-side reconciliation, not a faked
field.** `GET /api/me` (`MeAccount`) has no persistent "pending change"
column — only the change-email POST response carries `pending_email`. Rather
than leave the "pending: check your inbox" state disappearing on next page
load (technically honest, but a worse experience than the brief's wording
implies), it's remembered in `localStorage` keyed by user id and cleared the
moment a LATER `/api/me` snapshot shows `email` actually equals the
remembered candidate — i.e., the verification link was clicked. Every value
compared is real data the API actually returned at some point; nothing is
invented client-side that the server never said.

**`window.alert()`/blocking dialogs, deliberately avoided on this page even
though existing code uses them.** `memories.js`'s unlink/delete-photo error
paths use `window.alert()`, and copying that would have been the path of
least resistance. Found in the browser, not in review: an alert on the
resend-verification 503 path fully blocked the automated preview tool (a
real native modal — exactly what it would do to a real user mid-task) on a
page the brief explicitly wants to "feel calm, not like a settings dump."
Reworked every error path on this page to the SAME inline `.alert-danger`
(`showInlineError`/`alertFormError`, both pre-existing in `fh-common.js`)
the form-submit paths already used, so the whole page has one consistent,
non-blocking error idiom instead of two competing ones. `window.confirm()`
is kept for the final delete gate — a deliberate, answerable yes/no the user
must actively dismiss, not a one-way notice, and it matches the existing
delete-photo precedent exactly.

**Two real layout bugs found only at 375px, not caught by pytest or a
desktop check:**
1. **`.chip-group` never had `flex-wrap`.** People's living-status filter (3
   chips) always fit one row at any real width, so the missing wrap never
   showed. My Contributions' subject-type filter (6 chips) overflowed off a
   375px viewport instead of dropping to a second row. Fixed in the shared
   rule (`chronicle-app.css`) rather than a page-local override, since the
   fix is correct for any future chip-group with more items than fits one
   line; re-verified People's own filter still renders on one line
   afterward.
2. **A `<label>` immediately before a `.chip-group` sits on the same visual
   line as the chip.** Bootstrap's `.form-label` is `display: inline-block`;
   `.chip-group` is `inline-flex` — with nothing block-level between them,
   "TIMEZONE" and the "Site default" chip rendered side by side instead of
   label-then-control. Every other `.chip-group` usage in the app is
   preceded by a plain `<div>`, not a `<label>`, so this pairing never
   existed before the Timezone field. Fixed with `d-block` on that one
   label rather than changing `.form-label`'s default globally (other
   Bootstrap-rendered fields elsewhere may depend on the inline-block
   behavior for their own layout).

**Files created/changed:** `app/routes/account.py` (new blueprint, two thin
view routes); `app/__init__.py` (registered it); `app/templates/account/
{security,contributions,_subnav}.html` (new); `app/static/js/account.js`
(new — both pages, DOM-guarded); `app/templates/base.html` (user menu:
Account & Security repointed, My Contributions added); `app/forms/
auth_forms.py` (`ChangePasswordForm` render_kw autocomplete attributes —
template-adjacent fix, brief-authorized); `app/static/js/memories.js`
(`?photo=` deep link); `app/static/css/chronicle-app.css` (new Account &
Security section; `.chip-group` flex-wrap fix); `app/static/js/sw.js`
(cache version bump); `docs/openapi.yaml` (two new Views-tag paths + one new
query param on `/memories`).

---

### 2026-07-06 — FE-6: Admin Console (native Chronicle rebuild)

**What changed:** every `/admin/*` page rebuilt as a client-rendered,
native-Chronicle console (`app/static/js/admin.js`, one file, seven
DOM-guarded page inits — the established pattern) over the AdminApi/Inbox/
WriteControl tags, plus a new shared `admin/_subnav.html` tab strip.

**"Restyle or rebuild, per section" — the calls made, and why.** The brief
explicitly left this choice to FE, naming `/admin/users/new` as the
exemplar case. Rebuilt (old template replaced with a client-rendered shell):
Users list, Backups, Activity — all three had a JSON endpoint that already
returned strictly more than the old server-rendered page showed. Kept
verbatim, restyled only (the shared Chronicle stylesheet cascade repaints
any page using Bootstrap's own classes for free, the same mechanism WP5
used app-wide): account-create/edit, the direct-set-password form, and the
tagline/About/banner form — none of these have a JSON equivalent in the
contract at all (account create/edit/reset-password because there's no
"admin sets an arbitrary role/display-name/password" API endpoint, only the
role-request-approval and secure-change-email paths; the tagline/About/
banner form because it's a completely different settings surface — see
next).

**Two settings pages, not one, because the backend already has two settings
systems.** `settings_service.py` has carried two independent, non-overlapping
mechanisms since WP3: `KNOWN_KEYS`/`get_all()` (tagline/about_text/
contact_text/the hero image — HTML-form-only, no `/api/settings` exposure)
and `SETTING_GROUPS`/`editable_settings()` (branding/defaults/security/email
— the JSON-only surface this brief's "Settings" section describes). Rather
than relocate the legacy form (which would have orphaned two passing tests
in `tests/test_admin.py` that POST to its exact URL) or bury the new grouped
console as a sub-section of the old page, the new console lives at
`/admin/config` and links to the legacy page (`/admin/settings`, relabeled
"Site Text" in the subnav) with one sentence — two clearly-labeled,
independently-reachable pages instead of a forced merger of two things the
backend itself keeps apart. Not filed as a `BLOCKERS.md` gap: nothing here
needs a NEW backend capability, it's a UI decision about how to present two
capabilities that already exist.

**Restore vs. Revert, one action per Activity row, not two.** Both
`POST /api/restore` and `POST /api/audit/{id}/revert` can undo a delete, but
they're semantically different (restore: "this subject is currently
soft-deleted, bring it back"; revert: "undo whatever THIS specific audit
entry changed") and showing both on every row would be confusing, redundant
UI for little real benefit. The row's OWN action (`delete` vs. anything
else) picks which one single button applies, matching the more intuitive
verb to the more common case (a delete row says "Restore"; every other
revertible row says "Revert").

**The Activity page's actor filter is Admin-only, INSIDE a Curator+ page.**
`GET /api/admin/users` (the only way to turn "user id 4" into a name for a
dropdown) is `administer`-gated, so a Curator viewing this Curator+ page
would get a 403 fetching it. Rather than show a broken control or a raw
numeric-id input to a Curator, `admin/activity.html` passes
`data-is-admin="{{ 'true' if current_user.is_admin else 'false' }}'` and
`admin.js` only builds the actor dropdown when that's true — an Admin gets
full filtering, a Curator gets everything else (action/subject-type/date)
with no half-working affordance.

**Two real bugs found only by scripting the live pages, not by reading the
code (see `DEVDIARY_FE.md`'s FE-6 entry for full repro detail):** the
guarded restore's own success message was invisible (a `load()` call
immediately after setting it silently overwrote it in the same synchronous
callback — fixed with a `{ skipRestoreArea: true }` option); and the
Activity page's per-subject resolution cache never invalidated, so a row's
subject kept reading "(since removed)" immediately after the very Restore/
Revert action that un-deleted it, until a full reload (fixed by deleting the
specific cache entry right after a successful action). Both are the same
underlying lesson: a UI that "refreshes everything" or "caches the result"
needs the refresh/cache-invalidation half designed WITH the action, not
assumed to be free.

**A real, necessary test update — not incidental scope creep.** The brief's
own Activity requirement (Curator+, not Admin-only — BLOCKERS.md, 2026-07-03
RESOLVED) directly contradicted one assertion in a pre-existing BE-authored
test, `tests/test_wp5_authz_alignment.py`, which listed `/admin/activity` as
admin-only (written before this page existed in its Curator+ form). Moved it
into that file's existing `CURATOR_PLUS_GET_ENDPOINTS` list, right alongside
its own API (`/api/activity`), which the same file already tests the
identical way — logged in `BLOCKERS.md` for BE review, not silently changed.

**Files created/changed:** `app/routes/admin.py` (rewritten — thin views
only); `app/templates/admin/_subnav.html`, `admin/{dashboard,suggestions,
role_requests,config}.html` (new); `admin/{users,backups,activity}.html`
(rebuilt); `admin/{new_user,edit_user,reset_password,settings}.html` (subnav
include only); `app/static/js/admin.js` (new); `app/static/css/
chronicle-app.css` (new §16 — `.btn-danger`/`.text-bg-warning`/
`.text-bg-danger` repaints); `app/templates/base.html` (Admin nav link
repointed, new Curator-only Activity entry); `app/static/js/sw.js` (cache
bump); `tests/test_wp5_authz_alignment.py` (`/admin/activity` re-listed as
Curator+); `docs/openapi.yaml` (Admin tag trimmed to the four kept legacy
flows, seven Views-tag entries new/moved).

---

## Design Parking Lot

Future constraints and ideas — captured here, not yet scheduled or enforced.
(Larger functionality ideas belong in the Master Plan §11 parking lot instead.)

### FUTURE — WCAG AA accessibility pass
Chronicle's current colour palette has not been formally checked against WCAG 2.1
AA (4.5:1 for normal text, 3:1 for large text). Before any public launch the
full palette must be audited, especially `--gold` on `--paper` and any text on
the antique-blue `--navy`. Rust-red CTAs on paper backgrounds are likely to pass
but must be verified. **This is not a WP3 task** — record as a WP4/WP5
pre-launch gate.

### FUTURE — Large tap targets & readable type for elderly users
§5B specifies elderly-accessible design: large readable type (16px+ body, 20px+
for forms), minimum 44×44 px tap targets, high contrast, forgiving forms (no
inline validation loss of focus). Chronicle's base type is somewhat small for
this audience. A WP4 "accessibility tune" pass should:
- Bump body type to 18px minimum on mobile.
- Audit all form inputs (catalog search, login form) for tap-target size.
- Add `font-size` zoom support (no layout break at 200% zoom).

### FUTURE — Calm-by-design on interior (post-WP3) pages
The §5B "calm by design" brief (one primary action per screen, progressive
disclosure, generous whitespace) applies most to the interior CRUD pages (people,
families, events) that WP4 builds. The Chronicle aesthetic should inform those
pages even though they live inside `base.html` (Bootstrap). Consider a custom
Bootstrap theme that picks up `--paper`, `--rust`, and `--ink` so the interior
feels continuous with the public Chronicle face.

### FUTURE — Cross-generational tone on content pages
The public Chronicle page speaks to a broad family audience. Interior pages should
maintain that warmth — avoid clinical table-heavy UIs, favour "card with context"
over raw data grids, and keep photo thumbnails prominent wherever a person or
family is shown. This is a style guide constraint for WP4 template design.

### FUTURE — Identity guardrail (no Chronicle code copyright drift)
Chronicle is an original design used by permission as the starting point.
As the site evolves, ensure changes are sufficiently transformative that the
final product is unambiguously FamilyHub's own. Keep the design language (colour,
type, motifs) but let the content, IA, and features make it unmistakably a
family genealogy product, not a general-purpose "expeditions" theme.

### FUTURE — Imagery-as-texture, not illustration
Chronicle achieves atmosphere through real antique map images + aged-paper CSS
gradients rather than bespoke illustration. This principle should guide future
additions: prefer real family photos, historical documents, and map-style
visualisations over stock illustration or icon packs. This is consistent with the
PII-first, family-archive mission.
