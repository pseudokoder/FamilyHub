"""API tests: /api/media — upload, EXIF/GPS stripping, login-walled serving."""

import os

from PIL import Image

from app.extensions import db
from app.models import MediaObject
from app.services import media_service
from tests.conftest import make_fake_image, make_image


def _upload(client, fileobj=None, name="photo.jpg", **fields):
    data = {"file": (fileobj or make_image(), name)}
    data.update(fields)
    return client.post("/api/media", data=data, content_type="multipart/form-data")


def test_upload_and_serve(member_client):
    response = _upload(member_client, title="Portrait")
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Portrait"
    assert data["media_type"] == "image/jpeg"

    # The bytes are served (login-walled), full size and thumbnail.
    assert member_client.get(f"/api/media/{data['id']}/file").status_code == 200
    assert member_client.get(f"/api/media/{data['id']}/thumb").status_code == 200


def test_serving_is_login_walled(client, member_client):
    media_id = _upload(member_client).get_json()["id"]
    # An anonymous client gets 401 — a family photo is never public.
    assert client.get(f"/api/media/{media_id}/file").status_code == 401


def test_upload_strips_gps(member_client):
    """The privacy headline: a phone photo's GPS coordinates must NOT survive
    the upload (rule 5 — re-encode through Pillow, drop the EXIF block)."""
    media_id = _upload(member_client, make_image(gps=True), "geotagged.jpg").get_json()["id"]
    media = db.session.get(MediaObject, media_id)
    stored = Image.open(media_service.disk_path(media))
    exif = stored.getexif()
    stored.close()
    assert 0x8825 not in exif  # 0x8825 = the GPS sub-directory pointer


def test_rejects_non_image(member_client):
    response = _upload(member_client, make_fake_image(), "virus.jpg")
    assert response.status_code == 400


def test_upload_requires_a_file(member_client):
    response = member_client.post(
        "/api/media", data={"title": "no file"}, content_type="multipart/form-data")
    assert response.status_code == 400


def test_media_links_inline_and_managed(member_client):
    pid = member_client.post(
        "/api/individuals", json={"name": {"given": "Jo"}}).get_json()["id"]
    media_id = _upload(
        member_client, subject_type="individual", subject_id=str(pid)
    ).get_json()["id"]

    got = member_client.get(f"/api/media/{media_id}").get_json()
    assert got["links"][0]["subject_label"] == "Jo"

    dup = member_client.post(f"/api/media/{media_id}/links",
                             json={"subject_type": "individual", "subject_id": pid})
    assert dup.status_code == 409
    assert member_client.delete(
        f"/api/media/{media_id}/links/individual/{pid}").status_code == 204


def test_delete_removes_files_from_disk(member_client):
    media_id = _upload(member_client).get_json()["id"]
    media = db.session.get(MediaObject, media_id)
    path = media_service.disk_path(media)
    assert os.path.exists(path)

    member_client.delete(f"/api/media/{media_id}")
    assert not os.path.exists(path)
