/* api.js — the one place every authenticated page talks to the WP2 JSON API
 * (docs/openapi.yaml). Vanilla JS, CSP-safe (no inline scripts anywhere —
 * this file is loaded via <script src>, same pattern as chronicle.js).
 *
 * WHY A SHARED HELPER: every state-changing call (POST/PUT/DELETE) needs the
 * X-CSRFToken header (base.html prints the token into a <meta> tag once per
 * page); every call needs `credentials: 'same-origin'` so the session cookie
 * rides along. Repeating that in every page's JS invites the one place you
 * forget it turning into a silent 400/403. One function, used everywhere.
 *
 * -> WGU: JavaScript Programming (D280), Security (D315 — CSRF defense),
 *    Back-End (D286+ — this is the same fetch() a v2 Angular HttpClient
 *    interceptor would attach the token from).
 */
'use strict';

/* apiFetch(url, options) -> Promise<any parsed JSON, or null for 204>
 * Throws an Error whose `.data` carries the API's {error, fields} body,
 * so callers can show field-level messages instead of a generic failure. */
function apiFetch(url, options) {
  options = options || {};
  var method = (options.method || 'GET').toUpperCase();
  var headers = Object.assign({}, options.headers || {});

  // Only attach the CSRF header on state-changing verbs — GET is read-only
  // and CSRFProtect doesn't check it, matching Flask-WTF's own rule.
  if (method !== 'GET' && method !== 'HEAD') {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) headers['X-CSRFToken'] = meta.getAttribute('content');
  }
  // JSON bodies (multipart/form-data uploads set their own Content-Type and
  // must NOT set this one, so callers pass a FormData body without headers).
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    if (typeof options.body !== 'string') {
      options = Object.assign({}, options, { body: JSON.stringify(options.body) });
    }
  }

  return fetch(url, Object.assign({ credentials: 'same-origin' }, options, { method: method, headers: headers }))
    .then(function(response) {
      if (response.status === 204) return null;
      return response.json().catch(function() { return null; }).then(function(data) {
        if (!response.ok) {
          var err = new Error((data && data.error) || ('Request failed (' + response.status + ')'));
          err.status = response.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
}

/* Small formatting helpers shared by home.js / people.js. */
var FamilyHubFmt = {
  /* "Rosa Vega" + 1951 + 2019 (living=false)  ->  "1951–2019"
   * "Sofía Rivera" + 1989 + null (living=true) -> "b. 1989" */
  lifespan: function(birthYear, deathYear, living) {
    if (!birthYear && !deathYear) return living ? 'living' : '';
    if (living) return birthYear ? ('b. ' + birthYear) : '';
    return (birthYear || '?') + '–' + (deathYear || '?');
  },
  /* Joins non-empty parts with a middle dot, the separator used everywhere
   * a person row shows name + dates + place (matches the Chronicle style). */
  joinDot: function(parts) {
    return parts.filter(function(p) { return p; }).join(' · ');
  },
};
