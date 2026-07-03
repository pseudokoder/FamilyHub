"""source_service — the evidence layer's documents: repositories and sources.

A repository (an archive) holds many sources (documents); a source is cited by
many facts (see source.py). Deleting a repository nulls its sources' pointer (the
SET NULL the app does for SQLite); deleting a source is a SOFT delete (ADR-0001)
that keeps its citations intact so a restore brings the evidence back.
"""

from app.extensions import db
from app.models import Repository, Source
from app.services import write_control


# --- Repositories -------------------------------------------------------------

def serialize_repository(repo):
    return {
        "id": repo.id,
        "gedcom_xref": repo.gedcom_xref,
        "name": repo.name,
        "address": repo.address,
        "website": repo.website,
        "sources_count": len(repo.sources),
    }


def list_repositories():
    return [serialize_repository(r)
            for r in Repository.query.order_by(Repository.name).all()]


def get_repository(repo_id):
    from app.routes.api import get_or_404
    return serialize_repository(get_or_404(Repository, repo_id, "repository"))


def create_repository(data):
    from app.routes.api import require
    require(data, "name")
    repo = Repository(
        name=data.get("name"),
        address=data.get("address") or None,
        website=data.get("website") or None,
        gedcom_xref=data.get("gedcom_xref") or None,
    )
    db.session.add(repo)
    db.session.commit()
    return serialize_repository(repo)


def update_repository(repo_id, data):
    from app.routes.api import get_or_404
    repo = get_or_404(Repository, repo_id, "repository")
    for field in ("name", "address", "website", "gedcom_xref"):
        if field in data:
            setattr(repo, field, data.get(field) or None)
    db.session.commit()
    return serialize_repository(repo)


def delete_repository(repo_id):
    from app.routes.api import get_or_404
    repo = get_or_404(Repository, repo_id, "repository")
    # Detach sources first (SET NULL the app enforces), then remove the archive.
    Source.query.filter_by(repository_id=repo.id).update({"repository_id": None})
    db.session.delete(repo)
    db.session.commit()


# --- Sources ------------------------------------------------------------------

def _validate_repository(repository_id):
    from app.services.api_errors import ApiError
    if repository_id is None:
        return None
    if db.session.get(Repository, repository_id) is None:
        raise ApiError(f"No repository with id {repository_id}.", 400,
                       fields={"repository_id": "no such repository"})
    return repository_id


def serialize_source(source):
    return {
        "id": source.id,
        "gedcom_xref": source.gedcom_xref,
        "title": source.title,
        "author": source.author,
        "publication": source.publication,
        "repository_id": source.repository_id,
        "repository": source.repository.name if source.repository else None,
        "citations_count": sum(1 for c in source.citations if not c.is_deleted),
    }


def list_sources():
    return [serialize_source(s) for s in Source.query
            .filter(Source.deleted_at.is_(None))
            .order_by(Source.title).all()]


def get_source(source_id):
    from app.routes.api import get_or_404
    return serialize_source(get_or_404(Source, source_id, "source"))


def create_source(data):
    from app.routes.api import require
    require(data, "title")
    source = Source(
        title=data.get("title"),
        author=data.get("author") or None,
        publication=data.get("publication") or None,
        repository_id=_validate_repository(data.get("repository_id")),
        gedcom_xref=data.get("gedcom_xref") or None,
    )
    db.session.add(source)
    db.session.flush()
    write_control.log_create("source", source)
    db.session.commit()
    return serialize_source(source)


def update_source(source_id, data):
    from app.routes.api import get_or_404
    source = get_or_404(Source, source_id, "source")
    before = write_control.snapshot(source)
    for field in ("title", "author", "publication", "gedcom_xref"):
        if field in data:
            setattr(source, field, data.get(field) or None)
    if "repository_id" in data:
        source.repository_id = _validate_repository(data.get("repository_id"))
    write_control.log_update("source", source, before)
    db.session.commit()
    return serialize_source(source)


def delete_source(source_id):
    from app.routes.api import get_or_404
    # SOFT delete + audit (ADR-0001). Its citations stay intact (not cascade-
    # removed) so restoring the source brings its evidence back with it.
    source = get_or_404(Source, source_id, "source")
    write_control.soft_delete("source", source)
