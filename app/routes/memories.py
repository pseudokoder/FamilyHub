"""The Memories blueprint: photo album views + Stories (Master Plan §4, FE-4).

Thin controllers, same rule as every other route in this app (CLAUDE.md's
layered architecture) and the exact pattern tree.py/people.py already
established: each view just renders a shell template. All data comes from
the browser calling the WP2 JSON API (docs/openapi.yaml) with fetch() — see
app/static/js/memories.js and app/static/js/stories.js.

"ONE PHOTO STORE, ALBUM VIEWS" (Master Plan §2/§4): By Person / By Family /
By Event / Chronological are never separate stores — each is a different
client-side filter over the SAME GET /api/media. Stories is the memory-blog
lane of the same section, over GET /api/notes.

v2 mapping: MemoriesController.java, each @GetMapping returning a Thymeleaf-
free view name for Angular's router to mount a component on.
"""

from flask import Blueprint, render_template
from flask_login import login_required

memories_bp = Blueprint("memories", __name__, url_prefix="/memories")


@memories_bp.route("")
@login_required
def index():
    """Chronological: every photo ordered by capture date, falling back to
    upload date (visibly labeled) when none exists — GET /api/media?order_by
    =capture. Also the section's default landing page and its "+ Upload a
    photo" entry point (Home's Quick Add Photo tile lands here)."""
    return render_template("memories/index.html")


@memories_bp.route("/person")
@login_required
def by_person():
    """By Person: pick a person (search-as-you-type), see every photo linked
    to them — the same GET /api/media?subject_type=individual&subject_id=
    call the Person Page's own Photos tab already uses."""
    return render_template("memories/by_person.html")


@memories_bp.route("/family")
@login_required
def by_family():
    """By Family: pick a family, see photos linked to the family itself, its
    own events, and its members' events — an honest client-side aggregation
    over GET /api/media's existing subject_type filters (individual/family/
    event — see docs/openapi.yaml's Media Link schema), not a new backend
    capability."""
    return render_template("memories/by_family.html")


@memories_bp.route("/event")
@login_required
def by_event():
    """By Event: every event with at least one linked photo, grouped
    (weddings, reunions…) — a whole-archive view, same spirit as
    Chronological, not a single-event picker."""
    return render_template("memories/by_event.html")


@memories_bp.route("/stories")
@login_required
def stories():
    """Stories: the memory-blog lane of this section — list/browse notes
    (Markdown), newest first."""
    return render_template("memories/stories.html")


@memories_bp.route("/stories/new")
@login_required
def new_story():
    """Write a story. Contributor+ is a template/JS-rendered affordance (the
    `data-can-contribute` pattern people/show.html established) — the route
    itself stays login_required; the API enforces the real write permission."""
    return render_template("memories/story_new.html")


@memories_bp.route("/stories/<int:note_id>")
@login_required
def story(note_id):
    """One story's read view."""
    return render_template("memories/story_show.html", note_id=note_id)
