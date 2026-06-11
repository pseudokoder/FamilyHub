"""Wiki business logic: the family-member pages.

Editing policy (straight from CLAUDE.md): EVERY authenticated family member
may create and edit wiki pages — it's a collaborative family encyclopedia,
not a personal blog. Only deletion is admin-only (removing a person's page
is a big deal).
"""

from app.extensions import db
from app.models import FamilyMember


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
    db.session.commit()
    return member


def update_member(member, form_data, user):
    member.name = form_data["name"].strip()
    member.location = (form_data["location"] or "").strip()
    member.bio = (form_data["bio"] or "").strip()
    member.birth_date = form_data["birth_date"]
    member.death_date = form_data["death_date"]
    member.updated_by = user.id
    db.session.commit()
    return member


def delete_member(member):
    db.session.delete(member)
    db.session.commit()
