/* FamilyHub's service worker — deliberately small.
 *
 * TEACHING NOTE: a service worker is a script the browser keeps AFTER
 * the tab closes; it sits between the page and the network and may
 * answer requests from a local cache. That's what lets "Add to Home
 * Screen" feel like a real app. Ours does exactly two jobs:
 *
 *   1. Cache the STATIC SHELL (css, js, icons) — instant loads, and the
 *      offline page can render with styling.
 *   2. When a page NAVIGATION fails (no signal at the cabin), show the
 *      friendly /offline page instead of the browser's dinosaur.
 *
 * What it deliberately does NOT do: cache family photos or pages.
 * Photos are login-walled PII — parking them in a device cache would
 * outlive the login session. Privacy beats offline galleries.
 *
 * CACHE versioning: bump the name to ship changes; activate() deletes
 * old caches so stale shells can't linger.
 */
var CACHE = "familyhub-shell-v1";
var SHELL = [
    "/offline",
    "/static/css/style.css",
    "/static/icons/icon-192.png"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE)
            .then(function (cache) { return cache.addAll(SHELL); })
            .then(function () { return self.skipWaiting(); })
    );
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.filter(function (key) {
                return key !== CACHE;
            }).map(function (key) { return caches.delete(key); }));
        }).then(function () { return self.clients.claim(); })
    );
});

self.addEventListener("fetch", function (event) {
    var request = event.request;
    if (request.method !== "GET") { return; }           // never touch POSTs
    var url = new URL(request.url);
    if (url.origin !== location.origin) { return; }     // our origin only

    // Static files: cache-first (they're fingerprint-stable enough at
    // family scale; the cache version bump is the refresh lever).
    if (url.pathname.indexOf("/static/") === 0) {
        event.respondWith(
            caches.open(CACHE).then(function (cache) {
                return cache.match(request).then(function (hit) {
                    return hit || fetch(request).then(function (response) {
                        // Only cache complete responses — partial/range responses
                        // (206) cannot be stored and throw if you try.
                        if (response.status === 200) {
                            cache.put(request, response.clone());
                        }
                        return response;
                    });
                });
            })
        );
        return;
    }

    // Page navigations: network-first, friendly page when there isn't one.
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request)["catch"](function () {
                return caches.match("/offline");
            })
        );
    }
    // Everything else (photo bytes, JSON) goes straight to the network.
});
