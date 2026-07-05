/* tree.js — the Tree section (FE-3, Master Plan §4): Pedigree, Family Group,
 * and Relationship Finder. Three independent pieces in one file, each guarded
 * by a DOM check (chronicle.js's/people.js's own pattern) so this single
 * <script> works unmodified on all three tree/*.html templates.
 *
 * SHARED DATA MODEL: the tree is a GRAPH, not a linked list — a person can
 * have more than one recorded parent set (birth + adoptive both active), and
 * `/api/individuals/{id}/pedigree` only ever returns a bounded generation
 * slice so the front-end can lazy-expand from any node (tree_service.py's own
 * docstring). Every getter below either reads that bounded slice or, for
 * data the pedigree endpoint doesn't carry (portraits, a specific family's
 * per-child pedigree_type), does ONE family-scale fetch and memoizes it —
 * the same "brute force is fine" call already made for Relationships/People
 * (see person.js, people.js).
 *
 * CSP-strict: no inline styles/handlers. The Pedigree view in particular
 * needs ZERO position math (no data-x/data-y/el.style writes at all) — it's
 * a pure nested <ul>/<li> tree laid out by chronicle-app.css's flexbox +
 * ::before/::after connectors, unlike chronicle.js's absolutely-positioned
 * hero tree.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315),
 *    Discrete Math II (D286 covers graph BFS — the same shape as
 *    tree_service.py's ancestor walk this file just renders).
 */
'use strict';

/* =============================================================================
 * 0) SHARED HELPERS — small, page-scoped copies of the same helpers person.js
 * and people.js each keep (CLAUDE.md: no premature shared module for three
 * tiny functions three files each use a little differently).
 * ===========================================================================*/

function escapeHtml(value) {
  var div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function debounce(fn, ms) {
  var t = null;
  return function() {
    var args = arguments, ctx = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(ctx, args); }, ms);
  };
}

/* One shared memoized-fetch cache for data every view here might touch more
 * than once per page load (person.js's exact `once` pattern). */
var _cache = {};
function once(key, factory) {
  if (!(key in _cache)) _cache[key] = factory();
  return _cache[key];
}

/* getIndividualsMap/getMediaMap — the two family-scale, fetch-once lookups
 * every view below needs (vitals for an id not already in hand; a portrait
 * for an id). Media has no `subject_id` of its own — it carries a `links[]`
 * array (one photo can be attached to more than one person/family/event), so
 * building "first portrait per individual" means scanning every link. */
function getIndividualsMap() {
  return once('individualsMap', function() {
    return apiFetch('/api/individuals').then(function(d) {
      var map = {};
      (d.individuals || []).forEach(function(p) { map[p.id] = p; });
      return map;
    });
  });
}
function getMediaMap() {
  return once('mediaMap', function() {
    return apiFetch('/api/media').then(function(d) {
      var map = {};
      (d.media || []).forEach(function(m) {
        (m.links || []).forEach(function(link) {
          if (link.subject_type === 'individual' && !(link.subject_id in map)) {
            map[link.subject_id] = m;
          }
        });
      });
      return map;
    }).catch(function() { return {}; });
  });
}

/* A small, fixed palette (same values as person.js's TONE_PALETTE) so a
 * person without a real photo gets the same deterministic sepia-tone cameo
 * on the Tree pages as on their own Person Page — no "tone" field exists on
 * Individual; this is a purely decorative, front-end-only choice. */
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
/* personCameoHtml — a real thumbnail if one is linked, else a toned initials
 * cameo (chronicle.js's `photo()` global, loaded by base.html). Call
 * applyTones() on the parent after any innerHTML insertion containing one. */
function personCameoHtml(id, name, media, cls) {
  var tones = toneFor(id);
  cls = cls || '';
  if (media) {
    return '<div class="photo ' + cls + '" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
      '<img src="' + media.thumb_url + '" alt=""></div>';
  }
  return photo(initialsFromDisplay(name), tones, cls); // chronicle.js global
}

var PEDIGREE_LABELS = { birth: 'Birth', adopted: 'Adopted', foster: 'Foster', step: 'Step' };
function pedigreeBadge(type) {
  return '<span class="badge text-bg-light">' + escapeHtml(PEDIGREE_LABELS[type] || 'Birth') + '</span>';
}
function joinDateplace(e) {
  return FamilyHubFmt.joinDot([e.date_original, e.place]);
}

