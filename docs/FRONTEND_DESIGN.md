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
