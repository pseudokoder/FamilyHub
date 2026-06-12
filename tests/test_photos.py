"""Photo album tests — uploads simulated with generated sample files.

This is the file-upload security model from DEVDIARY Chapter 3, encoded as
tests: allow-list + content verification + UUID names + login-walled
serving. Plus the elderly-first behaviors (forgiving batches, friendly
messages).
"""

import io
import os

from PIL import Image

from app.extensions import db
from app.models import Album, Photo
from app.services import photo_service
from tests.conftest import make_fake_image, make_image


def _create_album(client, title="Test Album"):
    response = client.post(
        "/albums/new", data={"title": title, "description": ""},
        follow_redirects=False,
    )
    return response.headers["Location"]  # /albums/<id>


def test_create_album(admin_client):
    location = _create_album(admin_client, "Thanksgiving 1987")
    response = admin_client.get(location)
    assert b"Thanksgiving 1987" in response.data
    assert b"album is empty" in response.data


def test_upload_jpg_png_and_heic(admin_client, app):
    """A mixed batch like a real family would send — including iPhone HEIC."""
    album_url = _create_album(admin_client)
    response = admin_client.post(
        album_url + "/photos",
        data={"photos": [
            (make_image("JPEG"), "vacation.jpg"),
            (make_image("PNG"), "scan.png"),
            (make_image("HEIF"), "IMG_0042.heic"),
        ]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"3 photos added" in response.data

    photos = Photo.query.all()
    assert len(photos) == 3
    for photo in photos:
        full_path, thumb_path = photo_service.photo_paths(photo)
        assert os.path.exists(full_path), "original file on disk"
        assert os.path.exists(thumb_path), "thumbnail on disk"
        # UUID names: never the user's filename on disk.
        assert photo.original_filename not in photo.filename

    heic = Photo.query.filter_by(original_filename="IMG_0042.heic").one()
    assert heic.filename.endswith(".jpg"), "HEIC converted to JPEG at the door"
    full_path, _ = photo_service.photo_paths(heic)
    assert Image.open(full_path).format == "JPEG"


def test_bad_files_rejected_good_file_still_saved(admin_client):
    """Forgiving batches: one good photo among junk still makes it in,
    and each reject gets its own named, friendly explanation."""
    album_url = _create_album(admin_client)
    response = admin_client.post(
        album_url + "/photos",
        data={"photos": [
            (make_fake_image(), "corrupt.jpg"),          # wrong bytes
            (io.BytesIO(b"MZ\x90\x00"), "virus.exe"),     # wrong extension
            (io.BytesIO(b"MZ\x90\x00"), "sneaky.jpg.exe"),  # double extension
            (make_image("JPEG"), "good.jpg"),
        ]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"1 photo added" in response.data
    assert b"corrupt.jpg" in response.data and b"damaged" in response.data
    assert b"virus.exe" in response.data
    assert Photo.query.count() == 1


def test_empty_upload_gets_friendly_nudge(admin_client):
    album_url = _create_album(admin_client)
    response = admin_client.post(
        album_url + "/photos", data={}, follow_redirects=True
    )
    assert b"No photos were chosen" in response.data


def test_exif_sideways_photo_gets_portrait_thumbnail(admin_client, app):
    """A landscape-stored file with EXIF 'rotate me' must thumbnail as
    portrait — the sideways-grandma defense from DEVDIARY Chapter 3."""
    album_url = _create_album(admin_client)
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image("JPEG", size=(800, 400), orientation=6), "sideways.jpg")]},
        content_type="multipart/form-data",
    )
    photo = Photo.query.one()
    _, thumb_path = photo_service.photo_paths(photo)
    width, height = Image.open(thumb_path).size
    assert height > width


def test_photo_bytes_are_login_walled(admin_client, app):
    album_url = _create_album(admin_client)
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "p.jpg")]},
        content_type="multipart/form-data",
    )
    photo_id = Photo.query.one().id

    anon = app.test_client()
    for route in (f"/photos/{photo_id}/file", f"/photos/{photo_id}/thumb"):
        assert anon.get(route).status_code == 302, "anonymous gets login redirect"
        response = admin_client.get(route)
        assert response.status_code == 200
        assert response.content_type.startswith("image/")


def test_comments(admin_client):
    album_url = _create_album(admin_client)
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "p.jpg")]},
        content_type="multipart/form-data",
    )
    photo_id = Photo.query.one().id
    response = admin_client.post(
        f"/photos/{photo_id}/comments",
        data={"body": "Is that Aunt Ruth on the left?"},
        follow_redirects=True,
    )
    assert b"Aunt Ruth" in response.data


def test_delete_rules_and_disk_cleanup(admin_client, member_client, app):
    """Authorization: a member can't delete the admin's photo; the uploader
    (or admin) can — and deletion removes the files, not just the row."""
    album_url = _create_album(admin_client)
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "admins.jpg")]},
        content_type="multipart/form-data",
    )
    photo = Photo.query.one()
    full_path, thumb_path = photo_service.photo_paths(photo)

    assert member_client.post(f"/photos/{photo.id}/delete").status_code == 403

    response = admin_client.post(f"/photos/{photo.id}/delete", follow_redirects=True)
    assert b"Photo deleted" in response.data
    assert Photo.query.count() == 0
    assert not os.path.exists(full_path) and not os.path.exists(thumb_path)


def test_album_cover_is_first_photo(admin_client):
    album_url = _create_album(admin_client)
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(color=(255, 0, 0)), "first.jpg"),
                         (make_image(color=(0, 255, 0)), "second.jpg")]},
        content_type="multipart/form-data",
    )
    album = Album.query.one()
    assert album.cover_photo.original_filename == "first.jpg"
