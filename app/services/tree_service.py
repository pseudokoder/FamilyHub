"""tree_service — pedigree traversal and the relationship-path finder.

THE TREE IS A GRAPH, NOT A LINKED LIST (Master Plan v2.0.0 §3). A person can have
many ancestors, many descendants, and several spouses; branches rejoin (cousins
marry, pedigrees collapse). So we never assume a single linear chain — we do a
breadth-first walk over the FAM links and return a GRAPH SLICE: a set of nodes
plus the edges between them, bounded by a ``depth`` so the front-end can
lazy-expand from any node (the seam for the v2 pan/zoom canvas).

Two public operations:
  * ``graph(root_id, direction, depth)``   — the pedigree/descendant slice.
  * ``relationship(a_id, b_id)``           — shortest blood path + English label.

v2 mapping: a ``TreeService`` doing the same BFS over JPA entities; the heavy
dynamic canvas consumes ``graph`` slices on demand.
"""

from sqlalchemy import or_

from app.models import Family, FamilyChild, Individual
from app.services import individual_service
from app.services.api_errors import ApiError

MAX_DEPTH = 6          # a single request never returns more than this many generations
_SAFETY_GENERATIONS = 30  # cycle guard for the relationship walk


# --- Small graph-navigation helpers (the FAM-link primitives) -----------------

def _live_individual(ind_id):
    ind = Individual.query.filter(
        Individual.id == ind_id, Individual.deleted_at.is_(None)).first()
    if ind is None:
        raise ApiError(f"No individual found with id {ind_id}.", 404)
    return ind


def _parent_families(ind_id):
    """The live families in which ``ind_id`` is a child (→ their parents)."""
    fam_ids = [fc.family_id for fc in FamilyChild.query.filter(
        FamilyChild.child_id == ind_id, FamilyChild.deleted_at.is_(None)).all()]
    if not fam_ids:
        return []
    return (Family.query.filter(Family.id.in_(fam_ids),
                                Family.deleted_at.is_(None)).all())


def _spouse_families(ind_id):
    """The live families in which ``ind_id`` is a partner (→ spouses + children)."""
    return (Family.query.filter(
        Family.deleted_at.is_(None),
        or_(Family.partner1_id == ind_id, Family.partner2_id == ind_id)).all())


def _live_child_ids(family_id):
    return [fc.child_id for fc in FamilyChild.query.filter(
        FamilyChild.family_id == family_id,
        FamilyChild.deleted_at.is_(None)).all()]


def _has_parents(ind_id):
    return bool(_parent_families(ind_id))


def _has_children(ind_id):
    return any(_live_child_ids(f.id) for f in _spouse_families(ind_id))


# --- Pedigree / descendant graph slice ----------------------------------------

def graph(root_id, direction="both", depth=3):
    """A bounded graph slice around ``root_id``.

    direction: 'ancestors' | 'descendants' | 'both'. depth: generations each way
    (clamped to MAX_DEPTH). Returns nodes (the list-item shape + expandability
    flags) and edges (parent-child and partner), so the FE can render AND know
    where more exists to lazy-fetch."""
    _live_individual(root_id)
    if direction not in ("ancestors", "descendants", "both"):
        raise ApiError("direction must be ancestors, descendants, or both.", 400,
                       fields={"direction": "invalid"})
    depth = max(1, min(int(depth), MAX_DEPTH))

    node_ids = {root_id}
    edges = []
    seen_edges = set()

    def _add_partner_edge(fam):
        if fam.partner1_id and fam.partner2_id:
            key = ("partner", fam.id)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"type": "partner", "family_id": fam.id,
                              "partner1_id": fam.partner1_id,
                              "partner2_id": fam.partner2_id})

    def _add_parent_edge(parent_id, child_id, fam_id):
        key = ("pc", parent_id, child_id)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({"type": "parent-child", "parent_id": parent_id,
                          "child_id": child_id, "family_id": fam_id})

    # Walk UP (ancestors): each generation, add a person's parents.
    if direction in ("ancestors", "both"):
        frontier, gen = {root_id}, 0
        while frontier and gen < depth:
            nxt = set()
            for person in frontier:
                for fam in _parent_families(person):
                    _add_partner_edge(fam)
                    for parent in (fam.partner1_id, fam.partner2_id):
                        if parent is None:
                            continue
                        node_ids.add(parent)
                        _add_parent_edge(parent, person, fam.id)
                        nxt.add(parent)
            frontier, gen = nxt, gen + 1

    # Walk DOWN (descendants): each generation, add a person's children.
    if direction in ("descendants", "both"):
        frontier, gen = {root_id}, 0
        while frontier and gen < depth:
            nxt = set()
            for person in frontier:
                for fam in _spouse_families(person):
                    _add_partner_edge(fam)
                    for child in _live_child_ids(fam.id):
                        node_ids.add(child)
                        parent = person
                        _add_parent_edge(parent, child, fam.id)
                        nxt.add(child)
            frontier, gen = nxt, gen + 1

    nodes = []
    for ind in Individual.query.filter(Individual.id.in_(node_ids)).all():
        item = individual_service.serialize_list_item(ind)
        # Expandability flags drive the FE's lazy-fetch affordances.
        item["has_ancestors"] = _has_parents(ind.id)
        item["has_descendants"] = _has_children(ind.id)
        nodes.append(item)
    nodes.sort(key=lambda n: n["id"])

    return {"root_id": root_id, "direction": direction, "depth": depth,
            "nodes": nodes, "edges": edges}


