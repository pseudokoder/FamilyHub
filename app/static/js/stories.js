/* stories.js — Stories, the memory-blog lane of Memories (FE-4, Master Plan
 * §4): list/browse notes, a read view, and a Contributor+ "Write a story"
 * flow. Reuses person.js's Story-tab patterns (Markdown rendering, the
 * search-as-you-type link picker, inline "+ Add …" drawers) via
 * fh-common.js rather than re-typing them — see that file's header note.
 *
 * Depends on api.js (apiFetch) and fh-common.js (escapeHtml, debounce,
 * subjectPicker, renderNoteContent, resolveLinkTarget, toggleForm/hideForm,
 * alertFormError) — both loaded before this file (base.html, globally).
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315 —
 *    renderNoteContent escapes raw Markdown before any HTML is built).
 */
'use strict';

var canContribute = false;

function snippetOf(content) {
  var text = String(content || '')
    .replace(/^#{1,6}\s+/gm, '').replace(/[*_`]/g, '').replace(/\s+/g, ' ').trim();
  return text.length <= 160 ? text : text.slice(0, 160).trim() + '…';
}

/* =============================================================================
 * SHARED FORM BONES — every user-meaningful Note column (title, content,
 * content_type, is_shared — Master Plan §5A depth bar; author_id/timestamps
 * are system fields, excluded) used by both the create page and the read
 * view's inline "Edit" drawer.
 * ===========================================================================*/
function noteFormHtml(note) {
  note = note || {};
  return (
    '<div class="mb-2"><label class="form-label" for="storyTitle">Title</label>' +
      '<input type="text" class="form-control" id="storyTitle" value="' + escapeHtml(note.title || '') + '"></div>' +
    '<div class="row g-3">' +
      '<div class="col-md-8"><label class="form-label" for="storyContent">Story</label>' +
        '<textarea class="form-control" id="storyContent" rows="10">' + escapeHtml(note.content || '') + '</textarea>' +
        '<p class="form-text">Markdown: **bold**, *italic*, `code`, "- " lists, and # headings.</p></div>' +
      '<div class="col-md-4"><label class="form-label">Preview</label><div class="panel story-form__preview" id="storyPreview"></div></div>' +
    '</div>' +
    '<div class="row g-3 mt-0">' +
      '<div class="col-md-6"><label class="form-label" for="storyContentType">Format</label>' +
        '<select class="form-select" id="storyContentType">' +
          '<option value="markdown"' + (note.content_type !== 'plain' ? ' selected' : '') + '>Markdown</option>' +
          '<option value="plain"' + (note.content_type === 'plain' ? ' selected' : '') + '>Plain text</option>' +
        '</select></div>' +
      '<div class="col-md-6 d-flex align-items-end">' +
        '<div class="form-check">' +
          '<input class="form-check-input" type="checkbox" id="storyIsShared"' + (note.is_shared ? ' checked' : '') + '>' +
          '<label class="form-check-label" for="storyIsShared">Shared note</label>' +
          '<p class="form-text mb-0">Shared notes (GEDCOM SNOTE) can be reused across multiple people or events, rather than living on just one.</p>' +
        '</div>' +
      '</div>' +
    '</div>'
  );
}
function wireLivePreview(root) {
  var contentEl = root.querySelector('#storyContent');
  var typeEl = root.querySelector('#storyContentType');
  var previewEl = root.querySelector('#storyPreview');
  function update() { previewEl.innerHTML = renderNoteContent({ content: contentEl.value, content_type: typeEl.value }); }
  contentEl.addEventListener('input', debounce(update, 150));
  typeEl.addEventListener('change', update);
  update();
}
function readNoteForm(form) {
  return {
    title: form.querySelector('#storyTitle').value.trim() || null,
    content: form.querySelector('#storyContent').value.trim(),
    content_type: form.querySelector('#storyContentType').value,
    is_shared: form.querySelector('#storyIsShared').checked,
  };
}

/* =============================================================================
 * STORIES LIST — every note, newest first (GET /api/notes' default order;
 * "Stories" IS the memory-blog view over the same notes table Master Plan §4
 * maps to it — no separate "is a story" flag to filter on).
 * ===========================================================================*/
function storyRowHtml(n) {
  var meta = [n.author ? 'By ' + n.author : null, new Date(n.updated_at).toLocaleDateString()].filter(Boolean).join(' · ');
  return '<a class="list-group-item list-group-item-action story-row" href="/memories/stories/' + n.id + '">' +
    '<span class="story-row__title">' + escapeHtml(n.title || 'Untitled story') + '</span>' +
    '<span class="story-row__snippet">' + escapeHtml(snippetOf(n.content)) + '</span>' +
    '<span class="story-row__meta">' + escapeHtml(meta) + '</span>' +
  '</a>';
}
function loadStoriesList() {
  var root = document.getElementById('storiesListView');
  if (!root) return;
  var listEl = document.getElementById('storiesList');
  apiFetch('/api/notes').then(function(d) {
    var notes = d.notes || [];
    listEl.innerHTML = notes.length ? '<div class="list-group">' + notes.map(storyRowHtml).join('') + '</div>' :
      '<p class="text-muted">No stories have been written yet.</p>';
  }).catch(function() { listEl.innerHTML = '<p class="text-muted">Stories aren’t available right now.</p>'; });
}

/* =============================================================================
 * WRITE A STORY — Contributor+ only (§10). A Viewer landing here directly
 * (e.g. a stale link) sees an honest explanation, not a form that would just
 * 403 on submit — same data-can-contribute gating convention people/show.html
 * established for person.js.
 * ===========================================================================*/
function loadNewStory() {
  var root = document.getElementById('storyNewView');
  if (!root) return;
  canContribute = root.dataset.canContribute === 'true';
  var host = document.getElementById('storyNewForm');

  if (!canContribute) {
    host.innerHTML = '<p class="text-muted">Writing a story needs Contributor access — ask a Curator or Admin to raise your role.</p>';
    return;
  }

  var picked = null;
  host.innerHTML = '<form id="newStoryForm" class="panel">' + noteFormHtml(null) +
    '<div class="mt-3 mb-3"><label class="form-label d-block">Who or what is this about? (optional)</label>' +
      '<div class="picker-panel" id="storySubjectPicker"></div>' +
      '<p class="text-muted small mt-1 mb-0" id="storySubjectPicked"></p></div>' +
    '<button type="submit" class="btn btn-primary">Save story</button>' +
  '</form>';
  wireLivePreview(host);

  subjectPicker(document.getElementById('storySubjectPicker'), function(type, id, label) {
    picked = { type: type, id: id };
    document.getElementById('storySubjectPicked').textContent = 'About: ' + label;
  });

  document.getElementById('newStoryForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var form = e.target;
    var payload = readNoteForm(form);
    if (!payload.content) { alertFormError(form, { message: 'Write something before saving.' }); return; }
    if (picked) { payload.subject_type = picked.type; payload.subject_id = picked.id; }
    apiFetch('/api/notes', { method: 'POST', body: payload }).then(function(note) {
      window.location.href = '/memories/stories/' + note.id;
    }).catch(function(err) { alertFormError(form, err); });
  });
}

