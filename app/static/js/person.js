/* person.js — the Person Page (FE-2, Master Plan §5A/§5B): six tabs (Story,
 * Relationships, Timeline, Photos, Details, Sources) over one individual,
 * switched by URL hash so every tab is deep-linkable and back/forward works.
 *
 * ARCHITECTURE: one shared, memoized fetch cache (`cache`/`once`/`invalidate`)
 * so the same API call is never made twice across tabs that need the same
 * data (e.g. Relationships' family graph also feeds Story's Family card and
 * Timeline's Family-class events). Each tab is lazy-loaded — its fetches
 * don't run until the visitor actually opens it (`loadedTabs`).
 *
 * CSP-strict, same as every other FamilyHub script: no inline styles or
 * handlers anywhere. Dynamic styling goes through chronicle.js's global
 * `photo()`/`applyTones()` helpers (already loaded by base.html) — the exact
 * data-p1/data-p2 → CSS-custom-property mechanism the public page uses for
 * its toned photo placeholders, reused here for this page's cameos so a
 * person with no uploaded portrait still gets the Chronicle look instead of
 * a blank box.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+ — this is the same
 *    fetch() contract a v2 Angular PersonComponent would call), Security
 *    (D315 — every dynamic string goes through escapeHtml before it becomes
 *    innerHTML).
 */
'use strict';

/* =============================================================================
 * 0) SHARED STATE + SMALL HELPERS
 * ===========================================================================*/

var personId = null;
var canContribute = false;
var personTabsNav = null;
var currentMediaList = [];   // the Photos tab's last-rendered list, for the lightbox
var lightboxEl = null;
var placesCache = null;

function escapeHtml(value) {
  var div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

/* debounce(fn, ms) — collapses rapid keystrokes (search-as-you-type pickers)
 * into one call, same pattern as people.js. */
function debounce(fn, ms) {
  var t = null;
  return function() {
    var args = arguments, ctx = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(ctx, args); }, ms);
  };
}

/* A tiny memoization cache: every getX() below is called from several tabs,
 * so `once` guarantees the network request behind it happens at most once
 * per page load (until something mutates the data and calls invalidate()). */
var cache = {};
function once(key, factory) {
  if (!(key in cache)) cache[key] = factory();
  return cache[key];
}
function invalidate(key) { delete cache[key]; }
function invalidatePrefix(prefix) {
  Object.keys(cache).forEach(function(k) { if (k.indexOf(prefix) === 0) delete cache[k]; });
}

/* yearOf("1850-00-00") -> 1850. Mirrors individual_service._year in Python —
 * the sortable date string always leads with the year. */
function yearOf(dateSort) {
  if (!dateSort) return null;
  var head = String(dateSort).slice(0, 4);
  return /^\d{4}$/.test(head) && head !== '0000' ? parseInt(head, 10) : null;
}

function joinDateplace(e) {
  return FamilyHubFmt.joinDot([e.date_original, e.place]);
}

var SEX_LABELS = { M: 'Male', F: 'Female', X: 'Other', U: 'Unknown' };
function sexLabel(s) { return SEX_LABELS[s] || 'Unknown'; }

var PEDIGREE_LABELS = { birth: 'Birth', adopted: 'Adopted', foster: 'Foster', step: 'Step' };
function pedigreeBadge(type) {
  return '<span class="badge text-bg-light">' + escapeHtml(PEDIGREE_LABELS[type] || 'Birth') + '</span>';
}

var TAG_LABELS = {
  BIRT: 'Birth', CHR: 'Christening', DEAT: 'Death', BURI: 'Burial', CREM: 'Cremation',
  ADOP: 'Adoption', BAPM: 'Baptism', CONF: 'Confirmation', BARM: 'Bar Mitzvah', BASM: 'Bat Mitzvah',
  FCOM: 'First Communion', ORDN: 'Ordination', NATU: 'Naturalization', IMMI: 'Immigration',
  EMIG: 'Emigration', CENS: 'Census', WILL: 'Will', PROB: 'Probate', GRAD: 'Graduation',
  RETI: 'Retirement', OCCU: 'Occupation', RESI: 'Residence', EDUC: 'Education', RELI: 'Religion',
  TITL: 'Title', DSCR: 'Physical Description', NCHI: 'Number of Children',
  SSN: 'Social Security Number', IDNO: 'ID Number', MARR: 'Marriage', DIV: 'Divorce',
  ENGA: 'Engagement', ANUL: 'Annulment',
};
function tagLabel(tag) { return TAG_LABELS[tag] || tag; }
function eventLabel(e) { return tagLabel(e.event_tag) + (e.event_value ? ': ' + e.event_value : ''); }

function nameOf(person) { return (person && person.primary_name) || 'Unnamed person'; }
function personLink(id, name) {
  return '<a href="/people/' + id + '">' + escapeHtml(name || 'Unnamed person') + '</a>';
}

/* A small, fixed palette (lifted from chronicle.js's SAMPLE_DATA) so every
 * person without a real photo still gets one of the site's sepia tones,
 * picked deterministically from their id — no "tone" field exists on
 * Individual, so this is a purely decorative, front-end-only choice
 * (see docs/FRONTEND_DESIGN.md's FE-2 entry). */
var TONE_PALETTE = [
  ['#caa066', '#43301a'], ['#c0894c', '#3a2714'], ['#b07c43', '#33230f'],
  ['#c79355', '#3c2815'], ['#a9763f', '#2e1f0e'], ['#bd8a4e', '#3d2a16'],
  ['#9c6e3a', '#2c1d0d'], ['#ca9a60', '#42301b'],
];
function toneFor(id) { return TONE_PALETTE[Math.abs(id) % TONE_PALETTE.length]; }

