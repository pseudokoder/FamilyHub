/* memories.js — the Memories section (FE-4, Master Plan §4): Chronological /
 * By Person / By Family / By Event album views over the ONE photo store
 * (GET /api/media), plus the richer Photo Detail overlay that extends FE-2's
 * simple person-page lightbox (person.js) with metadata, navigable links,
 * and Contributor+ edit/manage-link/delete actions.
 *
 * Depends on api.js (apiFetch, FamilyHubFmt) and fh-common.js (escapeHtml,
 * debounce, toneFor/personPhotoHtml, subjectPicker, toggleForm/hideForm,
 * formToObject, alertFormError/showInlineError, fuzzy-date helpers,
 * personLink/familyLink, resolveLinkTarget/tagLabel) — both loaded before
 * this file (see templates).
 * Also uses chronicle.js's photo()/applyTones() globals (base.html loads it
 * on every page) for the toned-cameo photo placeholders.
 *
 * Every page section below DOM-guards on its own root element, same
 * no-op-if-absent pattern as chronicle.js/person.js/tree.js, so this ONE
 * file safely covers all four album-view templates.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315).
 */
'use strict';

var canContribute = false;
var currentAlbumMedia = []; // whichever view is on-screen, for the lightbox's id lookup

/* =============================================================================
 * PHOTO TILE — the one grid cell every album view renders. Chronological's
 * "fall back to upload date, visibly labeled" requirement (brief) shows up
 * here: a tile with no capture_date shows "Uploaded <date>" instead of
 * silently going dateless.
 * ===========================================================================*/
function photoTileHtml(m) {
  var tones = toneFor(m.id);
  var dateBit = m.capture_date ? '<span class="d">' + escapeHtml(m.capture_date) + '</span>' :
    '<span class="u">Uploaded ' + escapeHtml(new Date(m.created_at).toLocaleDateString()) + '</span>';
  return '<figure class="cell" data-open-photo="' + m.id + '">' +
    '<div class="photo" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
      '<img src="' + m.thumb_url + '" alt="' + escapeHtml(m.title || '') + '">' +
    '</div>' +
    '<figcaption class="cell__cap"><span class="t">' + escapeHtml(m.title || 'Untitled') + '</span>' + dateBit + '</figcaption>' +
  '</figure>';
}
function albumGridHtml(mediaList) {
  return mediaList.length ? '<div class="wall gallery-wall">' + mediaList.map(photoTileHtml).join('') + '</div>' :
    '<p class="text-muted">No photos here yet.</p>';
}
function wireAlbumClicks(container, onOpen) {
  container.addEventListener('click', function(e) {
    var tile = e.target.closest('[data-open-photo]');
    if (!tile) return;
    var media = currentAlbumMedia.filter(function(m) { return m.id === parseInt(tile.dataset.openPhoto, 10); })[0];
    if (media) openPhotoDetail(media.id, onOpen);
  });
}

/* =============================================================================
 * UPLOAD FORM — shared by every view's "+ Upload a photo" (Contributor+).
 * Uploads land UNLINKED in the one photo store (POST /api/media only
 * requires the file — docs/openapi.yaml); linking to a person/family happens
 * afterward via "Manage links" in the Photo Detail panel below. This is the
 * "one photo store, album views" idea made literal: you don't have to know
 * who a photo is of before you can save it.
 *
 * Capture date uses the same Precision+Year+Month+Day fuzzy-date group as
 * every other date in the app (fh-common.js), populating BOTH capture_date
 * (raw) and capture_date_sort (normalized) — person.js's own upload form
 * only ever set capture_date, leaving capture_date_sort null, so its photos
 * fall back to upload-date ordering in Chronological. That's the documented,
 * honest fallback (not a bug) for photos uploaded before this form existed;
 * new uploads through THIS form sort correctly. */
