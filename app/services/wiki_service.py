"""Wiki business logic: the family-member pages.

Editing policy (straight from CLAUDE.md): EVERY authenticated family member
may create and edit wiki pages — it's a collaborative family encyclopedia,
not a personal blog. Only deletion is admin-only (removing a person's page
is a big deal).

Every save also records a WikiRevision snapshot (see that model's docstring
for why a collaborative wiki without history is a data-loss machine).
"""

from app.extensions import db
from app.models import FamilyMember, WikiRevision


def get_all_members():
    """Alphabetical — an encyclopedia, not a feed."""
    return FamilyMember.query.order_by(FamilyMember.name).all()


def find_by_name(name):
    """Case-insensitive exact-name lookup — powers the [[Name]] links.

    db.func.lower() is portable SQL (works in SQLite today, MySQL in v2);
    no database-specific collation tricks.
    """
    return FamilyMember.query.filter(
        db.func.lower(FamilyMember.name) == name.strip().lower()
    ).first()


def _record_revision(member, user):
    """Snapshot the member's CURRENT state as a new revision row.

    Called inside create/update/restore *before* their commit, so the
    page change and its history row land in the same transaction —
    either both exist or neither does (atomicity, D426)."""
    db.session.add(WikiRevision(
        member=member,
        name=member.name,
        location=member.location,
        bio=member.bio,
        birth_date=member.birth_date,
        death_date=member.death_date,
        edited_by=user.id,
    ))


def create_member(form_data, user):
    member = FamilyMember(
        name=form_data["name"].strip(),
        location=(form_data["location"] or "").strip(),
        bio=(form_data["bio"] or "").strip(),
        birth_date=form_data["birth_date"],
        death_date=form_data["death_date"],
        created_by=user.id,
        updated_by=user.id,
    )
    db.session.add(member)
    _record_revision(member, user)  # version 1: the page as first written
    db.session.commit()
    return member


def update_member(member, form_data, user):
    member.name = form_data["name"].strip()
    member.location = (form_data["location"] or "").strip()
    member.bio = (form_data["bio"] or "").strip()
    member.birth_date = form_data["birth_date"]
    member.death_date = form_data["death_date"]
    member.updated_by = user.id
    _record_revision(member, user)
    db.session.commit()
    return member


def get_revision(member, revision_id):
    """A revision, but ONLY if it belongs to this member's page.

    Filtering by BOTH ids closes an authorization-adjacent hole: without
    it, /family/3/history/99 could show a revision of someone else's page
    under the wrong breadcrumb (an "insecure direct object reference"
    smell, D315 — always check the relationship, not just the id)."""
    return WikiRevision.query.filter_by(
        id=revision_id, member_id=member.id
    ).first()


def restore_revision(member, revision, user):
    """Copy a snapshot back onto the live page.

    The restore itself is recorded as a NEW revision (not a rewind of the
    list) — history only ever grows. If the restore was itself a mistake,
    it can be un-restored the same way. Nothing is ever lost."""
    member.name = revision.name
    member.location = revision.location
    member.bio = revision.bio
    member.birth_date = revision.birth_date
    member.death_date = revision.death_date
    member.updated_by = user.id
    _record_revision(member, user)
    db.session.commit()
    return member


def delete_member(member):
    db.session.delete(member)  # cascade removes the page's history too
    db.session.commit()
