"""Tests for the family_text filter — small, but it guards an XSS boundary.

The headline assertion: a "<script>" typed into admin text comes out ESCAPED,
never as a live tag. The CSP is one layer of XSS defense; this escaping is the
other, and a test pins it so a future "improvement" can't quietly remove it.
"""

from app.services.text_service import family_text


def test_escapes_html_so_it_cannot_execute():
    out = str(family_text("Hello <script>alert('x')</script> & friends"))
    assert "<script>" not in out          # the dangerous tag is gone...
    assert "&lt;script&gt;" in out        # ...shown as harmless text instead
    assert "&amp; friends" in out         # ampersand escaped too


def test_paragraphs_and_line_breaks():
    out = str(family_text("Line one\nline two\n\nSecond paragraph"))
    # Blank line starts a new paragraph; single newline is a <br>.
    assert out.count("<p>") == 2
    assert "Line one<br>line two" in out


def test_blank_input_is_empty():
    assert str(family_text("")) == ""
    assert str(family_text(None)) == ""
