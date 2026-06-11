"""Turning what the family TYPES into safe HTML the browser shows.

THE SECURITY PROBLEM (D315): if we drop user text straight into a page as
HTML, anyone who types <script>...</script> in a comment is now running
JavaScript in everyone else's browser — Cross-Site Scripting (XSS), the #1
web vulnerability. Jinja auto-escapes template variables, but the moment WE
build HTML strings ourselves (paragraphs, links), escaping becomes OUR job.

The deal this module makes: it takes RAW text, escapes every character the
user typed, and only adds HTML tags that *we* wrote. The result is wrapped
in Markup(), which tells Jinja "this is safe, don't double-escape it."

Used as a Jinja filter:   {{ post.body | family_text }}
"""

import re

from markupsafe import Markup, escape


def family_text(raw):
    """Render user-typed text as safe paragraphs.

    Blank line  -> new paragraph     (how everyone naturally types)
    Single \\n  -> line break <br>

    WHY not Markdown or a rich-text editor? Elderly-first: the parents type
    into a big plain box exactly like an email, and it comes out right.
    No toolbar to learn, no syntax to remember, nothing to get "wrong".
    """
    if not raw:
        return Markup("")
    safe = str(escape(raw.strip()))
    paragraphs = [
        "<p>" + p.strip().replace("\n", "<br>") + "</p>"
        for p in re.split(r"\r?\n\s*\r?\n", safe)
        if p.strip()
    ]
    return Markup("".join(paragraphs))
