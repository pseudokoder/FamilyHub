"""individual_service — business logic for individuals and their names.

Layered architecture (CLAUDE.md): the route is the @Controller, THIS is the
@Service, the models are the @Repository. Routes never touch the database
directly; they call these functions, which validate, mutate, and serialize.

The ``serialize`` functions define the JSON SHAPE of the contract — change the
shape here and the OpenAPI doc + every consumer changes with it, in one place.
"""

from app.extensions import db
from app.models import Individual, Name
from app.services import write_control
from app.services.api_errors import ApiError

# The GEDCOM SEX enum — a closed set the schema can hold (individual.py).
SEX_VALUES = {"M", "F", "X", "U"}


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def _bool(value, default=False):
    """Coerce a JSON value to a real bool. Accepts true/false, 1/0, and the
    strings a form might send ('true'/'on'). Anything else falls back."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


# --- Serialization (the contract shapes) --------------------------------------

def serialize_name(name):
    return {
        "id": name.id,
        "individual_id": name.individual_id,
        "name_type": name.name_type,
        "name_prefix": name.name_prefix,
        "given": name.given,
        "nickname": name.nickname,
        "surname_prefix": name.surname_prefix,
        "surname": name.surname,
        "name_suffix": name.name_suffix,
        "is_primary": name.is_primary,
        "sort_order": name.sort_order,
        "display": name.display,  # the reassembled "Dr. Jane van Berg III"
    }


def _live_names(individual):
    """The individual's names, excluding any soft-deleted ones (ADR-0001)."""
    return [n for n in individual.names if not n.is_deleted]


def serialize(individual, with_names=True):
    names = _live_names(individual)
    primary = next((n for n in names if n.is_primary), names[0] if names else None)
    data = {
        "id": individual.id,
        "gedcom_xref": individual.gedcom_xref,
        "sex": individual.sex,
        "living": individual.living,
        "restriction": individual.restriction,
        "created_at": _iso(individual.created_at),
        "updated_at": _iso(individual.updated_at),
        "primary_name": primary.display if primary else None,
        "names_count": len(names),
    }
    if with_names:
        data["names"] = [serialize_name(n) for n in names]
    return data


# --- Individual CRUD ----------------------------------------------------------

def list_all():
    # Soft-delete aware (ADR-0001): live rows only.
    return [serialize(i, with_names=False)
            for i in Individual.query
            .filter(Individual.deleted_at.is_(None))
            .order_by(Individual.id).all()]


def get(individual_id):
    from app.routes.api import get_or_404
    return serialize(get_or_404(Individual, individual_id, "individual"))


def _validate_sex(data):
    sex = data.get("sex")
    if sex is not None and sex != "" and sex not in SEX_VALUES:
        raise ApiError(f"sex must be one of: {', '.join(sorted(SEX_VALUES))}.",
                       400, fields={"sex": "invalid"})
    return sex or None


def create(data):
    """Create an individual, optionally with one primary name supplied inline as
    a ``name`` object — the common "add a person" path."""
    individual = Individual(
        sex=_validate_sex(data),
        living=_bool(data.get("living"), default=True),
        restriction=(data.get("restriction") or None),
        gedcom_xref=(data.get("gedcom_xref") or None),
    )
    db.session.add(individual)
    db.session.flush()  # need the id before attaching a name

    if isinstance(data.get("name"), dict):
        _build_name(individual, data["name"], force_primary=True)

    write_control.log_create("individual", individual)  # audit (ADR-0001)
    db.session.commit()
    return serialize(individual)


def update(individual_id, data):
    from app.routes.api import get_or_404
    individual = get_or_404(Individual, individual_id, "individual")
    before = write_control.snapshot(individual)  # capture pre-image for the audit
    if "sex" in data:
        individual.sex = _validate_sex(data)
    if "living" in data:
        individual.living = _bool(data.get("living"), default=individual.living)
    if "restriction" in data:
        individual.restriction = data.get("restriction") or None
    if "gedcom_xref" in data:
        individual.gedcom_xref = data.get("gedcom_xref") or None
    write_control.log_update("individual", individual, before)
    db.session.commit()
    return serialize(individual)


def delete(individual_id):
    from app.routes.api import get_or_404
    individual = get_or_404(Individual, individual_id, "individual")
    # SOFT delete (ADR-0001): recoverable + audited. We deliberately do NOT purge
    # the individual's polymorphic attachments (events, citations, media/note
    # links) the way a hard delete had to — keeping them intact is what lets a
    # Curator restore/revert the person whole. Reads hide the person meanwhile.
    write_control.soft_delete("individual", individual)


# --- Names sub-resource -------------------------------------------------------

def _build_name(individual, data, force_primary=False):
    """Attach a Name to an individual from a dict. Enforces "at most one primary
    name per person" by clearing the others when this one is primary."""
    is_primary = force_primary or _bool(data.get("is_primary"))
    if is_primary:
        for existing in individual.names:
            existing.is_primary = False
    name = Name(
        individual_id=individual.id,
        name_type=(data.get("name_type") or "birth"),
        name_prefix=data.get("name_prefix") or None,
        given=data.get("given") or None,
        nickname=data.get("nickname") or None,
        surname_prefix=data.get("surname_prefix") or None,
        surname=data.get("surname") or None,
        name_suffix=data.get("name_suffix") or None,
        is_primary=is_primary,
        sort_order=int(data.get("sort_order") or 0),
    )
    db.session.add(name)
    return name


def add_name(individual_id, data):
    from app.routes.api import get_or_404
    individual = get_or_404(Individual, individual_id, "individual")
    if not (data.get("given") or data.get("surname")):
        raise ApiError("A name needs at least a given name or a surname.",
                       400, fields={"given": "required", "surname": "required"})
    name = _build_name(individual, data)
    db.session.flush()
    write_control.log_create("name", name)
    db.session.commit()
    return serialize_name(name)


def update_name(name_id, data):
    from app.routes.api import get_or_404
    name = get_or_404(Name, name_id, "name")
    before = write_control.snapshot(name)
    for field in ("name_type", "name_prefix", "given", "nickname",
                  "surname_prefix", "surname", "name_suffix"):
        if field in data:
            setattr(name, field, data.get(field) or None)
    if "sort_order" in data:
        name.sort_order = int(data.get("sort_order") or 0)
    if "is_primary" in data and _bool(data.get("is_primary")):
        for other in name.individual.names:
            other.is_primary = (other.id == name.id)
        name.is_primary = True
    write_control.log_update("name", name, before)
    db.session.commit()
    return serialize_name(name)


def delete_name(name_id):
    from app.routes.api import get_or_404
    name = get_or_404(Name, name_id, "name")
    write_control.soft_delete("name", name)  # soft delete + audit (ADR-0001)