/* =============================================================================
 * 1) PEDIGREE VIEW (tree/pedigree.html) — a vertical, lazy-expandable
 * ancestor tree. See docs/FRONTEND_DESIGN.md's FE-3 entry for the layout
 * system (a pure-CSS nested-list "org chart," upside down).
 * ===========================================================================*/
(function() {
  var page = document.getElementById('pedigreePage');
  if (!page) return;

  var canContribute = page.dataset.canContribute === 'true';
  var canvas = document.getElementById('pedigreeCanvas');
  var headerEl = document.getElementById('pedigreeHeader');

  var PEDIGREE_DEPTH = 4; // generations per fetch — the lazy-expand seam (Master Plan §4)
  var nodesById = {};
  var parentsOf = {};        // childId -> [{parent_id, family_id, pedigree_type}]
  var fetchedFamilies = {};  // family_id -> true once its children[] have been read for pedigree_type
  var nodeMediaMap = {};
  var rootId = null;

  /* ORIENTATION SEAM (a v2-reserved toggle — do NOT build it, FE-3 brief):
   * nothing below computes a node's screen position. The nested <ul>/<li>
   * markup plus chronicle-app.css's .pedigree-canvas--vertical flex rules do
   * 100% of the layout, so a future --horizontal variant is one CSS class
   * swap with zero changes to mergeGraph/renderAncestor — the graph
   * traversal itself has no notion of "vertical." */

  function currentRootParam() {
    var v = new URLSearchParams(window.location.search).get('root');
    var n = parseInt(v, 10);
    return isNaN(n) ? null : n;
  }

  function mergeGraph(graph) {
    (graph.nodes || []).forEach(function(n) { nodesById[n.id] = n; });
    (graph.edges || []).forEach(function(e) {
      if (e.type !== 'parent-child' || e.parent_id == null) return;
      var list = parentsOf[e.child_id] || (parentsOf[e.child_id] = []);
      var exists = list.some(function(l) { return l.parent_id === e.parent_id && l.family_id === e.family_id; });
      if (!exists) list.push({ parent_id: e.parent_id, family_id: e.family_id, pedigree_type: 'birth' });
    });
  }

  /* The pedigree edge shape doesn't carry pedigree_type (only which family
   * links parent to child) — that lives on the family's children[] row, so
   * this reads each newly-seen family ONCE and patches the real value in. */
  function ensurePedigreeTypes() {
    var familyIds = [];
    Object.keys(parentsOf).forEach(function(cid) {
      parentsOf[cid].forEach(function(l) {
        if (!fetchedFamilies[l.family_id] && familyIds.indexOf(l.family_id) === -1) familyIds.push(l.family_id);
      });
    });
    if (!familyIds.length) return Promise.resolve();
    return Promise.all(familyIds.map(function(fid) {
      return apiFetch('/api/families/' + fid).then(function(fam) {
        fetchedFamilies[fid] = true;
        var byChild = {};
        (fam.children || []).forEach(function(c) { byChild[c.child_id] = c.pedigree_type; });
        Object.keys(parentsOf).forEach(function(cid) {
          parentsOf[cid].forEach(function(l) {
            if (l.family_id === fid && byChild[cid]) l.pedigree_type = byChild[cid];
          });
        });
      }).catch(function() { fetchedFamilies[fid] = true; }); // a family that 404s just keeps the 'birth' default
    }));
  }

  function nodeCardHtml(id, edgeMeta) {
    var node = nodesById[id];
    var name = node ? (node.primary_name || 'Unnamed person') : 'Unnamed person';
    var life = node ? FamilyHubFmt.lifespan(node.birth_year, node.death_year, node.living) : '';
    var badge = edgeMeta && edgeMeta.pedigree_type && edgeMeta.pedigree_type !== 'birth' ?
      '<div class="pedigree-node__badge">' + pedigreeBadge(edgeMeta.pedigree_type) + '</div>' : '';
    var actions = [];
    if (id !== rootId) actions.push('<button type="button" class="btn btn-outline-secondary" data-center="' + id + '">Center</button>');
    if (edgeMeta) actions.push('<a class="btn btn-outline-secondary" href="/tree/family/' + edgeMeta.family_id + '">Family</a>');
    return '<div class="pedigree-node">' +
      '<div class="pedigree-node__photo">' + personCameoHtml(id, name, nodeMediaMap[id], 'pedigree-node__cameo') + '</div>' +
      '<div class="pedigree-node__body">' +
        '<a class="pedigree-node__name" href="/people/' + id + '">' + escapeHtml(name) + '</a>' +
        (life ? '<span class="pedigree-node__life">' + escapeHtml(life) + '</span>' : '') +
      '</div>' +
      badge +
      (actions.length ? '<div class="pedigree-node__actions">' + actions.join('') + '</div>' : '') +
    '</div>';
  }

  /* renderParentsUl — the recursive step. Three honest outcomes when a
   * person has no LOADED parent links: more exist but aren't fetched yet
   * (has_ancestors, from the API) -> a lazy-expand button; none are on
   * record and this member can add some -> an invite into the Person Page's
   * Relationships tab (no CRUD duplicated here, per the FE-3 brief); neither
   * -> nothing rendered at all (§5A: never fake an empty slot). */
  function renderParentsUl(childId, visited) {
    var links = parentsOf[childId];
    if (links && links.length) {
      return '<ul>' + links.map(function(l) { return renderAncestor(l.parent_id, visited, l); }).join('') + '</ul>';
    }
    var node = nodesById[childId];
    if (node && node.has_ancestors) {
      return '<ul><li><div class="pedigree-node pedigree-node--placeholder">' +
        '<button type="button" class="pedigree-expand-btn" data-expand="' + childId + '">Show earlier generations</button>' +
        '</div></li></ul>';
    }
    if (canContribute) {
      return '<ul><li><div class="pedigree-node pedigree-node--placeholder">' +
        '<a class="pedigree-invite-link" href="/people/' + childId + '#relationships">+ Add parent</a>' +
        '</div></li></ul>';
    }
    return '';
  }

  /* visited guards a client-side cycle even though the API's own BFS should
   * never hand back one ("trust the API but never infinite-loop" — FE-3
   * brief) — a defensive stop, not an expected path. */
  function renderAncestor(id, visited, edgeMeta) {
    if (visited.indexOf(id) !== -1) {
      return '<li><div class="pedigree-node pedigree-node--cycle">Already shown above</div></li>';
    }
    return '<li>' + nodeCardHtml(id, edgeMeta) + renderParentsUl(id, visited.concat([id])) + '</li>';
  }

  function renderHeader() {
    var root = nodesById[rootId];
    var name = root ? (root.primary_name || 'Unnamed person') : 'this person';
    headerEl.innerHTML = '<h1 class="mb-0">Ancestors of ' + escapeHtml(name) + '</h1>' +
      '<p class="text-muted mb-0"><a href="/people/' + rootId + '">View ' + escapeHtml(name) + '&rsquo;s Person Page</a></p>';
  }

  function renderPedigree() {
    canvas.innerHTML = '<ul class="pedigree-tree">' + renderAncestor(rootId, [], null) + '</ul>';
    applyTones(canvas); // chronicle.js global
  }

  function showEmpty(message) {
    headerEl.innerHTML = '<h1 class="mb-0">Family Tree</h1>';
    canvas.innerHTML = '<p class="text-muted">' + escapeHtml(message) + '</p>';
  }

  function loadAndRender(id) {
    canvas.innerHTML = '<p class="text-muted">Loading the tree…</p>';
    return Promise.all([
      apiFetch('/api/individuals/' + id + '/pedigree?direction=ancestors&depth=' + PEDIGREE_DEPTH),
      getMediaMap(),
    ]).then(function(results) {
      mergeGraph(results[0]);
      nodeMediaMap = results[1];
      return ensurePedigreeTypes();
    }).then(function() {
      renderHeader();
      renderPedigree();
    }).catch(function(err) {
      showEmpty(err.message || 'This tree isn’t available right now.');
    });
  }

  function setRoot(id, push) {
    rootId = id;
    if (push) {
      var url = new URL(window.location.href);
      url.searchParams.set('root', id);
      window.history.pushState({ root: id }, '', url.pathname + '?' + url.searchParams.toString());
    }
    loadAndRender(id);
  }

  canvas.addEventListener('click', function(e) {
    var centerBtn = e.target.closest('[data-center]');
    if (centerBtn) { setRoot(parseInt(centerBtn.dataset.center, 10), true); return; }

    var expandBtn = e.target.closest('[data-expand]');
    if (expandBtn) {
      var id = parseInt(expandBtn.dataset.expand, 10);
      expandBtn.disabled = true;
      expandBtn.textContent = 'Loading…';
      apiFetch('/api/individuals/' + id + '/pedigree?direction=ancestors&depth=' + PEDIGREE_DEPTH)
        .then(function(graph) { mergeGraph(graph); return ensurePedigreeTypes(); })
        .then(renderPedigree)
        .catch(function() {
          expandBtn.disabled = false;
          expandBtn.textContent = 'Show earlier generations';
        });
    }
  });

  window.addEventListener('popstate', function() {
    var explicit = currentRootParam();
    if (explicit != null) setRoot(explicit, false);
  });

  var explicitRoot = currentRootParam();
  if (explicitRoot != null) {
    setRoot(explicitRoot, false);
  } else {
    apiFetch('/api/tree/root').then(function(d) {
      if (d.individual_id == null) { showEmpty('No one is in the family tree yet.'); return; }
      setRoot(d.individual_id, false);
    }).catch(function() { showEmpty('The tree isn’t available right now.'); });
  }
})();