function photoUploadFormHtml() {
  return '<form id="photoUploadForm" class="mb-3">' +
    '<div class="row g-2 align-items-end">' +
      '<div class="col-md-5"><label class="form-label" for="photoFile">Upload a photo</label>' +
        '<input type="file" id="photoFile" class="form-control" accept="image/*" required></div>' +
      '<div class="col-md-5"><label class="form-label" for="photoTitle">Title</label><input type="text" id="photoTitle" class="form-control"></div>' +
      '<div class="col-md-2"><button type="submit" class="btn btn-primary w-100">Upload</button></div>' +
    '</div>' +
    '<div class="mb-2"><label class="form-label" for="photoDescription">Description</label>' +
      '<textarea id="photoDescription" class="form-control" rows="2"></textarea></div>' +
    '<label class="form-label d-block">When was it taken?</label>' +
    fuzzyDateFieldsHtml({ qualifier: 'exact', year: '', month: '', day: '' }, 'capture') +
  '</form>';
}
function wireUploadForm(container, onUploaded) {
  container.addEventListener('submit', function(e) {
    if (e.target.id !== 'photoUploadForm') return;
    e.preventDefault();
    var form = e.target;
    var fileInput = form.querySelector('#photoFile');
    if (!fileInput.files.length) { alertFormError(form, { message: 'Choose a photo to upload.' }); return; }
    var date = readFuzzyDateFromForm(form, 'capture');
    var fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('title', form.querySelector('#photoTitle').value.trim());
    fd.append('description', form.querySelector('#photoDescription').value.trim());
    fd.append('capture_date', date ? date.date_original : '');
    fd.append('capture_date_sort', date ? date.date_sort : '');
    apiFetch('/api/media', { method: 'POST', body: fd }).then(function() {
      onUploaded();
    }).catch(function(err) { alertFormError(form, err); });
  });
}

/* =============================================================================
 * PHOTO DETAIL — extends FE-2's simple person-page lightbox (caption + one
 * unlink button) with full metadata, EVERY link as a navigable chip, and
 * Contributor+ edit-metadata / manage-links / soft-delete actions. Always
 * re-fetches the single media object (GET /api/media/{id}) rather than
 * reusing the album's list-item shape, because the LIST endpoint omits
 * `links` (only the single-object GET includes it — docs/openapi.yaml).
 * ===========================================================================*/
var photoDetailEl = null;
function ensurePhotoDetail() {
  if (photoDetailEl) return photoDetailEl;
  photoDetailEl = document.createElement('div');
  photoDetailEl.className = 'photo-detail';
  photoDetailEl.innerHTML =
    '<button type="button" class="photo-detail__close" aria-label="Close">&times;</button>' +
    '<div class="photo-detail__stage"><img class="photo-detail__img" alt=""></div>' +
    '<div class="photo-detail__panel"></div>';
  document.body.appendChild(photoDetailEl);
  photoDetailEl.querySelector('.photo-detail__close').addEventListener('click', closePhotoDetail);
  photoDetailEl.addEventListener('click', function(e) { if (e.target === photoDetailEl) closePhotoDetail(); });
  document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closePhotoDetail(); });
  return photoDetailEl;
}
function closePhotoDetail() { if (photoDetailEl) photoDetailEl.classList.remove('is-on'); }

/* resolveLinkTarget/tagLabel now live in fh-common.js (shared with
 * stories.js's own "About" links section — see that file). */

