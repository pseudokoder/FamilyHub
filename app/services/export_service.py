"""Data export — the ZERO-DATA-LOSS guarantee for the v2 migration.

CLAUDE.md's promise: when FamilyHub v2 (Java/Spring Boot + MySQL) is built,
every memory, photo, comment, and wiki page moves over intact. This module
is that promise in code: `flask export-data` dumps EVERYTHING to a plain,
documented, portable format —

    export/familyhub-export-<timestamp>/
        data.json             every table, every row, as honest JSON
        files_manifest.json   every uploaded file: path, size, sha256
        README.txt            the format, documented inside the export itself

WHY JSON and not a SQL dump? A .sql file is welded to its database dialect;
JSON is readable by a future Java import tool, a Python script, or a human
in a text editor in 2040. Dates are ISO-8601 strings, ids are plain
integers — nothing SQLite-flavored survives into the export (D426
portability, the whole v2 design rule).

The sha256 hashes in the manifest let the v2 importer PROVE every photo
arrived unchanged — checksums are how you trust a copy you didn't watch
happen.
"""

import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from flask import current_app
from sqlalchemy import text

from app.extensions import db
from app.models import (
    AuditLog, Citation, Event, Family, FamilyChild, Individual, MediaLink,
    MediaObject, Name, Note, NoteLink, Place, Repository, SiteSetting, Source,
    User,
)

# Every model in the app, in an order a future importer can load without
# tripping over foreign keys. The rule: a table comes AFTER everything it
# points at. users first (media/notes/audit reference them); then the genealogy
# core parent-before-child (individuals before names, families before children,
# sources before citations); then the app's own tables. (WGU D426: respecting
# referential order is how you restore a relational backup without disabling
# constraints.)
EXPORTED_MODELS = [
    User,
    Individual, Name,
    Family, FamilyChild,
    Place,
    Event,
    Repository, Source, Citation,
    MediaObject, MediaLink,
    Note, NoteLink,
    SiteSetting, AuditLog,
]


def _serialize(value):
    """Coerce SQLAlchemy column values into JSON-friendly primitives.

    JSON can't hold datetimes or DECIMALs natively, so: datetimes become
    ISO-8601 strings (Java's LocalDateTime.parse reads them), and the DECIMAL
    lat/long on places become floats (a future importer reads them as doubles).
    Everything else (ints, strings, booleans, None) is already JSON-native."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _dump_table(model):
    """Every row of a model as plain dicts, via table introspection.

    TEACHING NOTE: model.__table__.columns is SQLAlchemy showing us a
    table's own structure at runtime — so ONE generic function exports
    every table, and a model added next month is exported automatically
    (one EXPORTED_MODELS entry, no new code)."""
    columns = [c.name for c in model.__table__.columns]
    return [
        {col: _serialize(getattr(row, col)) for col in columns}
        for row in model.query.all()
    ]


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        # Read in chunks: a 10 MB photo shouldn't need 10 MB of RAM to hash.
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_all():
    """Write a complete export; returns (out_dir, table_counts, file_count)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(
        current_app.config["EXPORT_FOLDER"], f"familyhub-export-{stamp}"
    )
    os.makedirs(out_dir, exist_ok=True)

    # --- data.json: every table -------------------------------------------
    # alembic_version only exists on databases managed via migrations.
    # Test databases are built with db.create_all(), so the table is absent.
    try:
        schema_version = db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    except Exception:
        schema_version = None
    tables = {model.__tablename__: _dump_table(model) for model in EXPORTED_MODELS}
    data = {
        "format": "familyhub-export",
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        # The migration revision this data shape corresponds to — the v2
        # importer can refuse exports it doesn't understand.
        "schema_version": schema_version,
        "tables": tables,
    }
    with open(os.path.join(out_dir, "data.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    # --- files_manifest.json: every uploaded file + checksum ---------------
    uploads = current_app.config["UPLOAD_FOLDER"]
    files = []
    for root, _dirs, names in os.walk(uploads):
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, uploads).replace(os.sep, "/")
            files.append(
                {"path": rel, "bytes": os.path.getsize(full), "sha256": _sha256(full)}
            )
    manifest = {
        "exported_at": data["exported_at"],
        "uploads_root": "uploads/",
        "file_count": len(files),
        "files": sorted(files, key=lambda f: f["path"]),
    }
    with open(
        os.path.join(out_dir, "files_manifest.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(manifest, fh, indent=2)

    # --- README.txt: the format documents itself ----------------------------
    counts = {name: len(rows) for name, rows in tables.items()}
    readme = (
        "FamilyHub data export (format_version 1)\n"
        "=========================================\n\n"
        "data.json            every database table as JSON. Dates are ISO-8601,\n"
        "                     ids are integers, foreign keys keep their names\n"
        "                     (individual_id, source_id, ...). Polymorphic links\n"
        "                     (events, citations, media_links, note_links) carry a\n"
        "                     subject_type + subject_id pair instead of a single FK.\n"
        "files_manifest.json  every uploaded file with size and sha256 checksum.\n"
        "                     Paths are relative to the uploads folder; a media\n"
        "                     object's file_path column points at the same file.\n\n"
        "NOTE: users includes bcrypt password_hash values so logins survive the\n"
        "v2 migration (Spring Security reads bcrypt natively). Treat this export\n"
        "as SENSITIVE — it is the whole family archive in one folder.\n\n"
        "Row counts at export time:\n"
        + "".join(f"  {name}: {count}\n" for name, count in counts.items())
    )
    with open(os.path.join(out_dir, "README.txt"), "w", encoding="utf-8") as fh:
        fh.write(readme)

    return out_dir, counts, len(files)
