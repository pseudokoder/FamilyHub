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

THE FUN FEATURE — [[wikilinks]]: typing [[Grandma Jo]] in any memory, bio,
or comment-free text field turns into a link to Grandma Jo's wiki page,
exactly like linking works on Wikipedia. If no page with that name exists
(yet!), the name renders as plain text — never an error, never a broken
link. CLAUDE.md asks for blog posts "linkable to wiki entries"; this is how.
"""

import re

from flask import url_for
from markupsafe import Markup, escape

# [[ anything that isn't brackets ]]  — non-greedy and bracket-free inside,
# so "[[Jo]] and [[Bob]]" finds two links, not one giant one.
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _linkify(raw):
    """Escape raw text and replace [[Name]] with a wiki link.

    ORDER MATTERS: we escape each PIECE of user text individually and only
    then weave in our own <a> tags. Escaping the finished HTML would break
    our links; not escaping the user text would invite XSS. Walk the string
    once, keep the two kinds of content separate.
    """
    from app.services import wiki_service  # imported here: avoids circular import

    parts = []
    cursor = 0
    for match in WIKILINK_RE.finditer(raw):
        parts.append(str(escape(raw[cursor:match.start()])))
        name = match.group(1).strip()
        member = wiki_service.find_by_name(name)
        if member:
            href = url_for("wiki.view_member", member_id=member.id)
            parts.append(f'<a href="{href}">{escape(name)}</a>')
        else:
            # No page by that name (yet) — show the name, drop the brackets.
            parts.append(str(escape(name)))
        cursor = match.end()
    parts.append(str(escape(raw[cursor:])))
    return "".join(parts)


def family_text(raw):
    """Render user-typed text as safe paragraphs with [[wikilinks]].

    Blank line  -> new paragraph     (how everyone naturally types)
    Single \\n  -> line break <br>

    WHY not Markdown or a rich-text editor? Elderly-first: the parents type
    into a big plain box exactly like an email, and it comes out right.
    No toolbar to learn, no syntax to remember, nothing to get "wrong".
    """
    if not raw:
        return Markup("")
    safe = _linkify(raw.strip())
    paragraphs = [
        "<p>" + p.strip().replace("\n", "<br>") + "</p>"
        for p in re.split(r"\r?\n\s*\r?\n", safe)
        if p.strip()
    ]
    return Markup("".join(paragraphs))
