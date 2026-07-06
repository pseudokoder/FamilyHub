"""account_service — the Account ↔ Person link and the tree's default root (ADR-0002).

WHY (ADR-0002): a living member is usually BOTH a login (a User) and a person in
the tree (an Individual). Linking the two — a nullable ``users.individual_id`` —
unlocks three things:
  1. "My person": the tree can root on *you*.
  2. Self-authored records: a linked member may edit their OWN person even if
     their role wouldn't otherwise permit writes (high-value original data).
  3. A stable identity seam for a future companion app.

THE FALLBACK ROOT: an *unlinked* user has no personal anchor, so the tree defaults
to the **oldest known ancestor** — the earliest-born person who is nobody's child
in the database (a root of the pedigree). That gives every visitor a sensible
starting view instead of a blank screen.

Layered architecture (CLAUDE.md): routes call these functions; linking is audited
through write_control's action log so account changes are as traceable as data edits.

v2 mapping: an ``AccountService`` with the same nullable FK on the JPA ``User``.
"""

from zoneinfo import available_timezones

from flask import url_for

from app.extensions import db
from app.models import Event, FamilyChild, Individual, User
from app.models.role import Role
from app.services import audit_service, individual_service, mail_service, user_service
from app.services.api_errors import ApiError


# --- The link (admin-managed) -------------------------------------------------

def _get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError(f"No user found with id {user_id}.", 404)
    return user


def _get_live_individual(individual_id):
    ind = db.session.get(Individual, individual_id)
    if ind is None or ind.deleted_at is not None:
        raise ApiError(f"No individual found with id {individual_id}.", 400,
                       fields={"individual_id": "no such individual"})
    return ind


def link(user_id, individual_id, actor=None):
    """Point a user account at its person record (admin action, audited).

    Enforces the one-to-one rule ADR-0002 states: an individual has *zero or one*
    linked user, so we refuse to link a person who's already claimed by someone
    else (a mis-link would mis-attribute edits)."""
    if individual_id is None:
        raise ApiError("individual_id is required.", 400,
                       fields={"individual_id": "required"})
    user = _get_user(user_id)
    _get_live_individual(individual_id)

    clash = (User.query
             .filter(User.individual_id == individual_id, User.id != user.id)
             .first())
    if clash is not None:
        raise ApiError("That person is already linked to another account.", 409,
                       fields={"individual_id": "already linked"})

    user.individual_id = individual_id
    audit_service.log_event(actor, "link", "user", user.id,
                            f"linked to individual #{individual_id}")
    db.session.commit()
    return serialize_link(user)


def unlink(user_id, actor=None):
    """Clear a user's person link (admin action, audited)."""
    user = _get_user(user_id)
    previous = user.individual_id
    user.individual_id = None
    audit_service.log_event(actor, "unlink", "user", user.id,
                            f"unlinked from individual #{previous}")
    db.session.commit()
    return serialize_link(user)


def serialize_link(user):
    return {
        "user_id": user.id,
        "individual_id": user.individual_id,
        "individual": (individual_service.serialize(user.individual)
                       if user.individual and user.individual.deleted_at is None
                       else None),
    }


# --- "My person" + self-edit --------------------------------------------------

def my_person(user):
    """The individual linked to ``user``, serialized — or None if unlinked (or the
    linked person was since deleted)."""
    if user.individual_id is None:
        return None
    ind = db.session.get(Individual, user.individual_id)
    if ind is None or ind.deleted_at is not None:
        return None
    return individual_service.serialize(ind)


def self_update(user, data):
    """Let a linked member edit THEIR OWN person record (ADR-0002 self-authoring),
    regardless of role — it's their own data. Reuses individual_service.update, so
    the edit is validated and audited exactly like any other."""
    if user.individual_id is None:
        raise ApiError("Your account isn't linked to a person yet.", 400,
                       fields={"individual_id": "not linked"})
    return individual_service.update(user.individual_id, data)


# --- The tree's default root --------------------------------------------------

def _birth_sort(individual_id):
    """The sortable birth date of an individual, or None. Used to find the
    *oldest* ancestor (earliest birth) for the default root."""
    birth = (Event.query
             .filter(Event.deleted_at.is_(None),
                     Event.subject_type == "individual",
                     Event.subject_id == individual_id,
                     Event.event_tag == "BIRT")
             .order_by(Event.date_sort).first())
    return birth.date_sort if birth else None


def oldest_ancestor():
    """The default tree root for an unlinked user: the earliest-born person who is
    nobody's child in the database (a pedigree root). Family-sized data, so a
    little Python is clearer than a heroic single query.

    Ties and unknowns fail gracefully: people with no birth date sort last, then
    by id, so there is always a deterministic answer when any individual exists."""
    child_ids = {row.child_id for row in
                 FamilyChild.query.filter(FamilyChild.deleted_at.is_(None)).all()}
    roots = (Individual.query.filter(Individual.deleted_at.is_(None)).all())
    candidates = [i for i in roots if i.id not in child_ids] or roots
    if not candidates:
        return None
    # Sort key: known birth first (earliest), unknowns last, then id.
    candidates.sort(key=lambda i: (_birth_sort(i.id) is None,
                                   _birth_sort(i.id) or "", i.id))
    return candidates[0]


