"""Backup + export tests — the round-trip restore, now automated forever.

DEVDIARY Chapter 8 says a restore "tested once" beats a restore tested
never. This file upgrades that: the round trip now runs on EVERY pytest
run, so backup code can't silently rot.
"""

import hashlib
import json
import os
import zipfile

from app.extensions import db
from app.models import Photo, SiteSetting
from app.services import backup_service, export_service, photo_service
from tests.conftest import make_image


def _seed_photo(admin_client):
    response = admin_client.post(
        "/albums/new", data={"title": "Seed", "description": ""}, follow_redirects=False
    )
    album_url = response.headers["Location"]
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "keeper.jpg")]},
        content_type="multipart/form-data",
    )


def test_backup_contains_db_uploads_and_manifest(admin_client, app):
    _seed_photo(admin_client)
    zip_path = backup_service.create_backup()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "familyhub.db" in names
        assert "manifest.json" in names
        uploads = [n for n in names if n.startswith("uploads/")]
        assert len(uploads) == 2  # the photo + its thumbnail
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["file_count"] == 2


def test_verify_passes_on_good_backup(admin_client, app):
    _seed_photo(admin_client)
    report = backup_service.verify_backup(backup_service.create_backup())
    assert report["ok"], report["problems"]
    assert report["db_tables"] > 5


def test_verify_fails_on_corrupt_backup(app, tmp_path):
    """An unverified backup is a hope — prove the verifier actually catches
    damage by handing it garbage."""
    garbage = tmp_path / "broken.zip"
    garbage.write_bytes(b"this was never a zip file")
    report = backup_service.verify_backup(str(garbage))
    assert not report["ok"]
    assert report["problems"]


def test_restore_round_trip(admin_client, app):
    """The headline test: change AFTER the backup must vanish on restore,
    and the photo files must come back byte-for-byte."""
    _seed_photo(admin_client)
    photo = Photo.query.one()
    full_path, _ = photo_service.photo_paths(photo)
    original_bytes = open(full_path, "rb").read()

    zip_path = backup_service.create_backup()

    # Mutate the world after the backup: new row + deleted photo file.
    db.session.add(SiteSetting(key="marker", value="added after backup"))
    db.session.commit()
    os.remove(full_path)

    report = backup_service.restore_backup(zip_path)
    assert report["ok"]

    # SQLAlchemy still holds pre-restore state in its session cache — drop it
    # and look at the restored database with fresh eyes.
    db.session.remove()
    assert db.session.get(SiteSetting, "marker") is None, "post-backup row gone"
    assert open(full_path, "rb").read() == original_bytes, "photo back, byte-identical"


def test_restore_refuses_unverifiable_zip(app, tmp_path):
    garbage = tmp_path / "evil.zip"
    garbage.write_bytes(b"nope")
    try:
        backup_service.restore_backup(str(garbage))
        assert False, "should have raised"
    except RuntimeError as err:
        assert "Refusing to restore" in str(err)


def test_export_format(admin_client, app):
    _seed_photo(admin_client)
    out_dir, counts, file_count = export_service.export_all()

    data = json.load(open(os.path.join(out_dir, "data.json"), encoding="utf-8"))
    assert data["format"] == "familyhub-export"
    assert counts["photos"] == 1 and counts["users"] == 1
    # bcrypt hashes ride along so logins survive the v2 migration.
    assert data["tables"]["users"][0]["password_hash"].startswith("$2b$")
    # ISO-8601 dates — Java's LocalDateTime.parse reads these natively.
    assert "T" in data["tables"]["users"][0]["created_at"]

    manifest = json.load(open(os.path.join(out_dir, "files_manifest.json")))
    assert manifest["file_count"] == file_count == 2
    # The checksum promise: hash in the manifest == hash of the actual file.
    entry = manifest["files"][0]
    actual = hashlib.sha256(
        open(os.path.join(app.config["UPLOAD_FOLDER"], entry["path"]), "rb").read()
    ).hexdigest()
    assert entry["sha256"] == actual