function initialsFromDisplay(name) {
  var parts = (name || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  var first = parts[0][0];
  var last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

/* personPhotoHtml — a real thumbnail if one is linked, else a toned initials
 * cameo (chronicle.js's `photo()` global). Call applyTones() on the parent
 * after inserting this via innerHTML (chronicle.js's own CSP-compliance
 * rule: data-p1/data-p2 need that sweep to become real CSS custom props). */
function personPhotoHtml(person, media, cls) {
  var tones = toneFor(person.id);
  cls = cls || '';
  if (media) {
    return '<div class="photo ' + cls + '" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
      '<img src="' + media.thumb_url + '" alt="">' +
    '</div>';
  }
  return photo(initialsFromDisplay(person.primary_name), tones, cls); // chronicle.js global
}

/* A minimal, SAFE Markdown-ish renderer for Note.content (raw Markdown per
 * the contract — note_service.py: "rendering to safe HTML is a VIEW concern
 * (WP3)"). No CDN/npm markdown library exists here (self-hosted-only CSP;
 * BE owns Python dependencies, not FE), so this is a small, deliberately
 * limited subset: paragraphs, headings, bold/italic/code spans, "- " lists.
 * Full CommonMark is out of scope, matching the fuzzy-date precedent already
 * set in FRONTEND_DESIGN.md. Escaping happens FIRST, on the raw text, so no
 * amount of Markdown syntax can smuggle real HTML through (D315). */
function inlineMarkdown(escaped) {
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*(?!\*)(.+?)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}
function renderNoteContent(note) {
  var text = String(note.content || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  var blocks = text.split(/\n\n+/).filter(function(b) { return b.trim(); });
  if (note.content_type === 'plain') {
    return blocks.map(function(b) { return '<p>' + escapeHtml(b).replace(/\n/g, '<br>') + '</p>'; }).join('');
  }
  return blocks.map(function(block) {
    var heading = block.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      var level = heading[1].length + 2; // # -> h3 .. ### -> h5 (page keeps its own h1/h2)
      return '<h' + level + '>' + inlineMarkdown(escapeHtml(heading[2])) + '</h' + level + '>';
    }
    var lines = block.split('\n');
    if (lines.length && lines.every(function(l) { return /^[-*]\s+/.test(l.trim()); })) {
      return '<ul>' + lines.map(function(l) {
        return '<li>' + inlineMarkdown(escapeHtml(l.replace(/^[-*]\s+/, ''))) + '</li>';
      }).join('') + '</ul>';
    }
    return '<p>' + inlineMarkdown(escapeHtml(block)).replace(/\n/g, '<br>') + '</p>';
  }).join('');
}

/* Generic form -> plain-object reader for the simple CRUD forms (Names,
 * events use a custom reader instead because of the fuzzy-date group).
 * Checkbox -> boolean; everything else -> string (the API's own `or None`
 * handling on the Python side turns "" into null, so no client conversion
 * is needed here). */
function formToObject(form) {
  var obj = {};
  Array.prototype.forEach.call(form.elements, function(el) {
    if (!el.name) return;
    if (el.type === 'checkbox') obj[el.name] = el.checked;
    else if (el.type !== 'submit' && el.type !== 'button') obj[el.name] = el.value;
  });
  return obj;
}

function alertFormError(form, err) {
  var msg = (err && err.message) || 'Something went wrong — please try again.';
  var el = form.querySelector('.alert');
  if (!el) {
    el = document.createElement('div');
    el.className = 'alert alert-danger mt-2';
    el.setAttribute('role', 'alert');
    form.appendChild(el);
  }
  el.textContent = msg;
  el.classList.remove('d-none');
}
function showInlineError(container, message) {
  var el = container.querySelector('.alert');
  if (!el) {
    el = document.createElement('div');
    el.className = 'alert alert-danger mt-2';
    el.setAttribute('role', 'alert');
    container.appendChild(el);
  }
  el.textContent = message || 'Something went wrong.';
  el.classList.remove('d-none');
}

/* toggleForm/hideForm — the one open/close mechanism every inline "+ Add …"
 * drawer in this file uses (Names, Events, Relationships pickers, Sources).
 * Cancel buttons are found by the shared `.inline-form-slot` class, so one
 * delegated handler per tab covers all of them (see each wireXActions). */
function toggleForm(slot, html) {
  slot.innerHTML = html;
  slot.classList.remove('d-none');
}
function hideForm(slot) {
  slot.classList.add('d-none');
  slot.innerHTML = '';
}

/* A reusable search-as-you-type person picker (Master Plan §5A: "Person
 * pickers = search-as-you-type against /api/search") used by every
 * Relationships "add" action (spouse, child, parent). Excludes this page's
 * own subject — you can't be your own parent/spouse/child. */
function personPicker(container, onPick) {
  container.innerHTML =
    '<input type="text" class="form-control person-picker__input" placeholder="Search by name…" autocomplete="off">' +
    '<div class="list-group person-picker__results"></div>';
  var input = container.querySelector('.person-picker__input');
  var results = container.querySelector('.person-picker__results');
  input.addEventListener('input', debounce(function() {
    var q = input.value.trim();
    if (!q) { results.innerHTML = ''; return; }
    apiFetch('/api/search?q=' + encodeURIComponent(q)).then(function(data) {
      var people = (data.people || []).filter(function(p) { return p.id !== personId; });
      results.innerHTML = people.length ? people.map(function(p) {
        return '<button type="button" class="list-group-item list-group-item-action" ' +
          'data-id="' + p.id + '" data-name="' + escapeHtml(p.primary_name || 'Unnamed person') + '">' +
          escapeHtml(p.primary_name || 'Unnamed person') +
          '<span class="text-muted small d-block">' +
            escapeHtml(FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living)) +
          '</span></button>';
      }).join('') : '<p class="text-muted small mb-0 p-2">No matches.</p>';
    }).catch(function() {
      results.innerHTML = '<p class="text-muted small mb-0 p-2">Search isn’t available right now.</p>';
    });
  }, 250));
  results.addEventListener('click', function(e) {
    var row = e.target.closest('[data-id]');
    if (!row) return;
    onPick(parseInt(row.dataset.id, 10), row.dataset.name);
  });
}
function markPicked(container, label) {
  container.innerHTML = '<p class="mb-0 text-muted">Selected: <strong>' + escapeHtml(label) + '</strong></p>';
}

/* =============================================================================
 * 1) MEMOIZED DATA GETTERS — one fetch per key per page load
 * ===========================================================================*/

function getIndividual() { return once('individual', function() { return apiFetch('/api/individuals/' + personId); }); }
function getOwnEvents() {
  return once('ownEvents', function() {
    return apiFetch('/api/events?subject_type=individual&subject_id=' + personId).then(function(d) { return d.events || []; });
  });
}
function getIndividualEvents(id) {
  return once('events:' + id, function() {
    return apiFetch('/api/events?subject_type=individual&subject_id=' + id).then(function(d) { return d.events || []; });
  });
}
function getOwnNotes() {
  return once('ownNotes', function() {
    return apiFetch('/api/notes?subject_type=individual&subject_id=' + personId).then(function(d) { return d.notes || []; });
  });
}
function getOwnMedia() {
  return once('ownMedia', function() {
    return apiFetch('/api/media?subject_type=individual&subject_id=' + personId).then(function(d) { return d.media || []; });
  });
}
function getAllMedia() {
  return once('allMedia', function() { return apiFetch('/api/media').then(function(d) { return d.media || []; }); });
}
function getAllIndividuals() {
  return once('allIndividuals', function() {
    return apiFetch('/api/individuals').then(function(d) {
      var map = {};
      (d.individuals || []).forEach(function(p) { map[p.id] = p; });
      return map;
    });
  });
}
function getAllFamilies() {
  return once('allFamilies', function() { return apiFetch('/api/families').then(function(d) { return d.families || []; }); });
}
function getFamilyDetail(famId) { return once('family:' + famId, function() { return apiFetch('/api/families/' + famId); }); }
function getFamilyEvents(famId) {
  return once('familyEvents:' + famId, function() {
    return apiFetch('/api/events?subject_type=family&subject_id=' + famId).then(function(d) { return d.events || []; });
  });
}
function getAllCitations() {
  return once('allCitations', function() { return apiFetch('/api/citations').then(function(d) { return d.citations || []; }); });
}
function getAllSources() {
  return once('allSources', function() { return apiFetch('/api/sources').then(function(d) { return d.sources || []; }); });
}

/* getRelationships — the one function that turns the graph the API exposes
 * (pedigree edges + the flat family list) into the Parents/Spouses/Children/
 * Siblings shape the Relationships tab (and Story's Family card, and
 * Timeline's Family-class events) all need. See docs/openapi.yaml's Tree tag:
 * `/api/families` never returns child rows in its LIST shape (only on a
 * single family's detail GET), and there is no "families I'm a child in"
 * endpoint — so parent-family discovery goes through
 * `/api/individuals/{id}/pedigree?direction=ancestors&depth=1`, whose edges
 * name exactly the family id(s) where this person is the child. Everyone's
 * vitals (birth/death year, living) come from ONE `/api/individuals` call,
 * the same family-scale "fetch it all, filter client-side" approach
 * people.js already uses for sort — see DEVDIARY_FE.md's FE-2 entry. */
function getRelationships() {
  return once('relationships', function() {
    return Promise.all([
      apiFetch('/api/individuals/' + personId + '/pedigree?direction=ancestors&depth=1'),
      getAllFamilies(),
      getAllIndividuals(),
    ]).then(function(results) {
      var pedigree = results[0], allFamilies = results[1], peopleMap = results[2];

      var parentFamilyIds = [];
      (pedigree.edges || []).forEach(function(e) {
        if (e.type === 'parent-child' && e.child_id === personId && parentFamilyIds.indexOf(e.family_id) === -1) {
          parentFamilyIds.push(e.family_id);
        }
      });

      var spouseFamilies = allFamilies.filter(function(f) {
        return f.partner1_id === personId || f.partner2_id === personId;
      });

      var detailIds = parentFamilyIds.concat(spouseFamilies.map(function(f) { return f.id; }));
      return Promise.all(detailIds.map(getFamilyDetail)).then(function(details) {
        var detailById = {};
        details.forEach(function(d) { detailById[d.id] = d; });

        var parents = [];
        parentFamilyIds.forEach(function(famId) {
          var fam = detailById[famId];
          var mine = (fam.children || []).filter(function(c) { return c.child_id === personId; })[0];
          [fam.partner1_id, fam.partner2_id].forEach(function(pid) {
            if (pid) {
              parents.push({
                id: pid, person: peopleMap[pid],
                pedigree_type: mine ? mine.pedigree_type : 'birth',
                family_id: famId,
              });
            }
          });
        });

        var siblingsMap = {};
        parentFamilyIds.forEach(function(famId) {
          var fam = detailById[famId];
          (fam.children || []).forEach(function(c) {
            if (c.child_id !== personId) {
              siblingsMap[c.child_id] = {
                id: c.child_id, person: peopleMap[c.child_id],
                pedigree_type: c.pedigree_type, child_order: c.child_order, family_id: famId,
              };
            }
          });
        });
        var siblings = Object.keys(siblingsMap).map(function(k) { return siblingsMap[k]; })
          .sort(function(a, b) { return a.child_order - b.child_order; });

        var spouseCards = spouseFamilies.map(function(f) {
          var detail = detailById[f.id];
          var spouseId = f.partner1_id === personId ? f.partner2_id : f.partner1_id;
          return {
            family_id: f.id,
            spouse: spouseId ? peopleMap[spouseId] : null,
            children: (detail.children || []).slice().sort(function(a, b) { return a.child_order - b.child_order; }),
          };
        });

        return { parents: parents, siblings: siblings, spouseCards: spouseCards };
      });
    });
  });
}

/* Cache-reset helpers — called after any mutation, so the NEXT time a tab
 * (re)renders it sees fresh data. Deliberately coarse (family scale — same
 * "brute force is fine" call FRONTEND_DESIGN.md already made for sorting). */
function resetRelationshipCaches() {
  invalidate('relationships');
  invalidate('allFamilies');
  invalidatePrefix('family:');
  invalidatePrefix('familyEvents:');
  loadedTabs.story = false;
  loadedTabs.timeline = false;
}
function resetDetailsCaches() {
  invalidate('individual');
  invalidate('ownEvents');
  loadedTabs.story = false;
  loadedTabs.timeline = false;
  loadedTabs.sources = false;
}
function resetPhotosCaches() {
  invalidate('ownMedia');
  invalidate('allMedia');
  loadedTabs.story = false;
}
function resetSourcesCaches() {
  invalidate('allCitations');
  invalidate('allSources');
  loadedTabs.story = false;
  loadedTabs.timeline = false;
}

/* =============================================================================
 * 2) TAB INFRASTRUCTURE — hash-based, deep-linkable, lazy-loaded
 * ===========================================================================*/

var TABS = ['story', 'relationships', 'timeline', 'photos', 'details', 'sources'];
var loadedTabs = {};
var loaders = {
  story: loadStoryTab,
  relationships: loadRelationshipsTab,
  timeline: loadTimelineTab,
  photos: loadPhotosTab,
  details: loadDetailsTab,
  sources: loadSourcesTab,
};

function currentTab() {
  var h = (window.location.hash || '').replace('#', '');
  return TABS.indexOf(h) !== -1 ? h : 'story';
}

function activateTab(tab) {
  TABS.forEach(function(t) {
    var panel = document.getElementById('tab-' + t);
    var link = personTabsNav.querySelector('[data-tab="' + t + '"]');
    var active = t === tab;
    panel.classList.toggle('d-none', !active);
    link.classList.toggle('is-active', active);
    if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  if (!loadedTabs[tab]) {
    loadedTabs[tab] = true;
    loaders[tab]();
  }
}

/* =============================================================================
 * 3) HEADER — portrait, name, lifespan, id, actions
 * ===========================================================================*/

function renderHeader() {
  var el = document.getElementById('personHeader');
  Promise.all([getIndividual(), getOwnEvents(), getOwnMedia()]).then(function(results) {
    var ind = results[0], events = results[1], media = results[2];
    var birt = events.filter(function(e) { return e.event_tag === 'BIRT'; })[0];
    var deat = events.filter(function(e) { return e.event_tag === 'DEAT'; })[0];
    var life = FamilyHubFmt.lifespan(birt ? yearOf(birt.date_sort) : null, deat ? yearOf(deat.date_sort) : null, ind.living);
    var portrait = media[0] || null;

    document.title = (ind.primary_name || ('Person #' + ind.id)) + ' — FamilyHub';

    el.innerHTML =
      '<div class="person-header__photo">' + personPhotoHtml({ id: ind.id, primary_name: ind.primary_name }, portrait, 'person-header__cameo') + '</div>' +
      '<div class="person-header__body">' +
        '<h1 class="person-header__name">' + escapeHtml(ind.primary_name || 'Unnamed person') + '</h1>' +
        '<p class="person-header__meta">' + escapeHtml(FamilyHubFmt.joinDot([life, '#' + ind.id])) + '</p>' +
        '<div class="person-header__actions">' +
          '<a class="btn btn-outline-secondary" href="/coming-soon?feature=' + encodeURIComponent('View Tree') + '">View Tree</a>' +
          '<a class="btn btn-outline-secondary" href="/coming-soon?feature=' + encodeURIComponent('View Relationship') + '">View Relationship</a>' +
          /* No /api/follow endpoint exists yet — BLOCKERS.md (FE-2, OPEN) asks
           * the BE whether this lands in v1 or is cut. Rendered disabled, not
           * faked, per §5A. */
          '<button type="button" class="btn btn-outline-secondary" disabled ' +
            'title="Coming soon — following a person isn’t available yet">Follow</button>' +
        '</div>' +
      '</div>';
    applyTones(el); // chronicle.js global
  }).catch(function() {
    el.innerHTML = '<p class="text-muted mb-0">This person could not be loaded.</p>';
  });
}

/* =============================================================================
 * PLACES — find-or-create, same pattern as people.js's Register form (a
 * shared <datalist id="placesDatalist"> lives once in show.html; this page's
 * Details-tab event form reuses it exactly as people/new.html's birth/death
 * fields do).
 * ===========================================================================*/

function getPlaces() {
  if (!placesCache) placesCache = apiFetch('/api/places').then(function(d) { return d.places || []; });
  return placesCache;
}
function refreshPlacesDatalist() {
  getPlaces().then(function(places) {
    var list = document.getElementById('placesDatalist');
    if (list) list.innerHTML = places.map(function(p) { return '<option value="' + escapeHtml(p.full_name) + '">'; }).join('');
  });
}
function resolvePlaceId(placeText) {
  if (!placeText) return Promise.resolve(null);
  return getPlaces().then(function(places) {
    var existing = places.filter(function(p) { return p.full_name.toLowerCase() === placeText.toLowerCase(); })[0];
    if (existing) return existing.id;
    return apiFetch('/api/places', { method: 'POST', body: { full_name: placeText } }).then(function(place) {
      placesCache = placesCache.then(function(list) { list.push(place); return list; });
      refreshPlacesDatalist();
      return place.id;
    });
  });
}

/* =============================================================================
 * 5) STORY TAB — the read view. Every card renders real data or is omitted
 * entirely (§5A) — there is no empty-shell "Latest Changes" card because
 * GET /api/activity/feed has no per-subject filter (BLOCKERS.md, FE-2, OPEN).
 * ===========================================================================*/

function panelCard(title, bodyHtml) {
  return '<div class="panel story-card"><h2 class="section-title">' + escapeHtml(title) + '</h2>' + bodyHtml + '</div>';
}

function vitalsRowsHtml(ind, events) {
  var rows = [['Sex', sexLabel(ind.sex)]];
  var birt = events.filter(function(e) { return e.event_tag === 'BIRT'; })[0];
  var deat = events.filter(function(e) { return e.event_tag === 'DEAT'; })[0];
  var buri = events.filter(function(e) { return e.event_tag === 'BURI'; })[0];
  if (birt) rows.push(['Born', joinDateplace(birt)]);
  if (deat) rows.push(['Died', joinDateplace(deat)]);
  if (buri) rows.push(['Buried', joinDateplace(buri)]);
  events.filter(function(e) { return ['OCCU', 'RESI', 'EDUC', 'RELI'].indexOf(e.event_tag) !== -1; })
    .forEach(function(e) { rows.push([tagLabel(e.event_tag), e.event_value || joinDateplace(e)]); });
  return '<div class="vitals-list">' + rows.map(function(r) {
    return '<div class="vitals-list__row"><span class="vitals-list__k">' + escapeHtml(r[0]) +
      '</span><span class="vitals-list__v">' + escapeHtml(r[1] || '—') + '</span></div>';
  }).join('') + '</div>';
}

function loadStoryTab() {
  var panel = document.getElementById('tab-story');
  panel.innerHTML =
    '<div class="story-layout">' +
      '<div class="story-main" id="storyMain"><p class="text-muted">Loading…</p></div>' +
      '<aside class="story-rail panel" id="storyRail">' +
        '<h2 class="section-title">Timeline</h2>' +
        '<div id="storyRailBody"><p class="text-muted">Loading…</p></div>' +
      '</aside>' +
    '</div>';
  var mainEl = document.getElementById('storyMain');
  var railEl = document.getElementById('storyRailBody');

  Promise.all([
    getIndividual(), getOwnEvents(), getOwnNotes(), getOwnMedia(), getRelationships(), getAllCitations(),
  ]).then(function(results) {
    var ind = results[0], events = results[1], notes = results[2], media = results[3],
        rel = results[4], citations = results[5];
    var cards = [];

    // Life Sketch: the primary attached note. Note has no is_primary flag
    // (unlike Name), so "primary" here means "the first note that isn't a
    // Name Meaning entry" — see DEVDIARY_FE.md's FE-2 decisions.
    var nameMeaningNote = notes.filter(function(n) { return (n.title || '').toLowerCase().indexOf('name meaning') === 0; })[0];
    var lifeSketchNote = notes.filter(function(n) { return n !== nameMeaningNote; })[0];
    if (lifeSketchNote) cards.push(panelCard('Life Sketch', renderNoteContent(lifeSketchNote)));

    if (media.length) {
      var strip = media.slice(0, 6).map(function(m) {
        var tones = toneFor(m.id);
        return '<a href="#photos" class="photo-strip__item">' +
          '<div class="photo" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
            '<img src="' + m.thumb_url + '" alt="' + escapeHtml(m.title || '') + '">' +
          '</div></a>';
      }).join('');
      cards.push(panelCard('Photos', '<div class="photo-strip">' + strip + '</div>'));
    }

    var famBits = [];
    if (rel.parents.length) {
      famBits.push(rel.parents.map(function(p) { return personLink(p.id, nameOf(p.person)); }).join(' & ') +
        ' <span class="text-muted">(parents)</span>');
    }
    rel.spouseCards.forEach(function(card) {
      if (card.spouse) famBits.push(personLink(card.spouse.id, nameOf(card.spouse)) + ' <span class="text-muted">(spouse)</span>');
      card.children.forEach(function(c) { famBits.push(personLink(c.child_id, c.child_name) + ' <span class="text-muted">(child)</span>'); });
    });
    if (famBits.length) cards.push(panelCard('Family', '<p class="mb-0"><a href="#relationships">' + famBits.join(', ') + '</a></p>'));

    if (nameMeaningNote) cards.push(panelCard('Name Meaning', renderNoteContent(nameMeaningNote)));

    cards.push(panelCard('Vitals', vitalsRowsHtml(ind, events)));

    var ownCitations = citations.filter(function(c) { return c.subject_type === 'individual' && c.subject_id === personId; });
    if (ownCitations.length) {
      var top = ownCitations.slice(0, 3).map(function(c) {
        return '<li>' + escapeHtml(c.source_title || 'Untitled source') + (c.page ? ' — ' + escapeHtml(c.page) : '') + '</li>';
      }).join('');
      cards.push(panelCard('Sources',
        '<p>' + ownCitations.length + ' citation' + (ownCitations.length === 1 ? '' : 's') + ' — <a href="#sources">see all</a></p>' +
        '<ul class="mb-0">' + top + '</ul>'));
    }

    mainEl.innerHTML = cards.join('');
    applyTones(mainEl);

    var sortedEvents = events.slice().sort(function(a, b) { return (a.date_sort || '').localeCompare(b.date_sort || ''); });
    railEl.innerHTML = sortedEvents.length ? sortedEvents.map(function(e) {
      return '<div class="story-rail__row"><span class="story-rail__year">' + (yearOf(e.date_sort) || '?') +
        '</span><span class="story-rail__label">' + escapeHtml(eventLabel(e)) + '</span></div>';
    }).join('') : '<p class="text-muted">No events recorded yet.</p>';
  }).catch(function() {
    mainEl.innerHTML = '<p class="text-muted">This person’s story isn’t available right now.</p>';
  });
}

/* =============================================================================
 * 6) RELATIONSHIPS TAB — Parents, Spouses & Partners, Siblings. ASSO ("Other
 * Relationships") is v2 scope (Master Plan §3.6) — not built here.
 * ===========================================================================*/

function relSectionHeader(title, actionHtml) {
  return '<div class="d-flex justify-content-between align-items-center rel-section-head"><h2 class="section-title mb-0">' +
    escapeHtml(title) + '</h2>' + actionHtml + '</div>';
}

function relCard(person, id, badges, actionsHtml) {
  var p = person || { id: id, primary_name: null };
  var vitals = (p.birth_year || p.death_year || p.living != null) ?
    '<div class="text-muted small">' + escapeHtml(FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living)) + '</div>' : '';
  var badgeHtml = badges.filter(Boolean).join('');
  return '<div class="rel-card">' +
    '<div class="rel-card__photo">' + personPhotoHtml({ id: id, primary_name: p.primary_name }, null, 'rel-card__cameo') + '</div>' +
    '<div class="rel-card__body">' +
      personLink(id, p.primary_name) + vitals +
      (badgeHtml ? '<div class="rel-card__badges">' + badgeHtml + '</div>' : '') +
    '</div>' +
    (actionsHtml ? '<div class="rel-card__actions">' + actionsHtml + '</div>' : '') +
  '</div>';
}

function spouseCardHtml(card) {
  var marr = card.events.filter(function(e) { return e.event_tag === 'MARR'; })[0];
  var div_ = card.events.filter(function(e) { return e.event_tag === 'DIV'; })[0];
  var spouseHtml = card.spouse ? personLink(card.spouse.id, nameOf(card.spouse)) : '<span class="text-muted">Unlinked partner</span>';
  var meta = [];
  if (marr) meta.push('Married ' + joinDateplace(marr));
  if (div_) meta.push('Divorced ' + joinDateplace(div_));

  var childrenHtml = card.children.length ? '<div class="rel-cards">' + card.children.map(function(c) {
    var actions = canContribute ?
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-edit-child="' +
        card.family_id + ':' + c.child_id + ':' + c.pedigree_type + ':' + c.child_order + '">Edit</button> ' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-remove-link ' +
        'data-family-id="' + card.family_id + '" data-child-id="' + c.child_id + '">Remove</button>' : '';
    return relCard({ id: c.child_id, primary_name: c.child_name }, c.child_id, [pedigreeBadge(c.pedigree_type)], actions) +
      '<div data-child-edit-form="' + card.family_id + '-' + c.child_id + '" class="d-none inline-form-slot mb-2 w-100"></div>';
  }).join('') + '</div>' : '<p class="text-muted small mb-0">No children recorded in this family yet.</p>';

  return '<div class="rel-family-card">' +
    '<div class="rel-family-card__head">' +
      '<strong>' + spouseHtml + '</strong>' +
      (meta.length ? '<span class="text-muted small"> · ' + escapeHtml(meta.join(' · ')) + '</span>' : '') +
      (canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm ms-auto" data-remove-family="' + card.family_id + '">Remove</button>' : '') +
    '</div>' +
    (canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm mt-2 mb-2" data-add-child="' + card.family_id + '">+ Add child</button>' : '') +
    '<div data-child-form="' + card.family_id + '" class="d-none inline-form-slot mt-2 mb-2"></div>' +
    childrenHtml +
  '</div>';
}

function linkParentsFormHtml() {
  return '<div class="row g-3">' +
    '<div class="col-md-6"><label class="form-label">Parent 1</label><div class="parent1-picker"></div></div>' +
    '<div class="col-md-6"><label class="form-label">Parent 2 (optional)</label><div class="parent2-picker"></div></div>' +
    '<div class="col-md-4"><label class="form-label">This person is a…</label><select class="form-select" id="linkParentsPedigree">' +
      '<option value="birth">Birth child</option><option value="adopted">Adopted child</option>' +
      '<option value="foster">Foster child</option><option value="step">Stepchild</option></select></div>' +
    '<div class="col-md-4"><label class="form-label">Birth order</label><input type="number" class="form-control" id="linkParentsOrder" value="0" min="0"></div>' +
  '</div>' +
  '<div class="mt-2 d-flex gap-2"><button type="button" class="btn btn-primary btn-sm" id="btnSaveLinkParents">Save</button>' +
    '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>';
}

/* find-or-create a family between two (possibly null) partner ids — the
 * same find-or-create spirit as people.js's Place handling, applied to a
 * Family instead of a Place. */
function findOrCreateFamily(id1, id2) {
  return getAllFamilies().then(function(families) {
    var existing = families.filter(function(f) {
      if (id1 != null && id2 != null) {
        return (f.partner1_id === id1 && f.partner2_id === id2) || (f.partner1_id === id2 && f.partner2_id === id1);
      }
      var only = id1 != null ? id1 : id2;
      return f.partner1_id === only || f.partner2_id === only;
    })[0];
    if (existing) return existing.id;
    return apiFetch('/api/families', { method: 'POST', body: { partner1_id: id1, partner2_id: id2 } })
      .then(function(f) { invalidate('allFamilies'); return f.id; });
  });
}

function renderRelationshipsHtml(panel, rel) {
  var html = '';

  html += relSectionHeader('Parents', canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm" id="btnLinkParents">+ Link parents</button>' : '');
  html += '<div id="linkParentsForm" class="d-none inline-form-slot mb-3"></div>';
  html += rel.parents.length ? '<div class="rel-cards">' + rel.parents.map(function(p) {
    var actions = canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm" data-remove-link ' +
      'data-family-id="' + p.family_id + '" data-child-id="' + personId + '">Remove</button>' : '';
    return relCard(p.person, p.id, [pedigreeBadge(p.pedigree_type)], actions);
  }).join('') + '</div>' : '<p class="text-muted">No parents recorded yet.</p>';

  html += relSectionHeader('Spouses & Partners', canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm" id="btnAddSpouse">+ Add spouse/partner</button>' : '');
  html += '<div id="addSpouseForm" class="d-none inline-form-slot mb-3"></div>';
  html += rel.spouseCards.length ? rel.spouseCards.map(spouseCardHtml).join('') : '<p class="text-muted">No spouses or partners recorded yet.</p>';

  html += relSectionHeader('Siblings', '');
  html += rel.siblings.length ? '<div class="rel-cards">' + rel.siblings.map(function(s) {
    return relCard(s.person, s.id, [pedigreeBadge(s.pedigree_type)], '');
  }).join('') : '<p class="text-muted">No siblings on file.</p>';

  panel.innerHTML = '<div class="panel">' + html + '</div>';
  applyTones(panel);
  wireRelationshipsActions(panel);
}

function wireRelationshipsActions(panel) {
  var picked = {}; // scratch space for open person-pickers this render

  panel.addEventListener('click', function(e) {
    var cancelBtn = e.target.closest('[data-cancel-form]');
    if (cancelBtn) { var slot = cancelBtn.closest('.inline-form-slot'); if (slot) hideForm(slot); return; }

    if (e.target.closest('#btnLinkParents')) {
      var lpSlot = panel.querySelector('#linkParentsForm');
      toggleForm(lpSlot, linkParentsFormHtml());
      picked.parent1 = null; picked.parent2 = null;
      personPicker(lpSlot.querySelector('.parent1-picker'), function(id, label) { picked.parent1 = { id: id, label: label }; markPicked(lpSlot.querySelector('.parent1-picker'), label); });
      personPicker(lpSlot.querySelector('.parent2-picker'), function(id, label) { picked.parent2 = { id: id, label: label }; markPicked(lpSlot.querySelector('.parent2-picker'), label); });
      return;
    }
    if (e.target.closest('#btnSaveLinkParents')) {
      var lpSlot2 = panel.querySelector('#linkParentsForm');
      if (!picked.parent1 && !picked.parent2) { showInlineError(lpSlot2, 'Pick at least one parent.'); return; }
      var pedigree = lpSlot2.querySelector('#linkParentsPedigree').value;
      var order = parseInt(lpSlot2.querySelector('#linkParentsOrder').value || '0', 10);
      findOrCreateFamily(picked.parent1 ? picked.parent1.id : null, picked.parent2 ? picked.parent2.id : null)
        .then(function(famId) {
          return apiFetch('/api/families/' + famId + '/children', { method: 'POST', body: { child_id: personId, pedigree_type: pedigree, child_order: order } });
        }).then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { showInlineError(lpSlot2, err.message); });
      return;
    }

    if (e.target.closest('#btnAddSpouse')) {
      var spSlot = panel.querySelector('#addSpouseForm');
      toggleForm(spSlot, '<div class="spouse-picker"></div><div class="mt-2 d-flex gap-2">' +
        '<button type="button" class="btn btn-primary btn-sm" id="btnSaveSpouse">Save</button>' +
        '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>');
      picked.spouse = null;
      personPicker(spSlot.querySelector('.spouse-picker'), function(id, label) { picked.spouse = { id: id, label: label }; markPicked(spSlot.querySelector('.spouse-picker'), label); });
      return;
    }
    if (e.target.closest('#btnSaveSpouse')) {
      var spSlot2 = panel.querySelector('#addSpouseForm');
      if (!picked.spouse) { showInlineError(spSlot2, 'Pick a person first.'); return; }
      apiFetch('/api/families', { method: 'POST', body: { partner1_id: personId, partner2_id: picked.spouse.id } })
        .then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { showInlineError(spSlot2, err.message); });
      return;
    }

    var addChildBtn = e.target.closest('[data-add-child]');
    if (addChildBtn) {
      var famId = addChildBtn.dataset.addChild;
      var cSlot = panel.querySelector('[data-child-form="' + famId + '"]');
      toggleForm(cSlot, '<div class="child-picker"></div>' +
        '<div class="row g-3 mt-0"><div class="col-md-4"><label class="form-label">Relationship</label>' +
        '<select class="form-select child-pedigree"><option value="birth">Birth child</option><option value="adopted">Adopted</option>' +
        '<option value="foster">Foster</option><option value="step">Step</option></select></div>' +
        '<div class="col-md-4"><label class="form-label">Birth order</label><input type="number" class="form-control child-order" value="0" min="0"></div></div>' +
        '<div class="mt-2 d-flex gap-2"><button type="button" class="btn btn-primary btn-sm" data-save-child="' + famId + '">Save</button>' +
        '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>');
      picked['child_' + famId] = null;
      personPicker(cSlot.querySelector('.child-picker'), function(id, label) { picked['child_' + famId] = { id: id, label: label }; markPicked(cSlot.querySelector('.child-picker'), label); });
      return;
    }
    var saveChildBtn = e.target.closest('[data-save-child]');
    if (saveChildBtn) {
      var famId2 = saveChildBtn.dataset.saveChild;
      var cSlot2 = panel.querySelector('[data-child-form="' + famId2 + '"]');
      var pick = picked['child_' + famId2];
      if (!pick) { showInlineError(cSlot2, 'Pick a person first.'); return; }
      var pedigree2 = cSlot2.querySelector('.child-pedigree').value;
      var order2 = parseInt(cSlot2.querySelector('.child-order').value || '0', 10);
      apiFetch('/api/families/' + famId2 + '/children', { method: 'POST', body: { child_id: pick.id, pedigree_type: pedigree2, child_order: order2 } })
        .then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { showInlineError(cSlot2, err.message); });
      return;
    }

    var editChildBtn = e.target.closest('[data-edit-child]');
    if (editChildBtn) {
      var parts = editChildBtn.dataset.editChild.split(':');
      var famId3 = parts[0], childId3 = parts[1], curPedigree = parts[2], curOrder = parts[3];
      var ecSlot = panel.querySelector('[data-child-edit-form="' + famId3 + '-' + childId3 + '"]');
      toggleForm(ecSlot,
        '<div class="row g-3"><div class="col-md-4"><label class="form-label">Relationship</label><select class="form-select edit-child-pedigree">' +
          ['birth', 'adopted', 'foster', 'step'].map(function(p) { return '<option value="' + p + '"' + (p === curPedigree ? ' selected' : '') + '>' + PEDIGREE_LABELS[p] + '</option>'; }).join('') +
        '</select></div><div class="col-md-4"><label class="form-label">Birth order</label><input type="number" class="form-control edit-child-order" value="' + curOrder + '" min="0"></div></div>' +
        '<div class="mt-2 d-flex gap-2"><button type="button" class="btn btn-primary btn-sm" data-save-child-edit="' + famId3 + ':' + childId3 + '">Save</button>' +
        '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>');
      return;
    }
    var saveChildEditBtn = e.target.closest('[data-save-child-edit]');
    if (saveChildEditBtn) {
      var parts2 = saveChildEditBtn.dataset.saveChildEdit.split(':');
      var famId4 = parts2[0], childId4 = parts2[1];
      var ecSlot2 = panel.querySelector('[data-child-edit-form="' + famId4 + '-' + childId4 + '"]');
      var pedigree3 = ecSlot2.querySelector('.edit-child-pedigree').value;
      var order3 = parseInt(ecSlot2.querySelector('.edit-child-order').value || '0', 10);
      // No PUT exists for an ACTIVE family_children row (BLOCKERS.md forward
      // note, FE-2): DELETE then re-POST is the real restore-with-new-values
      // path family_service.add_child already implements for a soft-deleted
      // link — reused here for "edit," not faked.
      apiFetch('/api/families/' + famId4 + '/children/' + childId4, { method: 'DELETE' })
        .then(function() { return apiFetch('/api/families/' + famId4 + '/children', { method: 'POST', body: { child_id: parseInt(childId4, 10), pedigree_type: pedigree3, child_order: order3 } }); })
        .then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { showInlineError(ecSlot2, err.message); });
      return;
    }

    var removeLinkBtn = e.target.closest('[data-remove-link]');
    if (removeLinkBtn) {
      if (!window.confirm('Remove this family link? A Curator can restore it later.')) return;
      apiFetch('/api/families/' + removeLinkBtn.dataset.familyId + '/children/' + removeLinkBtn.dataset.childId, { method: 'DELETE' })
        .then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { window.alert(err.message || 'Could not remove that link.'); });
      return;
    }

    var removeFamilyBtn = e.target.closest('[data-remove-family]');
    if (removeFamilyBtn) {
      if (!window.confirm('Remove this spousal relationship? A Curator can restore it later.')) return;
      apiFetch('/api/families/' + removeFamilyBtn.dataset.removeFamily, { method: 'DELETE' })
        .then(function() { resetRelationshipCaches(); renderRelationships(panel); })
        .catch(function(err) { window.alert(err.message || 'Could not remove that relationship.'); });
      return;
    }
  });
}

function loadRelationshipsTab() {
  var panel = document.getElementById('tab-relationships');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';
  renderRelationships(panel);
}
function renderRelationships(panel) {
  getRelationships().then(function(rel) {
    return Promise.all(rel.spouseCards.map(function(c) { return getFamilyEvents(c.family_id); }))
      .then(function(eventsPerFamily) {
        rel.spouseCards.forEach(function(c, i) { c.events = eventsPerFamily[i]; });
        renderRelationshipsHtml(panel, rel);
      });
  }).catch(function() {
    panel.innerHTML = '<p class="text-muted">Relationships aren’t available right now.</p>';
  });
}

/* =============================================================================
 * 7) TIMELINE TAB — age spine, color-coded event classes (Life/Family/World),
 * a migration thread (place-change marks), "N sources" badges. Life-chapter
 * buckets and the migration thread are FE-only groupings computed from
 * date_sort + place — no schema support needed (see DEVDIARY_FE.md).
 * ===========================================================================*/

var LIFE_CHAPTERS = [
  { min: 0, max: 12, title: 'Childhood' },
  { min: 13, max: 17, title: 'Adolescence' },
  { min: 18, max: 29, title: 'Young Adult' },
  { min: 30, max: 64, title: 'Adult' },
  { min: 65, max: 999, title: 'Senior' },
];

/* ageAtEvent — years between a birth date_sort and an event's date_sort.
 * Falls back to a plain year difference when month/day are unknown (fuzzy
 * dates are the genealogy norm; an approximate age beats none). */
function ageAtEvent(birthSort, eventSort) {
  if (!birthSort || !eventSort) return null;
  var by = parseInt(birthSort.slice(0, 4), 10), bm = parseInt(birthSort.slice(5, 7), 10), bd = parseInt(birthSort.slice(8, 10), 10);
  var ey = parseInt(eventSort.slice(0, 4), 10), em = parseInt(eventSort.slice(5, 7), 10), ed = parseInt(eventSort.slice(8, 10), 10);
  if (!by || !ey) return null;
  var age = ey - by;
  if (bm && em && (em < bm || (em === bm && bd && ed && ed < bd))) age -= 1;
  return age;
}

function bucketIntoChapters(events, birthSort) {
  var buckets = LIFE_CHAPTERS.map(function(c) { return { title: c.title, min: c.min, max: c.max, events: [] }; });
  var before = { title: 'Before Birth', events: [] };
  var unaged = { title: 'Undated', events: [] };
  events.forEach(function(e) {
    var age = ageAtEvent(birthSort, e.date_sort);
    if (age == null) { unaged.events.push(e); return; }
    if (age < 0) { before.events.push(e); return; }
    var bucket = buckets.filter(function(b) { return age >= b.min && age <= b.max; })[0];
    (bucket || buckets[buckets.length - 1]).events.push(e);
  });
  var result = [];
  if (before.events.length) result.push(before);
  buckets.forEach(function(b) { if (b.events.length) result.push(b); });
  if (unaged.events.length) result.push(unaged);
  return result;
}

function relatedEventLabel(e) {
  var who = e.subject_label || 'A family member';
  if (e.event_tag === 'BIRT') return who + ' is born';
  if (e.event_tag === 'DEAT') return who + ' dies';
  return who + ' — ' + tagLabel(e.event_tag);
}
function timelineLabel(e) {
  if (e._class === 'world') return e.date_original; // the almanac title, stashed here — see loadTimelineTab
  if (e._related) return relatedEventLabel(e);
  if (e.subject_type === 'family') return e.event_tag === 'MARR' ? 'Married' : 'Divorced';
  return eventLabel(e);
}

function renderTimeline(panel, events, birthSort, citations) {
  if (!events.length) { panel.innerHTML = '<p class="text-muted">No events recorded yet.</p>'; return; }

  var citationCountByEvent = {};
  citations.forEach(function(c) {
    if (c.subject_type === 'event') citationCountByEvent[c.subject_id] = (citationCountByEvent[c.subject_id] || 0) + 1;
  });

  var chapters = birthSort ? bucketIntoChapters(events, birthSort) : [{ title: 'Timeline', events: events }];
  var lastPlace = null;

  var html = chapters.map(function(chapter) {
    var rows = chapter.events.map(function(e) {
      var age = birthSort ? ageAtEvent(birthSort, e.date_sort) : null;
      var moved = false;
      if (e._class !== 'world' && e.place) {
        moved = lastPlace !== null && e.place !== lastPlace;
        lastPlace = e.place;
      }
      var count = (typeof e.id === 'number' && citationCountByEvent[e.id]) || 0;
      var badge = count ? '<a href="#sources" class="tl-event__sources">' + count + ' source' + (count === 1 ? '' : 's') + '</a>' : '';
      return '<div class="tl-event tl-event--' + e._class + '">' +
        '<span class="tl-event__age' + (age == null ? ' tl-event__age--blank' : '') + '">' + (age != null ? 'age ' + age : '') + '</span>' +
        '<span class="tl-event__year">' + (yearOf(e.date_sort) || '?') + '</span>' +
        '<span class="tl-event__body">' +
          '<span class="tl-event__title">' + escapeHtml(timelineLabel(e)) + '</span>' +
          (e.place ? '<span class="tl-event__place">' + escapeHtml(e.place) + (moved ? ' <span class="tl-event__moved">— moved</span>' : '') + '</span>' : '') +
        '</span>' + badge +
      '</div>';
    }).join('');
    return '<div class="timeline-chapter"><h3 class="timeline-chapter__title">' + escapeHtml(chapter.title) + '</h3>' + rows + '</div>';
  }).join('');

  panel.innerHTML = '<div class="panel">' + html + '</div>';
}

function loadTimelineTab() {
  var panel = document.getElementById('tab-timeline');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';

  Promise.all([getOwnEvents(), getRelationships(), getAllCitations()]).then(function(results) {
    var ownEvents = results[0], rel = results[1], citations = results[2];

    var famFamilyIds = rel.spouseCards.map(function(c) { return c.family_id; });

    // The brief is specific: children's BIRTHS, spouse/parent DEATHS — not
    // the reverse (a spouse's own birth, a child's own death) — so these are
    // two separate id sets, each fetched for one tag only.
    var childIds = [];
    var spouseParentIds = [];
    rel.spouseCards.forEach(function(c) {
      if (c.spouse) spouseParentIds.push(c.spouse.id);
      c.children.forEach(function(ch) { childIds.push(ch.child_id); });
    });
    rel.parents.forEach(function(p) { spouseParentIds.push(p.id); });

    return Promise.all(
      famFamilyIds.map(getFamilyEvents)
        .concat(childIds.map(getIndividualEvents))
        .concat(spouseParentIds.map(getIndividualEvents))
    ).then(function(eventLists) {
        var familyEvents = [].concat.apply([], eventLists.slice(0, famFamilyIds.length))
          .filter(function(e) { return e.event_tag === 'MARR' || e.event_tag === 'DIV'; })
          .map(function(e) { return Object.assign({}, e, { _class: 'family' }); });

        var childBirths = [].concat.apply([], eventLists.slice(famFamilyIds.length, famFamilyIds.length + childIds.length))
          .filter(function(e) { return e.event_tag === 'BIRT'; })
          .map(function(e) { return Object.assign({}, e, { _class: 'family', _related: true }); });

        var spouseParentDeaths = [].concat.apply([], eventLists.slice(famFamilyIds.length + childIds.length))
          .filter(function(e) { return e.event_tag === 'DEAT'; })
          .map(function(e) { return Object.assign({}, e, { _class: 'family', _related: true }); });

        var relatedEvents = childBirths.concat(spouseParentDeaths);

        var lifeEvents = ownEvents.map(function(e) { return Object.assign({}, e, { _class: 'life' }); });
        var birt = lifeEvents.filter(function(e) { return e.event_tag === 'BIRT'; })[0];
        var deat = lifeEvents.filter(function(e) { return e.event_tag === 'DEAT'; })[0];
        var birthSort = birt ? birt.date_sort : null;
        var birthYear = birt ? yearOf(birt.date_sort) : null;
        var endYear = deat ? yearOf(deat.date_sort) : new Date().getFullYear();

        var historyUrl = '/api/historical-events' + (birthYear ? ('?year_from=' + birthYear + '&year_to=' + endYear) : '');
        return apiFetch(historyUrl).then(function(hd) {
          var worldEvents = (hd.historical_events || []).map(function(e) {
            return { _class: 'world', event_tag: 'HIST', date_sort: e.date_sort || (e.year + '-00-00'), date_original: e.title, place: null, id: 'hist-' + e.id };
          });
          var all = lifeEvents.concat(familyEvents, relatedEvents, worldEvents);
          all.sort(function(a, b) { return (a.date_sort || '').localeCompare(b.date_sort || ''); });
          renderTimeline(panel, all, birthSort, citations);
        });
      });
  }).catch(function() {
    panel.innerHTML = '<p class="text-muted">This person’s timeline isn’t available right now.</p>';
  });
}

/* =============================================================================
 * 8) PHOTOS TAB — grid + lightbox + upload + link/unlink an existing photo.
 * ===========================================================================*/

function ensureLightbox() {
  if (lightboxEl) return lightboxEl;
  lightboxEl = document.createElement('div');
  lightboxEl.className = 'lightbox';
  lightboxEl.innerHTML =
    '<button type="button" class="lightbox__close" aria-label="Close">&times;</button>' +
    '<img class="lightbox__img" alt="">' +
    '<figcaption class="lightbox__cap"></figcaption>' +
    '<button type="button" class="btn btn-outline-light btn-sm lightbox__unlink d-none">Remove from this person</button>';
  document.body.appendChild(lightboxEl);
  lightboxEl.querySelector('.lightbox__close').addEventListener('click', closeLightbox);
  lightboxEl.addEventListener('click', function(e) { if (e.target === lightboxEl) closeLightbox(); });
  document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeLightbox(); });
  return lightboxEl;
}
function closeLightbox() { if (lightboxEl) lightboxEl.classList.remove('is-on'); }
function openLightbox(media) {
  var el = ensureLightbox();
  el.querySelector('.lightbox__img').src = media.file_url;
  el.querySelector('.lightbox__cap').textContent = [media.title, media.capture_date].filter(Boolean).join(' · ');
  var unlinkBtn = el.querySelector('.lightbox__unlink');
  if (canContribute) {
    unlinkBtn.classList.remove('d-none');
    unlinkBtn.onclick = function() {
      if (!window.confirm('Remove this photo from this person’s page? The photo itself is not deleted.')) return;
      apiFetch('/api/media/' + media.id + '/links/individual/' + personId, { method: 'DELETE' }).then(function() {
        closeLightbox(); resetPhotosCaches(); renderPhotos(document.getElementById('tab-photos'));
      }).catch(function(err) { window.alert(err.message || 'Could not remove that photo.'); });
    };
  } else {
    unlinkBtn.classList.add('d-none');
  }
  el.classList.add('is-on');
}

