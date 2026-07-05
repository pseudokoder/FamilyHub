/* fh-common.js — small helpers shared by the FE-4 pages (Memories, Stories,
 * Search). Several of these patterns already exist inside person.js/tree.js
 * (each page-specific script is self-contained, loaded standalone per
 * template — no bundler, CSP-safe plain <script> tags), but three NEW pages
 * in one work package independently re-typing the same escapeHtml/debounce/
 * markdown-renderer/photo-cameo helpers is exactly the duplication the FE-4
 * brief asks to avoid ("extract shared helpers rather than duplicating").
 * This file is that extraction point for the NEW code — person.js/tree.js/
 * people.js are already shipped, browser-verified, and untouched by this
 * change (rewriting them to also consume this file would be a separate,
 * riskier refactor of working code, out of this work package's scope).
 *
 * Loaded before memories.js/stories.js/search.js, same plain-global pattern
 * every other script in this app uses (chronicle.js's photo()/applyTones()
 * globals, api.js's apiFetch()/FamilyHubFmt).
 *
 * -> WGU: JavaScript Programming (D280), Security (D315 — escapeHtml first).
 */
'use strict';

function escapeHtml(value) {
  var div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

/* debounce(fn, ms) — collapses rapid keystrokes into one call (every
 * search-as-you-type field in this app uses this exact pattern). */
function debounce(fn, ms) {
  var t = null;
  return function() {
    var args = arguments, ctx = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(ctx, args); }, ms);
  };
}

/* yearOf("1850-00-00") -> 1850. Mirrors individual_service._year in Python. */
function yearOf(dateSort) {
  if (!dateSort) return null;
  var head = String(dateSort).slice(0, 4);
  return /^\d{4}$/.test(head) && head !== '0000' ? parseInt(head, 10) : null;
}

function nameOf(person) { return (person && person.primary_name) || 'Unnamed person'; }
function personLink(id, name) {
  return '<a href="/people/' + id + '">' + escapeHtml(name || 'Unnamed person') + '</a>';
}
function familyLink(id, label) {
  return '<a href="/tree/family/' + id + '">' + escapeHtml(label || 'Family') + '</a>';
}

/* A small friendly label map for the handful of event tags a photo/note is
 * commonly linked to (Memories/Stories' "linked to" chips) — a shorter
 * subset of person.js's own TAG_LABELS, which that file keeps to itself
 * since it needs the FULL GEDCOM tag vocabulary for its event-tag picker. */
var TAG_LABELS = {
  BIRT: 'Birth', DEAT: 'Death', MARR: 'Marriage', DIV: 'Divorce', BURI: 'Burial',
  BAPM: 'Baptism', GRAD: 'Graduation', RETI: 'Retirement', OCCU: 'Occupation',
  RESI: 'Residence', ENGA: 'Engagement',
};
function tagLabel(tag) { return TAG_LABELS[tag] || tag; }

/* resolveLinkTarget — where a polymorphic Link (individual|family|event)
 * should navigate to. An event has no page of its own in this app, so it
 * resolves to the EVENT'S OWN subject (a person or family) — shared by
 * Memories' Photo Detail panel and Stories' "About" section, both of which
 * show a note/media's `links` array as navigable chips. */
function resolveLinkTarget(link) {
  if (link.subject_type === 'individual') {
    return Promise.resolve({ href: '/people/' + link.subject_id, label: link.subject_label || 'Person', cls: '' });
  }
  if (link.subject_type === 'family') {
    return Promise.resolve({ href: '/tree/family/' + link.subject_id, label: link.subject_label || 'Family', cls: 'stamp--blue' });
  }
  return apiFetch('/api/events/' + link.subject_id).then(function(ev) {
    var href = ev.subject_type === 'family' ? '/tree/family/' + ev.subject_id : '/people/' + ev.subject_id;
    var label = tagLabel(ev.event_tag) + (ev.subject_label ? ': ' + ev.subject_label : '');
    return { href: href, label: label, cls: '' };
  }).catch(function() { return { href: '#', label: 'Event #' + link.subject_id, cls: '' }; });
}

/* A small, fixed palette (lifted from chronicle.js's SAMPLE_DATA, same copy
 * person.js/tree.js each already carry) so anything without a real photo
 * still gets one of the site's sepia tones, picked deterministically from
 * its id — no "tone" field exists on Individual/Media; purely decorative. */
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
 * cameo (chronicle.js's `photo()` global) — same mechanism person.js's
 * Relationships/Timeline cards use, reused here for Memories/Search rows. */
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
 * the contract). Escaping happens FIRST, on the raw text, so no Markdown
 * syntax can smuggle real HTML through (D315) — the exact subset person.js's
 * Story tab already renders (paragraphs, headings, bold/italic/code, lists);
 * duplicated as data here (not a shared call into person.js) since Stories
 * needs it without loading the whole Person Page script. */
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
      var level = heading[1].length + 2;
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

