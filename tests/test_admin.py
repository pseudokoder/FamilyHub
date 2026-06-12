"""Admin panel tests: the 403 wall, user management, site settings."""

import pytest
from PIL import Image

from app.models import User
from app.services import settings_service
from tests.conftest import make_image

ADMIN_ONLY_ROUTES = ["/admin/users", "/admin/users/new", "/admin/settings", "/admin/backups"]


@pytest.mark.parametrize("route", ADMIN_ONLY_ROUTES)
def test_member_gets_403_not_404(member_client, route):
    """403 = 'I know who you are, and the answer is no' — the status-code
    precision lesson from DEVDIARY Chapter 2."""
    assert member_client.get(route).status_code == 403


def test_member_sees_no_admin_menu(member_client):
    assert b"Manage Users" not in member_client.get("/").data


def test_admin_creates_account_and_it_works(admin_client, app):
    response = admin_client.post(
        "/admin/users/new",
        data={"username": "GrandmaJo", "display_name": "Grandma Jo",
              "password": "Tomatoes1969"},
        follow_redirects=True,
    )
    assert b"Account for Grandma Jo created" in response.data

    # Username normalized to lowercase; the new person can actually log in.
    assert User.query.filter_by(username="grandmajo").one()
    fresh = app.test_client()
    response = fresh.post(
        "/auth/login",
        data={"username": "grandmajo", "password": "Tomatoes1969"},
        follow_redirects=True,
    )
    assert b"Welcome back, Grandma Jo!" in response.data


def test_duplicate_username_friendly_error(admin_client, member):
    response = admin_client.post(
        "/admin/users/new",
        data={"username": "member", "display_name": "Clone", "password": "Whatever123"},
        follow_redirects=True,
    )
    assert b"already taken" in response.data


def test_short_password_rejected(admin_client):
    response = admin_client.post(
        "/admin/users/new",
        data={"username": "shorty", "display_name": "S", "password": "abc"},
        follow_redirects=True,
    )
    assert b"at least 8 characters" in response.data


def test_password_reset(admin_client, member, app):
    admin_client.post(
        f"/admin/users/{member.id}/reset-password",
        data={"password": "BrandNewPass1", "confirm": "BrandNewPass1"},
        follow_redirects=True,
    )
    fresh = app.test_client()
    # Old password dead, new one works.
    old = fresh.post("/auth/login", data={"username": "member", "password": "MemberPass123"}, follow_redirects=True)
    assert b"Welcome back" not in old.data
    new = fresh.post("/auth/login", data={"username": "member", "password": "BrandNewPass1"}, follow_redirects=True)
    assert b"Welcome back, Member!" in new.data


def test_site_settings_save_and_show(admin_client, member_client):
    admin_client.post(
        "/admin/settings",
        data={"tagline": "All of us, one place.", "about_text": "Our private site.",
              "contact_text": "Call Wes."},
        follow_redirects=True,
    )
    # Tagline on the dashboard, texts on the About page — visible to members.
    assert b"All of us, one place." in member_client.get("/").data
    about = member_client.get("/about").data
    assert b"Our private site." in about and b"Call Wes." in about


def test_hero_upload_processed_and_walled(admin_client, app):
    admin_client.post(
        "/admin/settings",
        data={"tagline": "", "about_text": "", "contact_text": "",
              "hero": (make_image("PNG", size=(2400, 1000)), "banner.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    # Re-encoded JPEG, shrunk to <=1600px (it loads on every dashboard view).
    img = Image.open(settings_service.hero_path())
    assert img.format == "JPEG" and max(img.size) <= 1600
    img.close()

    assert app.test_client().get("/site/hero").status_code == 302  # login wall
    assert admin_client.get("/site/hero").status_code == 200