function panelHtml(media, linkChips) {
  var whenBits = [];
  if (media.capture_date) whenBits.push('Taken: ' + media.capture_date);
  else whenBits.push('No capture date recorded');
  whenBits.push('Uploaded ' + new Date(media.created_at).toLocaleDateString() + (media.uploader ? ' by ' + media.uploader : ''));

  var actions = canContribute ?
    '<div class="photo-detail__actions">' +
      '<button type="button" class="btn btn-outline-light btn-sm" id="btnEditMedia">Edit metadata</button>' +
      '<button type="button" class="btn btn-outline-light btn-sm" id="btnAddMediaLink">+ Add a link</button>' +
      '<button type="button" class="btn btn-outline-danger btn-sm" id="btnDeleteMedia">Delete photo</button>' +
    '</div>' : '';

  return '<h2 class="photo-detail__title">' + escapeHtml(media.title || 'Untitled photo') + '</h2>' +
    (media.description ? '<p class="photo-detail__desc">' + escapeHtml(media.description) + '</p>' : '') +
    '<p class="photo-detail__meta">' + escapeHtml(whenBits.join(' · ')) + '</p>' +
    '<div class="photo-detail__links"><span class="section-title">Linked to</span>' +
      (linkChips || '<p class="text-muted small mb-0">Not linked to anyone yet.</p>') +
    '</div>' +
    '<div id="mediaLinkForm" class="d-none inline-form-slot mb-2"></div>' +
    '<div id="mediaEditForm" class="d-none inline-form-slot mb-2"></div>' +
    actions;
}

function editMediaFormHtml(media) {
  var prefill = parseFuzzyForEdit(media.capture_date, media.capture_date_sort);
  return '<form id="mediaEditFormEl">' +
    '<div class="mb-2"><label class="form-label">Title</label><input type="text" class="form-control" name="title" value="' + escapeHtml(media.title || '') + '"></div>' +
    '<div class="mb-2"><label class="form-label">Description</label><textarea class="form-control" name="description" rows="2">' + escapeHtml(media.description || '') + '</textarea></div>' +
    '<label class="form-label d-block">When was it taken?</label>' + fuzzyDateFieldsHtml(prefill, 'capture') +
    '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Save</button>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div>' +
  '</form>';
}

function openPhotoDetail(mediaId, onChanged) {
  var el = ensurePhotoDetail();
  var panel = el.querySelector('.photo-detail__panel');
  panel.innerHTML = '<p class="text-muted">Loading…</p>';
  el.querySelector('.photo-detail__img').src = '';
  el.classList.add('is-on');

  function refresh() {
    apiFetch('/api/media/' + mediaId).then(function(media) {
      el.querySelector('.photo-detail__img').src = media.file_url;
      var links = media.links || [];
      Promise.all(links.map(resolveLinkTarget)).then(function(targets) {
        var chips = targets.map(function(t, i) {
          var link = links[i];
          var removeBtn = canContribute ?
            '<button type="button" class="btn btn-outline-secondary btn-sm" data-unlink="' + link.subject_type + ':' + link.subject_id + '">Remove</button>' : '';
          return '<div class="photo-detail__link-row"><a class="stamp ' + t.cls + '" href="' + t.href + '">' + escapeHtml(t.label) + '</a>' + removeBtn + '</div>';
        }).join('');
        panel.innerHTML = panelHtml(media, chips);
        wirePanelActions(panel, media, refresh, onChanged);
      });
    }).catch(function() { panel.innerHTML = '<p class="text-muted">This photo isn’t available right now.</p>'; });
  }
  refresh();
}

