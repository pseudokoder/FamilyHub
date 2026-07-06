/* admin.js — the Admin Console (FE-6, Master Plan §9/§10): Dashboard, Users,
 * Suggestions inbox, Role requests, Settings, Backups, Activity. Seven pages,
 * one file — the same "each page's init function is DOM-guarded, so one
 * script safely covers every template" pattern account.js/memories.js
 * already established. Every action funnels through the AdminApi/Inbox/
 * WriteControl/Tree tags in docs/openapi.yaml; nothing here talks to a
 * business-logic endpoint outside the contract.
 *
 * Depends on api.js (apiFetch) and fh-common.js (escapeHtml, debounce,
 * toggleForm/hideForm, alertFormError/showInlineError) — both loaded on every
 * authenticated page by base.html, so no extra <script> tag is needed for
 * those.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315).
 */
'use strict';

/* --- Small shared formatters -------------------------------------------- */

/* formatBytes(1234567) -> "1.2 MB" — Jinja's `filesizeformat` isn't available
 * here since every admin page is entirely client-rendered. */
function formatBytes(bytes) {
  if (bytes == null) return '—';
  var units = ['B', 'KB', 'MB', 'GB', 'TB'];
  var n = Number(bytes), i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return (i === 0 ? n : n.toFixed(1)) + ' ' + units[i];
}
function formatWhen(iso) {
  return iso ? new Date(iso).toLocaleString() : null;
}
function vitalsRow(k, v) {
  return '<div class="vitals-list__row"><span class="vitals-list__k">' + escapeHtml(k) +
    '</span><span>' + escapeHtml(String(v)) + '</span></div>';
}

/* Shared role vocabulary (Users, Role Requests both need it) — same labels
 * account.js's Role section uses, kept here rather than imported since each
 * page script in this app is a standalone <script src> (no bundler). */
var ROLE_LABEL = { viewer: 'Viewer', contributor: 'Contributor', curator: 'Curator', admin: 'Admin' };
var ROLE_BADGE_CLASS = {
  admin: 'text-bg-primary', curator: 'text-bg-info',
  contributor: 'text-bg-secondary', viewer: 'text-bg-light border',
};

/* =============================================================================
 * DASHBOARD — stats, backup health, and the suggestions/role-request queues
 * that need an admin's eyes, each with a one-click jump to its own section.
 * ===========================================================================*/
var STAT_LABELS = {
  people: 'People', families: 'Families', events: 'Events', sources: 'Sources',
  citations: 'Citations', photos: 'Photos', notes: 'Stories', places: 'Places',
  repositories: 'Repositories', users: 'Accounts',
};
var STAT_ORDER = ['people', 'families', 'events', 'photos', 'notes', 'sources',
  'citations', 'places', 'repositories', 'users'];

function initDashboardPage() {
  var page = document.getElementById('adminDashboardPage');
  if (!page) return;

  var statsEl = document.getElementById('adminStats');
  apiFetch('/api/stats').then(function(data) {
    var counts = data.counts || {};
    var items = STAT_ORDER.filter(function(k) { return k in counts; }).map(function(k) {
      return { n: counts[k], label: STAT_LABELS[k] || k };
    });
    items.push({ n: formatBytes(data.storage_bytes), label: 'Storage used' });
    statsEl.innerHTML = items.map(function(i) {
      return '<div class="stat-strip__item"><span class="stat-strip__n">' + i.n +
        '</span><span class="stat-strip__label">' + escapeHtml(i.label) + '</span></div>';
    }).join('');
  }).catch(function() {
    statsEl.innerHTML = '<p class="text-muted mb-0">Stats aren’t available right now.</p>';
  });

  var backupHealthEl = document.getElementById('adminBackupHealth');
  apiFetch('/api/admin/backups').then(function(data) {
    var freePct = (data.disk_free_bytes != null && data.disk_total_bytes) ?
      Math.round(100 * data.disk_free_bytes / data.disk_total_bytes) : null;
    backupHealthEl.innerHTML =
      '<div class="vitals-list">' +
        vitalsRow('Last backup', formatWhen(data.last_run) || 'Never') +
        vitalsRow('Next scheduled', data.schedule === 'off' ? 'Off — not scheduled' : (formatWhen(data.next_run) || '—')) +
        vitalsRow('Backups on disk', String((data.backups || []).length)) +
        vitalsRow('Disk free', freePct != null ? (formatBytes(data.disk_free_bytes) + ' (' + freePct + '%)') : '—') +
        vitalsRow('Off-site bucket', data.offsite_bucket || 'Not configured') +
      '</div>';
  }).catch(function() {
    backupHealthEl.innerHTML = '<p class="text-muted mb-0">Backup status isn’t available right now.</p>';
  });

  var suggestionsEl = document.getElementById('adminSuggestionsQueue');
  apiFetch('/api/suggestions?status=new').then(function(data) {
    var rows = data.suggestions || [];
    if (!rows.length) { suggestionsEl.innerHTML = '<p class="text-muted mb-0">Nothing new — the inbox is clear.</p>'; return; }
    suggestionsEl.innerHTML =
      '<p class="mb-2"><strong>' + rows.length + '</strong> new suggestion' + (rows.length === 1 ? '' : 's') + ' waiting for triage.</p>' +
      '<div class="list-group">' + rows.slice(0, 5).map(function(s) {
        return '<div class="list-group-item"><span class="badge text-bg-secondary me-1">' + escapeHtml(s.topic) + '</span>' +
          escapeHtml((s.body || '').slice(0, 80)) + (s.body && s.body.length > 80 ? '…' : '') +
          '<span class="text-muted small d-block">' + escapeHtml(s.author || 'A member') + ' · ' + escapeHtml(formatWhen(s.created_at) || '') + '</span></div>';
      }).join('') + '</div>';
  }).catch(function() {
    suggestionsEl.innerHTML = '<p class="text-muted mb-0">The inbox isn’t available right now.</p>';
  });

  var roleQueueEl = document.getElementById('adminRoleQueue');
  apiFetch('/api/role-requests?status=pending').then(function(data) {
    var rows = data.role_requests || [];
    if (!rows.length) { roleQueueEl.innerHTML = '<p class="text-muted mb-0">No pending role requests.</p>'; return; }
    roleQueueEl.innerHTML =
      '<p class="mb-2"><strong>' + rows.length + '</strong> pending request' + (rows.length === 1 ? '' : 's') + '.</p>' +
      '<div class="list-group">' + rows.slice(0, 5).map(function(r) {
        return '<div class="list-group-item">' + escapeHtml(r.user || 'A member') + ' requests <span class="badge text-bg-secondary">' +
          escapeHtml(ROLE_LABEL[r.requested_role] || r.requested_role) + '</span>' +
          '<span class="text-muted small d-block">' + escapeHtml(formatWhen(r.created_at) || '') + '</span></div>';
      }).join('') + '</div>';
  }).catch(function() {
    roleQueueEl.innerHTML = '<p class="text-muted mb-0">Role requests aren’t available right now.</p>';
  });
}

