"""Family history blog routes.

Same RESTful shape as photos — resources in URLs, verbs in HTTP methods:

    GET  /posts                 all memories, newest first
    GET+POST /posts/new         write one
    GET  /posts/<id>            read one (+ its comments)
    GET+POST /posts/<id>/edit   fix a typo, add a detail (author/admin)
    POST /posts/<id>/delete     remove it (author/admin, confirmed)
    POST /posts/<id>/comments   join the conversation
"""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.comment_forms import CommentForm
from app.forms.post_forms import PostForm
from app.models import Post
from app.services import post_service

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/posts")
@login_required
def list_posts():
    return render_template("posts/posts.html", posts=post_service.get_all_posts())


@posts_bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = post_service.create_post(form.title.data, form.body.data, current_user)
        flash("Your memory is saved — thank you for writing it down!", "success")
        return redirect(url_for("posts.view_post", post_id=post.id))
    return render_template("posts/new_post.html", form=form)


@posts_bp.route("/posts/<int:post_id>")
@login_required
def view_post(post_id):
    post = db.get_or_404(Post, post_id)
    return render_template(
        "posts/post.html",
        post=post,
        comment_form=CommentForm(),
        can_modify=post_service.can_modify(post, current_user),
    )


@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(Post, post_id)
    if not post_service.can_modify(post, current_user):
        abort(403)
    # obj=post pre-fills the form with the existing title and body — the
    # same PostForm class handles both "new" and "edit". One form, two jobs.
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post_service.update_post(post, form.title.data, form.body.data)
        flash("Your changes are saved.", "success")
        return redirect(url_for("posts.view_post", post_id=post.id))
    return render_template("posts/edit_post.html", form=form, post=post)


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    if not post_service.can_modify(post, current_user):
        abort(403)
    post_service.delete_post(post)
    flash("The memory was deleted.", "success")
    return redirect(url_for("posts.list_posts"))


@posts_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@login_required
def add_comment(post_id):
    post = db.get_or_404(Post, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        post_service.add_comment(post, current_user, form.body.data)
        flash("Comment added!", "success")
    else:
        for message in form.body.errors:
            flash(message, "danger")
    return redirect(url_for("posts.view_post", post_id=post.id))
