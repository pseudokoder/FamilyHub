"""Family Plans tests: the plan lifecycle, the collaborative checklist,
the locking rule, and — most importantly — the attachment allow-list
(images + PDFs in, everything else out)."""

import io

from app.models import FamilyPlan, PlanAttachment, PlanItem
from tests.conftest import make_image


def _new_plan(client, title="Summer Reunion 2026"):
    return client.post(
        "/plans/new", data={"title": title, "description": "Let's plan it!"},
        follow_redirects=False,
    ).headers["Location"]  # /plans/<id>


def _fake_pdf(name="itinerary.pdf"):
    return (io.BytesIO(b"%PDF-1.4 a tiny but valid-looking pdf"), name)


# --- Plan lifecycle -----------------------------------------------------------

def test_create_and_view_plan(admin_client):
    url = _new_plan(admin_client)
    page = admin_client.get(url).data
    assert b"Summer Reunion 2026" in page
    assert b"Checklist" in page and b"Shared files" in page


def test_any_member_can_edit(admin_client, member_client):
    """Collaborative, like the wiki: a member edits the admin's plan."""
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    response = member_client.post(
        f"/plans/{plan_id}/edit",
        data={"title": "Summer Reunion 2026", "description": "Member helped."},
        follow_redirects=True,
    )
    assert b"Plan updated" in response.data
    assert b"Member helped." in response.data


# --- Checklist ----------------------------------------------------------------

def test_checklist_add_toggle_delete(admin_client, member_client):
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id

    # Any member adds and ticks items (the collaboration).
    member_client.post(f"/plans/{plan_id}/items", data={"text": "Book the cabin"})
    item = PlanItem.query.one()
    assert item.is_done is False

    member_client.post(f"/plans/items/{item.id}/toggle")
    assert PlanItem.query.one().is_done is True

    # A member can't delete the admin's item, but its author (admin) can.
    item2 = _add_admin_item(admin_client, plan_id, "Admin's task")
    assert member_client.post(f"/plans/items/{item2.id}/delete").status_code == 403
    admin_client.post(f"/plans/items/{item2.id}/delete")
    assert PlanItem.query.count() == 1


def _add_admin_item(admin_client, plan_id, text):
    admin_client.post(f"/plans/{plan_id}/items", data={"text": text})
    return PlanItem.query.filter_by(text=text).one()


# --- Attachments: the allow-list is the whole point ---------------------------

def test_image_and_pdf_attachments_are_accepted(admin_client):
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id

    admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": (make_image(), "map.jpg")},
        content_type="multipart/form-data",
    )
    admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": _fake_pdf()},
        content_type="multipart/form-data",
    )
    kinds = sorted(a.kind for a in PlanAttachment.query.all())
    assert kinds == ["image", "pdf"]


def test_dangerous_file_types_are_rejected(admin_client):
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    for payload, name in [
        (b"<script>alert(1)</script>", "evil.html"),
        (b"MZ\x90\x00", "malware.exe"),
        (b"<svg onload=alert(1)>", "sneaky.svg"),
    ]:
        response = admin_client.post(
            f"/plans/{plan_id}/attachments",
            data={"file": (io.BytesIO(payload), name)},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert b"allow here" in response.data
    assert PlanAttachment.query.count() == 0


def test_pdf_must_really_be_a_pdf(admin_client):
    """A .pdf extension isn't enough — the bytes must start with %PDF-."""
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    response = admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": (io.BytesIO(b"not really a pdf"), "fake.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"look like a real PDF" in response.data
    assert PlanAttachment.query.count() == 0


def test_attachment_is_login_walled(admin_client, app):
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": _fake_pdf()},
        content_type="multipart/form-data",
    )
    att_id = PlanAttachment.query.one().id

    anon = app.test_client()
    assert anon.get(f"/plans/attachments/{att_id}/file").status_code == 302
    assert admin_client.get(f"/plans/attachments/{att_id}/file").status_code == 200


def test_image_attachment_is_exif_stripped(admin_client):
    """Shared photos get the same privacy treatment as gallery photos."""
    from PIL import Image
    from app.services import plan_service

    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": (make_image(gps=True), "where_we_stayed.jpg")},
        content_type="multipart/form-data",
    )
    attachment = PlanAttachment.query.one()
    saved = Image.open(plan_service.attachment_path(attachment))
    assert len(saved.getexif()) == 0, "GPS/EXIF must not survive the upload"


# --- Locking (Trial Period) + cascade -----------------------------------------

def test_lock_protects_plan_then_admin_deletes(admin_client, member_client):
    member_url = member_client.post(
        "/plans/new", data={"title": "Member's plan", "description": ""},
        follow_redirects=False,
    ).headers["Location"]
    plan_id = FamilyPlan.query.one().id

    admin_client.post(f"/plans/{plan_id}/lock")
    # Locked: the creator can no longer delete.
    assert member_client.post(f"/plans/{plan_id}/delete").status_code == 403
    # Admin still can.
    assert admin_client.post(f"/plans/{plan_id}/delete",
                             follow_redirects=True).status_code == 200
    assert FamilyPlan.query.count() == 0


def test_delete_plan_cascades_items_and_attachment_files(admin_client):
    url = _new_plan(admin_client)
    plan_id = FamilyPlan.query.one().id
    admin_client.post(f"/plans/{plan_id}/items", data={"text": "a task"})
    admin_client.post(
        f"/plans/{plan_id}/attachments",
        data={"file": _fake_pdf()},
        content_type="multipart/form-data",
    )
    from app.services import plan_service
    import os
    path = plan_service.attachment_path(PlanAttachment.query.one())
    assert os.path.exists(path)

    admin_client.post(f"/plans/{plan_id}/delete")
    assert FamilyPlan.query.count() == 0
    assert PlanItem.query.count() == 0
    assert PlanAttachment.query.count() == 0
    assert not os.path.exists(path), "attachment file removed from disk"


# --- Integrations -------------------------------------------------------------

def test_plan_is_searchable_and_in_activity(admin_client):
    _new_plan(admin_client, "Grand Canyon Trip")
    assert b"Grand Canyon Trip" in admin_client.get("/search?q=canyon").data
    assert b"started a plan" in admin_client.get("/activity").data


def test_plans_login_walled(client):
    assert client.get("/plans", follow_redirects=False).status_code == 302