/* =============================================================================
 * USERS — every account, plus email-a-reset-link / secure change-email /
 * link-unlink-person actions, plus the read-only role→permission matrix.
 * ===========================================================================*/
function initUsersPage() {
  var page = document.getElementById('adminUsersPage');
  if (!page) return;

  var tbody = document.getElementById('adminUsersBody');
  var matrixEl = document.getElementById('adminPermMatrix');

  function statusBadges(u) {
    var badges = [];
    if (!u.is_active) badges.push('<span class="badge text-bg-warning">Inactive</span>');
    if (u.locked) badges.push('<span class="badge text-bg-danger">Locked</span>');
    badges.push(u.email_verified ?
      '<span class="badge text-bg-secondary">Verified</span>' :
      '<span class="badge text-bg-warning">Unverified</span>');
    return badges.join(' ');
  }

  function linkedCellHtml(u, personLabel) {
    if (!u.linked) return '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="link">Link to person…</button>';
    var label = personLabel || ('Person #' + u.individual_id);
    return '<a href="/people/' + u.individual_id + '">' + escapeHtml(label) + '</a> ' +
      '<button type="button" class="btn btn-outline-secondary btn-sm ms-1" data-action="unlink">Unlink</button>';
  }

  function rowHtml(u, personLabel) {
    return '<tr data-user-row="' + u.id + '">' +
      '<td>' + escapeHtml(u.display_name) + '</td>' +
      '<td><code>' + escapeHtml(u.email) + '</code></td>' +
      '<td><span class="badge ' + (ROLE_BADGE_CLASS[u.role] || 'text-bg-secondary') + '">' + escapeHtml(ROLE_LABEL[u.role] || u.role) + '</span></td>' +
      '<td data-linked-cell>' + linkedCellHtml(u, personLabel) + '</td>' +
      '<td>' + statusBadges(u) + '</td>' +
      '<td class="text-nowrap">' + (u.created_at ? new Date(u.created_at).toLocaleDateString() : '—') + '</td>' +
      '<td class="text-end text-nowrap">' +
        '<a class="btn btn-outline-secondary btn-sm" href="/admin/users/' + u.id + '/edit">Edit</a> ' +
        '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="reset">Reset link</button> ' +
        '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="change-email">Change email</button>' +
      '</td>' +
    '</tr>' +
    '<tr class="d-none" data-detail-row="' + u.id + '"><td colspan="7"><div class="inline-form-slot"></div></td></tr>';
  }

  function load() {
    apiFetch('/api/admin/users').then(function(data) {
      var users = data.users || [];
      var linkedUsers = users.filter(function(u) { return u.linked; });
      Promise.all(linkedUsers.map(function(u) {
        return apiFetch('/api/individuals/' + u.individual_id)
          .then(function(ind) { return [u.id, ind.primary_name]; })
          .catch(function() { return [u.id, null]; });
      })).then(function(pairs) {
        var names = {};
        pairs.forEach(function(p) { names[p[0]] = p[1]; });
        tbody.innerHTML = users.length ?
          users.map(function(u) { return rowHtml(u, names[u.id]); }).join('') :
          '<tr><td colspan="7" class="text-muted">No accounts yet.</td></tr>';
      });
    }).catch(function() {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted">Accounts aren’t available right now.</td></tr>';
    });
  }

  function detailSlot(id) {
    var row = tbody.querySelector('[data-detail-row="' + id + '"]');
    return row ? row.querySelector('.inline-form-slot') : null;
  }
  function openDetail(id) {
    var row = tbody.querySelector('[data-detail-row="' + id + '"]');
    if (row) row.classList.remove('d-none');
  }
  function closeDetail(id) {
    var row = tbody.querySelector('[data-detail-row="' + id + '"]');
    if (row) { row.classList.add('d-none'); row.querySelector('.inline-form-slot').innerHTML = ''; }
  }

  tbody.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var tr = btn.closest('tr[data-user-row]');
    var id = tr.dataset.userRow;
    var action = btn.dataset.action;

    if (action === 'reset') {
      btn.disabled = true;
      apiFetch('/api/admin/users/' + id + '/reset-password', { method: 'POST' }).then(function() {
        btn.textContent = 'Link sent ✓';
      }).catch(function(err) {
        btn.disabled = false;
        window.alert(err.message || 'Could not send the reset link.');
      });
      return;
    }

    if (action === 'change-email') {
      var slot = detailSlot(id);
      openDetail(id);
      toggleForm(slot,
        '<form class="row g-2 align-items-end">' +
          '<div class="col-sm-4"><label class="form-label">New email address</label>' +
            '<input type="email" class="form-control" name="new_email" required></div>' +
          '<div class="col-sm-4"><label class="form-label">Your current password (step-up)</label>' +
            '<input type="password" class="form-control" name="current_password" autocomplete="current-password" required></div>' +
          '<div class="col-sm-4">' +
            '<button type="submit" class="btn btn-primary btn-sm">Send Secure Change</button> ' +
            '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button>' +
          '</div>' +
        '</form>');
      slot.querySelector('[data-cancel-form]').addEventListener('click', function() { closeDetail(id); });
      slot.querySelector('form').addEventListener('submit', function(e2) {
        e2.preventDefault();
        var form = e2.target;
        apiFetch('/api/admin/users/' + id + '/change-email', { method: 'POST', body: {
          new_email: form.elements.new_email.value.trim(),
          current_password: form.elements.current_password.value,
        }}).then(function() {
          slot.innerHTML = '<p class="text-success mb-0">Email changed — a verification link and a forced password reset were emailed to the new address.</p>';
          load();
        }).catch(function(err) { alertFormError(form, err); });
      });
      return;
    }

    if (action === 'link') {
      var slot2 = detailSlot(id);
      openDetail(id);
      toggleForm(slot2, '<div class="subject-picker"></div>');
      subjectPicker(slot2.querySelector('.subject-picker'), function(type, pickedId) {
        apiFetch('/api/users/' + id + '/individual', { method: 'PUT', body: { individual_id: pickedId } })
          .then(function() { closeDetail(id); load(); })
          .catch(function(err) {
            showInlineError(slot2, err.status === 409 ?
              'That person is already linked to another account.' : (err.message || 'Could not link that person.'));
          });
      }, { types: ['individual'] });
      return;
    }

    if (action === 'unlink') {
      if (!window.confirm('Unlink this account from its person record?')) return;
      apiFetch('/api/users/' + id + '/individual', { method: 'DELETE' }).then(function() { load(); })
        .catch(function(err) { window.alert(err.message || 'Could not unlink.'); });
      return;
    }
  });

  load();

  /* --- Read-only permission matrix (§10) -------------------------------- */
  apiFetch('/api/permissions/matrix').then(function(data) {
    var perms = data.permissions || [];
    var matrix = data.matrix || {};
    var roleOrder = ['viewer', 'contributor', 'curator', 'admin'].filter(function(r) { return r in matrix; });
    var head = '<tr><th>Role</th>' + perms.map(function(p) { return '<th>' + escapeHtml(p) + '</th>'; }).join('') + '</tr>';
    var rows = roleOrder.map(function(r) {
      return '<tr><td><span class="badge ' + (ROLE_BADGE_CLASS[r] || 'text-bg-secondary') + '">' + escapeHtml(ROLE_LABEL[r] || r) + '</span></td>' +
        perms.map(function(p) { return '<td>' + (matrix[r][p] ? '✓' : '—') + '</td>'; }).join('') + '</tr>';
    }).join('');
    matrixEl.innerHTML = '<table class="table table-sm align-middle mb-0"><thead>' + head + '</thead><tbody>' + rows + '</tbody></table>';
  }).catch(function() {
    matrixEl.innerHTML = '<p class="text-muted mb-0">The permission matrix isn’t available right now.</p>';
  });
}