function wirePanelActions(panel, media, refresh, onChanged) {
  var cancelBtn = panel.querySelector('[data-cancel-form]');
  if (cancelBtn) cancelBtn.addEventListener('click', function() {
    hideForm(panel.querySelector('#mediaEditForm'));
    hideForm(panel.querySelector('#mediaLinkForm'));
  });

  var editBtn = panel.querySelector('#btnEditMedia');
  if (editBtn) editBtn.addEventListener('click', function() {
    toggleForm(panel.querySelector('#mediaEditForm'), editMediaFormHtml(media));
    panel.querySelector('#mediaEditFormEl').addEventListener('submit', function(e) {
      e.preventDefault();
      var form = e.target;
      var date = readFuzzyDateFromForm(form, 'capture');
      apiFetch('/api/media/' + media.id, {
        method: 'PUT',
        body: {
          title: form.elements.title.value.trim() || null,
          description: form.elements.description.value.trim() || null,
          capture_date: date ? date.date_original : null,
          capture_date_sort: date ? date.date_sort : null,
        },
      }).then(function() { refresh(); if (onChanged) onChanged(); })
        .catch(function(err) { alertFormError(form, err); });
    });
    panel.querySelector('[data-cancel-form]').addEventListener('click', function() { hideForm(panel.querySelector('#mediaEditForm')); });
  });

  var addLinkBtn = panel.querySelector('#btnAddMediaLink');
  if (addLinkBtn) addLinkBtn.addEventListener('click', function() {
    var slot = panel.querySelector('#mediaLinkForm');
    toggleForm(slot, '<div class="link-picker"></div>');
    subjectPicker(slot.querySelector('.link-picker'), function(type, id) {
      apiFetch('/api/media/' + media.id + '/links', { method: 'POST', body: { subject_type: type, subject_id: id } })
        .then(function() { hideForm(slot); refresh(); if (onChanged) onChanged(); })
        .catch(function(err) { window.alert(err.message || 'Could not add that link.'); });
    });
  });

  var deleteBtn = panel.querySelector('#btnDeleteMedia');
  if (deleteBtn) deleteBtn.addEventListener('click', function() {
    if (!window.confirm('Delete this photo? A Curator can restore it later.')) return;
    apiFetch('/api/media/' + media.id, { method: 'DELETE' }).then(function() {
      closePhotoDetail();
      if (onChanged) onChanged();
    }).catch(function(err) { window.alert(err.message || 'Could not delete that photo.'); });
  });

  panel.addEventListener('click', function(e) {
    var unlinkBtn = e.target.closest('[data-unlink]');
    if (!unlinkBtn) return;
    var parts = unlinkBtn.dataset.unlink.split(':');
    if (!window.confirm('Remove this photo from there? A Curator can restore it later.')) return;
    apiFetch('/api/media/' + media.id + '/links/' + parts[0] + '/' + parts[1], { method: 'DELETE' })
      .then(function() { refresh(); if (onChanged) onChanged(); })
      .catch(function(err) { window.alert(err.message || 'Could not remove that link.'); });
  });
}

/* =============================================================================
 * CHRONOLOGICAL (default /memories) — every photo, capture date first,
 * upload date for the rest, plus the shared upload form.
 * ===========================================================================*/
function loadChronological() {
  var root = document.getElementById('chronologicalView');
  if (!root) return;
  var uploadSlot = document.getElementById('chronologicalUpload');
  var gridEl = document.getElementById('chronologicalGrid');

  function render() {
    gridEl.innerHTML = '<p class="text-muted">Loading…</p>';
    apiFetch('/api/media?order_by=capture').then(function(d) {
      currentAlbumMedia = d.media || [];
      gridEl.innerHTML = albumGridHtml(currentAlbumMedia);
    }).catch(function() { gridEl.innerHTML = '<p class="text-muted">Photos aren’t available right now.</p>'; });
  }

  if (canContribute) {
    uploadSlot.innerHTML = photoUploadFormHtml();
    wireUploadForm(uploadSlot, render);
  }
  wireAlbumClicks(gridEl, render);
  render();
}

/* =============================================================================
 * BY PERSON — pick a person, see every photo linked to them. Same
 * GET /api/media?subject_type=individual&subject_id= call person.js's own
 * Photos tab already uses.
 * ===========================================================================*/