/* Generic form -> plain-object reader (same rule as person.js's copy):
 * checkbox -> boolean, everything else -> string. */
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
 * drawer uses; cancel buttons share the `.inline-form-slot`/`[data-cancel-
 * form]` convention (see each page's wireXActions). */
function toggleForm(slot, html) {
  slot.innerHTML = html;
  slot.classList.remove('d-none');
}
function hideForm(slot) {
  slot.classList.add('d-none');
  slot.innerHTML = '';
}

/* =============================================================================
 * FUZZY DATES — Precision (Exact/About/Before/After) + Year + optional Month
 * + optional Day, converted to the schema's (raw, sortable) pair. Same GEDCOM-
 * ish grammar person.js's event form and people.js's Register form already
 * use, reused here for Media.capture_date/capture_date_sort — a real column
 * pair the Memories upload/edit form should populate properly so the
 * Chronological view can actually sort by it (Master Plan §5A depth bar).
 * ===========================================================================*/
var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
  'August', 'September', 'October', 'November', 'December'];

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
/* 2-up on narrow containers, 4-up only once there's really room — Bootstrap's
 * col-md-3 alone would compute 25% against whatever CONTAINER holds this
 * (not the viewport), so nesting it inside a narrow sidebar (the Photo
 * Detail panel is 340px) squeezed all four fields unreadably even on a wide
 * desktop viewport — a real bug found in the browser, not caught by pytest. */
function fuzzyDateFieldsHtml(d, namePrefix) {
  namePrefix = namePrefix || 'date';
  return '<div class="row g-3">' +
    '<div class="col-6 col-md-3"><label class="form-label">Precision</label><select class="form-select" name="' + namePrefix + '_qualifier">' +
      ['exact', 'about', 'before', 'after'].map(function(q) { return '<option value="' + q + '"' + (d.qualifier === q ? ' selected' : '') + '>' + q.charAt(0).toUpperCase() + q.slice(1) + '</option>'; }).join('') +
    '</select></div>' +
    '<div class="col-6 col-md-3"><label class="form-label">Year</label><input type="number" class="form-control" name="' + namePrefix + '_year" min="1" max="2100" value="' + escapeHtml(d.year) + '"></div>' +
    '<div class="col-6 col-md-3"><label class="form-label">Month</label><select class="form-select" name="' + namePrefix + '_month"><option value="">— optional —</option>' +
      MONTHS.map(function(m, i) { return '<option value="' + (i + 1) + '"' + (String(d.month) === String(i + 1) ? ' selected' : '') + '>' + m + '</option>'; }).join('') +
    '</select></div>' +
    '<div class="col-6 col-md-3"><label class="form-label">Day</label><input type="number" class="form-control" name="' + namePrefix + '_day" min="1" max="31" value="' + escapeHtml(d.day) + '"></div>' +
  '</div>';
}
function readFuzzyDateFromForm(form, namePrefix) {
  namePrefix = namePrefix || 'date';
  var year = form.elements[namePrefix + '_year'].value;
  if (!year) return null;
  var month = form.elements[namePrefix + '_month'].value, day = form.elements[namePrefix + '_day'].value,
      qualifier = form.elements[namePrefix + '_qualifier'].value;
  var y = String(parseInt(year, 10)).padStart(4, '0');
  var m = month ? String(month).padStart(2, '0') : '00';
  var d = day ? String(day).padStart(2, '0') : '00';
  var datePart = day && month ? (parseInt(day, 10) + ' ' + MONTHS[month - 1] + ' ' + year) : month ? (MONTHS[month - 1] + ' ' + year) : String(parseInt(year, 10));
  var prefixText = { about: 'ABT ', before: 'BEF ', after: 'AFT ' }[qualifier] || '';
  return { date_original: prefixText + datePart, date_sort: y + '-' + m + '-' + d };
}

/* =============================================================================
 * SUBJECT PICKER — search-as-you-type over people AND/OR families, used by
 * Memories' link picker, Stories' "who/what it's about," and the Search
 * section's quick-search widget. Generalizes person.js's personPicker
 * (which only ever searched people, for its own Relationships tab) to
 * optionally include families too, since notes/media can be linked to
 * either (docs/openapi.yaml's Link schema: individual|family|event).
 *
 * Families have no name field of their own (Master Plan §3: a FAM row is
 * just two partner ids) — matching happens against the SAME partner1/
 * partner2 display strings GET /api/families already computes server-side,
 * fetched once and cached for the session (family-scale dataset, the same
 * "brute force is fine" precedent FRONTEND_DESIGN.md already set for sort).
 * ===========================================================================*/
