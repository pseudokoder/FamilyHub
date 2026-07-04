/* home.js — the Home page (Master Plan §4, WP4 Piece 2). Wires the three
 * empty containers dashboard.html renders to the JSON API: GET /api/stats,
 * /api/on-this-day, and (only when the container exists — see dashboard.html's
 * Curator+ gate) /api/activity. Vanilla JS, CSP-safe (no inline scripts —
 * every dynamic value is set via textContent/className, never innerHTML of
 * untrusted strings; see escapeHtml below for the one spot that DOES build
 * markup from server data).
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+ — same fetch()
 *    contract a v2 Angular HomeComponent would call).
 */
'use strict';

/* Family/person/place text comes from the database (a member typed it), so
 * anywhere it's inserted as HTML it must be escaped — the textbook stored-XSS
 * lesson (D315). Every render function below builds strings with this. */
function escapeHtml(value) {
  var div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {

  /* --- STAT STRIP ----------------------------------------------------- */
  var statStrip = document.getElementById('statStrip');
  if (statStrip) {
    apiFetch('/api/stats').then(function(data) {
      var counts = data.counts || {};
      // "The motivating subset only" (WP4 brief) — people + photos, not the
      // full admin dashboard's every-table breakdown.
      var items = [
        { n: counts.people || 0, label: 'people' },
        { n: counts.photos || 0, label: 'photos' },
        { n: counts.notes || 0, label: 'stories' },
      ];
      statStrip.innerHTML = items.map(function(i) {
        return '<div class="stat-strip__item">' +
          '<span class="stat-strip__n">' + i.n + '</span>' +
          '<span class="stat-strip__label">' + escapeHtml(i.label) + '</span>' +
        '</div>';
      }).join('');
      statStrip.removeAttribute('data-loading');
    }).catch(function() {
      statStrip.innerHTML = '<p class="text-muted small mb-0">Stats aren’t available right now.</p>';
    });
  }

  /* --- ON THIS DAY ------------------------------------------------------
   * Warm tone: births celebratory, marriages a milestone, deaths a gentle
   * remembrance — never a flat "3 events matched" list (WP4 brief). */
  var onThisDay = document.getElementById('onThisDay');
  if (onThisDay) {
    apiFetch('/api/on-this-day').then(function(data) {
      var year = new Date().getFullYear();
      var rows = [];

      (data.births || []).forEach(function(a) {
        var age = a.year ? (year - a.year) : null;
        rows.push(otdRow('🎉', escapeHtml(a.who || 'A family member') +
          (age != null ? ' turns <b>' + age + '</b> today!' : '’s birthday is today!'),
          a.place));
      });
      (data.marriages || []).forEach(function(a) {
        var years = a.year ? (year - a.year) : null;
        rows.push(otdRow('💍', escapeHtml(a.who || 'A family couple') +
          (years != null ? ' — married <b>' + years + '</b> years ago today.' : ' were married on this day.'),
          a.place));
      });
      (data.deaths || []).forEach(function(a) {
        rows.push(otdRow('🕊️', 'In loving memory of ' + escapeHtml(a.who || 'a family member') +
          (a.year ? ' <span class="text-muted">(' + a.year + ')</span>' : ''),
          a.place));
      });

      onThisDay.innerHTML = rows.length ? rows.join('') :
        '<p class="text-muted">No family milestones fall on today’s date — check back tomorrow.</p>';
      onThisDay.removeAttribute('data-loading');
    }).catch(function() {
      onThisDay.innerHTML = '<p class="text-muted">Today’s family history isn’t available right now.</p>';
    });
  }

  function otdRow(icon, htmlText, place) {
    return '<div class="on-this-day__row">' +
      '<span class="on-this-day__icon" aria-hidden="true">' + icon + '</span>' +
      '<span>' + htmlText + (place ? ' <span class="text-muted">· ' + escapeHtml(place) + '</span>' : '') + '</span>' +
    '</div>';
  }

  /* --- RECENT ACTIVITY ---------------------------------------------------
   * WP5 (BLOCKERS.md 2026-07-03, RESOLVED): GET /api/activity/feed is a
   * friendly, ALL-MEMBERS view over the same audit_log table — safe creates
   * only (new people/photos/stories), never deletes/reverts/account actions
   * — and the backend already returns a pre-formatted sentence per row
   * ("Jane added a photo: Family reunion 1962"), so there's no verb/noun
   * mapping to do here anymore; this is just render + escape. The fuller
   * Curator+ audit trail (GET /api/activity) is a separate, untouched view
   * for a future Activity/audit page. */
  var recentActivity = document.getElementById('recentActivity');
  if (recentActivity) {
    apiFetch('/api/activity/feed?limit=10').then(function(data) {
      var rows = (data.activity || []).map(function(entry) {
        return '<div class="list-group-item">' +
          '<span>' + escapeHtml(entry.text) + '</span>' +
          '<span class="text-muted small d-block">' + escapeHtml(new Date(entry.created_at).toLocaleString()) + '</span>' +
        '</div>';
      });
      recentActivity.innerHTML = rows.length ? rows.join('') :
        '<p class="text-muted">Nothing new yet.</p>';
      recentActivity.removeAttribute('data-loading');
    }).catch(function() {
      recentActivity.innerHTML = '<p class="text-muted">Recent activity isn’t available right now.</p>';
    });
  }

});