function loadByPerson() {
  var root = document.getElementById('byPersonView');
  if (!root) return;
  var pickerHost = document.getElementById('byPersonPicker');
  var resultHost = document.getElementById('byPersonResult');

  function showPerson(id, label) {
    window.history.pushState({}, '', '/memories/person?person=' + id);
    resultHost.innerHTML = '<h2 class="section-title">' + escapeHtml(label) + '</h2>' +
      '<div id="byPersonUpload"></div><div id="byPersonGrid"><p class="text-muted">Loading…</p></div>';
    var uploadSlot = document.getElementById('byPersonUpload');
    var gridEl = document.getElementById('byPersonGrid');

    function render() {
      gridEl.innerHTML = '<p class="text-muted">Loading…</p>';
      apiFetch('/api/media?subject_type=individual&subject_id=' + id).then(function(d) {
        currentAlbumMedia = d.media || [];
        gridEl.innerHTML = albumGridHtml(currentAlbumMedia);
      }).catch(function() { gridEl.innerHTML = '<p class="text-muted">Photos aren’t available right now.</p>'; });
    }
    if (canContribute) {
      uploadSlot.innerHTML = '<button type="button" class="btn btn-outline-secondary btn-sm mb-2" id="byPersonUploadBtn">+ Upload a photo of them</button>' +
        '<div id="byPersonUploadForm" class="d-none inline-form-slot mb-2"></div>';
      document.getElementById('byPersonUploadBtn').addEventListener('click', function() {
        var slot = document.getElementById('byPersonUploadForm');
        toggleForm(slot, photoUploadFormHtml());
        wireUploadForm(slot, function() { hideForm(slot); render(); });
      });
    }
    wireAlbumClicks(gridEl, render);
    render();
  }

  subjectPicker(pickerHost, function(type, id, label) { showPerson(id, label); }, { types: ['individual'] });

  var params = new URLSearchParams(window.location.search);
  var preId = params.get('person');
  if (preId) {
    apiFetch('/api/individuals/' + preId).then(function(ind) { showPerson(ind.id, ind.primary_name || 'Unnamed person'); }).catch(function() {});
  }
}

/* =============================================================================
 * BY FAMILY — pick a family, see photos linked to the family itself, its own
 * events (marriage, divorce…), and its members' own events. Every one of
 * these is a real GET /api/media?subject_type=…&subject_id=… call already
 * in the contract (individual|family|event — docs/openapi.yaml's Media Link
 * schema); no missing backend capability, just an honest client-side
 * aggregation across several real targets (same family-scale "one call per
 * target, not per record" shape person.js's Timeline tab already uses for
 * events, not a new pattern invented here).
 * ===========================================================================*/
function loadByFamily() {
  var root = document.getElementById('byFamilyView');
  if (!root) return;
  var pickerHost = document.getElementById('byFamilyPicker');
  var resultHost = document.getElementById('byFamilyResult');

  function showFamily(id, label) {
    window.history.pushState({}, '', '/memories/family?family=' + id);
    resultHost.innerHTML = '<h2 class="section-title">' + escapeHtml(label) + '</h2><div id="byFamilyGrid"><p class="text-muted">Loading…</p></div>';
    var gridEl = document.getElementById('byFamilyGrid');

    function render() {
      gridEl.innerHTML = '<p class="text-muted">Loading…</p>';
      apiFetch('/api/families/' + id).then(function(family) {
        var memberIds = [family.partner1_id, family.partner2_id].filter(function(x) { return x; })
          .concat((family.children || []).map(function(c) { return c.child_id; }));

        var directMediaP = apiFetch('/api/media?subject_type=family&subject_id=' + id).then(function(d) { return d.media || []; });
        var familyEventsP = apiFetch('/api/events?subject_type=family&subject_id=' + id).then(function(d) { return d.events || []; });
        var memberEventsP = Promise.all(memberIds.map(function(mid) {
          return apiFetch('/api/events?subject_type=individual&subject_id=' + mid).then(function(d) { return d.events || []; });
        })).then(function(lists) { return [].concat.apply([], lists); });

        return Promise.all([directMediaP, familyEventsP, memberEventsP]).then(function(r) {
          var directMedia = r[0], familyEvents = r[1], memberEvents = r[2];
          var allEvents = familyEvents.concat(memberEvents);
          return Promise.all(allEvents.map(function(e) {
            return apiFetch('/api/media?subject_type=event&subject_id=' + e.id).then(function(d) { return d.media || []; });
          })).then(function(eventMediaLists) {
            var byId = {};
            [].concat.apply(directMedia, eventMediaLists).forEach(function(m) { byId[m.id] = m; });
            return Object.keys(byId).map(function(k) { return byId[k]; })
              .sort(function(a, b) { return (b.created_at || '').localeCompare(a.created_at || ''); });
          });
        });
      }).then(function(media) {
        currentAlbumMedia = media;
        gridEl.innerHTML = albumGridHtml(media);
      }).catch(function() { gridEl.innerHTML = '<p class="text-muted">Photos aren’t available right now.</p>'; });
    }
    wireAlbumClicks(gridEl, render);
    render();
  }

  subjectPicker(pickerHost, function(type, id, label) { showFamily(id, label); }, { types: ['family'] });

  var params = new URLSearchParams(window.location.search);
  var preId = params.get('family');
  if (preId) {
    getFamiliesCached().then(function(list) {
      var f = list.filter(function(x) { return x.id === parseInt(preId, 10); })[0];
      if (f) showFamily(f.id, familyLabel(f));
    });
  }
}

