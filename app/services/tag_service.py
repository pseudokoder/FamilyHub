"""Tagging: connect photos to wiki pages ("who's in this photo?").

POLICY (same spirit as the wiki): ANY authenticated family member may add
or remove tags — naming faces is collaborative memory work, and the most
likely tagger ("that's Aunt Ruth!") is rarely the person who uploaded the
file. The audit log records every change either way.

v2 mapping: TagService.java; the queries become Spring Data join methods.
"""

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import FamilyMember, Photo, PhotoTag
from app.services import audit_service


def tag_photo(photo, member, user):
    """Name a face. Returns the tag, or None if already tagged.

    The duplicate check is TWO layers: a friendly query first (so the
    user gets a calm message), and the database's unique constraint as
    the backstop for the race where two people tag simultaneously —
    IntegrityError is caught and treated as "already done"."""
    existing = PhotoTag.query.filter_by(
        photo_id=photo.id, member_id=member.id
    ).first()
    if existing:
        return None
    tag = PhotoTag(photo_id=photo.id, member_id=member.id, created_by=user.id)
    db.session.add(tag)
    audit_service.log_event(
        user, "tag", "photo", photo.id, f"tagged {member.name}"
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    return tag


def untag_photo(photo, member, user):
    """Remove a name from a photo. Returns True if there was one."""
    tag = PhotoTag.query.filter_by(
        photo_id=photo.id, member_id=member.id
    ).first()
    if tag is None:
        return False
    audit_service.log_event(
        user, "untag", "photo", photo.id, f"untagged {member.name}"
    )
    db.session.delete(tag)
    db.session.commit()
    return True


def members_tagged_in(photo):
    """The people in this photo, alphabetically (for the chips)."""
    return (FamilyMember.query
            .join(PhotoTag, PhotoTag.member_id == FamilyMember.id)
            .filter(PhotoTag.photo_id == photo.id)
            .order_by(FamilyMember.name).all())


def members_not_tagged_in(photo):
    """Everyone who COULD still be tagged (for the add-dropdown)."""
    tagged_ids = [tag.member_id for tag in photo.tags]
    query = FamilyMember.query.order_by(FamilyMember.name)
    if tagged_ids:
        query = query.filter(~FamilyMember.id.in_(tagged_ids))
    return query.all()


def photos_featuring(member):
    """Every photo this person is tagged in, newest first (for the
    wiki page's gallery)."""
    return (Photo.query
            .join(PhotoTag, PhotoTag.photo_id == Photo.id)
            .filter(PhotoTag.member_id == member.id)
            .order_by(Photo.uploaded_at.desc()).all())
