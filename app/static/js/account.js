/* account.js — the Account area (FE-5, Master Plan §5): My Contributions +
 * Account & Security. Two independent pages, each DOM-guarded so this one
 * file safely covers both templates (same no-op-if-absent pattern as every
 * other page script in this app — chronicle.js/person.js/tree.js/memories.js).
 *
 * Depends on api.js (apiFetch) and fh-common.js (escapeHtml, debounce,
 * tagLabel, toggleForm/hideForm, alertFormError) — both loaded on every
 * authenticated page by base.html, so no extra <script> tag is needed for
 * those.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315).
 */
'use strict';

/* =============================================================================
 * TIMEZONE PICKER — the Profile section's searchable IANA-zone select.
 * `Intl.supportedValuesOf('timeZone')` is the browser's OWN copy of the same
 * IANA database `zoneinfo.available_timezones()` validates against
 * server-side (account_service.update_me) — no bundled zone list to keep in
 * sync. Older browsers without that API (Safari <15.4) fall back to a short,
 * hand-picked list rather than leaving the field with nothing to search.
 * ===========================================================================*/
var FALLBACK_TIMEZONES = [
  'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Anchorage', 'America/Phoenix', 'America/Sao_Paulo', 'America/Mexico_City',
  'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Madrid', 'Europe/Rome',
  'Europe/Moscow', 'Africa/Cairo', 'Africa/Johannesburg', 'Asia/Jerusalem', 'Asia/Dubai',
  'Asia/Kolkata', 'Asia/Shanghai', 'Asia/Tokyo', 'Asia/Seoul', 'Asia/Singapore',
  'Australia/Sydney', 'Australia/Perth', 'Pacific/Auckland', 'Pacific/Honolulu',
];
var _tzListCache = null;
function timezoneList() {
  if (_tzListCache) return _tzListCache;
  try {
    if (typeof Intl !== 'undefined' && typeof Intl.supportedValuesOf === 'function') {
      _tzListCache = Intl.supportedValuesOf('timeZone');
      return _tzListCache;
    }
  } catch (e) { /* fall through to the fallback list below */ }
  _tzListCache = FALLBACK_TIMEZONES;
  return _tzListCache;
}

/* =============================================================================
 * ACCOUNT & SECURITY — Profile / Role / Email / Password / Delete.
 * Five calm, independently-rendered sections over ONE GET /api/me snapshot
 * (Password is a static link-out, no fetch needed).
 * ===========================================================================*/
var ROLE_BADGE_CLASS = {
  admin: 'text-bg-primary', curator: 'text-bg-info',
  contributor: 'text-bg-secondary', viewer: 'text-bg-light border',
};
var ROLE_LABEL = { viewer: 'Viewer', contributor: 'Contributor', curator: 'Curator', admin: 'Admin' };
var ROLE_ORDER = ['viewer', 'contributor', 'curator', 'admin'];

