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

from app.extensions import db
from app.models import Event, FamilyChild, Individual, User
from app.services import audit_service, individual_service
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
