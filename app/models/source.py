"""Sources, citations, and repositories — genealogy's evidence layer.

WHAT MAKES GENEALOGY DIFFERENT FROM A CONTACT LIST: every claim ("born 1850")
should be backed by EVIDENCE. GEDCOM models this with three records:

    REPOSITORY  — *where* a source physically lives (an archive, a library,
                  Ancestry.com). One repository holds many sources.
    SOURCE      — a whole document (a census, a birth certificate, a family
                  bible). One source backs many facts.
    CITATION    — the precise pointer from ONE fact to ONE source ("1880 US
                  Census, p. 42, line 7"), plus how trustworthy it is.

So the chain is: a citation cites a source, which sits in a repository. This
mirrors how a historian footnotes a claim — and it's three tables because each
is a distinct real-world thing that's reused independently (WGU D426).

v2 mapping: three `@Entity` classes with `@ManyToOne` links up the chain.
"""

from app.extensions import db
from app.models.mixins import SoftDeleteMixin


class Repository(db.Model):
    """An archive or library where sources live — GEDCOM REPO."""

    __tablename__ = "repositories"

    id = db.Column(db.Integer, primary_key=True)
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)  # @R1@
    name = db.Column(db.String(255))
    address = db.Column(db.String(500))
    website = db.Column(db.String(255))

    sources = db.relationship("Source", back_populates="repository")

    def __repr__(self):
        return f"<Repository #{self.id} {self.name!r}>"


class Source(SoftDeleteMixin, db.Model):
    """A whole source document — GEDCOM SOUR."""

    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    gedcom_xref = db.Column(db.String(20), unique=True, nullable=True)  # @S1@
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    publication = db.Column(db.String(255))

    # SET NULL: a source can outlive the record of where it was found.
    repository_id = db.Column(
        db.Integer, db.ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
    )

    repository = db.relationship("Repository", back_populates="sources")
    # Delete a source and its citations go too — a citation pointing at a
    # source that no longer exists is a dangling footnote.
    citations = db.relationship(
        "Citation", back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Source #{self.id} {self.title!r}>"


class Citation(SoftDeleteMixin, db.Model):
    """One fact's pointer to one source — GEDCOM SOURCE_CITATION.

    POLYMORPHIC, like Event: a citation can back an individual, a family, an
    event, or even a specific name ("this surname spelling per the parish
    register"). Same subject_type + subject_id mechanism, same trade-off (the
    app maintains the link; see genealogy_service).
    """

    __tablename__ = "citations"

    id = db.Column(db.Integer, primary_key=True)

    # CASCADE: handled from the Source side above; the DB-level rule makes it
    # true for direct SQL / MySQL too.
    source_id = db.Column(
        db.Integer, db.ForeignKey("sources.id", ondelete="CASCADE"), nullable=True
    )

    # 'individual' | 'family' | 'event' | 'name'
    subject_type = db.Column(db.String(20), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)

    page = db.Column(db.String(255))   # "p. 42" / film & frame numbers
    # GEDCOM QUAY: evidence quality 0 (unreliable) – 3 (direct/primary). A tiny
    # integer that lets a careful researcher rank conflicting evidence.
    quality = db.Column(db.Integer)
    notes = db.Column(db.Text)

    source = db.relationship("Source", back_populates="citations")

    __table_args__ = (
        db.Index("ix_citations_subject", "subject_type", "subject_id"),
    )

    def __repr__(self):
        return (f"<Citation #{self.id} src={self.source_id} "
                f"{self.subject_type}#{self.subject_id}>")
