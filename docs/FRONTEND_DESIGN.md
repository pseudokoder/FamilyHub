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

| Token         | Hex       | Role                                      |
|---------------|-----------|-------------------------------------------|
| `--ink`       | `#1c1008` | Primary text / masthead                   |
| `--rust`      | `#8b2e12` | Archival red — primary accent, CTAs       |
| `--navy`      | `#1a3254` | Antique blue — secondary accent           |
| `--gold`      | `#c8860a` | Warm amber — stamps, marks, hover         |
| `--paper`     | `#f5edd6` | Aged parchment — page background          |
| `--paper-mid` | `#ede0bf` | Slightly deeper parchment — card tones    |
| `--fog`       | `#d4c8ad` | Muted border / divider                    |
| `--warm-wh`   | `#fdf8ef` | Near-white for text on dark backgrounds   |

Dark section backgrounds use `--ink` (nearly black-brown); the masthead
and footer live in deep navy or near-black.

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
