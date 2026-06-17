"""family_service — families (FAM) and their parent/child links.

The family is the join record that makes the tree a graph (see family.py): two
partner slots, plus a ``family_children`` row per child. This service validates
that the people you're linking actually exist (a referential check the
application owns) and serializes the family with friendly names so the contract
is readable, not just a bag of ids.
"""

from app.extensions import db
from app.models import Family, FamilyChild, Individual
from app.services import genealogy_service
from app.services.api_errors import ApiError

# GEDCOM pedigree linkage types — how a child belongs to a family.
PEDIGREE_TYPES = {"birth", "adopted", "foster", "step"}


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def _display(individual):
    if individual is None:
        return None
    primary = individual.primary_name
    return primary.display if primary else None


def _require_individual(individual_id, field):
    """An individual id must point at a real person — the app enforces this
    because no two-partner family can reference a ghost."""
    if individual_id is None:
        return None
    individual = db.session.get(Individual, individual_id)
    if individual is None:
        raise ApiError(f"No individual with id {individual_id}.", 400,
                       fields={field: "no such individual"})
    return individual_id


# --- Serialization ------------------------------------------------------------

def serialize_child(link):
    return {
        "family_id": link.family_id,
        "child_id": link.child_id,
        "child_name": _display(link.child),
        "pedigree_type": link.pedigree_type,
        "child_order": link.child_order,
    }


def serialize(family, with_children=True):
    data = {
        "id": family.id,
        "gedcom_xref": family.gedcom_xref,
        "partner1_id": family.partner1_id,
        "partner2_id": family.partner2_id,
        "partner1": _display(family.partner1),
        "partner2": _display(family.partner2),
        "created_at": _iso(family.created_at),
        "updated_at": _iso(family.updated_at),
        "children_count": len(family.children),
    }
    if with_children:
        data["children"] = [serialize_child(c) for c in family.children]
    return data


# --- Family CRUD --------------------------------------------------------------

def list_all():
    return [serialize(f, with_children=False)
            for f in Family.query.order_by(Family.id).all()]


def get(family_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Family, family_id, "family"))


def create(data):
    family = Family(
        partner1_id=_require_individual(data.get("partner1_id"), "partner1_id"),
        partner2_id=_require_individual(data.get("partner2_id"), "partner2_id"),
        gedcom_xref=(data.get("gedcom_xref") or None),
    )
    db.session.add(family)
    db.session.commit()
    return serialize(family)


def update(family_id, data):
    from app.routes.api import get_or_404
    family = get_or_404(Family, family_id, "family")
    if "partner1_id" in data:
        family.partner1_id = _require_individual(data.get("partner1_id"), "partner1_id")
    if "partner2_id" in data:
        family.partner2_id = _require_individual(data.get("partner2_id"), "partner2_id")
    if "gedcom_xref" in data:
        family.gedcom_xref = data.get("gedcom_xref") or None
    db.session.commit()
    return serialize(family)


def delete(family_id):
    from app.routes.api import get_or_404
    family = get_or_404(Family, family_id, "family")
    genealogy_service.delete_family(family)  # sweeps polymorphic attachments + commits


# --- Children sub-resource ----------------------------------------------------

def add_child(family_id, data):
    from app.routes.api import get_or_404, one_of, require
    family = get_or_404(Family, family_id, "family")
    require(data, "child_id")
    child_id = data["child_id"]
    _require_individual(child_id, "child_id")
    if db.session.get(FamilyChild, (family.id, child_id)) is not None:
        raise ApiError("That child is already in this family.", 409,
                       fields={"child_id": "already linked"})
    pedigree = one_of(data, "pedigree_type", PEDIGREE_TYPES) or "birth"
    link = FamilyChild(
        family_id=family.id, child_id=child_id,
        pedigree_type=pedigree, child_order=int(data.get("child_order") or 0),
    )
    db.session.add(link)
    db.session.commit()
    return serialize_child(link)


def remove_child(family_id, child_id):
    from app.routes.api import get_or_404
    link = db.session.get(FamilyChild, (family_id, child_id))
    if link is None:
        get_or_404(Family, family_id, "family")  # 404 the family if THAT's wrong
        raise ApiError("That child isn't in this family.", 404)
    db.session.delete(link)
    db.session.commit()