/* =============================================================================
 * BY EVENT — every event with at least one linked photo, grouped. A whole-
 * archive view (no picker): GET /api/events (all of them, family-scale —
 * the same "fetch it all" precedent people.js's sort already set) then one
 * GET /api/media?subject_type=event&subject_id= per event, groups with zero
 * photos simply don't render a section (§5A — never a hollow group).
 * ===========================================================================*/
function loadByEvent() {
  var root = document.getElementById('byEventView');
  if (!root) return;
  var listEl = document.getElementById('byEventList');

  function render() {
    listEl.innerHTML = '<p class="text-muted">Loading…</p>';
    // GET /api/events only filters when BOTH subject_type AND subject_id are
    // given (app/services/event_service.py) — with neither, it returns every
    // event regardless of subject, which is exactly what this whole-archive
    // view wants (no picker, family-scale dataset).
    apiFetch('/api/events').then(function(d) {
      var events = d.events || [];
      return Promise.all(events.map(function(e) {
        return apiFetch('/api/media?subject_type=event&subject_id=' + e.id).then(function(md) { return { event: e, media: md.media || [] }; });
      }));
    }).then(function(groups) {
      var withPhotos = groups.filter(function(g) { return g.media.length; })
        .sort(function(a, b) { return (b.event.date_sort || '').localeCompare(a.event.date_sort || ''); });
      if (!withPhotos.length) { listEl.innerHTML = '<p class="text-muted">No photos are linked to an event yet.</p>'; return; }
      currentAlbumMedia = [].concat.apply([], withPhotos.map(function(g) { return g.media; }));
      listEl.innerHTML = withPhotos.map(function(g) {
        var e = g.event;
        var title = tagLabel(e.event_tag) + (e.subject_label ? ': ' + e.subject_label : '');
        var meta = FamilyHubFmt.joinDot([e.date_original, e.place]);
        return '<div class="event-group"><div class="event-group__head">' +
          '<h2 class="event-group__title">' + escapeHtml(title) + '</h2>' +
          (meta ? '<p class="event-group__meta mb-0">' + escapeHtml(meta) + '</p>' : '') +
        '</div>' + albumGridHtml(g.media) + '</div>';
      }).join('');
    }).catch(function() { listEl.innerHTML = '<p class="text-muted">Events aren’t available right now.</p>'; });
  }
  wireAlbumClicks(listEl, render);
  render();
}

document.addEventListener('DOMContentLoaded', function() {
  var page = document.getElementById('memoriesPage');
  if (!page) return;
  canContribute = page.dataset.canContribute === 'true';

  loadChronological();
  loadByPerson();
  loadByFamily();
  loadByEvent();

  // Deep link from elsewhere in the app (My Contributions' "photo" rows,
  // FE-5) straight to one photo's detail panel — openPhotoDetail fetches by
  // id directly, so this works regardless of which album view is default.
  var photoParam = new URLSearchParams(window.location.search).get('photo');
  if (photoParam) openPhotoDetail(parseInt(photoParam, 10));
});