function photoTileHtml(m) {
  var tones = toneFor(m.id);
  return '<figure class="cell" data-open-lightbox="' + m.id + '">' +
    '<div class="photo" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
      '<img src="' + m.thumb_url + '" alt="' + escapeHtml(m.title || '') + '">' +
    '</div>' +
    '<figcaption class="cell__cap"><span class="t">' + escapeHtml(m.title || 'Untitled') + '</span>' +
      (m.capture_date ? '<span class="d">' + escapeHtml(m.capture_date) + '</span>' : '') + '</figcaption>' +
  '</figure>';
}

function photoUploadFormHtml() {
  return '<form id="photoUploadForm" class="mb-3">' +
    '<div class="row g-2 align-items-end">' +
      '<div class="col-md-4"><label class="form-label" for="photoFile">Upload a photo</label>' +
        '<input type="file" id="photoFile" class="form-control" accept="image/*" required></div>' +
      '<div class="col-md-3"><label class="form-label" for="photoTitle">Title</label><input type="text" id="photoTitle" class="form-control"></div>' +
      '<div class="col-md-3"><label class="form-label" for="photoCaptureDate">Taken</label>' +
        '<input type="text" id="photoCaptureDate" class="form-control" placeholder="e.g. Summer 1952"></div>' +
      '<div class="col-md-2"><button type="submit" class="btn btn-primary w-100">Upload</button></div>' +
    '</div>' +
    '<div class="mt-2"><label class="form-label" for="photoDescription">Description</label>' +
      '<textarea id="photoDescription" class="form-control" rows="2"></textarea></div>' +
  '</form>';
}