# --- Relationship-path finder -------------------------------------------------

def _ancestor_depths(ind_id):
    """BFS UP the FAM links from ``ind_id``. Returns two dicts:
      depths[x]  = fewest generations from ind_id up to ancestor x (0 = self),
      prev[x]    = the node one step CLOSER to ind_id (for path reconstruction).
    BFS guarantees the first time we reach an ancestor is via a shortest path,
    which is what "nearest common ancestor" needs."""
    depths = {ind_id: 0}
    prev = {ind_id: None}
    frontier, gen = [ind_id], 0
    while frontier and gen < _SAFETY_GENERATIONS:
        nxt = []
        for person in frontier:
            for fam in _parent_families(person):
                for parent in (fam.partner1_id, fam.partner2_id):
                    if parent is not None and parent not in depths:
                        depths[parent] = gen + 1
                        prev[parent] = person
                        nxt.append(parent)
        frontier, gen = nxt, gen + 1
    return depths, prev


def _chain_up(prev, ancestor):
    """The id chain from an ancestor DOWN to the source (following prev pointers)."""
    chain, node = [], ancestor
    while node is not None:
        chain.append(node)
        node = prev[node]
    return chain  # [ancestor, …, source]


def _are_partners(a_id, b_id):
    return Family.query.filter(
        Family.deleted_at.is_(None),
        or_((Family.partner1_id == a_id) & (Family.partner2_id == b_id),
            (Family.partner1_id == b_id) & (Family.partner2_id == a_id))).first() is not None


def _spouses(ind_id):
    out = []
    for fam in _spouse_families(ind_id):
        other = fam.partner2_id if fam.partner1_id == ind_id else fam.partner1_id
        if other is not None:
            out.append(other)
    return out


def relationship(a_id, b_id):
    """Shortest blood path between two people + a plain-English label describing
    B relative to A. Blood lines are the priority; spouse/in-law are best-effort
    fallbacks when there's no common ancestor (Master Plan §4)."""
    _live_individual(a_id)
    _live_individual(b_id)

    if a_id == b_id:
        return _result(a_id, b_id, "self", None, 0, 0, [a_id])

    da, pa = _ancestor_depths(a_id)
    db_, pb = _ancestor_depths(b_id)
    commons = set(da) & set(db_)

    if commons:
        # Nearest common ancestor: smallest combined distance (then shallower, then id).
        nca = min(commons, key=lambda c: (da[c] + db_[c], max(da[c], db_[c]), c))
        d1, d2 = da[nca], db_[nca]
        label = _relationship_label(d1, d2)
        # Path: A up to the NCA, then down to B (drop the duplicated NCA).
        up = list(reversed(_chain_up(pa, nca)))        # [A, …, NCA]
        down = _chain_up(pb, nca)                        # [NCA, …, B]
        path = up + down[1:]
        return _result(a_id, b_id, label, nca, d1, d2, path)

    # No shared blood ancestor → spouse / in-law best effort.
    if _are_partners(a_id, b_id):
        return _result(a_id, b_id, "spouse", None, None, None, [a_id, b_id])
    # In-law: B shares blood with one of A's spouses (or vice versa).
    if any(_share_blood(sp, b_id) for sp in _spouses(a_id)) or \
       any(_share_blood(sp, a_id) for sp in _spouses(b_id)):
        return _result(a_id, b_id, "in-law", None, None, None, [])

    return _result(a_id, b_id, "no known relationship", None, None, None, [])


def _share_blood(x_id, y_id):
    dx, _ = _ancestor_depths(x_id)
    dy, _ = _ancestor_depths(y_id)
    return bool(set(dx) & set(dy))


def _result(a_id, b_id, label, nca_id, d1, d2, path):
    return {"a": a_id, "b": b_id, "relationship": label, "nca_id": nca_id,
            "distance_a": d1, "distance_b": d2, "path": path}


# --- English-label construction -----------------------------------------------

def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _greats(base, k):
    """base='grandparent', k=1→'grandparent', 2→'great-grandparent', … """
    return ("great-" * (k - 1)) + base


def _relationship_label(d1, d2):
    """Label B relative to A, where d1/d2 are A's/B's distance to the NCA."""
    if d1 == 0:                         # A IS the ancestor → B is A's descendant
        return _descendant_term(d2)
    if d2 == 0:                         # B IS the ancestor → B is A's ancestor
        return _ancestor_term(d1)

    lower, diff = min(d1, d2), abs(d1 - d2)
    degree = lower - 1                  # cousin degree (prompt's formula)
    if degree == 0:
        if diff == 0:
            return "sibling"
        # Label is B relative to A. If A is FARTHER from the NCA than B (d1 > d2),
        # B is the older generation → B is A's aunt/uncle; otherwise niece/nephew.
        term = "aunt/uncle" if d1 > d2 else "niece/nephew"
        return ("great-" * (diff - 1)) + term
    times = {0: "", 1: " once removed", 2: " twice removed"}.get(
        diff, f" {diff} times removed")
    return f"{_ordinal(degree)} cousin{times}"


def _ancestor_term(k):
    if k == 1:
        return "parent"
    if k == 2:
        return "grandparent"
    return _greats("grandparent", k - 1)   # k=3 → great-grandparent


def _descendant_term(k):
    if k == 1:
        return "child"
    if k == 2:
        return "grandchild"
    return _greats("grandchild", k - 1)     # k=3 → great-grandchild
