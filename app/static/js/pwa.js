/* Register the service worker (progressive enhancement: browsers
 * without support — or with it disabled — just run the plain site).
 * Registered at /sw.js, NOT /static/js/sw.js: a worker may only control
 * pages within its own path, so controlling "/" means serving from "/".
 */
if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/sw.js");
    });
}