function wirePhotoPicker(container) {
  getAllMedia().then(function(all) {
    container.innerHTML =
      '<input type="text" class="form-control mb-2" id="photoSearchInput" placeholder="Search photos by title…" autocomplete="off">' +
      '<div class="wall gallery-wall" id="photoSearchResults"></div>';
    var input = container.querySelector('#photoSearchInput');
    var results = container.querySelector('#photoSearchResults');
    function render(list) {
      results.innerHTML = list.slice(0, 12).map(function(m) {
        var tones = toneFor(m.id);
        return '<figure class="cell" data-link-media="' + m.id + '">' +
          '<div class="photo" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '"><img src="' + m.thumb_url + '" alt=""></div>' +
          '<figcaption class="cell__cap"><span class="t">' + escapeHtml(m.title || 'Untitled') + '</span></figcaption></figure>';
      }).join('');
      applyTones(results);
    }
    render(all);
    input.addEventListener('input', debounce(function() {
      var q = input.value.trim().toLowerCase();
      render(q ? all.filter(function(m) { return (m.title || '').toLowerCase().indexOf(q) !== -1; }) : all);
    }, 200));
    results.addEventListener('click', function(e) {
      var fig = e.target.closest('[data-link-media]');
      if (!fig) return;
      apiFetch('/api/media/' + fig.dataset.linkMedia + '/links', { method: 'POST', body: { subject_type: 'individual', subject_id: personId } })
        .then(function() { resetPhotosCaches(); renderPhotos(document.getElementById('tab-photos')); })
        .catch(function(err) { window.alert(err.message || 'Could not link that photo.'); });
    });
  });
}

