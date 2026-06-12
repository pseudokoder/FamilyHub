"""Blog business logic. Same shape as photo_service — by now the layered
pattern should feel familiar: routes ask, services decide, models store.

v2 mapping: PostService.java (@Service).
"""

from app.extensions import db
from app.models import Post, PostComment
from app.services import audit_service


def get_all_posts():
    """Newest memories first — the family checks in for what's new."""
    return Post.query.order_by(Post.created_at.desc()).all()


def create_post(title, body, user):
    post = Post(title=title.strip(), body=body.strip(), author_id=user.id)
    db.session.add(post)
    db.session.flush()  # assigns post.id so the audit row can name it
    audit_service.log_event(user, "create", "post", post.id, post.title)
    db.session.commit()
    return post


def update_post(post, title, body, user):
    post.title = title.strip()
    post.body = body.strip()
    audit_service.log_event(user, "edit", "post", post.id, post.title)
    db.session.commit()  # updated_at stamps itself (onupdate in the model)
    return post


def can_modify(post, user):
    """One rule, one place: the author or an admin may edit/delete a post.

    Posts are deliberately NOT lockable (Wes's rule): they're personal
    words, and their author may always take them back — unlike photos and
    wiki pages, which become shared archive once an admin locks them."""
    return user.is_admin or post.author_id == user.id


def delete_post(post, user):
    audit_service.log_event(user, "delete", "post", post.id, post.title)
    db.session.delete(post)  # cascade removes its comments
    db.session.commit()


def add_comment(post, user, body):
    comment = PostComment(post_id=post.id, author_id=user.id, body=body.strip())
    db.session.add(comment)
    db.session.commit()
    return comment


def can_delete_comment(comment, user):
    """Your words, your delete — or the admin's cleanup power."""
    return user.is_admin or comment.author_id == user.id


def delete_comment(comment, user):
    audit_service.log_event(user, "delete", "post comment", comment.id)
    db.session.delete(comment)
    db.session.commit()
