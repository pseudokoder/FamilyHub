"""Unit tests for text_service — the smallest, fastest kind of test.

TEACHING NOTE: the other test files are INTEGRATION tests (whole requests
through routes, services, models, templates). These are UNIT tests: one
function, called directly, edge cases enumerated. Pure-logic modules like
text rendering deserve this treatment — each case is one line to write and
microseconds to run (D480: the test pyramid).
"""

from app.services.text_service import family_text


def test_empty_and_none(app):
    assert str(family_text("")) == ""
    assert str(family_text(None)) == ""


def test_paragraphs_and_linebreaks(app):
    html = str(family_text("Line one\nLine two\n\nNew paragraph"))
    assert html == "<p>Line one<br>Line two</p><p>New paragraph</p>"


def test_html_is_escaped(app):
    html = str(family_text('<b onmouseover="evil()">hi</b>'))
    assert "<b" not in html
    assert "&lt;b" in html


def test_unknown_wikilink_renders_plain(app):
    html = str(family_text("Ask [[Nobody Known]] about it"))
    assert "Nobody Known" in html
    assert "<a" not in html
    assert "[[" not in html  # brackets dropped, text kept


def test_wikilink_with_special_chars_is_safe(app, admin_client):
    """A name like O'Brien & Sons must neither break the link nor sneak
    HTML through the escaping."""
    admin_client.post(
        "/family/new",
        data={"name": "Jo O'Brien & Co", "location": "", "bio": "",
              "birth_date": "", "death_date": ""},
    )
    # family_text calls url_for internally, which requires a request context.
    # In production this is always the case (Jinja filter during a request);
    # in unit tests we push one explicitly.
    with app.test_request_context("/"):
        html = str(family_text("Talk to [[Jo O'Brien & Co]] first"))
    assert "<a href=" in html
    assert "&amp; Co" in html  # ampersand escaped inside the link text


def test_windows_line_endings(app):
    """The parents' machines send \\r\\n — paragraphs must still split."""
    html = str(family_text("One\r\n\r\nTwo"))
    assert html == "<p>One</p><p>Two</p>"