/* =============================================================================
 * SUGGESTIONS INBOX — filterable triage list; status/priority edits save
 * inline, per row (PUT /api/suggestions/{id}).
 * ===========================================================================*/
var SUGGESTION_STATUS_LABEL = { new: 'New', in_progress: 'In Progress', done: 'Done', declined: 'Declined' };
var SUGGESTION_STATUS_BADGE = {
  new: 'text-bg-warning', in_progress: 'text-bg-info',
  done: 'text-bg-secondary', declined: 'text-bg-light border',
};
var SUGGESTION_TOPIC_LABEL = { idea: 'Idea', bug: 'Bug', photo_request: 'Photo Request', other: 'Other' };

function initSuggestionsPage() {
  var page = document.getElementById('adminSuggestionsPage');
  if (!page) return;

  var listEl = document.getElementById('adminSuggestionsList');
  var statusChips = document.querySelectorAll('[data-chip-group="status"] .filter-chip');
  var topicChips = document.querySelectorAll('[data-chip-group="topic"] .filter-chip');
  var prioritizedChip = document.getElementById('adminPrioritizedChip');

  var state = { status: '', topic: '', prioritized: false };

  function rowHtml(s) {
    return '<div class="list-group-item">' +
      '<div class="d-flex justify-content-between flex-wrap gap-2">' +
        '<div><span class="badge text-bg-secondary me-1">' + escapeHtml(SUGGESTION_TOPIC_LABEL[s.topic] || s.topic) + '</span>' +
        '<span class="badge ' + (SUGGESTION_STATUS_BADGE[s.status] || 'text-bg-secondary') + '">' + escapeHtml(SUGGESTION_STATUS_LABEL[s.status] || s.status) + '</span>' +
        (s.priority != null ? ' <span class="badge text-bg-light border ms-1">Priority #' + s.priority + '</span>' : '') + '</div>' +
        '<span class="text-muted small">' + escapeHtml(s.author || 'A member') + ' · ' + escapeHtml(formatWhen(s.created_at) || '') + '</span>' +
      '</div>' +
      '<p class="mb-2 mt-2">' + escapeHtml(s.body) + '</p>' +
      '<form class="row g-2 align-items-end suggestion-triage-form" data-id="' + s.id + '">' +
        '<div class="col-auto"><label class="form-label">Status</label>' +
          '<select class="form-select form-select-sm" name="status">' +
            Object.keys(SUGGESTION_STATUS_LABEL).map(function(k) {
              return '<option value="' + k + '"' + (k === s.status ? ' selected' : '') + '>' + SUGGESTION_STATUS_LABEL[k] + '</option>';
            }).join('') +
          '</select></div>' +
        '<div class="col-auto"><label class="form-label">Priority</label>' +
          '<input type="number" class="form-control form-control-sm" name="priority" size="4" placeholder="none" value="' + (s.priority != null ? s.priority : '') + '"></div>' +
        '<div class="col-auto"><button type="submit" class="btn btn-primary btn-sm">Save</button> ' +
          '<span class="text-success small ms-1 d-none" data-saved>Saved &#10003;</span></div>' +
      '</form>' +
    '</div>';
  }

  function render() {
    listEl.innerHTML = '<p class="text-muted">Loading…</p>';
    var params = new URLSearchParams();
    if (state.status) params.set('status', state.status);
    if (state.topic) params.set('topic', state.topic);
    if (state.prioritized) params.set('prioritized', 'true');
    apiFetch('/api/suggestions?' + params.toString()).then(function(data) {
      var rows = data.suggestions || [];
      listEl.innerHTML = rows.length ? rows.map(rowHtml).join('') : '<p class="text-muted">No suggestions match these filters.</p>';
    }).catch(function() {
      listEl.innerHTML = '<p class="text-muted">The inbox isn’t available right now.</p>';
    });
  }

  listEl.addEventListener('submit', function(e) {
    var form = e.target.closest('.suggestion-triage-form');
    if (!form) return;
    e.preventDefault();
    var id = form.dataset.id;
    var priorityRaw = form.elements.priority.value;
    apiFetch('/api/suggestions/' + id, { method: 'PUT', body: {
      status: form.elements.status.value,
      priority: priorityRaw === '' ? null : parseInt(priorityRaw, 10),
    }}).then(function() {
      var saved = form.querySelector('[data-saved]');
      saved.classList.remove('d-none');
      setTimeout(function() { saved.classList.add('d-none'); }, 2000);
    }).catch(function(err) { alertFormError(form, err); });
  });

  function wireChipGroup(chips, key) {
    chips.forEach(function(chip) {
      chip.addEventListener('click', function() {
        chips.forEach(function(c) { c.classList.remove('is-active'); });
        chip.classList.add('is-active');
        state[key] = chip.dataset.value;
        render();
      });
    });
  }
  wireChipGroup(statusChips, 'status');
  wireChipGroup(topicChips, 'topic');
  prioritizedChip.addEventListener('click', function() {
    prioritizedChip.classList.toggle('is-active');
    state.prioritized = prioritizedChip.classList.contains('is-active');
    render();
  });

  render();
}

