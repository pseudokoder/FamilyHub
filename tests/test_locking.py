"""The Trial Period rule (Wes, June 12 2026), as executable policy:

  - New content starts UNLOCKED: its creator may still delete it.
  - An admin LOCKS content after review — from then on, only an admin
    can delete it. Unlocking reopens the trial period.
  - Posts and comments are never lockable: your words stay yours.

Plus the audit log: every state change writes a row; admins can read the
trail at /admin/activity.
"""

from app.models import AuditLog, FamilyMember, Photo, TimelineEvent
from tests.conftest import make_image


def _member_album_with_photo(member_client):
    """A member creates an album and uploads one photo into it."""
    album_url = member_client.post(
        "/albums/new", data={"title": "Members Album", "description": ""},
        follow_redirects=False,
    ).headers["Location"]
    member_client.post(
        album_url + "/photos",
        data={"photos": [(make_image(), "mine.jpg")]},
        content_type="multipart/form-data",
    )
    return album_url, Photo.query.one()


# --- Photos -------------------------------------------------------------------

def test_photo_trial_period_then_lock(admin_client, member_client):
    """Creator may delete while unlocked; locked = admin-only; unlock
    reopens the trial. The full lifecycle in one test."""
    _, photo = _member_album_with_photo(member_client)

    # Trial period: the uploader could delete... but don't yet — lock it.
    admin_client.post(f"/photos/{photo.id}/lock")
    assert Photo.query.one().is_locked

    # Locked: the UPLOADER is refused now.
    assert member_client.post(f"/photos/{photo.id}/delete").status_code == 403

    # The page explains why (badge visible to everyone).
    assert b"family archive" in member_client.get(f"/photos/{photo.id}").data

    # Unlock reopens the trial period; the uploader can delete again.
    admin_client.post(f"/photos/{photo.id}/unlock")
    response = member_client.post(f"/photos/{photo.id}/delete",
                                  follow_redirects=True)
    assert b"Photo deleted" in response.data
    assert Photo.query.count() == 0


def test_admin_can_delete_locked_photo(admin_client, member_client):
    _, photo = _member_album_with_photo(member_client)
    admin_client.post(f"/photos/{photo.id}/lock")
    response = admin_client.post(f"/photos/{photo.id}/delete",
                                 follow_redirects=True)
    assert b"Photo deleted" in response.data


def test_locking_is_admin_only(admin_client, member_client):
    _, photo = _member_album_with_photo(member_client)
    assert member_client.post(f"/photos/{photo.id}/lock").status_code == 403
    admin_client.post(f"/photos/{photo.id}/lock")
    assert member_client.post(f"/photos/{photo.id}/unlock").status_code == 403


# --- Albums --------------------------------------------------------------------

def test_locked_album_protected_from_creator(admin_client, member_client):
    album_url, _ = _member_album_with_photo(member_client)
    admin_client.post(album_url + "/lock")
    assert member_client.post(album_url + "/delete").status_code == 403
    # Admin still can.
    response = admin_client.post(album_url + "/delete", follow_redirects=True)
    assert b"were deleted" in response.data


def test_one_locked_photo_protects_the_whole_album(admin_client, member_client):
    """The strictest lock wins: an unlocked album with ONE locked photo
    inside cannot be deleted by its creator — deleting the album would
    take the protected photo with it."""
    album_url, photo = _member_album_with_photo(member_client)
    admin_client.post(f"/photos/{photo.id}/lock")  # photo, not album
    assert member_client.post(album_url + "/delete").status_code == 403


# --- Wiki pages ------------------------------------------------------------------

def test_wiki_creator_can_delete_during_trial_only(admin_client, member_client):
    """POLICY CHANGE from admin-only delete: the page's creator may delete
    while unlocked. After the admin locks it: admin-only again."""
    member_client.post(
        "/family/new",
        data={"name": "Draft Person", "location": "", "bio": "oops",
              "birth_date": "", "death_date": ""},
    )
    page = FamilyMember.query.one()

    admin_client.post(f"/family/{page.id}/lock")
    assert member_client.post(f"/family/{page.id}/delete").status_code == 403

    admin_client.post(f"/family/{page.id}/unlock")
    response = member_client.post(f"/family/{page.id}/delete",
                                  follow_redirects=True)
    assert b"was deleted" in response.data
    assert FamilyMember.query.count() == 0


# --- Timeline ---------------------------------------------------------------------

def test_timeline_lock_lifecycle(admin_client, member_client):
    member_client.post(
        "/timeline/new",
        data={"title": "The move west", "description": "", "year": "1956"},
    )
    event = TimelineEvent.query.one()

    admin_client.post(f"/timeline/{event.id}/lock")
    assert member_client.post(f"/timeline/{event.id}/delete").status_code == 403

    admin_client.post(f"/timeline/{event.id}/unlock")
    response = member_client.post(f"/timeline/{event.id}/delete",
                                  follow_redirects=True)
    assert b"was removed" in response.data


# --- The audit trail ---------------------------------------------------------------

def test_actions_write_audit_rows(admin_client, member_client):
    _, photo = _member_album_with_photo(member_client)
    admin_client.post(f"/photos/{photo.id}/lock")
    admin_client.post(f"/photos/{photo.id}/delete")

    actions = [(row.action, row.target_type) for row in AuditLog.query.all()]
    assert ("create", "album") in actions
    assert ("upload", "album") in actions
    assert ("lock", "photo") in actions
    assert ("delete", "photo") in actions


def test_activity_page_is_admin_only_and_readable(admin_client, member_client):
    _member_album_with_photo(member_client)
    assert member_client.get("/admin/activity").status_code == 403

    page = admin_client.get("/admin/activity")
    assert page.status_code == 200
    assert b"upload" in page.data
    assert b"Member" in page.data  # who did it
