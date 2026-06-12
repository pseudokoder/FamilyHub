"""Blog tests: writing, permissions, XSS safety, comments."""

from app.models import Post


def _write_post(client, title="The Buick Story", body="It caught fire.\n\nTwice."):
    return client.post(
        "/posts/new", data={"title": title, "body": body}, follow_redirects=True
    )


def test_write_and_render_paragraphs(admin_client):
    response = _write_post(admin_client)
    assert b"memory is saved" in response.data
    assert b"<p>It caught fire.</p>" in response.data
    assert b"<p>Twice.</p>" in response.data


def test_xss_is_neutralized(admin_client):
    response = _write_post(
        admin_client, body="Nice try.\n\n<script>alert('xss')</script>"
    )
    assert b"<script>" not in response.data
    assert b"&lt;script&gt;" in response.data  # visible as harmless text


def test_edit_permissions(admin_client, member_client):
    _write_post(admin_client)
    post_id = Post.query.one().id

    # Another member may READ but not EDIT someone else's memory.
    assert member_client.get(f"/posts/{post_id}").status_code == 200
    assert member_client.get(f"/posts/{post_id}/edit").status_code == 403
    assert member_client.post(f"/posts/{post_id}/delete").status_code == 403

    # The author may edit; the 'edited' note appears only after a real edit.
    response = admin_client.post(
        f"/posts/{post_id}/edit",
        data={"title": "The Chevy Story", "body": "It was a Chevy."},
        follow_redirects=True,
    )
    assert b"The Chevy Story" in response.data


def test_admin_can_moderate_others_posts(admin_client, member_client):
    _write_post(member_client, title="Members Post")
    post_id = Post.query.one().id
    response = admin_client.post(f"/posts/{post_id}/delete", follow_redirects=True)
    assert b"memory was deleted" in response.data
    assert Post.query.count() == 0


def test_comments_on_posts(admin_client, member_client):
    _write_post(admin_client)
    post_id = Post.query.one().id
    response = member_client.post(
        f"/posts/{post_id}/comments",
        data={"body": "I was THERE — it was a Ford!"},
        follow_redirects=True,
    )
    assert b"it was a Ford!" in response.data
    assert b"Member" in response.data  # comment shows its author


def test_validation_keeps_typed_text(admin_client):
    """Forgiving forms: a missing title must NOT throw away the story."""
    long_story = "Three paragraphs of typing nobody wants to redo."
    response = admin_client.post(
        "/posts/new", data={"title": "", "body": long_story}, follow_redirects=True
    )
    assert b"needs a title" in response.data
    assert long_story.encode() in response.data  # body survived the error