function wirePhotosActions(panel) {
  panel.addEventListener('click', function(e) {
    var cancelBtn = e.target.closest('[data-cancel-form]');
    if (cancelBtn) { var slot = cancelBtn.closest('.inline-form-slot'); if (slot) hideForm(slot); return; }

    if (e.target.closest('#btnLinkExistingPhoto')) {
      var slot2 = panel.querySelector('#linkPhotoForm');
      slot2.classList.remove('d-none');
      wirePhotoPicker(slot2);
      return;
    }
    var tile = e.target.closest('[data-open-lightbox]');
    if (tile) {
      var id = parseInt(tile.dataset.openLightbox, 10);
      var media = currentMediaList.filter(function(m) { return m.id === id; })[0];
      if (media) openLightbox(media);
      return;
    }
  });

  panel.addEventListener('submit', function(e) {
    if (e.target.id === 'photoUploadForm') {
      e.preventDefault();
      var form = e.target;
      var fileInput = form.querySelector('#photoFile');
      if (!fileInput.files.length) { alertFormError(form, { message: 'Choose a photo to upload.' }); return; }
      var fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('title', form.querySelector('#photoTitle').value.trim());
      fd.append('description', form.querySelector('#photoDescription').value.trim());
      fd.append('capture_date', form.querySelector('#photoCaptureDate').value.trim());
      fd.append('subject_type', 'individual');
      fd.append('subject_id', String(personId));
      apiFetch('/api/media', { method: 'POST', body: fd }).then(function() {
        resetPhotosCaches(); renderPhotos(panel);
      }).catch(function(err) { alertFormError(form, err); });
    }
  });
}