/* =============================================================================
 * READ VIEW — content, "About" (every link, navigable), and Contributor+
 * inline Edit / manage-links / soft-delete (the standard recoverable-confirm
 * wording used everywhere else in this app).
 * ===========================================================================*/
function loadStoryShow() {
  var root = document.getElementById('storyShowView');
  if (!root) return;
  canContribute = root.dataset.canContribute === 'true';
  var noteId = parseInt(root.dataset.noteId, 10);
  var el = document.getElementById('storyShowBody');

  function render() {
    el.innerHTML = '<p class="text-muted">Loading this story…</p>';
    apiFetch('/api/notes/' + noteId).then(function(note) {
      var links = note.links || [];
      Promise.all(links.map(resolveLinkTarget)).then(function(targets) {
        var aboutHtml = targets.length ? targets.map(function(t, i) {
          var link = links[i];
          var removeBtn = canContribute ?
            '<button type="button" class="btn btn-outline-secondary btn-sm" data-unlink-note="' + link.subject_type + ':' + link.subject_id + '">Remove</button>' : '';
          return '<div class="photo-detail__link-row"><a class="stamp ' + t.cls + '" href="' + t.href + '">' + escapeHtml(t.label) + '</a>' + removeBtn + '</div>';
        }).join('') : '<p class="text-muted small mb-0">Not linked to anyone yet.</p>';

        var meta = [note.author ? 'By ' + note.author : null, 'Updated ' + new Date(note.updated_at).toLocaleDateString()].filter(Boolean).join(' · ');
        var actions = canContribute ?
          '<div class="d-flex flex-wrap gap-2 mt-3">' +
            '<button type="button" class="btn btn-outline-secondary btn-sm" id="btnEditStory">Edit</button>' +
            '<button type="button" class="btn btn-outline-secondary btn-sm" id="btnAddStoryLink">+ Add a link</button>' +
            '<button type="button" class="btn btn-outline-danger btn-sm" id="btnDeleteStory">Delete story</button>' +
          '</div>' : '';

        el.innerHTML =
          '<div class="panel story-card">' +
            '<h1 class="mb-1">' + escapeHtml(note.title || 'Untitled story') + '</h1>' +
            '<p class="text-muted small">' + escapeHtml(meta) + '</p>' +
            '<div class="story-content">' + renderNoteContent(note) + '</div>' +
            '<div class="mt-3"><span class="section-title">About</span>' + aboutHtml + '</div>' +
            '<div id="storyLinkForm" class="d-none inline-form-slot mt-2"></div>' +
            '<div id="storyEditForm" class="d-none inline-form-slot mt-2"></div>' +
            actions +
          '</div>';
        wireActions();
      });
    }).catch(function() { el.innerHTML = '<p class="text-muted">This story isn’t available right now.</p>'; });
  }

  function wireActions() {
    var cancelBtns = el.querySelectorAll('[data-cancel-form]');
    cancelBtns.forEach(function(btn) { btn.addEventListener('click', function() { hideForm(btn.closest('.inline-form-slot')); }); });

    var editBtn = document.getElementById('btnEditStory');
    if (editBtn) editBtn.addEventListener('click', function() {
      apiFetch('/api/notes/' + noteId).then(function(note) {
        var slot = document.getElementById('storyEditForm');
        toggleForm(slot, '<form id="editStoryFormEl">' + noteFormHtml(note) +
          '<div class="mt-2 d-flex gap-2"><button type="submit" class="btn btn-primary btn-sm">Save</button>' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button></div></form>');
        wireLivePreview(slot);
        slot.querySelector('[data-cancel-form]').addEventListener('click', function() { hideForm(slot); });
        slot.querySelector('#editStoryFormEl').addEventListener('submit', function(e) {
          e.preventDefault();
          var form = e.target;
          apiFetch('/api/notes/' + noteId, { method: 'PUT', body: readNoteForm(form) })
            .then(function() { hideForm(slot); render(); })
            .catch(function(err) { alertFormError(form, err); });
        });
      });
    });

    var addLinkBtn = document.getElementById('btnAddStoryLink');
    if (addLinkBtn) addLinkBtn.addEventListener('click', function() {
      var slot = document.getElementById('storyLinkForm');
      toggleForm(slot, '<div class="link-picker"></div>');
      subjectPicker(slot.querySelector('.link-picker'), function(type, id) {
        apiFetch('/api/notes/' + noteId + '/links', { method: 'POST', body: { subject_type: type, subject_id: id } })
          .then(function() { hideForm(slot); render(); })
          .catch(function(err) { window.alert(err.message || 'Could not add that link.'); });
      });
    });

    var deleteBtn = document.getElementById('btnDeleteStory');
    if (deleteBtn) deleteBtn.addEventListener('click', function() {
      if (!window.confirm('Delete this story? A Curator can restore it later.')) return;
      apiFetch('/api/notes/' + noteId, { method: 'DELETE' }).then(function() {
        window.location.href = '/memories/stories';
      }).catch(function(err) { window.alert(err.message || 'Could not delete that story.'); });
    });

    Array.prototype.forEach.call(el.querySelectorAll('[data-unlink-note]'), function(btn) {
      btn.addEventListener('click', function() {
        var parts = btn.dataset.unlinkNote.split(':');
        if (!window.confirm('Remove this link? A Curator can restore it later.')) return;
        apiFetch('/api/notes/' + noteId + '/links/' + parts[0] + '/' + parts[1], { method: 'DELETE' })
          .then(function() { render(); })
          .catch(function(err) { window.alert(err.message || 'Could not remove that link.'); });
      });
    });
  }

  render();
}

document.addEventListener('DOMContentLoaded', function() {
  loadStoriesList();
  loadNewStory();
  loadStoryShow();
});
