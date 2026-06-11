"""Blog models: Post (a written family memory) and PostComment.

This is the parents' main activity — blog-style posts telling family
stories. Notice how closely this mirrors the photo feature's shape
(users 1--* posts 1--* post_comments): once you've learned one
parent-child-comment pattern, you've learned them all.
"""

from datetime import datetime, timezone

from app.extensions import db


class Post(db.Model):
    """One written memory — 'The Summer the Buick Caught Fire', etc."""

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    # db.Text, not String(n): memories can be as long as Mom wants. Text maps
    # cleanly to MySQL TEXT for v2 — no SQLite-only tricks here.
    body = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    # onupdate: SQLAlchemy stamps this automatically every time the row
    # changes — we never have to remember to set it by hand.
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    author = db.relationship("User")
    comments = db.relationship(
        "PostComment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostComment.created_at",
    )

    @property
    def was_edited(self):
        """True if the post changed after it was first written (we show a
        little 'edited' note — honest history matters in a family archive)."""
        return (self.updated_at - self.created_at).total_seconds() > 60

    def __repr__(self):
        return f"<Post {self.title!r}>"


class PostComment(db.Model):
    """A comment under a memory — 'I was THERE, it was a Chevy!'"""

    __tablename__ = "post_comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    post = db.relationship("Post", back_populates="comments")
    author = db.relationship("User")

    def __repr__(self):
        return f"<PostComment {self.id} on post {self.post_id}>"