function loadPhotosTab() {
  var panel = document.getElementById('tab-photos');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';
  renderPhotos(panel);
}
function renderPhotos(panel) {
  getOwnMedia().then(function(media) {
    currentMediaList = media;
    var uploadForm = canContribute ? photoUploadFormHtml() : '';
    var linkForm = canContribute ?
      '<div class="mb-3"><button type="button" class="btn btn-outline-secondary btn-sm" id="btnLinkExistingPhoto">Link an existing photo</button>' +
      '<div id="linkPhotoForm" class="d-none inline-form-slot mt-2"></div></div>' : '';
    var grid = media.length ? '<div class="wall gallery-wall">' + media.map(photoTileHtml).join('') + '</div>' :
      '<p class="text-muted">No photos linked to this person yet.</p>';
    panel.innerHTML = '<div class="panel">' + uploadForm + linkForm + grid + '</div>';
    applyTones(panel);
    wirePhotosActions(panel);
  }).catch(function() {
    panel.innerHTML = '<p class="text-muted">Photos aren’t available right now.</p>';
  });
}

/* =============================================================================
 * 9) DETAILS TAB — the CRUD workbench (§5A depth bar in full). System fields
 * (id, timestamps, gedcom_xref) are never user input, per Master Plan §5A.
 * ===========================================================================*/

var NAME_TYPE_LABELS = { birth: 'Birth name', married: 'Married name', aka: 'Also known as', immigrant: 'Immigrant name', maiden: 'Maiden name' };
var RESTRICTION_OPTIONS = [
  { value: '', label: 'None' }, { value: 'confidential', label: 'Confidential' },
  { value: 'locked', label: 'Locked' }, { value: 'privacy', label: 'Privacy hold' },
];
var RESTRICTION_HELP = {
  '': 'No extra restriction beyond the standard living-person privacy rule.',
  confidential: 'Hidden from casual browsing; still visible to logged-in members with view access.',
  locked: 'Protected from further edits without a Curator’s help.',
  privacy: 'A privacy hold — treat this record’s details as sensitive.',
};
var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function col(colClass, label, name, value) {
  return '<div class="' + colClass + '"><label class="form-label">' + escapeHtml(label) + '</label>' +
    '<input type="text" class="form-control" name="' + name + '" value="' + escapeHtml(value || '') + '"></div>';
}

