"""Backups: package the database + every uploaded photo into one zip,
verify it's restorable, and (in production) ship it to a Lightsail bucket.

CLAUDE.md is blunt: backups are a REQUIRED FEATURE, not an afterthought.
A family archive that can be lost in one disk failure isn't an archive.

The backup contract — every zip contains:
    familyhub.db     a CONSISTENT snapshot of the SQLite database
    uploads/...      every uploaded file, same relative paths as on disk
    manifest.json    what's inside (counts, sizes, timestamp) — so a backup
                     can prove its own completeness years later

Three rules learned from every backup horror story ever told:
  1. A backup you haven't VERIFIED is a hope, not a backup -> verify_backup()
  2. A backup on the same disk as the data dies WITH the data -> upload_backup()
  3. A restore you've never PRACTICED will fail at 2am -> restore_backup(),
     tested in this repo's history (see DEVDIARY Chapter 8)
"""

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone

from flask import current_app


def _db_path():
    """The SQLite file's location, extracted from the SQLAlchemy URI."""
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        # v2 note: with MySQL this becomes mysqldump instead.
        raise RuntimeError("Backups support the SQLite database only in v1.")
    return uri.replace("sqlite:///", "", 1)


def _backup_dir():
    path = current_app.config["BACKUP_FOLDER"]
    os.makedirs(path, exist_ok=True)
    return path


# --- Creating ------------------------------------------------------------------

def create_backup():
    """Build a timestamped backup zip; returns its path.

    THE SUBTLE PART: you can't just copy a live SQLite file — a write
    happening mid-copy leaves you with a corrupt half-old-half-new file.
    sqlite3's backup() API takes a CONSISTENT snapshot even while the app
    is running (it briefly coordinates with the database's own locking).
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    zip_path = os.path.join(_backup_dir(), f"familyhub-backup-{stamp}.zip")

    # 1. Consistent DB snapshot into a temp file.
    tmp_fd, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    src = sqlite3.connect(_db_path())
    dst = sqlite3.connect(tmp_db)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()

    # 2. Zip: snapshot + every uploaded file + the manifest.
    uploads = current_app.config["UPLOAD_FOLDER"]
    entries = []
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "familyhub.db")
            for root, _dirs, files in os.walk(uploads):
                for fname in files:
                    full = os.path.join(root, fname)
                    # Forward slashes in archives — the zip standard, and it
                    # keeps a backup made on Windows restorable on Linux.
                    rel = os.path.relpath(full, uploads).replace(os.sep, "/")
                    zf.write(full, f"uploads/{rel}")
                    entries.append(
                        {"path": f"uploads/{rel}", "bytes": os.path.getsize(full)}
                    )
            manifest = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "database": "familyhub.db",
                "db_bytes": os.path.getsize(tmp_db),
                "file_count": len(entries),
                "files": entries,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    finally:
        os.remove(tmp_db)
    return zip_path


# --- Verifying --------------------------------------------------------------------

def verify_backup(zip_path):
    """Prove the backup is restorable. Returns a report dict with 'ok',
    'problems' (list), and some human-friendly counts."""
    report = {"ok": False, "problems": [], "file_count": 0, "db_tables": 0}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            # CRC-checks EVERY member — catches silent corruption.
            bad_member = zf.testzip()
            if bad_member:
                report["problems"].append(f"Corrupt entry in zip: {bad_member}")

            names = set(zf.namelist())
            if "manifest.json" not in names:
                report["problems"].append("manifest.json is missing.")
                return report
            manifest = json.loads(zf.read("manifest.json"))

            missing = [f["path"] for f in manifest["files"] if f["path"] not in names]
            if missing:
                report["problems"].append(
                    f"{len(missing)} file(s) in the manifest are missing from the zip."
                )
            report["file_count"] = manifest["file_count"]

            # The real test: does the database INSIDE the zip actually open
            # and pass SQLite's own integrity check?
            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extract("familyhub.db", tmpdir)
                con = sqlite3.connect(os.path.join(tmpdir, "familyhub.db"))
                try:
                    result = con.execute("PRAGMA integrity_check").fetchone()[0]
                    if result != "ok":
                        report["problems"].append(f"DB integrity check failed: {result}")
                    report["db_tables"] = con.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                    ).fetchone()[0]
                finally:
                    con.close()
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, sqlite3.Error) as err:
        report["problems"].append(f"Could not read the backup: {err}")
        return report

    report["ok"] = not report["problems"]
    return report


# --- Off-site upload -----------------------------------------------------------------

def upload_backup(zip_path):
    """Ship the zip to the Lightsail bucket, if one is configured.

    Returns (uploaded?, message). Locally there's no bucket and that's fine —
    the admin page says so honestly instead of erroring. On the server,
    .env sets BACKUP_S3_BUCKET (+ AWS keys) and this becomes the off-site
    copy that survives the instance dying.
    """
    bucket = os.environ.get("BACKUP_S3_BUCKET", "").strip()
    if not bucket:
        return False, (
            "No off-site bucket configured (BACKUP_S3_BUCKET) — "
            "the backup is saved on this machine only."
        )
    # Imported here, not at the top: boto3 is a big library that only this
    # one path needs. boto3 reads AWS credentials from the environment.
    import boto3

    key = f"backups/{os.path.basename(zip_path)}"
    boto3.client("s3").upload_file(zip_path, bucket, key)
    return True, f"Uploaded off-site to s3://{bucket}/{key}"


# --- Listing & restoring ------------------------------------------------------------

def list_backups():
    """Local backup zips, newest first, with human-useful facts."""
    backups = []
    directory = _backup_dir()
    for name in os.listdir(directory):
        if name.endswith(".zip"):
            full = os.path.join(directory, name)
            backups.append(
                {
                    "filename": name,
                    "bytes": os.path.getsize(full),
                    "created": datetime.fromtimestamp(os.path.getmtime(full)),
                }
            )
    backups.sort(key=lambda b: b["created"], reverse=True)
    return backups


def restore_backup(zip_path):
    """Replace the live database and uploads with a backup's contents.

    DESTRUCTIVE — CLI-only on purpose (flask restore-backup), never a web
    button someone can click by accident. Safety nets:
      * refuses to restore a backup that fails verification
      * parks the current DB as familyhub.db.pre-restore first
      * ignores any zip entry that would escape the uploads folder
        ("zip-slip" — only matters for zips we didn't make, but cheap)
    In production: stop gunicorn first, restore, start it again.
    """
    report = verify_backup(zip_path)
    if not report["ok"]:
        raise RuntimeError(
            "Refusing to restore a backup that fails verification: "
            + "; ".join(report["problems"])
        )

    db_path = _db_path()
    uploads = os.path.normpath(current_app.config["UPLOAD_FOLDER"])

    if os.path.exists(db_path):
        shutil.copy2(db_path, db_path + ".pre-restore")

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("familyhub.db") as src, open(db_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        for name in zf.namelist():
            if not name.startswith("uploads/"):
                continue
            target = os.path.normpath(os.path.join(uploads, name[len("uploads/"):]))
            if not target.startswith(uploads):
                continue  # zip-slip guard
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return report
