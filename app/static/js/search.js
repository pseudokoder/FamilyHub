/* search.js — Quick search (header widget + /search page) and Advanced
 * search (Master Plan §12, FE-4). Depends on api.js (apiFetch, FamilyHubFmt)
 * and fh-common.js (escapeHtml, debounce, subjectPicker, personLink) — both
 * loaded before this file everywhere it runs (base.html, globally).
 *
 * Every block below DOM-guards on its own elements, same pattern as
 * chronicle.js/person.js, so this one file is safe to load on every
 * authenticated page (the header widget) AND on the /search page itself
 * (Quick + Advanced tabs).
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+ — GET /api/search
 *    is the same contract a v2 Angular SearchComponent would call).
 */
'use strict';

function navigateToSubject(type, id) {
  window.location.href = type === 'family' ? '/tree/family/' + id : '/people/' + id;
}

document.addEventListener('DOMContentLoaded', function() {

  /* =====================================================================
   * 1) HEADER QUICK-SEARCH OVERLAY — available from any authenticated page
   * (Tier-2 design call, docs/FRONTEND_DESIGN.md).
   * ===================================================================*/
  var headerBtn = document.getElementById('headerSearchBtn');
  var headerOverlay = document.getElementById('headerSearchOverlay');
  if (headerBtn && headerOverlay) {
    var headerInput = document.getElementById('headerSearchInput');
    var headerResults = document.getElementById('headerSearchResults');

    function openOverlay() {
      headerOverlay.classList.add('is-on');
      headerBtn.setAttribute('aria-expanded', 'true');
      headerOverlay.setAttribute('aria-hidden', 'false');
      headerInput.focus();
    }
    function closeOverlay() {
      headerOverlay.classList.remove('is-on');
      headerBtn.setAttribute('aria-expanded', 'false');
      headerOverlay.setAttribute('aria-hidden', 'true');
    }
    headerBtn.addEventListener('click', function() {
      if (headerOverlay.classList.contains('is-on')) closeOverlay(); else openOverlay();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && headerOverlay.classList.contains('is-on')) closeOverlay();
    });
    headerOverlay.addEventListener('click', function(e) {
      if (e.target === headerOverlay) closeOverlay();
    });

    subjectPicker(null, function(type, id) { navigateToSubject(type, id); },
      { inputEl: headerInput, resultsEl: headerResults });
  }

  /* =====================================================================
   * 2) THE /search PAGE — Quick + Advanced, hash-switched (#quick default).
   * ===================================================================*/
  var searchPage = document.getElementById('searchPage');
  if (!searchPage) return;

  var TABS = ['quick', 'advanced'];
  var tabsNav = document.getElementById('searchTabs');
  function currentTab() {
    var h = (window.location.hash || '').replace('#', '');
    return TABS.indexOf(h) !== -1 ? h : 'quick';
  }
  function activateTab(tab) {
    TABS.forEach(function(t) {
      var panel = document.getElementById('searchTab-' + t);
      var link = tabsNav.querySelector('[data-tab="' + t + '"]');
      var active = t === tab;
      panel.classList.toggle('d-none', !active);
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
  }
  activateTab(currentTab());
  window.addEventListener('hashchange', function() { activateTab(currentTab()); });

  // Quick tab: the same combined people+family picker as the header widget,
  // just embedded in the page instead of an overlay.
  var quickPickerHost = document.getElementById('quickSearchPicker');
  if (quickPickerHost) {
    subjectPicker(quickPickerHost, function(type, id) { navigateToSubject(type, id); });
  }

  /* =====================================================================
   * 3) ADVANCED SEARCH — multi-field form per Master Plan §12.
   * ===================================================================*/
  var form = document.getElementById('advancedSearchForm');
  if (!form) return;
  var resultsEl = document.getElementById('advancedSearchResults');
  var countEl = document.getElementById('advancedSearchCount');
  var livingChips = form.querySelectorAll('[data-chip-group="living"] .filter-chip');
  var livingValue = '';

  livingChips.forEach(function(chip) {
    chip.addEventListener('click', function() {
      livingChips.forEach(function(c) { c.classList.remove('is-active'); });
      chip.classList.add('is-active');
      livingValue = chip.dataset.value;
    });
  });

  function personRow(p) {
    var life = FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living);
    var meta = FamilyHubFmt.joinDot([life, p.birth_place]);
    return '<a class="list-group-item list-group-item-action person-row" href="/people/' + p.id + '">' +
      '<span class="person-row__name">' + escapeHtml(p.primary_name || 'Unnamed person') + '</span>' +
      (meta ? '<span class="person-row__meta text-muted">' + escapeHtml(meta) + '</span>' : '') +
    '</a>';
  }
  function noteRow(n) {
    return '<a class="list-group-item list-group-item-action story-row" href="/memories/stories/' + n.id + '">' +
      '<span class="story-row__title">' + escapeHtml(n.title || 'Untitled story') + '</span>' +
      '<span class="story-row__snippet">' + escapeHtml(n.snippet) + '</span>' +
      (n.author ? '<span class="story-row__meta">By ' + escapeHtml(n.author) + '</span>' : '') +
    '</a>';
  }

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    var params = new URLSearchParams();
    var given = form.elements.given.value.trim();
    var surname = form.elements.surname.value.trim();
    var q = form.elements.q.value.trim();
    var sex = form.elements.sex.value;
    var place = form.elements.place.value.trim();
    var birthFrom = form.elements.birth_from.value;
    var birthTo = form.elements.birth_to.value;
    var deathFrom = form.elements.death_from.value ? parseInt(form.elements.death_from.value, 10) : null;
    var deathTo = form.elements.death_to.value ? parseInt(form.elements.death_to.value, 10) : null;

    if (given) params.set('given', given);
    if (surname) params.set('surname', surname);
    if (q) params.set('q', q);
    if (sex) params.set('sex', sex);
    if (place) params.set('place', place);
    if (livingValue !== '') params.set('living', livingValue);
    if (birthFrom) params.set('birth_from', birthFrom);
    if (birthTo) params.set('birth_to', birthTo);

    resultsEl.innerHTML = '<p class="text-muted">Searching…</p>';
    countEl.textContent = '';

    apiFetch('/api/search?' + params.toString()).then(function(data) {
      // Death-year range has no server-side parameter (GET /api/search's
      // documented params stop at birth_from/birth_to — docs/openapi.yaml) —
      // PersonListItem.death_year IS already a real field on every row the
      // server DOES return, so filtering it client-side over that (already
      // fully filtered by every other criterion) result set is the same
      // "brute force is fine, family-scale dataset" call people.js's sort
      // already made, not an approximation of something the API can't
      // verify. Logged in docs/FRONTEND_DESIGN.md's FE-4 decision log.
      var people = (data.people || []).filter(function(p) {
        if (deathFrom != null && (p.death_year == null || p.death_year < deathFrom)) return false;
        if (deathTo != null && (p.death_year == null || p.death_year > deathTo)) return false;
        return true;
      });
      var notes = data.notes || [];

      var parts = [];
      if (people.length) parts.push(people.length + ' ' + (people.length === 1 ? 'person' : 'people'));
      if (notes.length) parts.push(notes.length + ' ' + (notes.length === 1 ? 'story/note' : 'stories/notes'));
      countEl.textContent = parts.length ? parts.join(' · ') : 'No matches';

      if (!people.length && !notes.length) {
        resultsEl.innerHTML = '<p class="text-muted">No one matches — try fewer filters.</p>';
        return;
      }
      var html = '';
      if (people.length) html += '<div class="list-group mb-3">' + people.map(personRow).join('') + '</div>';
      if (notes.length) html += '<div class="list-group">' + notes.map(noteRow).join('') + '</div>';
      resultsEl.innerHTML = html;
    }).catch(function() {
      resultsEl.innerHTML = '<p class="text-muted">Search isn’t available right now.</p>';
    });
  });
});
