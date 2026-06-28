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