/* =============================================================================
 * ROLE REQUESTS — the pending queue (approve/deny) + decided history. One
 * unfiltered fetch (family-scale dataset, same "brute force is fine"
 * precedent as People's sort — FRONTEND_DESIGN.md), split client-side into
 * the two sections so the history chips don't need a second round trip.
 * ===========================================================================*/
function initRoleRequestsPage() {
  var page = document.getElementById('adminRoleRequestsPage');
  if (!page) return;

  var pendingEl = document.getElementById('adminPendingRoleRequests');
  var historyEl = document.getElementById('adminRoleHistory');
  var historyChips = document.querySelectorAll('[data-chip-group="history-status"] .filter-chip');
  var allRequests = [];
  var historyFilter = '';

  function pendingRowHtml(r) {
    return '<div class="list-group-item" data-request-row="' + r.id + '">' +
      '<div class="d-flex justify-content-between flex-wrap gap-2 align-items-center">' +
        '<span>' + escapeHtml(r.user || 'A member') + ' requests <span class="badge ' +
          (ROLE_BADGE_CLASS[r.requested_role] || 'text-bg-secondary') + '">' +
          escapeHtml(ROLE_LABEL[r.requested_role] || r.requested_role) + '</span>' +
        '<span class="text-muted small d-block">' + escapeHtml(formatWhen(r.created_at) || '') + '</span></span>' +
        '<div><button type="button" class="btn btn-primary btn-sm" data-action="approve">Approve</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="deny">Deny</button></div>' +
      '</div></div>';
  }
  function historyRowHtml(r) {
    var badge = r.status === 'approved' ? 'text-bg-secondary' : 'text-bg-light border';
    return '<div class="list-group-item">' +
      escapeHtml(r.user || 'A member') + ' requested <span class="badge ' +
        (ROLE_BADGE_CLASS[r.requested_role] || 'text-bg-secondary') + '">' +
        escapeHtml(ROLE_LABEL[r.requested_role] || r.requested_role) + '</span> ' +
      '<span class="badge ' + badge + '">' + (r.status === 'approved' ? 'Approved' : 'Denied') + '</span>' +
      '<span class="text-muted small d-block">by ' + escapeHtml(r.decided_by || 'an admin') +
        ' · ' + escapeHtml(formatWhen(r.decided_at) || '') + '</span></div>';
  }

  function renderPending() {
    var pending = allRequests.filter(function(r) { return r.status === 'pending'; });
    pendingEl.innerHTML = pending.length ? pending.map(pendingRowHtml).join('') :
      '<p class="text-muted mb-0">No pending requests.</p>';
  }
  function renderHistory() {
    var rows = allRequests.filter(function(r) {
      return r.status !== 'pending' && (!historyFilter || r.status === historyFilter);
    });
    historyEl.innerHTML = rows.length ? rows.map(historyRowHtml).join('') :
      '<p class="text-muted mb-0">No decided requests yet.</p>';
  }

  function load() {
    apiFetch('/api/role-requests').then(function(data) {
      allRequests = data.role_requests || [];
      renderPending();
      renderHistory();
    }).catch(function() {
      var msg = '<p class="text-muted mb-0">Role requests aren’t available right now.</p>';
      pendingEl.innerHTML = msg;
      historyEl.innerHTML = msg;
    });
  }

  pendingEl.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var row = btn.closest('[data-request-row]');
    var id = row.dataset.requestRow;
    var action = btn.dataset.action;
    if (action === 'approve' && !window.confirm('Approve this role change?')) return;
    if (action === 'deny' && !window.confirm('Deny this role request?')) return;
    btn.disabled = true;
    apiFetch('/api/role-requests/' + id + '/' + action, { method: 'POST' }).then(function() {
      load();
    }).catch(function(err) {
      btn.disabled = false;
      window.alert(err.message || 'Could not update that request.');
    });
  });

  historyChips.forEach(function(chip) {
    chip.addEventListener('click', function() {
      historyChips.forEach(function(c) { c.classList.remove('is-active'); });
      chip.classList.add('is-active');
      historyFilter = chip.dataset.value;
      renderHistory();
    });
  });

  load();
}

/* =============================================================================
 * SETTINGS (/admin/config) — the grouped config-as-data settings over
 * GET/PUT /api/settings. Four independent per-group forms (not one big form)
 * so a mistake in one group never blocks saving another — update_settings
 * (app/services/settings_service.py) applies a flat, partial {key: value}
 * patch and ignores keys it doesn't recognize, so PUT-ing just one group's
 * fields is a real, supported partial update, not a workaround.
 *
 * Fields marked "Reserved" below are real, persisted settings no v1 page
 * reads yet (verified: grepped the whole app for each key outside
 * settings_service.py itself) — editing them is honest (a real write to a
 * real column) even though nothing consumes them today; see
 * docs/FRONTEND_DESIGN.md's FE-6 entry.
 * ===========================================================================*/