function initSecurityPage() {
  var page = document.getElementById('accountSecurityPage');
  if (!page) return;

  var profileBody = document.getElementById('acctProfileBody');
  var roleBody = document.getElementById('acctRoleBody');
  var emailBody = document.getElementById('acctEmailBody');
  var deleteBody = document.getElementById('acctDeleteBody');

  /* --- PROFILE ------------------------------------------------------------- */
  function renderProfile(me) {
    profileBody.innerHTML =
      '<form id="acctProfileForm">' +
        '<div class="mb-3"><label class="form-label" for="acctDisplayName">Display name</label>' +
          '<input type="text" class="form-control" id="acctDisplayName" name="display_name" ' +
            'value="' + escapeHtml(me.display_name) + '" autocomplete="name" required maxlength="120"></div>' +
        '<div class="mb-2">' +
          '<label class="form-label d-block" for="tzSearchInput">Timezone</label>' +
          '<div class="chip-group mb-2"><button type="button" class="filter-chip' + (me.timezone ? '' : ' is-active') + '" id="tzSiteDefaultChip">Site default</button></div>' +
          '<input type="text" class="form-control" id="tzSearchInput" placeholder="Search timezones (e.g. America/Chicago)…" autocomplete="off">' +
          '<div class="list-group subject-picker__results" id="tzResults"></div>' +
          '<p class="form-text mb-0" id="tzCurrentLabel">Currently: ' + escapeHtml(me.timezone || 'Site default') + '</p>' +
        '</div>' +
        '<button type="submit" class="btn btn-primary mt-2">Save Profile</button>' +
        '<span class="text-success small ms-2 d-none" id="acctProfileSaved">Saved.</span>' +
      '</form>';

    var tzValue = me.timezone || '';
    var form = document.getElementById('acctProfileForm');
    var siteDefaultChip = document.getElementById('tzSiteDefaultChip');
    var tzInput = document.getElementById('tzSearchInput');
    var tzResults = document.getElementById('tzResults');
    var tzLabel = document.getElementById('tzCurrentLabel');

    function setTz(value) {
      tzValue = value || '';
      siteDefaultChip.classList.toggle('is-active', !tzValue);
      tzLabel.textContent = 'Currently: ' + (tzValue || 'Site default');
      tzResults.innerHTML = '';
      tzInput.value = '';
    }
    siteDefaultChip.addEventListener('click', function() { setTz(''); });
    tzInput.addEventListener('input', debounce(function() {
      var q = tzInput.value.trim().toLowerCase();
      if (!q) { tzResults.innerHTML = ''; return; }
      var matches = timezoneList().filter(function(z) {
        return z.toLowerCase().indexOf(q) !== -1;
      }).slice(0, 25);
      tzResults.innerHTML = matches.length ? matches.map(function(z) {
        return '<button type="button" class="list-group-item list-group-item-action" data-tz="' + escapeHtml(z) + '">' +
          escapeHtml(z.replace(/_/g, ' ')) + '</button>';
      }).join('') : '<p class="text-muted small mb-0 p-2">No matching timezone.</p>';
    }, 200));
    tzResults.addEventListener('click', function(e) {
      var btn = e.target.closest('[data-tz]');
      if (btn) setTz(btn.dataset.tz);
    });

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      var name = form.elements.display_name.value.trim();
      apiFetch('/api/me', { method: 'PUT', body: { display_name: name, timezone: tzValue || null } })
        .then(function() {
          var saved = document.getElementById('acctProfileSaved');
          if (!saved) return;
          saved.classList.remove('d-none');
          setTimeout(function() { saved.classList.add('d-none'); }, 2500);
        })
        .catch(function(err) { alertFormError(form, err); });
    });
  }

  /* --- ROLE ------------------------------------------------------------------ */
  function renderRole(me) {
    var badgeClass = ROLE_BADGE_CLASS[me.role] || 'text-bg-secondary';
    var badgeLabel = ROLE_LABEL[me.role] || me.role;
    roleBody.innerHTML =
      '<p class="mb-2">You are currently a <span class="badge ' + badgeClass + '">' + escapeHtml(badgeLabel) + '</span>.</p>' +
      '<button type="button" class="btn btn-outline-secondary" id="acctRequestRoleBtn">Request a Role Change</button>' +
      '<div id="acctRoleForm" class="d-none inline-form-slot mt-2"></div>';

    var reqBtn = document.getElementById('acctRequestRoleBtn');
    var slot = document.getElementById('acctRoleForm');
    reqBtn.addEventListener('click', function() {
      var options = ROLE_ORDER.filter(function(r) { return r !== me.role; })
        .map(function(r) { return '<option value="' + r + '">' + ROLE_LABEL[r] + '</option>'; }).join('');
      toggleForm(slot,
        '<form id="acctRoleRequestForm">' +
          '<label class="form-label" for="acctRoleSelect">Requested role</label>' +
          '<select class="form-select mb-2" id="acctRoleSelect" name="requested_role">' + options + '</select>' +
          '<button type="submit" class="btn btn-primary btn-sm">Submit Request</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button>' +
        '</form>');
      slot.querySelector('[data-cancel-form]').addEventListener('click', function() { hideForm(slot); });
      slot.querySelector('#acctRoleRequestForm').addEventListener('submit', function(e) {
        e.preventDefault();
        var role = document.getElementById('acctRoleSelect').value;
        apiFetch('/api/role-requests', { method: 'POST', body: { requested_role: role } })
          .then(function() {
            slot.innerHTML = '<p class="text-success mb-0">Request submitted — an admin will review it soon.</p>';
          })
          .catch(function(err) {
            if (err.status === 409) {
              slot.innerHTML = '<p class="text-muted mb-0">You already have a pending role request — an admin will review it soon.</p>';
            } else {
              alertFormError(e.target, err);
            }
          });
      });
    });
  }

  /* --- EMAIL -------------------------------------------------------------- *
   * The pending (unverified) address, if any, comes straight from
   * GET /api/me's `pending_email` field. */
  function renderEmail(me) {
    var verified = !!me.email_verified_at;
    emailBody.innerHTML =
      '<p class="mb-1">' + escapeHtml(me.email) +
        (verified ? ' <span class="badge text-bg-secondary">Verified</span>' : ' <span class="badge text-bg-warning">Unverified</span>') +
      '</p>' +
      (me.pending_email ? '<p class="text-muted mb-2">Pending: check your inbox at <strong>' + escapeHtml(me.pending_email) + '</strong> to confirm your new address.</p>' : '') +
      (verified ? '' : '<div class="mb-2" id="acctResendVerifyWrap"><button type="button" class="btn btn-outline-secondary btn-sm" id="acctResendVerifyBtn">Resend Verification Email</button></div>') +
      '<div><button type="button" class="btn btn-outline-secondary btn-sm" id="acctChangeEmailBtn">Change Email</button></div>' +
      '<div id="acctChangeEmailForm" class="d-none inline-form-slot mt-2"></div>';

    var resendBtn = document.getElementById('acctResendVerifyBtn');
    if (resendBtn) resendBtn.addEventListener('click', function() {
      resendBtn.disabled = true;
      apiFetch('/api/me/verify-email', { method: 'POST' }).then(function(res) {
        resendBtn.outerHTML = '<p class="text-muted mb-0">' +
          (res.status === 'already_verified' ? 'Already verified.' : 'Verification email sent — check your inbox.') + '</p>';
      }).catch(function(err) {
        resendBtn.disabled = false;
        showInlineError(document.getElementById('acctResendVerifyWrap'),
          err.message || 'Could not send the verification email.');
      });
    });

    var changeBtn = document.getElementById('acctChangeEmailBtn');
    var slot = document.getElementById('acctChangeEmailForm');
    changeBtn.addEventListener('click', function() {
      toggleForm(slot,
        '<form id="acctChangeEmailFormEl">' +
          '<div class="mb-2"><label class="form-label" for="acctNewEmail">New email address</label>' +
            '<input type="email" class="form-control" id="acctNewEmail" name="new_email" autocomplete="email" required></div>' +
          '<div class="mb-2"><label class="form-label" for="acctChangeEmailPw">Your current password</label>' +
            '<input type="password" class="form-control" id="acctChangeEmailPw" name="current_password" autocomplete="current-password" required></div>' +
          '<button type="submit" class="btn btn-primary btn-sm">Send Verification Link</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button>' +
        '</form>');
      slot.querySelector('[data-cancel-form]').addEventListener('click', function() { hideForm(slot); });
      slot.querySelector('#acctChangeEmailFormEl').addEventListener('submit', function(e) {
        e.preventDefault();
        var form = e.target;
        apiFetch('/api/me/change-email', { method: 'POST', body: {
          new_email: form.elements.new_email.value.trim(),
          current_password: form.elements.current_password.value,
        }}).then(function() {
          hideForm(slot);
          return apiFetch('/api/me');
        }).then(function(freshMe) { renderEmail(freshMe); })
          .catch(function(err) { alertFormError(form, err); });
      });
    });
  }

  /* --- DELETE ACCOUNT ------------------------------------------------------ */
  function renderDelete() {
    deleteBody.innerHTML =
      '<p class="mb-2">Deleting your account removes your ability to sign in and replaces your ' +
        'name with a neutral placeholder. Every contribution you’ve made and the family tree ' +
        'itself are kept exactly as they are — nothing is erased.</p>' +
      '<button type="button" class="btn btn-outline-danger" id="acctDeleteBtn">Delete My Account…</button>' +
      '<div id="acctDeleteForm" class="d-none inline-form-slot mt-2"></div>';

    var btn = document.getElementById('acctDeleteBtn');
    var slot = document.getElementById('acctDeleteForm');
    btn.addEventListener('click', function() {
      toggleForm(slot,
        '<p class="mb-2"><strong>This can’t be undone.</strong> Your sign-in will be removed, your ' +
          'name will be replaced with "Former member," and everything you’ve contributed stays in ' +
          'the family archive under that name.</p>' +
        '<form id="acctDeleteFormEl">' +
          '<div class="mb-2"><label class="form-label" for="acctDeletePw">Your current password</label>' +
            '<input type="password" class="form-control" id="acctDeletePw" name="current_password" autocomplete="current-password" required></div>' +
          '<button type="submit" class="btn btn-danger btn-sm">Delete My Account</button> ' +
          '<button type="button" class="btn btn-outline-secondary btn-sm" data-cancel-form>Cancel</button>' +
        '</form>');
      slot.querySelector('[data-cancel-form]').addEventListener('click', function() { hideForm(slot); });
      slot.querySelector('#acctDeleteFormEl').addEventListener('submit', function(e) {
        e.preventDefault();
        var form = e.target;
        if (!window.confirm('Delete your account? This can’t be undone.')) return;
        apiFetch('/api/me/delete', { method: 'POST', body: { current_password: form.elements.current_password.value } })
          .then(function() {
            slot.innerHTML = '<p class="mb-0">Your account has been deleted — signing you out…</p>';
            setTimeout(function() { window.location.href = '/'; }, 1500);
          })
          .catch(function(err) { alertFormError(form, err); });
      });
    });
  }

  apiFetch('/api/me').then(function(me) {
    renderProfile(me);
    renderRole(me);
    renderEmail(me);
    renderDelete();
  }).catch(function() {
    var msg = '<p class="text-muted mb-0">This isn’t available right now.</p>';
    profileBody.innerHTML = roleBody.innerHTML = emailBody.innerHTML = deleteBody.innerHTML = msg;
  });
}

