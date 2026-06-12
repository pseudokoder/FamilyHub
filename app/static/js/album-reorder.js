/* Drag-to-rearrange for album pages.
 *
 * TEACHING NOTE: this is "progressive enhancement" — the page is fully
 * usable with JavaScript off (photos just stay in their saved order), and
 * this script ADDS the drag behavior when it can. Notice there's no
 * framework here: find the grid, hand it to SortableJS (vendored locally
 * in static/js/vendor — same no-CDN rule as Bootstrap), and after every
 * drop, POST the new order as JSON.
 *
 * The CSRF token rides in the X-CSRFToken HEADER because fetch() has no
 * HTML form to carry the hidden field — Flask-WTF checks headers too.
 */
document.addEventListener("DOMContentLoaded", function () {
    var grid = document.getElementById("photoGrid");
    if (!grid || typeof Sortable === "undefined") {
        return; // not an album page, or the library failed to load
    }
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var statusNote = document.getElementById("reorderStatus");

    function showStatus(text, isError) {
        if (!statusNote) return;
        statusNote.textContent = text;
        statusNote.className = isError ? "text-danger" : "text-success";
    }

    new Sortable(grid, {
        animation: 150,          // photos glide instead of teleporting
        ghostClass: "drag-ghost", // see style.css — shows where it will land
        // Elderly-friendly touch behavior: a TAP still opens the photo;
        // dragging starts only after a 150 ms press-and-hold.
        delay: 150,
        delayOnTouchOnly: true,

        onEnd: function () {
            var ids = Array.prototype.map.call(
                grid.querySelectorAll("[data-photo-id]"),
                function (el) { return parseInt(el.dataset.photoId, 10); }
            );
            fetch(grid.dataset.reorderUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfMeta ? csrfMeta.content : ""
                },
                body: JSON.stringify({ order: ids })
            })
                .then(function (response) {
                    if (!response.ok) { throw new Error("save failed"); }
                    showStatus("✓ New order saved", false);
                })
                .catch(function () {
                    showStatus("Couldn't save the new order — refresh and try again.", true);
                });
        }
    });
});
