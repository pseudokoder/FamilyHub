"""Blog business logic. Same shape as photo_service — by now the layered
pattern should feel familiar: routes ask, services decide, models store.

v2 mapping: PostService.java (@Service).
"""

from app.extensions import db
from app.models import Post, PostComment


def get_all_posts():
    """Newest memories first — the family checks in for what's new."""
    return Post.query.order_by(Post.created_at.desc()).all()


def create_post(title, body, user):
    post = Post(title=title.strip(), body=body.strip(), author_id=user.id)
    db.session.add(post)
    db.session.commit()
    return post


def update_post(post, title, body):
    post.title = title.strip()
    post.body = body.strip()
    db.session.commit()  # updated_at stamps itself (onupdate in the model)
    return post


def can_modify(post, user):
    """One rule, one place: the author or an admin may edit/delete a post.
    Identical policy to photos — consistent rules are learnable rules,
    for the family AND for whoever maintains this code."""
    return user.is_admin or post.author_id == user.id


def delete_post(post):
    db.session.delete(post)  # cascade removes its comments
    db.session.commit()


def add_comment(post, user, body):
    comment = PostComment(post_id=post.id, author_id=user.id, body=body.strip())
    db.session.add(comment)
    db.session.commit()
    return comment