var SETTINGS_GROUP_LABEL = { branding: 'Branding', security: 'Security', email: 'Email', defaults: 'Defaults' };
var SETTINGS_FIELD_SPECS = {
  branding: [
    { key: 'site_name', label: 'Site name', type: 'text' },
    { key: 'family_name', label: 'Family name (used instead of Site name when set)', type: 'text' },
    { key: 'logo_path', label: 'Logo path', type: 'text', hint: 'Reserved — no page renders a logo from this setting yet.' },
  ],
  defaults: [
    { key: 'default_timezone', label: 'Site default timezone', type: 'text',
      hint: 'IANA zone name, e.g. America/Chicago — used for any member who hasn’t set their own.' },
    { key: 'tree_orientation', label: 'Tree orientation', type: 'select', options: ['vertical', 'horizontal'],
      hint: 'Horizontal is a reserved seam — the Tree page renders vertical only today regardless of this setting.' },
    { key: 'date_format', label: 'Date format', type: 'select', options: ['original', 'iso'], hint: 'Reserved — not yet consumed by any page.' },
    { key: 'place_format', label: 'Place format', type: 'select', options: ['full', 'short'], hint: 'Reserved — not yet consumed by any page.' },
    { key: 'new_record_privacy', label: 'Default privacy for new records', type: 'select', options: ['living', 'public'],
      hint: 'Reserved — not yet consumed by any page.' },
  ],
  security: [
    { key: 'min_password_length', label: 'Minimum password length', type: 'number', min: 6 },
    { key: 'breach_check_enabled', label: 'Check new passwords against known breaches', type: 'checkbox' },
    { key: 'login_lockout_threshold', label: 'Failed logins before lockout', type: 'number', min: 1 },
    { key: 'session_timeout_days', label: 'Session timeout (days)', type: 'number', min: 1 },
  ],
  email: [
    { key: 'smtp_host', label: 'SMTP host', type: 'text' },
    { key: 'smtp_port', label: 'SMTP port', type: 'number' },
    { key: 'smtp_user', label: 'SMTP username', type: 'text' },
    { key: 'smtp_from', label: 'From address', type: 'text' },
  ],
};

function settingsFieldHtml(spec, value) {
  var id = 'cfg_' + spec.key;
  var hint = spec.hint ? '<p class="form-text mb-1">' + escapeHtml(spec.hint) + '</p>' : '';
  if (spec.type === 'checkbox') {
    return '<div class="mb-3 form-check">' +
      '<input type="checkbox" class="form-check-input" id="' + id + '" name="' + spec.key + '"' + (value ? ' checked' : '') + '>' +
      '<label class="form-check-label" for="' + id + '">' + escapeHtml(spec.label) + '</label>' + hint + '</div>';
  }
  if (spec.type === 'select') {
    return '<div class="mb-3"><label class="form-label" for="' + id + '">' + escapeHtml(spec.label) + '</label>' +
      '<select class="form-select" id="' + id + '" name="' + spec.key + '">' +
      spec.options.map(function(o) { return '<option value="' + o + '"' + (o === value ? ' selected' : '') + '>' + o + '</option>'; }).join('') +
      '</select>' + hint + '</div>';
  }
  return '<div class="mb-3"><label class="form-label" for="' + id + '">' + escapeHtml(spec.label) + '</label>' +
    '<input type="' + (spec.type === 'number' ? 'number' : 'text') + '" class="form-control" id="' + id + '" name="' + spec.key + '"' +
    (spec.min != null ? ' min="' + spec.min + '"' : '') + ' value="' + escapeHtml(value != null ? value : '') + '">' + hint + '</div>';
}

function settingsGroupFormHtml(group, values) {
  var specs = SETTINGS_FIELD_SPECS[group];
  return '<form class="settings-group-form" data-group="' + group + '">' +
    specs.map(function(spec) { return settingsFieldHtml(spec, values[spec.key]); }).join('') +
    '<div class="alert alert-danger d-none" role="alert"></div>' +
    '<button type="submit" class="btn btn-primary btn-sm">Save ' + SETTINGS_GROUP_LABEL[group] + '</button> ' +
    '<span class="text-success small ms-1 d-none" data-saved>Saved &#10003;</span>' +
  '</form>';
}

function initConfigPage() {
  var page = document.getElementById('adminConfigPage');
  if (!page) return;

  var containers = {
    branding: document.getElementById('cfgBranding'),
    defaults: document.getElementById('cfgDefaults'),
    security: document.getElementById('cfgSecurity'),
    email: document.getElementById('cfgEmail'),
  };

  function load() {
    apiFetch('/api/settings').then(function(data) {
      Object.keys(containers).forEach(function(group) {
        containers[group].innerHTML = settingsGroupFormHtml(group, data[group] || {});
      });
    }).catch(function() {
      Object.keys(containers).forEach(function(group) {
        containers[group].innerHTML = '<p class="text-muted mb-0">Settings aren’t available right now.</p>';
      });
    });
  }

  page.addEventListener('submit', function(e) {
    var form = e.target.closest('.settings-group-form');
    if (!form) return;
    e.preventDefault();
    var group = form.dataset.group;
    var specs = SETTINGS_FIELD_SPECS[group];
    var body = {};
    specs.forEach(function(spec) {
      var el = form.elements[spec.key];
      body[spec.key] = spec.type === 'checkbox' ? el.checked : el.value;
    });
    var errBox = form.querySelector('.alert-danger');
    errBox.classList.add('d-none');
    specs.forEach(function(spec) { form.elements[spec.key].classList.remove('is-invalid'); });

    apiFetch('/api/settings', { method: 'PUT', body: body }).then(function() {
      var saved = form.querySelector('[data-saved]');
      saved.classList.remove('d-none');
      setTimeout(function() { saved.classList.add('d-none'); }, 2000);
    }).catch(function(err) {
      // update_settings' ValueError messages consistently start with the
      // exact key name ("min_password_length must be…") — this endpoint has
      // no structured `fields` in its 400 body, so this is a safe, honest
      // heuristic for per-field highlighting, not a fabricated contract the
      // API doesn't actually send (docs/FRONTEND_DESIGN.md's FE-6 entry).
      var msg = err.message || 'Could not save these settings.';
      var match = /^([a-z_]+)\s/.exec(msg);
      var field = match && form.elements[match[1]] ? match[1] : null;
      if (field) { form.elements[field].classList.add('is-invalid'); form.elements[field].focus(); }
      errBox.textContent = msg;
      errBox.classList.remove('d-none');
    });
  });

  load();
}

