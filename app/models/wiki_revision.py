"""WikiRevision — one saved version of a family member's wiki page.

WHY THIS TABLE EXISTS: the wiki is editable by every family member, which
is wonderful right up until someone accidentally pastes over Grandma's
whole life story and presses Save. Without history, that text is *gone*.
With history, every save is a snapshot, and any version can be brought
back with one button. Wikipedia learned this lesson decades ago — a
collaborative encyclopedia without an undo is a data-loss machine.

DESIGN (D426): this is the **snapshot pattern** — each row stores the
complete editable state of the page *as of one save*, not a diff. Diffs
are smaller but restoring means replaying every diff since the beginning;
snapshots make restore a simple copy. At family scale (a page might see
dozens of edits, not millions), storage is a non-issue, so the simpler
design wins.

v2 mapping: WikiRevision @Entity; Hibernate Envers does this generically,
but writing it by hand once teaches you what Envers is doing.
"""

from datetime import datetime, timezone

from app.extensions import db


class WikiRevision(db.Model):
    __tablename__ = "wiki_revisions"

    id = db.Column(db.Integer, primary_key=True)

    # index=True: "show me this page's history" is THE query here.
    member_id = db.Column(
        db.Integer, db.ForeignKey("family_member.id"), nullable=False, index=True
    )

    # --- The snapshot: every field the edit form can change. -----------------
    # Same types and lengths as FamilyMember — a revision must be able to
    # hold anything the live row can hold, or restore would corrupt data.
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    bio = db.Column(db.Text, nullable=False, default="", server_default="")
    birth_date = db.Column(db.Date, nullable=True)
    death_date = db.Column(db.Date, nullable=True)

    # Who pressed Save, and when. Nullable editor: revisions backfilled by
    # the migration (for pages that existed before this feature) may not
    # know their author.
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    member = db.relationship("FamilyMember", back_populates="revisions")
    editor = db.relationship("User")

    def __repr__(self):
        return f"<WikiRevision {self.id} of member {self.member_id}>"