/* =============================================================================
 * 2) FAMILY GROUP SHEET (tree/family.html) — one family, read-only. Editing
 * membership stays on the Person Page's Relationships tab (this just links
 * there for Contributor+, same "don't duplicate CRUD here" rule as Pedigree's
 * "Add parent" invite).
 * ===========================================================================*/
(function() {
  var page = document.getElementById('familyPage');
  if (!page) return;

  var familyId = parseInt(page.dataset.familyId, 10);
  var canContribute = page.dataset.canContribute === 'true';
  var sheetEl = document.getElementById('familySheet');

  function partnerCardHtml(id, individuals, media) {
    if (id == null) {
      return '<div class="rel-card"><div class="rel-card__body"><span class="text-muted">Unknown partner</span></div></div>';
    }
    var p = individuals[id] || {};
    var life = FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living);
    return '<div class="rel-card">' +
      '<div class="rel-card__photo">' + personCameoHtml(id, p.primary_name, media[id], 'rel-card__cameo') + '</div>' +
      '<div class="rel-card__body">' +
        '<a href="/people/' + id + '">' + escapeHtml(p.primary_name || 'Unnamed person') + '</a>' +
        (life ? '<div class="text-muted small">' + escapeHtml(life) + '</div>' : '') +
      '</div></div>';
  }

  function childCardHtml(c, individuals, media) {
    var p = individuals[c.child_id] || {};
    var life = FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living);
    var badge = c.pedigree_type && c.pedigree_type !== 'birth' ? pedigreeBadge(c.pedigree_type) : '';
    return '<div class="rel-card">' +
      '<div class="rel-card__photo">' + personCameoHtml(c.child_id, c.child_name, media[c.child_id], 'rel-card__cameo') + '</div>' +
      '<div class="rel-card__body">' +
        '<a href="/people/' + c.child_id + '">' + escapeHtml(c.child_name || 'Unnamed person') + '</a>' +
        (life ? '<div class="text-muted small">' + escapeHtml(life) + '</div>' : '') +
        (badge ? '<div class="rel-card__badges">' + badge + '</div>' : '') +
      '</div></div>';
  }

  Promise.all([
    apiFetch('/api/families/' + familyId),
    getIndividualsMap(),
    getMediaMap(),
    apiFetch('/api/events?subject_type=family&subject_id=' + familyId).then(function(d) { return d.events || []; }),
  ]).then(function(results) {
    var fam = results[0], individuals = results[1], media = results[2], events = results[3];

    var marr = events.filter(function(e) { return e.event_tag === 'MARR'; })[0];
    var div_ = events.filter(function(e) { return e.event_tag === 'DIV'; })[0];
    var eventRows = [];
    if (marr) eventRows.push(['Married', joinDateplace(marr)]);
    if (div_) eventRows.push(['Divorced', joinDateplace(div_)]);
    var eventsHtml = eventRows.length ? '<div class="vitals-list my-3">' + eventRows.map(function(r) {
      return '<div class="vitals-list__row"><span class="vitals-list__k">' + escapeHtml(r[0]) +
        '</span><span class="vitals-list__v">' + escapeHtml(r[1] || '—') + '</span></div>';
    }).join('') + '</div>' : '';

    var children = (fam.children || []).slice().sort(function(a, b) { return a.child_order - b.child_order; });
    var childrenHtml = children.length ?
      '<div class="rel-cards">' + children.map(function(c) { return childCardHtml(c, individuals, media); }).join('') + '</div>' :
      '<p class="text-muted">No children recorded in this family.</p>';

    var editTarget = fam.partner1_id || fam.partner2_id;
    var editLink = (canContribute && editTarget) ?
      '<p class="mt-3 mb-0"><a class="btn btn-outline-secondary" href="/people/' + editTarget + '#relationships">Edit this family</a></p>' : '';

    sheetEl.innerHTML =
      '<h1 class="mb-3">Family Group Sheet</h1>' +
      '<div class="family-sheet__partners">' +
        partnerCardHtml(fam.partner1_id, individuals, media) +
        '<span class="family-sheet__amp" aria-hidden="true">&amp;</span>' +
        partnerCardHtml(fam.partner2_id, individuals, media) +
      '</div>' +
      eventsHtml +
      '<h2 class="section-title mt-3">Children</h2>' +
      childrenHtml +
      editLink;
    applyTones(sheetEl); // chronicle.js global
  }).catch(function(err) {
    sheetEl.innerHTML = '<p class="text-muted mb-0">' + escapeHtml(err.message || 'This family isn’t available right now.') + '</p>';
  });
})();