/* =============================================================================
 * MY CONTRIBUTIONS — summary cards + a paginated, filterable list of the
 * caller's OWN audit rows (GET /api/me/contributions — no actor_id parameter
 * anywhere in this file; that would be a side door into the Curator-only
 * /api/activity trail).
 * ===========================================================================*/
var CONTRIB_SUBJECT_LABEL = {
  individual: 'Person', name: 'Name', family: 'Family', event: 'Event',
  source: 'Source', citation: 'Citation', media: 'Photo', note: 'Story',
  family_child: 'Parent/child link', user: 'Account', backup: 'Backup',
};
var CONTRIB_ACTION_LABEL = {
  create: 'Added', update: 'Edited', delete: 'Deleted', restore: 'Restored', revert: 'Reverted',
};
/* Header-card grouping (FE-5 brief: "your grouping call, but every count
 * must come from the real summary, no derived guesses") — every number below
 * is a straight sum of real by_subject_type buckets the API returned, just
 * relabeled/combined for a friendlier card than a raw subject_type string. */
var CONTRIB_SUMMARY_GROUPS = [
  { label: 'People', types: ['individual', 'name'] },
  { label: 'Families', types: ['family'] },
  { label: 'Events', types: ['event'] },
  { label: 'Photos', types: ['media'] },
  { label: 'Stories', types: ['note'] },
  { label: 'Sources', types: ['source', 'citation'] },
];