/* =============================================================================
 * BACKUPS — overview, back-up-now with its verification report, the
 * schedule editor, and the guarded restore (the gravest action in the app).
 * Downloading a zip stays a plain <a href> to the existing
 * admin.download_backup route — a file download needs no JSON round trip.
 * ===========================================================================*/
function initBackupsPage() {
  var page = document.getElementById('adminBackupsPage');
  if (!page) return;

  var overviewEl = document.getElementById('bkOverview');
  var scheduleEl = document.getElementById('bkSchedule');
  var listBody = document.getElementById('bkListBody');
  var restoreArea = document.getElementById('bkRestoreArea');
  var runBtn = document.getElementById('bkRunBtn');
  var runReport = document.getElementById('bkRunReport');

  function renderOverview(data) {
    var freePct = (data.disk_free_bytes != null && data.disk_total_bytes) ?
      Math.round(100 * data.disk_free_bytes / data.disk_total_bytes) : null;
    overviewEl.innerHTML = '<div class="vitals-list">' +
      vitalsRow('Storage location', data.storage_location) +
      vitalsRow('Off-site bucket', data.offsite_bucket || 'Not configured') +
      vitalsRow('Disk free', freePct != null ?
        (formatBytes(data.disk_free_bytes) + ' of ' + formatBytes(data.disk_total_bytes) + ' (' + freePct + '%)') : '—') +
      vitalsRow('Last backup', formatWhen(data.last_run) || 'Never') +
      vitalsRow('Next scheduled', data.schedule === 'off' ? 'Off — not scheduled' : (formatWhen(data.next_run) || '—')) +
    '</div>';
  }

  function renderSchedule(data) {
    scheduleEl.innerHTML =
      '<form id="bkScheduleForm" class="row g-2 align-items-end">' +
        '<div class="col-auto"><label class="form-label">Frequency</label>' +
          '<select class="form-select" name="schedule">' +
            ['off', 'daily', 'weekly'].map(function(s) {
              return '<option value="' + s + '"' + (s === data.schedule ? ' selected' : '') + '>' +
                s.charAt(0).toUpperCase() + s.slice(1) + '</option>';
            }).join('') +
          '</select></div>' +
        '<div class="col-auto"><label class="form-label">Hour (server time, 0-23)</label>' +
          '<input type="number" class="form-control" name="hour" min="0" max="23" value="' + data.schedule_hour + '"></div>' +
        '<div class="col-auto"><button type="submit" class="btn btn-primary btn-sm">Save Schedule</button> ' +
          '<span class="text-success small ms-1 d-none" data-saved>Saved &#10003;</span></div>' +
      '</form>';
    document.getElementById('bkScheduleForm').addEventListener('submit', function(e) {
      e.preventDefault();
      var form = e.target;
      apiFetch('/api/admin/backups/schedule', { method: 'PUT', body: {
        schedule: form.elements.schedule.value,
        hour: parseInt(form.elements.hour.value, 10),
      }}).then(function(data2) {
        var saved = form.querySelector('[data-saved]');
        saved.classList.remove('d-none');
        setTimeout(function() { saved.classList.add('d-none'); }, 2000);
        renderOverview(data2);
      }).catch(function(err) { alertFormError(form, err); });
    });
  }

  function renderList(backups) {
    listBody.innerHTML = backups.length ? backups.map(function(b) {
      return '<tr><td><code>' + escapeHtml(b.filename) + '</code></td>' +
        '<td>' + escapeHtml(formatWhen(b.created_at) || '') + '</td>' +
        '<td>' + formatBytes(b.bytes) + '</td>' +
        '<td class="text-end"><a class="btn btn-outline-secondary btn-sm" href="/admin/backups/' +
          encodeURIComponent(b.filename) + '/download">&#8681; Download</a></td></tr>';
    }).join('') : '<tr><td colspan="4" class="text-muted">No backups yet — press “Back Up Now” to make the first one.</td></tr>';
  }

  function renderRestoreArea(backups) {
    if (!backups.length) {
      restoreArea.innerHTML = '<p class="text-muted mb-0">No backups exist yet to restore from.</p>';
      return;
    }
    restoreArea.innerHTML =
      '<form id="bkRestoreForm">' +
        '<div class="mb-2"><label class="form-label" for="bkRestoreFile">Backup to restore</label>' +
          '<select class="form-select" id="bkRestoreFile" name="filename">' +
            backups.map(function(b) {
              return '<option value="' + escapeHtml(b.filename) + '">' + escapeHtml(b.filename) +
                ' (' + escapeHtml(formatWhen(b.created_at) || '') + ')</option>';
            }).join('') +
          '</select></div>' +
        '<div class="mb-2"><label class="form-label" for="bkRestorePw">Your current password (step-up)</label>' +
          '<input type="password" class="form-control" id="bkRestorePw" name="current_password" autocomplete="current-password" required></div>' +
        '<div class="mb-2 form-check">' +
          '<input type="checkbox" class="form-check-input" id="bkRestoreConfirm" name="confirm" required>' +
          '<label class="form-check-label" for="bkRestoreConfirm">I understand this overwrites the live database and files, and cannot be undone except by restoring again.</label>' +
        '</div>' +
        '<div class="alert alert-danger d-none" role="alert"></div>' +
        '<button type="submit" class="btn btn-danger">Restore This Backup</button>' +
      '</form>';
    document.getElementById('bkRestoreForm').addEventListener('submit', function(e) {
      e.preventDefault();
      var form = e.target;
      if (!form.elements.confirm.checked) return;
      if (!window.confirm('This will overwrite the live database and every uploaded file. Continue?')) return;
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      apiFetch('/api/admin/backups/restore', { method: 'POST', body: {
        filename: form.elements.filename.value,
        current_password: form.elements.current_password.value,
        confirm: true,
      }}).then(function(result) {
        form.outerHTML = '<p class="text-success mb-0">Restored ' + escapeHtml(result.restored) +
          ' — a safety backup of the prior state was saved as <code>' + escapeHtml(result.safety_backup) + '</code>.</p>';
        load({ skipRestoreArea: true });
      }).catch(function(err) {
        btn.disabled = false;
        alertFormError(form, err);
      });
    });
  }

  // skipRestoreArea: after a successful restore, the restore area shows a
  // one-time "Restored ✓ — safety backup saved as …" confirmation in place of
  // the form; a full load() re-render would silently overwrite that message
  // with a fresh form before the admin ever saw it (found in browser testing,
  // not by pytest, which never renders this page's live DOM).
  function load(opts) {
    opts = opts || {};
    apiFetch('/api/admin/backups').then(function(data) {
      renderOverview(data);
      renderSchedule(data);
      renderList(data.backups || []);
      if (!opts.skipRestoreArea) renderRestoreArea(data.backups || []);
    }).catch(function() {
      var msg = '<p class="text-muted mb-0">Backups aren’t available right now.</p>';
      overviewEl.innerHTML = msg; scheduleEl.innerHTML = msg;
      if (!opts.skipRestoreArea) restoreArea.innerHTML = msg;
      listBody.innerHTML = '<tr><td colspan="4" class="text-muted">Backups aren’t available right now.</td></tr>';
    });
  }

  runBtn.addEventListener('click', function() {
    runBtn.disabled = true;
    runReport.innerHTML = '<p class="text-muted mb-0">Creating and verifying…</p>';
    apiFetch('/api/admin/backups/run', { method: 'POST' }).then(function(result) {
      runBtn.disabled = false;
      var report = result.report || {};
      if (result.ok) {
        runReport.innerHTML = '<p class="text-success mb-1">Backup created and verified — ' +
          report.db_tables + ' DB table(s), ' + report.file_count + ' uploaded file(s).</p>' +
          '<p class="text-muted small mb-0">' + escapeHtml(result.upload_message || '') + '</p>';
      } else {
        runReport.innerHTML = '<p class="text-danger mb-0">Backup FAILED verification: ' +
          escapeHtml((report.problems || []).join('; ')) + '</p>';
      }
      load();
    }).catch(function(err) {
      runBtn.disabled = false;
      runReport.innerHTML = '<p class="text-danger mb-0">' + escapeHtml(err.message || 'Could not run a backup.') + '</p>';
    });
  });

  load();
}

