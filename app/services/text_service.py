"""text_service — turn admin-entered plain text into safe, tidy HTML.

USED BY: the `family_text` Jinja filter (registered in the app factory), which
the About page pipes its admin-written text through:  {{ about_text | family_text }}

WHY A SERVICE FOR THIS? Two reasons, both about safety:
  1. ESCAPING. Admin text could contain "<", "&", or a stray "<script>". We
     escape every character that has meaning in HTML so the text is *shown*,
     never *executed*. This is the server-side half of XSS defense (the CSP in
     the app factory is the other half — defense in depth, D315).
  2. ONE place to evolve. Today it's escape-and-paragraph. When WP2 adds
     Markdown rendering for memories/bios, the upgrade happens here, behind the
     same filter name, and every caller benefits at once.

NOTE: the old version of this file also auto-linked [[Name]] mentions to wiki
pages. That depended on the now-removed wiki feature; WP2 reintroduces rich
rendering against the GEDCOM-7 schema. This trimmed version is intentionally
dependency-free so the preserved About page keeps working during the rebuild.

v2 mapping: a small TextService (or a Thymeleaf utility) doing the same escape.
"""

from markupsafe import Markup, escape


def family_text(text):
    """Render admin/free text as safe HTML: escape everything, then honor
    paragraph breaks (blank line → new <p>) and line breaks (single newline →
    <br>). Returns a Markup object so Jinja prints it as HTML, not as escaped
    source — safe because WE did the escaping first."""
    if not text:
        return Markup("")
    # Normalize Windows/Mac newlines so the split below is reliable.
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [block for block in normalized.split("\n\n") if block.strip()]
    rendered = []
    for block in paragraphs:
        # escape() makes each line safe; the <br> between lines is OUR markup.
        # The `Markup("…") % safe` form is the key trick: markupsafe substitutes
        # an already-safe value WITHOUT re-escaping it, while leaving our literal
        # <p>/<br> tags intact. (Plain string concatenation would let markupsafe
        # escape our own tags — a subtle gotcha worth knowing.)
        safe_lines = Markup("<br>").join(escape(line) for line in block.split("\n"))
        rendered.append(Markup("<p>%s</p>") % safe_lines)
    return Markup("").join(rendered)
