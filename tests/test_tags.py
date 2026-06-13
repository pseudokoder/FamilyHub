"""Photo-tagging tests: the photo↔wiki bridge works in both directions,
duplicates are friendly, and cascades clean up after themselves."""

from app.models import FamilyMember, Photo, PhotoTag
from tests.conftest import make_image


def _photo_and_person(admin_client):
    album_url = admin_client.post(
        "/albums/new", data={"title": "Reunion", "description": ""},
        follow_redirects=False,
    ).headers["Location"]
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "group_shot.jpg")]},
        content_type="multipart/form-data",
    )
    admin_client.post(
        "/family/new",
        data={"name": "Ruth Leiter", "location": "", "bio": "",
              "birth_date": "", "death_date": ""},
    )
    return Photo.query.one(), FamilyMember.query.one()


def test_tag_appears_on_photo_and_wiki_page(admin_client, member_client):
    photo, ruth = _photo_and_person(admin_client)

    # A DIFFERENT member tags — naming faces is collaborative.
    response = member_client.post(
        f"/photos/{photo.id}/tags", data={"member_id": ruth.id},
        follow_redirects=True,
    )
    assert b"Ruth Leiter is tagged" in response.data

    # Photo page shows the chip linking to the wiki...
    photo_page = admin_client.get(f"/photos/{photo.id}").data
    assert f'href="/family/{ruth.id}"'.encode() in photo_page

    # ...and the wiki page shows the photo back.
    wiki_page = admin_client.get(f"/family/{ruth.id}").data
    assert b"Photos featuring Ruth Leiter" in wiki_page
    assert f"/photos/{photo.id}/thumb".encode() in wiki_page


def test_duplicate_tag_is_friendly(admin_client):
    photo, ruth = _photo_and_person(admin_client)
    admin_client.post(f"/photos/{photo.id}/tags", data={"member_id": ruth.id})
    response = admin_client.post(
        f"/photos/{photo.id}/tags", data={"member_id": ruth.id},
        follow_redirects=True,
    )
    assert b"already tagged" in response.data
    assert PhotoTag.query.count() == 1, "the unique constraint held"


def test_untag_removes_the_bridge_both_ways(admin_client):
    photo, ruth = _photo_and_person(admin_client)
    admin_client.post(f"/photos/{photo.id}/tags", data={"member_id": ruth.id})

    response = admin_client.post(
        f"/photos/{photo.id}/tags/{ruth.id}/delete", follow_redirects=True
    )
    assert b"tag was removed" in response.data
    assert PhotoTag.query.count() == 0
    assert b"Photos featuring" not in admin_client.get(f"/family/{ruth.id}").data


def test_deleting_photo_or_person_cleans_up_tags(admin_client):
    """Cascade check from BOTH ends of the bridge."""
    photo, ruth = _photo_and_person(admin_client)
    admin_client.post(f"/photos/{photo.id}/tags", data={"member_id": ruth.id})

    admin_client.post(f"/photos/{photo.id}/delete")
    assert PhotoTag.query.count() == 0, "photo gone -> tag gone"

    # Re-build the bridge, then remove the person instead.
    album_url = f"/albums/{photo.album_id}"
    admin_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "again.jpg")]},
        content_type="multipart/form-data",
    )
    new_photo = Photo.query.one()
    admin_client.post(f"/photos/{new_photo.id}/tags",
                      data={"member_id": ruth.id})
    admin_client.post(f"/family/{ruth.id}/delete")
    assert PhotoTag.query.count() == 0, "person gone -> tag gone, photo stays"
    assert Photo.query.count() == 1


def test_tagging_requires_login(app, admin_client):
    photo, ruth = _photo_and_person(admin_client)
    anon = app.test_client()
    response = anon.post(f"/photos/{photo.id}/tags",
                         data={"member_id": ruth.id}, follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]