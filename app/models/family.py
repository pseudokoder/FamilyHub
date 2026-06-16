"""Families — the GEDCOM FAM record that wires individuals into a tree.

THE INSIGHT: a family tree is a GRAPH, and the trickiest part is the
parent↔child relationship, which is **many-to-many**. One child has (usually)
two parents; one couple has many children; and people remarry, blend families,
adopt. You cannot model that with a "parent_id" column on the person.

GEDCOM's solution — which we copy — is to make the *family* a first-class
record. A `families` row links the two partners; a `family_children` row links
each child to that family. Walk partner→family→children to go down the tree,
or child→family→partners to go up. (WGU D426: resolving a many-to-many with a
junction table is the canonical relational pattern.)

v2 mapping: `Family` is an `@Entity`; `family_children` becomes a `@OneToMany`
of an association entity (Hibernate's answer to the same junction table).
"""

from app.extensions import db
from app.models.individual import _utcnow


class Family(db.Model):
    """A partnership that may have children — GEDCOM's FAM record."""

    __tablename__ = "families"

    id = db.Column(db.Integer, primary_key=True)
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)  # @F1@

    # The two partners. GEDCOM calls these HUSB and WIFE, but the Master Plan
    # is deliberate (§3): do NOT infer sex, gender, or role from which slot a
    # person sits in. partner1/partner2 are just "the two people," nothing more.
    #
    # ON DELETE SET NULL: if an individual is deleted, the family survives with
    # an empty partner slot rather than vanishing — we'd rather keep the marriage
    # record and its children than cascade-delete a whole branch by accident.
    partner1_id = db.Column(
        db.Integer, db.ForeignKey("individuals.id", ondelete="SET NULL"),
        nullable=True,
    )
    partner2_id = db.Column(
        db.Integer, db.ForeignKey("individuals.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # foreign_keys is REQUIRED here: there are two FKs to the same table
    # (individuals), so SQLAlchemy can't guess which column powers which
    # relationship. We tell it explicitly.
    partner1 = db.relationship("Individual", foreign_keys=[partner1_id])
    partner2 = db.relationship("Individual", foreign_keys=[partner2_id])

    children = db.relationship(
        "FamilyChild",
        back_populates="family",
        cascade="all, delete-orphan",
        order_by="FamilyChild.child_order",
    )

    def __repr__(self):
        return f"<Family #{self.id} ({self.partner1_id} + {self.partner2_id})>"


class FamilyChild(db.Model):
    """One child's membership in one family — GEDCOM's FAM.CHIL link.

    This is an ASSOCIATION OBJECT: a junction-table row that also carries data
    of its own (how the child joined the family, and their birth order). A bare
    many-to-many table would only hold the two ids; we need `pedigree_type`
    too, so it gets a full model.
    """

    __tablename__ = "family_children"

    # COMPOSITE PRIMARY KEY: the pair (family, child) is itself the identity —
    # a child can't be in the same family twice, and the database guarantees it.
    # No surrogate id needed.
    family_id = db.Column(
        db.Integer, db.ForeignKey("families.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_id = db.Column(
        db.Integer, db.ForeignKey("individuals.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # How this child belongs: birth, adopted, foster, step. The genealogical
    # truth matters — an adopted child and a birth child are both real children
    # but the record should say which.
    pedigree_type = db.Column(db.String(20), nullable=False, default="birth")
    # GEDCOM convention: children listed in birth order.
    child_order = db.Column(db.Integer, nullable=False, default=0)

    family = db.relationship("Family", back_populates="children")
    child = db.relationship("Individual")

    def __repr__(self):
        return f"<FamilyChild fam={self.family_id} child={self.child_id}>"