/* =============================================================================
 * ACTIVITY (Curator+) — the full audit trail: paginated, filterable, with a
 * per-entry Revert (undo THIS specific change) or Restore (un-delete a
 * currently-soft-deleted subject) — one contextual action per row, not both,
 * to avoid two buttons that would do near-identical things on a delete row.
 * The actor filter is Admin-only (see the template's data-is-admin note).
 * ===========================================================================*/
var ACTIVITY_ACTION_LABEL = { create: 'Added', update: 'Edited', delete: 'Deleted', restore: 'Restored', revert: 'Reverted' };
var ACTIVITY_SUBJECT_LABEL = {
  individual: 'Person', name: 'Name', family: 'Family', event: 'Event',
  source: 'Source', citation: 'Citation', media: 'Photo', note: 'Story',
  family_child: 'Parent/child link', user: 'Account', backup: 'Backup',
};
var ACTIVITY_REVERTIBLE_TYPES = ['individual', 'name', 'family', 'event', 'source', 'citation', 'media', 'note'];

function initActivityPage() {
  var page = document.getElementById('adminActivityPage');
  if (!page) return;

  var isAdmin = page.dataset.isAdmin === 'true';
  var listEl = document.getElementById('activityList');
  var paginationEl = document.getElementById('activityPagination');
  var actionChips = document.querySelectorAll('[data-chip-group="action"] .filter-chip');
  var subjectChips = document.querySelectorAll('[data-chip-group="subject_type"] .filter-chip');
  var actorWrap = document.getElementById('activityActorFilterWrap');
  var actorSelect = document.getElementById('activityActorFilter');
  var dateFrom = document.getElementById('activityDateFrom');
  var dateTo = document.getElementById('activityDateTo');

  var state = { action: '', subject_type: '', actor_id: '', date_from: '', date_to: '', page: 1, perPage: 25 };
  var resolveCache = {};

  if (isAdmin) {
    actorWrap.classList.remove('d-none');
    apiFetch('/api/admin/users').then(function(data) {
      (data.users || []).forEach(function(u) {
        var opt = document.createElement('option');
        opt.value = u.id; opt.textContent = u.display_name;
        actorSelect.appendChild(opt);
      });
    }).catch(function() { /* leave "Anyone"-only — never block the rest of the page on this */ });
    actorSelect.addEventListener('change', function() {
      state.actor_id = actorSelect.value; state.page = 1; render();
    });
  }

  function resolveSubject(type, id) {
    var key = type + ':' + id;
    if (resolveCache[key]) return resolveCache[key];
    var promise;
    if (id == null) {
      promise = Promise.resolve({ label: ACTIVITY_SUBJECT_LABEL[type] || type, href: null });
    } else if (type === 'individual') {
      promise = apiFetch('/api/individuals/' + id)
        .then(function(ind) { return { label: ind.primary_name || 'Unnamed person', href: '/people/' + id }; })
        .catch(function() { return { label: 'a person', href: null, removed: true }; });
    } else if (type === 'family') {
      promise = apiFetch('/api/families/' + id)
        .then(function(f) { return { label: [f.partner1, f.partner2].filter(Boolean).join(' & ') || 'a family', href: '/tree/family/' + id }; })
        .catch(function() { return { label: 'a family', href: null, removed: true }; });
    } else if (type === 'media') {
      promise = apiFetch('/api/media/' + id)
        .then(function(m) { return { label: m.title || 'Untitled photo', href: '/memories?photo=' + id }; })
        .catch(function() { return { label: 'a photo', href: null, removed: true }; });
    } else if (type === 'note') {
      promise = apiFetch('/api/notes/' + id)
        .then(function(n) { return { label: n.title || 'Untitled story', href: '/memories/stories/' + id }; })
        .catch(function() { return { label: 'a story', href: null, removed: true }; });
    } else if (type === 'event') {
      promise = apiFetch('/api/events/' + id)
        .then(function(ev) {
          var href = ev.subject_type === 'family' ? '/tree/family/' + ev.subject_id :
            ev.subject_type === 'individual' ? '/people/' + ev.subject_id : null;
          return { label: tagLabel(ev.event_tag) + (ev.subject_label ? ': ' + ev.subject_label : ''), href: href };
        })
        .catch(function() { return { label: 'an event', href: null, removed: true }; });
    } else {
      promise = Promise.resolve({ label: ACTIVITY_SUBJECT_LABEL[type] || type, href: null });
    }
    resolveCache[key] = promise;
    return promise;
  }

  function actionButtonHtml(entry) {
    if (ACTIVITY_REVERTIBLE_TYPES.indexOf(entry.subject_type) === -1) return '';
    if (entry.action === 'delete') {
      return '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="restore" data-subject-type="' +
        entry.subject_type + '" data-subject-id="' + entry.subject_id + '">Restore</button>';
    }
    return '<button type="button" class="btn btn-outline-secondary btn-sm" data-action="revert" data-audit-id="' + entry.id +
      '" data-subject-type="' + entry.subject_type + '" data-subject-id="' + entry.subject_id + '">Revert</button>';
  }

  function rowHtml(entry, subject) {
    var when = new Date(entry.created_at).toLocaleString();
    var verb = ACTIVITY_ACTION_LABEL[entry.action] || entry.action;
    var subjectText = subject.removed ? escapeHtml(subject.label) + ' <span class="text-muted">(since removed)</span>' :
      (subject.href ? '<a href="' + subject.href + '">' + escapeHtml(subject.label) + '</a>' : escapeHtml(subject.label));
    return '<div class="list-group-item d-flex justify-content-between flex-wrap gap-2 align-items-center">' +
      '<span><span class="badge text-bg-secondary me-1">' + escapeHtml(verb) + '</span>' + subjectText +
        (entry.actor ? ' <span class="text-muted">— ' + escapeHtml(entry.actor) + '</span>' : '') +
        '<span class="text-muted small d-block">' + escapeHtml(when) + (entry.detail ? ' · ' + escapeHtml(entry.detail) : '') + '</span></span>' +
      '<span>' + actionButtonHtml(entry) + '</span>' +
    '</div>';
  }

  function renderPagination(data) {
    if (data.total <= data.per_page) { paginationEl.innerHTML = ''; return; }
    paginationEl.innerHTML =
      '<button type="button" class="btn btn-outline-secondary btn-sm" id="activityPrev"' + (data.page <= 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
      '<span class="text-muted small">Page ' + data.page + ' of ' + data.pages + '</span>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" id="activityNext"' + (data.page >= data.pages ? ' disabled' : '') + '>Next &rarr;</button>';
    var prevBtn = document.getElementById('activityPrev');
    var nextBtn = document.getElementById('activityNext');
    if (prevBtn) prevBtn.addEventListener('click', function() { state.page--; render(); });
    if (nextBtn) nextBtn.addEventListener('click', function() { state.page++; render(); });
  }

  function render() {
    listEl.innerHTML = '<p class="text-muted">Loading…</p>';
    var params = new URLSearchParams();
    if (state.action) params.set('action', state.action);
    if (state.subject_type) params.set('subject_type', state.subject_type);
    if (state.actor_id) params.set('actor_id', state.actor_id);
    if (state.date_from) params.set('date_from', state.date_from);
    if (state.date_to) params.set('date_to', state.date_to);
    params.set('page', state.page);
    params.set('per_page', state.perPage);

    apiFetch('/api/activity?' + params.toString()).then(function(data) {
      var rows = data.activity || [];
      if (!rows.length) {
        listEl.innerHTML = '<p class="text-muted">No activity matches these filters.</p>';
        paginationEl.innerHTML = '';
        return;
      }
      Promise.all(rows.map(function(entry) {
        return resolveSubject(entry.subject_type, entry.subject_id).then(function(subject) { return rowHtml(entry, subject); });
      })).then(function(htmls) { listEl.innerHTML = htmls.join(''); });
      renderPagination(data);
    }).catch(function() {
      listEl.innerHTML = '<p class="text-muted">Activity isn’t available right now.</p>';
      paginationEl.innerHTML = '';
    });
  }

  listEl.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var action = btn.dataset.action;
    if (action === 'revert') {
      if (!window.confirm('Undo this change? You can revert it again later if needed.')) return;
      btn.disabled = true;
      apiFetch('/api/audit/' + btn.dataset.auditId + '/revert', { method: 'POST' }).then(function() {
        // The row's subject may have just been un-deleted (or re-deleted) by
        // this revert — a cached "(since removed)" resolution from an
        // earlier render would otherwise keep showing stale, found in
        // browser testing (pytest never renders this page's live DOM).
        delete resolveCache[btn.dataset.subjectType + ':' + btn.dataset.subjectId];
        render();
      }).catch(function(err) { btn.disabled = false; window.alert(err.message || 'Could not revert that change.'); });
    } else if (action === 'restore') {
      if (!window.confirm('Restore this deleted record?')) return;
      btn.disabled = true;
      apiFetch('/api/restore', { method: 'POST', body: {
        subject_type: btn.dataset.subjectType, subject_id: parseInt(btn.dataset.subjectId, 10),
      }}).then(function() {
        delete resolveCache[btn.dataset.subjectType + ':' + btn.dataset.subjectId];
        render();
      }).catch(function(err) { btn.disabled = false; window.alert(err.message || 'Could not restore that record.'); });
    }
  });

  function wireChipGroup(chips, key) {
    chips.forEach(function(chip) {
      chip.addEventListener('click', function() {
        chips.forEach(function(c) { c.classList.remove('is-active'); });
        chip.classList.add('is-active');
        state[key] = chip.dataset.value;
        state.page = 1;
        render();
      });
    });
  }
  wireChipGroup(actionChips, 'action');
  wireChipGroup(subjectChips, 'subject_type');
  dateFrom.addEventListener('change', function() { state.date_from = dateFrom.value; state.page = 1; render(); });
  dateTo.addEventListener('change', function() { state.date_to = dateTo.value; state.page = 1; render(); });

  render();
}

document.addEventListener('DOMContentLoaded', function() {
  initDashboardPage();
  initUsersPage();
  initSuggestionsPage();
  initRoleRequestsPage();
  initConfigPage();
  initBackupsPage();
  initActivityPage();
});
