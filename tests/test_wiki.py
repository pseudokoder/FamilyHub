"""Wiki tests: collaborative editing, [[wikilinks]], date validation."""

from app.models import FamilyMember


def _add_person(client, name, bio="", birth="", death=""):
    return client.post(
        "/family/new",
        data={"name": name, "location": "", "bio": bio,
              "birth_date": birth, "death_date": death},
        follow_redirects=True,
    )


def test_create_person_with_lifespan(admin_client):
    response = _add_person(admin_client, "Jo Leiter", birth="1947-03-12")
    assert b"has a page" in response.data
    assert b"born 1947" in response.data


def test_death_before_birth_rejected(admin_client):
    response = _add_person(
        admin_client, "Impossible Dates", birth="1980-01-01", death="1970-01-01"
    )
    assert b"double-check those two dates" in response.data
    assert FamilyMember.query.count() == 0


def test_duplicate_name_redirects_to_existing_page(admin_client):
    _add_person(admin_client, "Frank Leiter")
    response = _add_person(admin_client, "  frank LEITER ")  # sloppy retype
    assert b"already a page" in response.data
    assert FamilyMember.query.count() == 1


def test_wikilinks_connect_pages_both_ways(admin_client):
    import re as _re

    _add_person(admin_client, "Jo Leiter", bio="Married [[Frank Leiter]] in 1969.")
    jo_id = FamilyMember.query.one().id

    # Before Frank's page exists: name shows as plain text, no member-view link.
    # (The template always has /family/ hrefs for the edit button and breadcrumb,
    # but those end in /edit or are /family with no ID — the regex below only
    # matches bare /family/<int> view links, which the wikilink would produce.)
    page = admin_client.get(f"/family/{jo_id}").data
    assert b"Frank Leiter" in page
    assert not _re.search(rb'href="/family/\d+"', page)

    _add_person(admin_client, "Frank Leiter", bio="Married to [[Jo Leiter]].")
    frank_id = FamilyMember.query.filter_by(name="Frank Leiter").one().id

    # After: both pages link to each other.
    assert f'href="/family/{frank_id}"'.encode() in admin_client.get(f"/family/{jo_id}").data
    assert f'href="/family/{jo_id}"'.encode() in admin_client.get(f"/family/{frank_id}").data


def test_wikilinks_work_from_blog_posts(admin_client):
    _add_person(admin_client, "Jo Leiter")
    jo_id = FamilyMember.query.one().id
    response = admin_client.post(
        "/posts/new",
        data={"title": "Tomatoes", "body": "Every summer [[Jo Leiter]] grew tomatoes."},
        follow_redirects=True,
    )
    assert f'href="/family/{jo_id}"'.encode() in response.data


def test_any_member_can_edit_only_admin_can_delete(admin_client, member_client):
    _add_person(admin_client, "Jo Leiter")
    member_id = FamilyMember.query.one().id

    # Collaborative: a regular member edits a page the admin created.
    response = member_client.post(
        f"/family/{member_id}/edit",
        data={"name": "Jo Leiter", "location": "Las Vegas, NV", "bio": "Added by member.",
              "birth_date": "", "death_date": ""},
        follow_redirects=True,
    )
    assert b"page is updated" in response.data
    assert b"Las Vegas" in response.data

    # ...but deleting a person is admin-only.
    assert member_client.post(f"/family/{member_id}/delete").status_code == 403
    response = admin_client.post(f"/family/{member_id}/delete", follow_redirects=True)
    assert b"was deleted" in response.data
    assert FamilyMember.query.count() == 0


def test_last_editor_is_tracked(admin_client, member_client):
    _add_person(admin_client, "Jo Leiter")
    page_id = FamilyMember.query.one().id
    member_client.post(
        f"/family/{page_id}/edit",
        data={"name": "Jo Leiter", "location": "", "bio": "x",
              "birth_date": "", "death_date": ""},
    )
    assert b"Last edited by Member" in admin_client.get(f"/family/{page_id}").data