/* =============================================================================
 * 3) RELATIONSHIP FINDER (tree/relationship.html) — two person pickers, the
 * shortest blood path + plain-English label, and the hop-by-hop chain that
 * makes the path visually traceable.
 * ===========================================================================*/
(function() {
  var page = document.getElementById('relationshipPage');
  if (!page) return;

  var aPickerEl = document.getElementById('personAPicker');
  var bPickerEl = document.getElementById('personBPicker');
  var resultEl = document.getElementById('relationshipResult');
  var picked = { a: null, b: null }; // {id, label}
  var refreshPicker = {};

  function paramInt(name) {
    var n = parseInt(new URLSearchParams(window.location.search).get(name), 10);
    return isNaN(n) ? null : n;
  }

  function updateUrl() {
    var url = new URL(window.location.href);
    if (picked.a) url.searchParams.set('a', picked.a.id); else url.searchParams.delete('a');
    if (picked.b) url.searchParams.set('b', picked.b.id); else url.searchParams.delete('b');
    var qs = url.searchParams.toString();
    window.history.replaceState(null, '', url.pathname + (qs ? '?' + qs : ''));
  }

  /* A search-as-you-type person picker (Master Plan §5A) — the same shape as
   * person.js's own personPicker, minus the "exclude myself" rule: comparing
   * a person to themselves is a real, honestly-handled case here (the API
   * returns relationship: "self"), not a mistake to prevent. */
  function buildPicker(container, slotKey) {
    container.innerHTML =
      '<input type="text" class="form-control person-picker__input" placeholder="Search by name…" autocomplete="off">' +
      '<div class="list-group person-picker__results"></div>' +
      '<div class="person-picker__selected"></div>';
    var input = container.querySelector('.person-picker__input');
    var results = container.querySelector('.person-picker__results');
    var selected = container.querySelector('.person-picker__selected');

    function refresh() {
      if (picked[slotKey]) {
        selected.innerHTML = '<p class="mb-0">Selected: <strong>' + escapeHtml(picked[slotKey].label) +
          '</strong> <button type="button" class="btn btn-outline-secondary btn-sm ms-2" data-clear-picker>Change</button></p>';
        input.classList.add('d-none');
        results.classList.add('d-none');
        results.innerHTML = '';
      } else {
        selected.innerHTML = '';
        input.classList.remove('d-none');
        results.classList.remove('d-none');
      }
    }
    refreshPicker[slotKey] = refresh;

    selected.addEventListener('click', function(e) {
      if (!e.target.closest('[data-clear-picker]')) return;
      picked[slotKey] = null;
      updateUrl();
      refresh();
      renderResult();
      input.focus();
    });
    input.addEventListener('input', debounce(function() {
      var q = input.value.trim();
      if (!q) { results.innerHTML = ''; return; }
      apiFetch('/api/search?q=' + encodeURIComponent(q)).then(function(data) {
        var people = data.people || [];
        results.innerHTML = people.length ? people.map(function(p) {
          return '<button type="button" class="list-group-item list-group-item-action" data-id="' + p.id +
            '" data-name="' + escapeHtml(p.primary_name || 'Unnamed person') + '">' +
            escapeHtml(p.primary_name || 'Unnamed person') +
            '<span class="text-muted small d-block">' + escapeHtml(FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living)) + '</span></button>';
        }).join('') : '<p class="text-muted small mb-0 p-2">No matches.</p>';
      }).catch(function() { results.innerHTML = '<p class="text-muted small mb-0 p-2">Search isn’t available right now.</p>'; });
    }, 250));
    results.addEventListener('click', function(e) {
      var row = e.target.closest('[data-id]');
      if (!row) return;
      picked[slotKey] = { id: parseInt(row.dataset.id, 10), label: row.dataset.name };
      updateUrl();
      refresh();
      renderResult();
    });
    refresh();
  }

  function chainNodeHtml(id, individuals, media) {
    var p = individuals[id] || {};
    var life = FamilyHubFmt.lifespan(p.birth_year, p.death_year, p.living);
    return '<div class="relationship-chain__node">' +
      '<div class="relationship-chain__photo">' + personCameoHtml(id, p.primary_name, media[id], 'relationship-chain__cameo') + '</div>' +
      '<a class="relationship-chain__name" href="/people/' + id + '">' + escapeHtml(p.primary_name || 'Unnamed person') + '</a>' +
      (life ? '<span class="relationship-chain__life">' + escapeHtml(life) + '</span>' : '') +
    '</div>';
  }
  function hopHtml(text) {
    return '<div class="relationship-chain__hop"><span aria-hidden="true">&rarr;</span><span>' + escapeHtml(text) + '</span></div>';
  }

  function renderRelationshipResult(rel, individuals, media) {
    var friendlyLabel;
    if (rel.a === rel.b) friendlyLabel = 'Same person';
    else if (rel.relationship === 'no known relationship') friendlyLabel = 'No known relationship';
    else friendlyLabel = rel.relationship.charAt(0).toUpperCase() + rel.relationship.slice(1);

    var html = '<div class="panel relationship-summary"><p class="relationship-label">' + escapeHtml(friendlyLabel) + '</p></div>';

    if (rel.a === rel.b) {
      html += '<p class="text-muted">You picked the same person twice.</p>';
    } else if (!rel.path || rel.path.length < 2) {
      html += '<p class="text-muted">No blood connection was found on record.</p>';
    } else {
      var chain = [chainNodeHtml(rel.path[0], individuals, media)];
      for (var i = 0; i < rel.path.length - 1; i++) {
        var hopType = (rel.distance_a == null || rel.distance_b == null) ? 'spouse' :
          (i < rel.distance_a ? 'parent' : 'child');
        chain.push(hopHtml(hopType));
        chain.push(chainNodeHtml(rel.path[i + 1], individuals, media));
      }
      html += '<div class="relationship-chain">' + chain.join('') + '</div>';
    }
    resultEl.innerHTML = html;
    applyTones(resultEl); // chronicle.js global
  }

  function renderResult() {
    if (!picked.a || !picked.b) {
      resultEl.innerHTML = (picked.a || picked.b) ?
        '<p class="text-muted">Pick a second person to see how they’re related.</p>' : '';
      return;
    }
    resultEl.innerHTML = '<p class="text-muted">Finding the connection…</p>';
    Promise.all([
      apiFetch('/api/individuals/' + picked.a.id + '/relationship/' + picked.b.id),
      getIndividualsMap(), getMediaMap(),
    ]).then(function(results) {
      renderRelationshipResult(results[0], results[1], results[2]);
    }).catch(function(err) {
      resultEl.innerHTML = '<p class="text-muted">' + escapeHtml(err.message || 'That relationship isn’t available right now.') + '</p>';
    });
  }

  buildPicker(aPickerEl, 'a');
  buildPicker(bPickerEl, 'b');

  var aParam = paramInt('a'), bParam = paramInt('b');
  var setup = [];
  if (aParam != null) {
    setup.push(getIndividualsMap().then(function(map) {
      if (map[aParam]) picked.a = { id: aParam, label: map[aParam].primary_name || 'Unnamed person' };
    }));
  } else {
    // Honest default (no fake placeholder): only pre-fill A when this member
    // really has a linked person (ADR-0002); otherwise the picker stays empty.
    setup.push(apiFetch('/api/me/person').then(function(d) {
      if (d.individual) picked.a = { id: d.individual.id, label: d.individual.primary_name || 'Unnamed person' };
    }).catch(function() {}));
  }
  if (bParam != null) {
    setup.push(getIndividualsMap().then(function(map) {
      if (map[bParam]) picked.b = { id: bParam, label: map[bParam].primary_name || 'Unnamed person' };
    }));
  }
  Promise.all(setup).then(function() {
    refreshPicker.a();
    refreshPicker.b();
    updateUrl();
    renderResult();
  });
})();