def tree_root(user):
    """Resolve where the tree should open for ``user`` (ADR-0002):
    the linked person if any, otherwise the oldest ancestor. Returns the root id,
    how it was chosen, and the serialized individual (or nulls for an empty tree)."""
    if user.individual_id is not None:
        ind = db.session.get(Individual, user.individual_id)
        if ind is not None and ind.deleted_at is None:
            return {"individual_id": ind.id, "source": "linked",
                    "individual": individual_service.serialize(ind)}
    root = oldest_ancestor()
    if root is None:
        return {"individual_id": None, "source": "empty", "individual": None}
    return {"individual_id": root.id, "source": "oldest_ancestor",
            "individual": individual_service.serialize(root)}


# --- The Account & Security page (FE-5) ----------------------------------------
#
# Member self-service: your own snapshot, your own contribution history, your
# own email/deletion — everything here acts on ``user`` (the session's OWN
# account), never on an id from the request, so there's no path from these
# functions into another member's account.

def me_snapshot(user):
    """The current user's own account snapshot — the Account page header and
    the My Contributions dashboard. Role and email are shown but NOT editable
    through ``update_me`` below (an admin-only change elsewhere)."""
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "role": user.role,
        "email_verified_at": (user.email_verified_at.isoformat()
                              if user.email_verified_at else None),
        "timezone": user.timezone,
        "individual_id": user.individual_id,
    }


def update_me(user, data):
    """Self-serve account edits: ONLY ``display_name`` and ``timezone``. Role
    and email are deliberately absent from this function — role is admin-only
    (§10) and email has its own guarded, verify-before-applying flow
    (``request_email_change``, below), not a plain field edit."""
    if "display_name" in data:
        name = (data.get("display_name") or "").strip()
        if not name:
            raise ApiError("display_name can't be blank.", 400,
                           fields={"display_name": "required"})
        user_service.set_display_name(user, name, actor=user)

    if "timezone" in data:
        tz = data.get("timezone") or None
        if tz is not None and tz not in available_timezones():
            raise ApiError("timezone must be a valid IANA zone name (e.g. "
                           "America/Chicago).", 400, fields={"timezone": "invalid"})
        user.timezone = tz
        audit_service.log_event(user, "edit", "user", user.id,
                                f"timezone -> {tz or '(site default)'}")
        db.session.commit()

    return me_snapshot(user)


def request_email_change(user, new_email, current_password):
    """Self-serve change-email (the member-facing dual of admin_service's
    secure dance): requires the CURRENT password, then emails a verification
    link to the NEW address. The stored ``email`` column does NOT change here
    — it changes only when that link is clicked (``user_service.
    confirm_email_token``), so a hijacked session can't silently take over
    login before the real owner notices."""
    if not mail_service.is_configured():
        raise ApiError("Email isn't set up on this server yet.", 503)
    if user_service.authenticate(user.email, current_password) is None:
        raise ApiError("Your current password isn't right.", 403,
                       fields={"current_password": "incorrect"})

    new_email = (new_email or "").strip().lower()
    if not new_email:
        raise ApiError("A new email address is required.", 400,
                       fields={"new_email": "required"})
    clash = user_service.find_by_email(new_email)
    if clash is not None and clash.id != user.id:
        raise ApiError(f'The email "{new_email}" is already in use.', 400,
                       fields={"new_email": "in use"})

    user.pending_email = new_email
    verify_token = user_service.generate_email_verify_token(user, email=new_email)
    verify_url = url_for("auth.verify_email", token=verify_token, _external=True)
    mail_service.send_email_verification(user, verify_url, email=new_email)
    audit_service.log_event(user, "request change email", "user", user.id,
                            f"{user.email} -> {new_email} (pending verification)")
    db.session.commit()
    return {"status": "verification_sent", "pending_email": new_email}


def delete_my_account(user, current_password):
    """"Delete my account" = ANONYMIZE the contributor, never erase (§9): every
    contribution and audit row this member ever made must survive with an
    intact subject_id, or the provenance trail (ADR-0001) breaks. Requires the
    current password (this is a one-way door), refuses to strand the family
    with zero active admins, and writes the audit entry BEFORE scrubbing the
    row so the trail still names who did it (afterward, ``entry.user`` reads
    back the neutral placeholder — exactly the "former member" attribution
    every past row should show too)."""
    if user_service.authenticate(user.email, current_password) is None:
        raise ApiError("Your current password isn't right.", 403,
                       fields={"current_password": "incorrect"})

    if user.is_admin:
        other_active_admins = (
            User.query
            .filter(User.role == Role.ADMIN.value, User.is_active.is_(True),
                    User.id != user.id)
            .count())
        if other_active_admins == 0:
            raise ApiError(
                "You're the last active admin — promote someone else before "
                "deleting this account.", 409, fields={"role": "last active admin"})

    old_email = user.email
    audit_service.log_event(user, "self-delete", "user", user.id,
                            f"account anonymized by its own owner ({old_email})")

    user.display_name = "Former member"
    user.email = f"deleted-user-{user.id}@familyhub.invalid"
    user.pending_email = None
    user.email_verified_at = None
    user.individual_id = None
    user.is_active = False
    db.session.commit()
    return {"status": "anonymized"}