function namesListHtml(names) {
  if (!names.length) return '<p class="text-muted">No names recorded.</p>';
  return '<div class="table-responsive"><table class="table table-hover align-middle"><thead><tr>' +
    '<th>Name</th><th>Type</th><th>Primary</th>' + (canContribute ? '<th></th>' : '') + '</tr></thead><tbody>' +
    names.map(function(n) {
      return '<tr>' +
        '<td>' + escapeHtml(n.display || '(blank)') + '</td>' +
        '<td>' + escapeHtml(NAME_TYPE_LABELS[n.name_type] || n.name_type) + '</td>' +
        '<td>' + (n.is_primary ? '<span class="badge text-bg-primary">Primary</span>' : '') + '</td>' +
        (canContribute ? '<td class="text-nowrap">' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-edit-name="' + n.id + '">Edit</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-delete-name="' + n.id + '">Delete</button></td>' : '') +
      '</tr>';
    }).join('') + '</tbody></table></div>';
}

function nameFormHtml(name) {
  name = name || {};
  return '<form class="name-form" data-name-id="' + (name.id || '') + '">' +
    '<div class="row g-3">' +
      col('col-md-3', 'Prefix', 'name_prefix', name.name_prefix) +
      col('col-md-5', 'Given name(s)', 'given', name.given) +
      col('col-md-4', 'Nickname', 'nickname', name.nickname) +
      col('col-md-3', 'Surname prefix', 'surname_prefix', name.surname_prefix) +
      col('col-md-5', 'Surname', 'surname', name.surname) +
      col('col-md-4', 'Suffix', 'name_suffix', name.name_suffix) +
      '<div class="col-md-4"><label class="form-label">Name type</label><select class="form-select" name="name_type">' +
        Object.keys(NAME_TYPE_LABELS).map(function(k) { return '<option value="' + k + '"' + (name.name_type === k ? ' selected' : '') + '>' + NAME_TYPE_LABELS[k] + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="col-md-4"><label class="form-label">Order</label><input type="number" class="form-control" name="sort_order" value="' + (name.sort_order != null ? name.sort_order : 0) + '" min="0"></div>' +
      '<div class="col-md-4 d-flex align-items-end"><div class="form-check"><input class="form-check-input" type="checkbox" name="is_primary" id="isPrimary' + (name.id || 'new') + '"' + (name.is_primary ? ' checked' : '') + '>' +
        '<label class="form-check-label" for="isPrimary' + (name.id || 'new') + '">Primary name</label></div></div>' +
    '</div>' +
    '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Save</button>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>' +
  '</form>';
}

function personFactsFormHtml(ind) {
  if (!canContribute) {
    var opt = RESTRICTION_OPTIONS.filter(function(o) { return o.value === (ind.restriction || ''); })[0];
    return '<div class="vitals-list">' +
      '<div class="vitals-list__row"><span class="vitals-list__k">Sex</span><span class="vitals-list__v">' + sexLabel(ind.sex) + '</span></div>' +
      '<div class="vitals-list__row"><span class="vitals-list__k">Living</span><span class="vitals-list__v">' + (ind.living ? 'Yes' : 'No') + '</span></div>' +
      '<div class="vitals-list__row"><span class="vitals-list__k">Restriction</span><span class="vitals-list__v">' + escapeHtml(opt ? opt.label : 'None') + '</span></div>' +
    '</div>';
  }
  return '<form id="personFactsForm">' +
    '<div class="row g-3">' +
      '<div class="col-md-4"><label class="form-label">Sex</label><select class="form-select" name="sex">' +
        ['U', 'F', 'M', 'X'].map(function(v) { return '<option value="' + v + '"' + (ind.sex === v ? ' selected' : '') + '>' + SEX_LABELS[v] + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="col-md-4 d-flex align-items-end"><div class="form-check form-switch"><input class="form-check-input" type="checkbox" role="switch" name="living"' + (ind.living ? ' checked' : '') + '>' +
        '<label class="form-check-label">This person is living</label></div></div>' +
      '<div class="col-md-4"><label class="form-label">Restriction</label><select class="form-select" name="restriction">' +
        RESTRICTION_OPTIONS.map(function(o) { return '<option value="' + o.value + '"' + ((ind.restriction || '') === o.value ? ' selected' : '') + '>' + o.label + '</option>'; }).join('') +
      '</select><p class="form-text">' + escapeHtml(RESTRICTION_HELP[ind.restriction || ''] || '') + '</p></div>' +
    '</div>' +
    '<button type="submit" class="btn btn-primary btn-sm mt-2">Save</button>' +
  '</form>';
}

function eventsTableHtml(events) {
  if (!events.length) return '<p class="text-muted">No events recorded yet.</p>';
  var sorted = events.slice().sort(function(a, b) { return (a.date_sort || '').localeCompare(b.date_sort || ''); });
  return '<div class="table-responsive"><table class="table table-hover align-middle"><thead><tr>' +
    '<th>Event</th><th>Date</th><th>Place</th><th>Value</th>' + (canContribute ? '<th></th>' : '') + '</tr></thead><tbody>' +
    sorted.map(function(e) {
      return '<tr>' +
        '<td>' + escapeHtml(tagLabel(e.event_tag)) + '</td>' +
        '<td>' + escapeHtml(e.date_original || '—') + '</td>' +
        '<td>' + escapeHtml(e.place || '—') + '</td>' +
        '<td>' + escapeHtml(e.event_value || e.cause || e.age || '—') + '</td>' +
        (canContribute ? '<td class="text-nowrap">' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-edit-event="' + e.id + '">Edit</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-delete-event="' + e.id + '">Delete</button></td>' : '') +
      '</tr>';
    }).join('') + '</tbody></table></div>';
}

function parseFuzzyForEdit(dateOriginal, dateSort) {
  var year = '', month = '', day = '', qualifier = 'exact';
  if (dateSort) {
    var parts = String(dateSort).split('-');
    year = parts[0] && parts[0] !== '0000' ? String(parseInt(parts[0], 10)) : '';
    month = parts[1] && parts[1] !== '00' ? String(parseInt(parts[1], 10)) : '';
    day = parts[2] && parts[2] !== '00' ? String(parseInt(parts[2], 10)) : '';
  }
  if (dateOriginal) {
    if (/^ABT /.test(dateOriginal)) qualifier = 'about';
    else if (/^BEF /.test(dateOriginal)) qualifier = 'before';
    else if (/^AFT /.test(dateOriginal)) qualifier = 'after';
  }
  return { year: year, month: month, day: day, qualifier: qualifier };
}

function fuzzyDateFieldsHtml(d) {
  return '<div class="row g-3">' +
    '<div class="col-md-3"><label class="form-label">Precision</label><select class="form-select" name="date_qualifier">' +
      ['exact', 'about', 'before', 'after'].map(function(q) { return '<option value="' + q + '"' + (d.qualifier === q ? ' selected' : '') + '>' + q.charAt(0).toUpperCase() + q.slice(1) + '</option>'; }).join('') +
    '</select></div>' +
    '<div class="col-md-3"><label class="form-label">Year</label><input type="number" class="form-control" name="date_year" min="1" max="2100" value="' + escapeHtml(d.year) + '"></div>' +
    '<div class="col-md-3"><label class="form-label">Month</label><select class="form-select" name="date_month"><option value="">— optional —</option>' +
      MONTHS.map(function(m, i) { return '<option value="' + (i + 1) + '"' + (String(d.month) === String(i + 1) ? ' selected' : '') + '>' + m + '</option>'; }).join('') +
    '</select></div>' +
    '<div class="col-md-3"><label class="form-label">Day</label><input type="number" class="form-control" name="date_day" min="1" max="31" value="' + escapeHtml(d.day) + '"></div>' +
  '</div>';
}
function readFuzzyDateFromForm(form) {
  var year = form.elements.date_year.value;
  if (!year) return null;
  var month = form.elements.date_month.value, day = form.elements.date_day.value, qualifier = form.elements.date_qualifier.value;
  var y = String(parseInt(year, 10)).padStart(4, '0');
  var m = month ? String(month).padStart(2, '0') : '00';
  var d = day ? String(day).padStart(2, '0') : '00';
  var datePart = day && month ? (parseInt(day, 10) + ' ' + MONTHS[month - 1] + ' ' + year) : month ? (MONTHS[month - 1] + ' ' + year) : String(parseInt(year, 10));
  var prefixText = { about: 'ABT ', before: 'BEF ', after: 'AFT ' }[qualifier] || '';
  return { date_original: prefixText + datePart, date_sort: y + '-' + m + '-' + d };
}

/* Event tags are a free string server-side (no enum — event.py's event_tag is
 * a plain VARCHAR), so this curated list is a UI convenience, not a schema
 * limit — "Other" lets any GEDCOM tag through, matching §5A's "every
 * user-meaningful field capturable" even for tags this list doesn't name. */
var EVENT_TAG_GROUPS = {
  'Life events': ['BIRT', 'CHR', 'BAPM', 'CONF', 'BARM', 'BASM', 'FCOM', 'GRAD', 'RETI', 'NATU', 'IMMI', 'EMIG', 'CENS', 'WILL', 'PROB', 'ADOP', 'ORDN', 'DEAT', 'BURI', 'CREM'],
  Attributes: ['OCCU', 'RESI', 'EDUC', 'RELI', 'TITL', 'DSCR', 'NCHI', 'SSN', 'IDNO'],
};
function eventTagOptionsHtml(selected) {
  var known = [].concat(EVENT_TAG_GROUPS['Life events'], EVENT_TAG_GROUPS.Attributes);
  var html = Object.keys(EVENT_TAG_GROUPS).map(function(g) {
    return '<optgroup label="' + g + '">' + EVENT_TAG_GROUPS[g].map(function(tag) {
      return '<option value="' + tag + '"' + (selected === tag ? ' selected' : '') + '>' + tagLabel(tag) + '</option>';
    }).join('') + '</optgroup>';
  }).join('');
  if (selected && known.indexOf(selected) === -1) html += '<option value="' + escapeHtml(selected) + '" selected>' + escapeHtml(selected) + ' (custom)</option>';
  html += '<option value="__other__">Other (type a GEDCOM tag)…</option>';
  return html;
}

function eventFormHtml(event) {
  event = event || {};
  var prefill = parseFuzzyForEdit(event.date_original, event.date_sort);
  return '<form class="event-form" data-event-id="' + (event.id || '') + '">' +
    '<div class="row g-3">' +
      '<div class="col-md-4"><label class="form-label">Event or attribute</label><select class="form-select" name="event_tag">' + eventTagOptionsHtml(event.event_tag) + '</select>' +
        '<input type="text" class="form-control mt-1 d-none" name="event_tag_other" placeholder="GEDCOM tag, e.g. PROB" maxlength="10"></div>' +
      '<div class="col-md-4"><label class="form-label">Value (for attributes)</label><input type="text" class="form-control" name="event_value" value="' + escapeHtml(event.event_value || '') + '" placeholder="e.g. an occupation"></div>' +
      '<div class="col-md-4"><label class="form-label">Place</label><input type="text" class="form-control" name="place_text" list="placesDatalist" value="' + escapeHtml(event.place || '') + '" autocomplete="off"></div>' +
    '</div>' +
    fuzzyDateFieldsHtml(prefill) +
    '<div class="row g-3 mt-0">' +
      '<div class="col-md-6"><label class="form-label">Age at event</label><input type="text" class="form-control" name="age" value="' + escapeHtml(event.age || '') + '" placeholder="e.g. 72y"></div>' +
      '<div class="col-md-6"><label class="form-label">Cause (death events)</label><input type="text" class="form-control" name="cause" value="' + escapeHtml(event.cause || '') + '"></div>' +
    '</div>' +
    '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Save</button>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>' +
  '</form>';
}

function wireDetailsActions(panel, ind, events) {
  panel.addEventListener('click', function(e) {
    var cancelBtn = e.target.closest('[data-cancel-form]');
    if (cancelBtn) { var slot = cancelBtn.closest('.inline-form-slot'); if (slot) hideForm(slot); return; }

    if (e.target.closest('#btnAddName')) { toggleForm(panel.querySelector('#addNameForm'), nameFormHtml(null)); return; }
    var editNameBtn = e.target.closest('[data-edit-name]');
    if (editNameBtn) {
      var name = ind.names.filter(function(n) { return n.id === parseInt(editNameBtn.dataset.editName, 10); })[0];
      toggleForm(panel.querySelector('#addNameForm'), nameFormHtml(name));
      return;
    }
    var delNameBtn = e.target.closest('[data-delete-name]');
    if (delNameBtn) {
      if (!window.confirm('Delete this name? A Curator can restore it later.')) return;
      apiFetch('/api/names/' + delNameBtn.dataset.deleteName, { method: 'DELETE' })
        .then(function() { resetDetailsCaches(); renderDetails(panel); })
        .catch(function(err) { window.alert(err.message || 'Could not delete that name.'); });
      return;
    }

    if (e.target.closest('#btnAddEvent')) { toggleForm(panel.querySelector('#addEventForm'), eventFormHtml(null)); return; }
    var editEventBtn = e.target.closest('[data-edit-event]');
    if (editEventBtn) {
      var ev = events.filter(function(x) { return x.id === parseInt(editEventBtn.dataset.editEvent, 10); })[0];
      toggleForm(panel.querySelector('#addEventForm'), eventFormHtml(ev));
      return;
    }
    var delEventBtn = e.target.closest('[data-delete-event]');
    if (delEventBtn) {
      if (!window.confirm('Delete this event? A Curator can restore it later.')) return;
      apiFetch('/api/events/' + delEventBtn.dataset.deleteEvent, { method: 'DELETE' })
        .then(function() { resetDetailsCaches(); renderDetails(panel); })
        .catch(function(err) { window.alert(err.message || 'Could not delete that event.'); });
      return;
    }
  });

  panel.addEventListener('change', function(e) {
    if (e.target.name === 'event_tag') {
      var other = e.target.parentElement.querySelector('[name="event_tag_other"]');
      if (other) other.classList.toggle('d-none', e.target.value !== '__other__');
    }
  });

  panel.addEventListener('submit', function(e) {
    var form = e.target;
    if (form.matches('.name-form')) {
      e.preventDefault();
      var nameId = form.dataset.nameId;
      var payload = formToObject(form);
      var call = nameId ? apiFetch('/api/names/' + nameId, { method: 'PUT', body: payload })
                         : apiFetch('/api/individuals/' + personId + '/names', { method: 'POST', body: payload });
      call.then(function() { resetDetailsCaches(); renderDetails(panel); }).catch(function(err) { alertFormError(form, err); });
      return;
    }
    if (form.matches('.event-form')) {
      e.preventDefault();
      var eventId = form.dataset.eventId;
      var tag = form.elements.event_tag.value;
      if (tag === '__other__') tag = (form.elements.event_tag_other.value || '').trim().toUpperCase();
      if (!tag) { alertFormError(form, { message: 'Choose an event type.' }); return; }
      var date = readFuzzyDateFromForm(form);
      var placeText = (form.elements.place_text.value || '').trim();
      resolvePlaceId(placeText).then(function(placeId) {
        var payload = {
          event_tag: tag,
          event_value: form.elements.event_value.value.trim() || null,
          age: form.elements.age.value.trim() || null,
          cause: form.elements.cause.value.trim() || null,
          place_id: placeId,
          date_original: date ? date.date_original : null,
          date_sort: date ? date.date_sort : null,
        };
        if (!eventId) { payload.subject_type = 'individual'; payload.subject_id = personId; }
        return eventId ? apiFetch('/api/events/' + eventId, { method: 'PUT', body: payload })
                       : apiFetch('/api/events', { method: 'POST', body: payload });
      }).then(function() { resetDetailsCaches(); renderDetails(panel); }).catch(function(err) { alertFormError(form, err); });
      return;
    }
    if (form.id === 'personFactsForm') {
      e.preventDefault();
      var payload2 = { sex: form.elements.sex.value, living: form.elements.living.checked, restriction: form.elements.restriction.value || null };
      apiFetch('/api/individuals/' + personId, { method: 'PUT', body: payload2 })
        .then(function() { resetDetailsCaches(); renderDetails(panel); renderHeader(); })
        .catch(function(err) { alertFormError(form, err); });
    }
  });
}

function loadDetailsTab() {
  var panel = document.getElementById('tab-details');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';
  renderDetails(panel);
}
function renderDetails(panel) {
  Promise.all([getIndividual(), getOwnEvents()]).then(function(results) {
    var ind = results[0], events = results[1];
    panel.innerHTML =
      '<div class="panel mb-3"><h2 class="section-title">Names</h2>' +
        '<div id="namesList">' + namesListHtml(ind.names) + '</div>' +
        (canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm mt-2" id="btnAddName">+ Add a name</button>' +
          '<div id="addNameForm" class="d-none inline-form-slot mt-2"></div>' : '') +
      '</div>' +
      '<div class="panel mb-3"><h2 class="section-title">Person facts</h2>' + personFactsFormHtml(ind) + '</div>' +
      '<div class="panel"><h2 class="section-title">Events &amp; attributes</h2>' +
        '<div id="eventsTable">' + eventsTableHtml(events) + '</div>' +
        (canContribute ? '<button type="button" class="btn btn-outline-secondary btn-sm mt-2" id="btnAddEvent">+ Add an event</button>' +
          '<div id="addEventForm" class="d-none inline-form-slot mt-3"></div>' : '') +
      '</div>';
    wireDetailsActions(panel, ind, events);
  }).catch(function() {
    panel.innerHTML = '<p class="text-muted">Details aren’t available right now.</p>';
  });
}

/* =============================================================================
 * 10) SOURCES TAB — citations backing this person / their names / their
 * events, grouped by what they support. QUAY (0–3) rendered as a plain-
 * language reliability label, per the standard GEDCOM meaning of the scale.
 * ===========================================================================*/

var QUALITY_LABELS = { 0: 'Unreliable / estimated', 1: 'Questionable', 2: 'Secondary evidence', 3: 'Direct / primary evidence' };

function citationGroupHtml(title, list) {
  if (!list.length) return '';
  return '<h2 class="section-title mt-4">' + escapeHtml(title) + '</h2>' +
    '<div class="table-responsive"><table class="table table-hover align-middle"><thead><tr>' +
      '<th>Source</th><th>Page</th><th>Reliability</th><th>For</th>' + (canContribute ? '<th></th>' : '') + '</tr></thead><tbody>' +
      list.map(function(c) {
        return '<tr data-citation-id="' + c.id + '">' +
          '<td>' + escapeHtml(c.source_title || 'Untitled source') + '</td>' +
          '<td>' + escapeHtml(c.page || '—') + '</td>' +
          '<td>' + escapeHtml(c.quality != null ? QUALITY_LABELS[c.quality] : 'Not rated') + '</td>' +
          '<td>' + escapeHtml(c.subject_label || '—') + '</td>' +
          (canContribute ? '<td class="text-nowrap">' +
            '<button type="button" class="btn btn-outline-secondary btn-sm" data-edit-citation="' + c.id + '">Edit</button> ' +
            '<button type="button" class="btn btn-outline-secondary btn-sm" data-delete-citation="' + c.id + '">Delete</button></td>' : '') +
        '</tr>';
      }).join('') + '</tbody></table></div>';
}

function attachCitationFormHtml(ind, events) {
  var subjectOptions = '<option value="individual:' + personId + '">' + escapeHtml(ind.primary_name || 'This person') + '</option>' +
    ind.names.map(function(n) { return '<option value="name:' + n.id + '">Name: ' + escapeHtml(n.display) + '</option>'; }).join('') +
    events.map(function(e) { return '<option value="event:' + e.id + '">Event: ' + escapeHtml(tagLabel(e.event_tag)) + ' (' + escapeHtml(e.date_original || 'undated') + ')</option>'; }).join('');

  return '<form id="attachCitationFormEl">' +
    '<div class="row g-3">' +
      '<div class="col-md-6"><label class="form-label">This citation is about</label><select class="form-select" name="subject_key">' + subjectOptions + '</select></div>' +
      '<div class="col-md-6"><label class="form-label">Page / location</label><input type="text" class="form-control" name="page"></div>' +
    '</div>' +
    '<div class="row g-3 mt-0">' +
      '<div class="col-md-6"><label class="form-label">Reliability</label><select class="form-select" name="quality"><option value="">Not rated</option>' +
        [0, 1, 2, 3].map(function(q) { return '<option value="' + q + '">' + QUALITY_LABELS[q] + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="col-md-6"><label class="form-label">Notes</label><input type="text" class="form-control" name="notes"></div>' +
    '</div>' +
    '<div class="mt-3"><label class="form-label">Source</label><div id="sourcePicker"></div>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm mt-2" id="btnNewSource">+ Create a new source instead</button>' +
      '<div id="newSourceFields" class="d-none row g-3 mt-0">' +
        '<div class="col-md-4"><label class="form-label">Title</label><input type="text" class="form-control" name="new_source_title"></div>' +
        '<div class="col-md-4"><label class="form-label">Author</label><input type="text" class="form-control" name="new_source_author"></div>' +
        '<div class="col-md-4"><label class="form-label">Publication</label><input type="text" class="form-control" name="new_source_publication"></div>' +
      '</div>' +
      '<input type="hidden" name="source_id" value="">' +
    '</div>' +
    '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Attach citation</button>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>' +
  '</form>';
}
function wireSourcePicker(container, sources) {
  var picker = container.querySelector('#sourcePicker');
  picker.innerHTML =
    '<input type="text" class="form-control" id="sourceSearchInput" placeholder="Search existing sources…" autocomplete="off">' +
    '<div class="list-group" id="sourceSearchResults"></div>' +
    '<p class="text-muted small mb-0 d-none" id="sourceSelectedLabel"></p>';
  var input = picker.querySelector('#sourceSearchInput');
  var results = picker.querySelector('#sourceSearchResults');
  var selectedLabel = picker.querySelector('#sourceSelectedLabel');
  input.addEventListener('input', debounce(function() {
    var q = input.value.trim().toLowerCase();
    var matches = q ? sources.filter(function(s) { return (s.title || '').toLowerCase().indexOf(q) !== -1; }).slice(0, 8) : [];
    results.innerHTML = matches.map(function(s) {
      return '<button type="button" class="list-group-item list-group-item-action" data-source-id="' + s.id + '">' + escapeHtml(s.title) + '</button>';
    }).join('');
  }, 200));
  results.addEventListener('click', function(e) {
    var row = e.target.closest('[data-source-id]');
    if (!row) return;
    container.querySelector('input[name="source_id"]').value = row.dataset.sourceId;
    selectedLabel.textContent = 'Selected: ' + row.textContent;
    selectedLabel.classList.remove('d-none');
    results.innerHTML = ''; input.value = '';
    container.querySelector('#newSourceFields').classList.add('d-none');
  });
}

function editCitationFormHtml(c) {
  return '<form class="edit-citation-form" data-citation-id="' + c.id + '">' +
    '<div class="row g-3">' +
      '<div class="col-md-4"><label class="form-label">Page / location</label><input type="text" class="form-control" name="page" value="' + escapeHtml(c.page || '') + '"></div>' +
      '<div class="col-md-4"><label class="form-label">Reliability</label><select class="form-select" name="quality"><option value="">Not rated</option>' +
        [0, 1, 2, 3].map(function(q) { return '<option value="' + q + '"' + (c.quality === q ? ' selected' : '') + '>' + QUALITY_LABELS[q] + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="col-md-4"><label class="form-label">Notes</label><input type="text" class="form-control" name="notes" value="' + escapeHtml(c.notes || '') + '"></div>' +
    '</div>' +
    '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Save</button>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>' +
  '</form>';
}

function wireSourcesActions(panel, sources, ind, events, citationsById) {
  panel.addEventListener('click', function(e) {
    var cancelBtn = e.target.closest('[data-cancel-form]');
    if (cancelBtn) {
      var slot = cancelBtn.closest('.inline-form-slot');
      if (slot) { hideForm(slot); return; }
      var extraRow = cancelBtn.closest('tr'); // the inline citation-edit row
      if (extraRow) { extraRow.remove(); return; }
      return;
    }

    if (e.target.closest('#btnAttachCitation')) {
      var slot2 = panel.querySelector('#attachCitationForm');
      toggleForm(slot2, attachCitationFormHtml(ind, events));
      wireSourcePicker(slot2, sources);
      return;
    }
    if (e.target.closest('#btnNewSource')) {
      panel.querySelector('#newSourceFields').classList.remove('d-none');
      panel.querySelector('input[name="source_id"]').value = '';
      return;
    }
    var editBtn = e.target.closest('[data-edit-citation]');
    if (editBtn) {
      var c = citationsById[parseInt(editBtn.dataset.editCitation, 10)];
      var row = editBtn.closest('tr');
      if (row.nextSibling && row.nextSibling.classList && row.nextSibling.classList.contains('citation-edit-row')) return; // already open
      var editRow = document.createElement('tr');
      editRow.className = 'citation-edit-row';
      editRow.innerHTML = '<td colspan="5">' + editCitationFormHtml(c) + '</td>';
      row.parentNode.insertBefore(editRow, row.nextSibling);
      return;
    }
    var delBtn = e.target.closest('[data-delete-citation]');
    if (delBtn) {
      if (!window.confirm('Delete this citation? A Curator can restore it later.')) return;
      apiFetch('/api/citations/' + delBtn.dataset.deleteCitation, { method: 'DELETE' })
        .then(function() { resetSourcesCaches(); renderSources(panel); })
        .catch(function(err) { window.alert(err.message || 'Could not delete that citation.'); });
      return;
    }
  });

  panel.addEventListener('submit', function(e) {
    var form = e.target;
    if (form.id === 'attachCitationFormEl') {
      e.preventDefault();
      var subjectKey = form.elements.subject_key.value.split(':');
      var subjectType = subjectKey[0], subjectId = parseInt(subjectKey[1], 10);
      var sourceId = form.elements.source_id.value;
      var ensureSource = sourceId ? Promise.resolve(parseInt(sourceId, 10)) :
        apiFetch('/api/sources', { method: 'POST', body: {
          title: (form.elements.new_source_title.value || '').trim(),
          author: (form.elements.new_source_author.value || '').trim() || null,
          publication: (form.elements.new_source_publication.value || '').trim() || null,
        } }).then(function(s) { return s.id; });
      ensureSource.then(function(sid) {
        return apiFetch('/api/citations', { method: 'POST', body: {
          source_id: sid, subject_type: subjectType, subject_id: subjectId,
          page: (form.elements.page.value || '').trim() || null,
          quality: form.elements.quality.value === '' ? null : parseInt(form.elements.quality.value, 10),
          notes: (form.elements.notes.value || '').trim() || null,
        } });
      }).then(function() { resetSourcesCaches(); renderSources(panel); }).catch(function(err) { alertFormError(form, err); });
      return;
    }
    if (form.matches('.edit-citation-form')) {
      e.preventDefault();
      apiFetch('/api/citations/' + form.dataset.citationId, { method: 'PUT', body: {
        page: (form.elements.page.value || '').trim() || null,
        quality: form.elements.quality.value === '' ? null : parseInt(form.elements.quality.value, 10),
        notes: (form.elements.notes.value || '').trim() || null,
      } }).then(function() { resetSourcesCaches(); renderSources(panel); }).catch(function(err) { alertFormError(form, err); });
    }
  });
}

function loadSourcesTab() {
  var panel = document.getElementById('tab-sources');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';
  renderSources(panel);
}
function renderSources(panel) {
  Promise.all([getIndividual(), getOwnEvents(), getAllCitations(), getAllSources()]).then(function(results) {
    var ind = results[0], events = results[1], citations = results[2], sources = results[3];
    var nameIds = ind.names.map(function(n) { return n.id; });
    var eventIds = events.map(function(e) { return e.id; });
    var mine = citations.filter(function(c) {
      return (c.subject_type === 'individual' && c.subject_id === personId) ||
             (c.subject_type === 'name' && nameIds.indexOf(c.subject_id) !== -1) ||
             (c.subject_type === 'event' && eventIds.indexOf(c.subject_id) !== -1);
    });
    var citationsById = {};
    mine.forEach(function(c) { citationsById[c.id] = c; });
    var groups = { individual: [], name: [], event: [] };
    mine.forEach(function(c) { groups[c.subject_type].push(c); });

    var html = canContribute ?
      '<button type="button" class="btn btn-outline-secondary btn-sm" id="btnAttachCitation">+ Attach a citation</button>' +
      '<div id="attachCitationForm" class="d-none inline-form-slot mt-2"></div>' : '';
    html += citationGroupHtml('About this person', groups.individual);
    html += citationGroupHtml('On a name', groups.name);
    html += citationGroupHtml('On an event', groups.event);
    if (!mine.length) html += '<p class="text-muted mt-3">No sources cited for this person yet.</p>';

    panel.innerHTML = '<div class="panel">' + html + '</div>';
    wireSourcesActions(panel, sources, ind, events, citationsById);
  }).catch(function() {
    panel.innerHTML = '<p class="text-muted">Sources aren’t available right now.</p>';
  });
}

/* =============================================================================
 * 11) BOOTSTRAP
 * ===========================================================================*/

document.addEventListener('DOMContentLoaded', function() {
  var page = document.getElementById('personPage');
  if (!page) return;

  personId = parseInt(page.dataset.individualId, 10);
  canContribute = page.dataset.canContribute === 'true';
  personTabsNav = document.getElementById('personTabs');

  refreshPlacesDatalist();
  renderHeader();
  activateTab(currentTab());
  window.addEventListener('hashchange', function() { activateTab(currentTab()); });
});
