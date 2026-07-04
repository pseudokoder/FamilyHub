/* people.js — Find/Register/Browse (Master Plan §4/§5A, WP4 Piece 3).
 * Two independent pieces live in this one file, each guarded by a DOM check
 * (chronicle.js's pattern) so this single <script> works unmodified on both
 * people/index.html and people/new.html:
 *
 *   1) The People list — find bar + filter chips + sort, all driven by
 *      GET /api/search (docs/openapi.yaml); sort/paginate happen client-side
 *      because the contract doesn't offer either yet (family-scale dataset —
 *      Master Plan §12 — so an in-memory sort/slice is plenty fast).
 *   2) The Register-a-person form — POST /api/individuals, then optionally
 *      POST /api/places (find-or-create) + POST /api/events for the birth/
 *      death vitals (Master Plan §5A depth bar).
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+).
 */
'use strict';

function escapeHtml(value) {
  var div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

/* debounce(fn, ms) — collapses rapid keystrokes into one call, so the find
 * bar and surname filter don't fire a network request per keypress. */
function debounce(fn, ms) {
  var t = null;
  return function() {
    var args = arguments, ctx = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(ctx, args); }, ms);
  };
}

document.addEventListener('DOMContentLoaded', function() {

  /* =====================================================================
   * 1) THE PEOPLE LIST (find bar, chips, sort, pagination)
   * ===================================================================*/
  var listEl = document.getElementById('peopleList');
  if (listEl) {
    var findInput   = document.getElementById('peopleFindInput');
    var surnameChip = document.getElementById('surnameChip');
    var surnameInput = document.getElementById('surnameFilterInput');
    var sortSelect  = document.getElementById('peopleSort');
    var pagination  = document.getElementById('peoplePagination');
    var livingChips = document.querySelectorAll('[data-chip-group="living"] .chip');

    var state = { q: '', living: '', surname: '', sort: 'name', page: 1, perPage: 20 };
    var results = [];

    function personRow(p) {
      var life = FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living);
      var meta = FamilyHubFmt.joinDot([life, p.birth_place]);
      return '<a class="list-group-item list-group-item-action person-row" href="/people/' + p.id + '">' +
        '<span class="person-row__name">' + escapeHtml(p.primary_name || 'Unnamed person') + '</span>' +
        (meta ? '<span class="person-row__meta text-muted">' + escapeHtml(meta) + '</span>' : '') +
      '</a>';
    }

    function sortResults(list) {
      var copy = list.slice();
      if (state.sort === 'birth_asc' || state.sort === 'birth_desc') {
        copy.sort(function(a, b) {
          // Unknown birth years sink to the bottom regardless of direction.
          var av = a.birth_year, bv = b.birth_year;
          if (av == null && bv == null) return 0;
          if (av == null) return 1;
          if (bv == null) return -1;
          return state.sort === 'birth_asc' ? av - bv : bv - av;
        });
      } else {
        copy.sort(function(a, b) {
          return (a.primary_name || '').localeCompare(b.primary_name || '');
        });
      }
      return copy;
    }

    function render() {
      var sorted = sortResults(results);
      var pages = Math.max(1, Math.ceil(sorted.length / state.perPage));
      state.page = Math.min(state.page, pages);
      var start = (state.page - 1) * state.perPage;
      var pageItems = sorted.slice(start, start + state.perPage);

      listEl.innerHTML = pageItems.length ? pageItems.map(personRow).join('') :
        '<p class="text-muted">No people match your search.</p>';
      listEl.removeAttribute('data-loading');

      pagination.innerHTML = sorted.length > state.perPage ?
        '<button type="button" class="btn btn-outline-secondary" id="pagePrev"' +
          (state.page <= 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
        '<span class="text-muted">Page ' + state.page + ' of ' + pages + '</span>' +
        '<button type="button" class="btn btn-outline-secondary" id="pageNext"' +
          (state.page >= pages ? ' disabled' : '') + '>Next &rarr;</button>'
        : '';

      var prevBtn = document.getElementById('pagePrev');
      var nextBtn = document.getElementById('pageNext');
      if (prevBtn) prevBtn.addEventListener('click', function() { state.page--; render(); });
      if (nextBtn) nextBtn.addEventListener('click', function() { state.page++; render(); });
    }

    function fetchAndRender() {
      listEl.setAttribute('data-loading', 'true');
      var params = new URLSearchParams();
      if (state.q) params.set('q', state.q);
      if (state.living !== '') params.set('living', state.living);
      if (state.surname) params.set('surname', state.surname);
      apiFetch('/api/search?' + params.toString()).then(function(data) {
        results = data.people || [];
        state.page = 1;
        render();
      }).catch(function() {
        listEl.innerHTML = '<p class="text-muted">People search isn’t available right now.</p>';
      });
    }

    findInput.addEventListener('input', debounce(function() {
      state.q = findInput.value.trim();
      fetchAndRender();
    }, 300));

    livingChips.forEach(function(chip) {
      chip.addEventListener('click', function() {
        livingChips.forEach(function(c) { c.classList.remove('is-active'); });
        chip.classList.add('is-active');
        state.living = chip.dataset.value;
        fetchAndRender();
      });
    });

    surnameChip.addEventListener('click', function() {
      var active = surnameChip.classList.toggle('is-active');
      surnameChip.setAttribute('aria-pressed', String(active));
      surnameInput.classList.toggle('d-none', !active);
      if (active) {
        surnameInput.focus();
      } else {
        surnameInput.value = '';
        state.surname = '';
        fetchAndRender();
      }
    });
    surnameInput.addEventListener('input', debounce(function() {
      state.surname = surnameInput.value.trim();
      fetchAndRender();
    }, 300));

    sortSelect.addEventListener('change', function() {
      state.sort = sortSelect.value;
      state.page = 1;
      render();
    });

    fetchAndRender();
  }

  /* =====================================================================
   * 2) REGISTER A PERSON (names, sex, living, birth/death vitals)
   * ===================================================================*/
  var form = document.getElementById('registerPersonForm');
  if (form) {
    var formError   = document.getElementById('formError');
    var formWarning = document.getElementById('formWarning');
    var livingCheck  = document.getElementById('living');
    var deathFieldset = document.getElementById('deathFieldset');
    var placesDatalist = document.getElementById('placesDatalist');
    var places = []; // [{id, full_name}] — loaded once, reused as a find-or-create cache

    // Deceased vitals only make sense once "living" is unchecked — the WP4
    // brief's "forgiving forms" spirit: don't ask for a death date up front.
    livingCheck.addEventListener('change', function() {
      deathFieldset.classList.toggle('d-none', livingCheck.checked);
    });

    apiFetch('/api/places').then(function(data) {
      places = data.places || [];
      placesDatalist.innerHTML = places.map(function(p) {
        return '<option value="' + escapeHtml(p.full_name) + '">';
      }).join('');
    }).catch(function() { /* the form still works without autocomplete */ });

    function showError(message) {
      formError.textContent = message;
      formError.classList.remove('d-none');
    }
    function showWarning(message) {
      formWarning.textContent = message;
      formWarning.classList.remove('d-none');
    }
    function clearMessages() {
      formError.classList.add('d-none');
      formWarning.classList.add('d-none');
    }

    var MONTHS = ['January','February','March','April','May','June','July',
                  'August','September','October','November','December'];

    /* Reads one birth/death fieldset (prefix = "birth" | "death") into GEDCOM-
     * ish {date_original, date_sort} — the fuzzy-date depth bar requirement
     * (Master Plan §5A). Returns null if no year was given (nothing to save). */
    function readFuzzyDate(prefix) {
      var year = document.getElementById(prefix + 'Year').value;
      if (!year) return null;
      var month = document.getElementById(prefix + 'Month').value;
      var day = document.getElementById(prefix + 'Day').value;
      var qualifier = document.getElementById(prefix + 'Qualifier').value;

      var y = String(parseInt(year, 10)).padStart(4, '0');
      var m = month ? String(month).padStart(2, '0') : '00';
      var d = day ? String(day).padStart(2, '0') : '00';

      var datePart = day && month ? (parseInt(day, 10) + ' ' + MONTHS[month - 1] + ' ' + year)
                   : month ? (MONTHS[month - 1] + ' ' + year)
                   : String(parseInt(year, 10));
      var prefixText = { about: 'ABT ', before: 'BEF ', after: 'AFT ' }[qualifier] || '';

      return { date_original: prefixText + datePart, date_sort: y + '-' + m + '-' + d };
    }

    function readPlaceText(prefix) {
      return (document.getElementById(prefix + 'Place').value || '').trim();
    }

    /* Find-or-create a place by name (docs/openapi.yaml POST /api/places) so
     * two people born in "Nashville, TN" share one Place row (§3: reusable
     * PLAC records), not a duplicate per person. */
    function resolvePlaceId(placeText) {
      if (!placeText) return Promise.resolve(null);
      var existing = places.filter(function(p) {
        return p.full_name.toLowerCase() === placeText.toLowerCase();
      })[0];
      if (existing) return Promise.resolve(existing.id);
      return apiFetch('/api/places', { method: 'POST', body: { full_name: placeText } })
        .then(function(place) { places.push(place); return place.id; });
    }

    function saveVitalEvent(individualId, prefix, tag) {
      var date = readFuzzyDate(prefix);
      var placeText = readPlaceText(prefix);
      if (!date && !placeText) return Promise.resolve(null);
      return resolvePlaceId(placeText).then(function(placeId) {
        return apiFetch('/api/events', {
          method: 'POST',
          body: Object.assign({
            subject_type: 'individual', subject_id: individualId, event_tag: tag,
            place_id: placeId,
          }, date || {}),
        });
      });
    }

    form.addEventListener('submit', function(event) {
      event.preventDefault();
      clearMessages();

      var given = document.getElementById('given').value.trim();
      var surname = document.getElementById('surname').value.trim();
      if (!given && !surname) {
        showError('Enter at least a given name or a surname.');
        return;
      }

      var submitBtn = document.getElementById('registerSubmit');
      submitBtn.disabled = true;

      var isLiving = livingCheck.checked;
      var payload = {
        sex: document.getElementById('sex').value,
        living: isLiving,
        name: {
          name_prefix: document.getElementById('namePrefix').value.trim() || null,
          given: given || null,
          nickname: document.getElementById('nickname').value.trim() || null,
          surname_prefix: document.getElementById('surnamePrefix').value.trim() || null,
          surname: surname || null,
          name_suffix: document.getElementById('nameSuffix').value.trim() || null,
          name_type: document.getElementById('nameType').value,
          is_primary: true,
        },
      };

      apiFetch('/api/individuals', { method: 'POST', body: payload }).then(function(individual) {
        var vitals = [saveVitalEvent(individual.id, 'birth', 'BIRT')];
        if (!isLiving) vitals.push(saveVitalEvent(individual.id, 'death', 'DEAT'));

        Promise.all(vitals).then(function() {
          window.location.href = '/people/' + individual.id;
        }).catch(function(err) {
          // The person is already saved — don't strand the user, just say
          // what didn't make it in and where to go finish the job.
          showWarning(escapeHtml(individual.primary_name || 'This person') +
            ' was registered, but a date/place couldn’t be saved: ' +
            escapeHtml(err.message) + '. You can add it from their page later.');
          submitBtn.disabled = false;
        });
      }).catch(function(err) {
        showError(err.message || 'Something went wrong — please try again.');
        submitBtn.disabled = false;
      });
    });
  }

});