function initContributionsPage() {
  var page = document.getElementById('myContributionsPage');
  if (!page) return;

  var summaryEl = document.getElementById('contribSummary');
  var listEl = document.getElementById('contribList');
  var paginationEl = document.getElementById('contribPagination');
  var actionChips = document.querySelectorAll('[data-chip-group="action"] .filter-chip');
  var subjectChips = document.querySelectorAll('[data-chip-group="subject_type"] .filter-chip');

  var state = { action: '', subject_type: '', page: 1, perPage: 20 };
  var resolveCache = {}; // "type:id" -> Promise<{label, href, removed}>

  function resolveSubject(type, id) {
    var key = type + ':' + id;
    if (resolveCache[key]) return resolveCache[key];
    var promise;
    if (id == null) {
      promise = Promise.resolve({ label: CONTRIB_SUBJECT_LABEL[type] || type, href: null });
    } else if (type === 'individual') {
      promise = apiFetch('/api/individuals/' + id)
        .then(function(ind) { return { label: ind.primary_name || 'Unnamed person', href: '/people/' + id }; })
        .catch(function() { return { label: 'a person', href: null, removed: true }; });
    } else if (type === 'family') {
      promise = apiFetch('/api/families/' + id)
        .then(function(f) {
          var label = [f.partner1, f.partner2].filter(Boolean).join(' & ');
          return { label: label || 'a family', href: '/tree/family/' + id };
        })
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
      // An event has no page of its own — it resolves to the EVENT'S OWN
      // subject (a person or family), same idea fh-common.js's
      // resolveLinkTarget uses for a photo/story's "linked to" chips.
      promise = apiFetch('/api/events/' + id)
        .then(function(ev) {
          var href = ev.subject_type === 'family' ? '/tree/family/' + ev.subject_id :
            ev.subject_type === 'individual' ? '/people/' + ev.subject_id : null;
          var label = tagLabel(ev.event_tag) + (ev.subject_label ? ': ' + ev.subject_label : '');
          return { label: label, href: href };
        })
        .catch(function() { return { label: 'an event', href: null, removed: true }; });
    } else {
      // No page exists for this subject type (source/citation/name/user/
      // backup/family_child) — name it, don't fake a link.
      promise = Promise.resolve({ label: CONTRIB_SUBJECT_LABEL[type] || type, href: null });
    }
    resolveCache[key] = promise;
    return promise;
  }

  function contribRowHtml(entry, subject) {
    var when = new Date(entry.created_at).toLocaleString();
    var verb = CONTRIB_ACTION_LABEL[entry.action] || entry.action;
    var subjectText = subject.removed ? escapeHtml(subject.label) + ' <span class="text-muted">(since removed)</span>' :
      (subject.href ? '<a href="' + subject.href + '">' + escapeHtml(subject.label) + '</a>' : escapeHtml(subject.label));
    return '<div class="list-group-item">' +
      '<span class="badge text-bg-secondary me-1">' + escapeHtml(verb) + '</span>' +
      '<span>' + subjectText + '</span>' +
      '<span class="text-muted small d-block">' + escapeHtml(when) + '</span>' +
    '</div>';
  }

  function renderSummary(summary, everContributed) {
    if (!everContributed) { summaryEl.classList.add('d-none'); summaryEl.innerHTML = ''; return; }
    summaryEl.classList.remove('d-none');
    var byType = summary.by_subject_type || {};
    var byAction = summary.by_action || {};
    var total = Object.keys(byAction).reduce(function(sum, k) { return sum + byAction[k]; }, 0);
    var cards = [{ label: 'Total contributions', n: total }].concat(
      CONTRIB_SUMMARY_GROUPS.map(function(g) {
        return { label: g.label, n: g.types.reduce(function(sum, t) { return sum + (byType[t] || 0); }, 0) };
      }).filter(function(c) { return c.n > 0; })
    );
    summaryEl.innerHTML = cards.map(function(c) {
      return '<div class="stat-strip__item"><span class="stat-strip__n">' + c.n + '</span><span class="stat-strip__label">' + escapeHtml(c.label) + '</span></div>';
    }).join('');
  }

  function renderPagination(data) {
    if (data.total <= data.per_page) { paginationEl.innerHTML = ''; return; }
    paginationEl.innerHTML =
      '<button type="button" class="btn btn-outline-secondary btn-sm" id="contribPrev"' + (data.page <= 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
      '<span class="text-muted small">Page ' + data.page + ' of ' + data.pages + '</span>' +
      '<button type="button" class="btn btn-outline-secondary btn-sm" id="contribNext"' + (data.page >= data.pages ? ' disabled' : '') + '>Next &rarr;</button>';
    var prevBtn = document.getElementById('contribPrev');
    var nextBtn = document.getElementById('contribNext');
    if (prevBtn) prevBtn.addEventListener('click', function() { state.page--; render(); });
    if (nextBtn) nextBtn.addEventListener('click', function() { state.page++; render(); });
  }

  function render() {
    listEl.innerHTML = '<p class="text-muted">Loading…</p>';
    var params = new URLSearchParams();
    if (state.action) params.set('action', state.action);
    if (state.subject_type) params.set('subject_type', state.subject_type);
    params.set('page', state.page);
    params.set('per_page', state.perPage);

    apiFetch('/api/me/contributions?' + params.toString()).then(function(data) {
      var everContributed = Object.keys((data.summary && data.summary.by_action) || {}).length > 0;
      renderSummary(data.summary || {}, everContributed);

      if (!everContributed) {
        listEl.innerHTML = '<div class="list-group-item"><p class="mb-2">You haven’t added anything yet.</p>' +
          '<a class="btn btn-primary btn-sm" href="/">Start with Quick Add</a></div>';
        paginationEl.innerHTML = '';
        return;
      }

      var rows = data.activity || [];
      if (rows.length === 0) {
        listEl.innerHTML = '<p class="text-muted">No contributions match these filters.</p>';
      } else {
        Promise.all(rows.map(function(entry) {
          return resolveSubject(entry.subject_type, entry.subject_id).then(function(subject) {
            return contribRowHtml(entry, subject);
          });
        })).then(function(htmls) { listEl.innerHTML = htmls.join(''); });
      }
      renderPagination(data);
    }).catch(function() {
      listEl.innerHTML = '<p class="text-muted">Contributions aren’t available right now.</p>';
      summaryEl.classList.add('d-none');
    });
  }

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

  render();
}

document.addEventListener('DOMContentLoaded', function() {
  initSecurityPage();
  initContributionsPage();
});
