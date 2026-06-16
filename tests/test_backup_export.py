"""Backup + export tests — the round-trip restore, now automated forever.

A restore "tested once" beats a restore tested never; this file upgrades that:
the round trip runs on EVERY pytest run, so the backup code can't silently rot.

WP1 NOTE: these used to seed data by uploading a photo through the (now removed)
album routes. They now seed via `seed_all()` (the GEDCOM-7 mock data) plus one
dummy uploaded file — proving backup/export work against the new schema.
"""

import hashlib
import json
import os
import zipfile

from app.extensions import db
from app.models import SiteSetting
from app.services import backup_service, export_service
from seed import seed_all


def _make_upload(app, rel="media/keeper.jpg", content=b"pretend image bytes"):
    """Drop one file into the uploads folder so the backup/export have a file
    to capture (the real media upload pipeline returns in WP2)."""
    path = os.path.join(app.config["UPLOAD_FOLDER"], *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content)
    return path


def test_backup_contains_db_uploads_and_manifest(app, admin):
    seed_all()
    _make_upload(app)
    zip_path = backup_service.create_backup()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "familyhub.db" in names
        assert "manifest.json" in names
        uploads = [n for n in names if n.startswith("uploads/")]
        assert len(uploads) == 1  # the one file we dropped in
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["file_count"] == 1


def test_verify_passes_on_good_backup(app, admin):
    seed_all()
    report = backup_service.verify_backup(backup_service.create_backup())
    assert report["ok"], report["problems"]
    # The GEDCOM-7 schema has well over a dozen tables — far more than 5.
    assert report["db_tables"] > 5


def test_verify_fails_on_corrupt_backup(app, tmp_path):
    """An unverified backup is a hope — prove the verifier actually catches
    damage by handing it garbage."""
    garbage = tmp_path / "broken.zip"
    garbage.write_bytes(b"this was never a zip file")
    report = backup_service.verify_backup(str(garbage))
    assert not report["ok"]
    assert report["problems"]


def test_restore_round_trip(app, admin):
    """The headline test: change AFTER the backup must vanish on restore,
    and the uploaded file must come back byte-for-byte."""
    seed_all()
    full_path = _make_upload(app)
    original_bytes = open(full_path, "rb").read()

    zip_path = backup_service.create_backup()

    # Mutate the world after the backup: new row + deleted file.
    db.session.add(SiteSetting(setting_key="marker", setting_value="added after backup"))
    db.session.commit()
    os.remove(full_path)

    report = backup_service.restore_backup(zip_path)
    assert report["ok"]

    # SQLAlchemy still holds pre-restore state in its session cache — drop it
    # and look at the restored database with fresh eyes.
    db.session.remove()
    assert db.session.get(SiteSetting, "marker") is None, "post-backup row gone"
    assert open(full_path, "rb").read() == original_bytes, "file back, byte-identical"


def test_restore_refuses_unverifiable_zip(app, tmp_path):
    garbage = tmp_path / "evil.zip"
    garbage.write_bytes(b"nope")
    try:
        backup_service.restore_backup(str(garbage))
        assert False, "should have raised"
    except RuntimeError as err:
        assert "Refusing to restore" in str(err)


def test_export_format(app, admin):
    seed_all()
    _make_upload(app)
    out_dir, counts, file_count = export_service.export_all()

    data = json.load(open(os.path.join(out_dir, "data.json"), encoding="utf-8"))
    assert data["format"] == "familyhub-export"
    # The export covers the new schema: the admin account plus seeded people.
    assert counts["users"] == 1
    assert counts["individuals"] >= 1
    # bcrypt hashes ride along so logins survive the v2 migration.
    assert data["tables"]["users"][0]["password_hash"].startswith("$2b$")
    # ISO-8601 dates — Java's LocalDateTime.parse reads these natively.
    assert "T" in data["tables"]["users"][0]["created_at"]

    manifest = json.load(open(os.path.join(out_dir, "files_manifest.json")))
    assert manifest["file_count"] == file_count == 1
    # The checksum promise: hash in the manifest == hash of the actual file.
    entry = manifest["files"][0]
    actual = hashlib.sha256(
        open(os.path.join(app.config["UPLOAD_FOLDER"], entry["path"]), "rb").read()
    ).hexdigest()
    assert entry["sha256"] == actual