var _familiesCache = null;
function getFamiliesCached() {
  if (!_familiesCache) _familiesCache = apiFetch('/api/families').then(function(d) { return d.families || []; });
  return _familiesCache;
}
function familyLabel(f) {
  return [f.partner1, f.partner2].filter(Boolean).join(' & ') || 'Unnamed family';
}

/* opts: { types: ['individual','family'] (default both), excludeIndividualId,
 *   inputEl/resultsEl (bind to existing elements instead of building markup
 *   inside `container` — the header quick-search widget has its own <label>
 *   around a fixed #headerSearchInput/#headerSearchResults pair) }.
 *
 * Keyboard nav (ArrowUp/ArrowDown/Enter) is built in once here rather than
 * once per caller — every picker in the app (Relationships' spouse/parent/
 * child pickers, Stories' link picker, quick search) gets it for free. */
function subjectPicker(container, onPick, opts) {
  opts = opts || {};
  var types = opts.types || ['individual', 'family'];
  var wantPeople = types.indexOf('individual') !== -1;
  var wantFamilies = types.indexOf('family') !== -1;

  var input, results;
  if (opts.inputEl && opts.resultsEl) {
    input = opts.inputEl;
    results = opts.resultsEl;
  } else {
    container.innerHTML =
      '<input type="text" class="form-control subject-picker__input" placeholder="Search by name…" autocomplete="off">' +
      '<div class="list-group subject-picker__results"></div>';
    input = container.querySelector('.subject-picker__input');
    results = container.querySelector('.subject-picker__results');
  }

  var activeIndex = -1;
  function rowEls() { return Array.prototype.slice.call(results.querySelectorAll('[data-id]')); }
  function highlight(idx) {
    var rows = rowEls();
    rows.forEach(function(r, i) { r.classList.toggle('is-active-option', i === idx); });
    if (rows[idx]) rows[idx].scrollIntoView({ block: 'nearest' });
    activeIndex = idx;
  }
  function pick(row) { onPick(row.dataset.type, parseInt(row.dataset.id, 10), row.dataset.label); }

  function renderRows(people, families) {
    var rows = people.map(function(p) {
      return '<button type="button" class="list-group-item list-group-item-action search-result-row" ' +
        'data-type="individual" data-id="' + p.id + '" data-label="' + escapeHtml(nameOf(p)) + '">' +
        escapeHtml(nameOf(p)) +
        '<span class="text-muted small d-block">' + escapeHtml(FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living) || 'Person') + '</span></button>';
    });
    var famRows = families.map(function(f) {
      var label = familyLabel(f);
      return '<button type="button" class="list-group-item list-group-item-action search-result-row" ' +
        'data-type="family" data-id="' + f.id + '" data-label="' + escapeHtml(label) + '">' +
        escapeHtml(label) + '<span class="text-muted small d-block">Family</span></button>';
    });
    results.innerHTML = rows.concat(famRows).join('') ||
      '<p class="text-muted small mb-0 p-2">No matches.</p>';
    activeIndex = -1;
  }

  input.addEventListener('input', debounce(function() {
    var q = input.value.trim();
    if (!q) { results.innerHTML = ''; activeIndex = -1; return; }
    var peoplePromise = wantPeople ?
      apiFetch('/api/search?q=' + encodeURIComponent(q)).then(function(d) {
        return (d.people || []).filter(function(p) { return p.id !== opts.excludeIndividualId; });
      }) : Promise.resolve([]);
    var familiesPromise = wantFamilies ?
      getFamiliesCached().then(function(list) {
        var needle = q.toLowerCase();
        return list.filter(function(f) { return familyLabel(f).toLowerCase().indexOf(needle) !== -1; });
      }) : Promise.resolve([]);
    Promise.all([peoplePromise, familiesPromise]).then(function(r) { renderRows(r[0], r[1]); })
      .catch(function() { results.innerHTML = '<p class="text-muted small mb-0 p-2">Search isn’t available right now.</p>'; });
  }, 250));

  input.addEventListener('keydown', function(e) {
    var rows = rowEls();
    if (!rows.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); highlight(Math.min(activeIndex + 1, rows.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(Math.max(activeIndex - 1, 0)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      var target = activeIndex >= 0 ? rows[activeIndex] : (rows.length === 1 ? rows[0] : null);
      if (target) pick(target);
    }
  });

  results.addEventListener('click', function(e) {
    var row = e.target.closest('[data-id]');
    if (!row) return;
    pick(row);
  });
}
function markPicked(container, label) {
  container.innerHTML = '<p class="mb-0 text-muted">Selected: <strong>' + escapeHtml(label) + '</strong></p>';
}
