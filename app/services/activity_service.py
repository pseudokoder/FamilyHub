"""The "What's New" feed: recent doings across every content type.

WHY IT EXISTS: the elderly-first failure mode of a growing site is that
Grandma logs in, sees the same dashboard, and doesn't know her grandson
posted forty photos yesterday. One page answering "what happened since I
last looked?" is the single best engagement feature a family site has.

DESIGN NOTES:
- No new tables. The feed is DERIVED from the content tables at read
  time — at family scale (hundreds of rows) merging five small queries
  in Python is instant, and there's no second copy of the truth to keep
  in sync. (The audit log is the wrong source: it's an admin forensic
  tool that includes deletes/locks and survives its subjects.)
- Photo uploads are GROUPED: forty photos uploaded to one album on one
  day reads as "Wes added 40 photos to ...", not forty feed lines.
  Same for repeated wiki saves: one line per page/editor/day.
- Feed items carry an (endpoint, kwargs) pair, NOT a URL — building URLs
  is the web layer's job, so the template calls url_for. The service
  stays HTTP-free (and maps cleanly to a v2 ActivityService that knows
  nothing about Angular routes).
"""

from collections import defaultdict

from app.models import (
    FamilyPlan, Photo, PhotoComment, Post, PostComment, TimelineEvent,
    WikiRevision,
)

FEED_LIMIT = 50
# Query a bit more than we show: after merging five sources, the newest
# FEED_LIMIT items might all come from one of them.
PER_SOURCE = FEED_LIMIT


def _item(when, icon, text, endpoint, **kwargs):
    return {"when": when, "icon": icon, "text": text,
            "endpoint": endpoint, "kwargs": kwargs}


def _post_items():
    posts = Post.query.order_by(Post.created_at.desc()).limit(PER_SOURCE)
    return [
        _item(post.created_at, "📖",
              f"{post.author.display_name} wrote down a memory: “{post.title}”",
              "posts.view_post", post_id=post.id)
        for post in posts
    ]


def _photo_upload_items():
    """Grouped by (uploader, album, calendar day) — one line per batch."""
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).limit(200).all()
    batches = defaultdict(list)
    for photo in photos:
        batches[(photo.uploaded_by, photo.album_id,
                 photo.uploaded_at.date())].append(photo)
    items = []
    for batch in batches.values():
        newest = max(batch, key=lambda p: p.uploaded_at)
        count = len(batch)
        plural = "s" if count != 1 else ""
        items.append(_item(
            newest.uploaded_at, "📸",
            f"{newest.uploader.display_name} added {count} photo{plural} "
            f"to “{newest.album.title}”",
            "photos.view_album", album_id=newest.album_id,
        ))
    return items


def _wiki_items():
    """One line per page/editor/day; the day a page is born says so."""
    revisions = (WikiRevision.query
                 .order_by(WikiRevision.created_at.desc())
                 .limit(200).all())
    # A page's very first revision is its birth certificate.
    first_revision_ids = {}
    for revision in revisions:
        current = first_revision_ids.get(revision.member_id)
        if current is None or revision.id < current:
            first_revision_ids[revision.member_id] = revision.id

    groups = {}
    for revision in revisions:
        if revision.member is None or revision.editor is None:
            continue  # backfilled rows may predate editor tracking
        key = (revision.member_id, revision.edited_by,
               revision.created_at.date())
        # revisions arrive newest-first; keep the newest per group
        if key not in groups:
            groups[key] = revision
    items = []
    for revision in groups.values():
        started = revision.id == first_revision_ids.get(revision.member_id)
        verb = "started a wiki page for" if started else "worked on the wiki page for"
        items.append(_item(
            revision.created_at, "👤",
            f"{revision.editor.display_name} {verb} {revision.member.name}",
            "wiki.view_member", member_id=revision.member_id,
        ))
    return items


def _timeline_items():
    events = (TimelineEvent.query
              .order_by(TimelineEvent.created_at.desc()).limit(PER_SOURCE))
    return [
        _item(event.created_at, "🕰️",
              f"{event.creator.display_name} put “{event.title}” "
              f"({event.display_date}) on the timeline",
              "timeline.list_events")
        for event in events
    ]


def _comment_items():
    items = []
    photo_comments = (PhotoComment.query
                      .order_by(PhotoComment.created_at.desc())
                      .limit(PER_SOURCE))
    for comment in photo_comments:
        items.append(_item(
            comment.created_at, "💬",
            f"{comment.author.display_name} commented on a photo "
            f"in “{comment.photo.album.title}”",
            "photos.view_photo", photo_id=comment.photo_id,
        ))
    post_comments = (PostComment.query
                     .order_by(PostComment.created_at.desc())
                     .limit(PER_SOURCE))
    for comment in post_comments:
        items.append(_item(
            comment.created_at, "💬",
            f"{comment.author.display_name} commented on “{comment.post.title}”",
            "posts.view_post", post_id=comment.post_id,
        ))
    return items


def _plan_items():
    plans = FamilyPlan.query.order_by(FamilyPlan.created_at.desc()).limit(PER_SOURCE)
    return [
        _item(plan.created_at, "🗂️",
              f"{plan.creator.display_name} started a plan: “{plan.title}”",
              "plans.view_plan", plan_id=plan.id)
        for plan in plans
    ]


def recent_activity(limit=FEED_LIMIT):
    """Everything recent, newest first, capped."""
    items = (_post_items() + _photo_upload_items() + _wiki_items()
             + _timeline_items() + _comment_items() + _plan_items())
    items.sort(key=lambda item: item["when"], reverse=True)
    return items[:limit]
