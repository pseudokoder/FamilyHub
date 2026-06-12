/* FamilyHub's site-wide JavaScript. Small on purpose.
 *
 * CONFIRMATION DIALOGS, the CSP-friendly way (DEVDIARY Ch. 19): forms
 * used to carry onsubmit="return confirm('...')" attributes. Inline
 * JavaScript like that is exactly what a Content-Security-Policy is
 * designed to block — the browser can't tell OUR inline code from code an
 * attacker smuggled in, so the policy bans both. The fix: each form now
 * carries a plain data-confirm="message" attribute (data, not code), and
 * this ONE listener does the asking.
 *
 * TEACHING NOTE — event delegation: we listen on the whole document
 * instead of wiring each form. Forms added by future templates get the
 * behavior for free, just by having the attribute.
 */
document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.hasAttribute && form.hasAttribute("data-confirm")) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
            event.preventDefault(); // they pressed Cancel — nothing happens
        }
    }
});
