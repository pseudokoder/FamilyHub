"""Admin panel tests: the 403 wall, user management, roles, site settings."""

import pytest
from PIL import Image

from app.extensions import db
from app.models import User
from app.services import settings_service
from tests.conftest import MEMBER_EMAIL, make_image

ADMIN_ONLY_ROUTES = ["/admin/users", "/admin/users/new", "/admin/settings", "/admin/backups"]


@pytest.mark.parametrize("route", ADMIN_ONLY_ROUTES)
def test_member_gets_403_not_404(member_client, route):
    """403 = 'I know who you are, and the answer is no' — the status-code
    precision lesson from DEVDIARY Chapter 2. Enforced by the §10 authz layer."""
    assert member_client.get(route).status_code == 403


def test_member_sees_no_admin_menu(member_client):
    assert b"Manage Users" not in member_client.get("/").data


def test_admin_creates_account_and_it_works(admin_client, app):
    response = admin_client.post(
        "/admin/users/new",
        data={"email": "GrandmaJo@example.com", "display_name": "Grandma Jo",
              "password": "Tomatoes1969", "role": "user"},
        follow_redirects=True,
    )
    assert b"Account for Grandma Jo created" in response.data

    # Email normalized to lowercase; the new person can actually log in.
    assert User.query.filter_by(email="grandmajo@example.com").one()
    fresh = app.test_client()
    response = fresh.post(
        "/auth/login",
        data={"email": "grandmajo@example.com", "password": "Tomatoes1969"},
        follow_redirects=True,
    )
    assert b"Welcome back, Grandma Jo!" in response.data


def test_admin_can_create_a_power_user(admin_client):
    """The role dropdown actually sets the role on the new account (§10)."""
    admin_client.post(
        "/admin/users/new",
        data={"email": "tech@example.com", "display_name": "Tech Cousin",
              "password": "Gadgets123", "role": "power_user"},
        follow_redirects=True,
    )
    assert User.query.filter_by(email="tech@example.com").one().role == "power_user"


def test_admin_can_change_a_members_role(admin_client, member):
    """Editing an account can promote/demote it — the change is audited and
    takes effect immediately."""
    admin_client.post(
        f"/admin/users/{member.id}/edit",
        data={"display_name": "Member", "email": MEMBER_EMAIL,
              "role": "power_user"},
        follow_redirects=True,
    )
    assert db.session.get(User, member.id).role == "power_user"


def test_duplicate_email_friendly_error(admin_client, member):
    response = admin_client.post(
        "/admin/users/new",
        data={"email": MEMBER_EMAIL, "display_name": "Clone",
              "password": "Whatever123", "role": "user"},
        follow_redirects=True,
    )
    assert b"already in use" in response.data


def test_short_password_rejected(admin_client):
    response = admin_client.post(
        "/admin/users/new",
        data={"email": "shorty@example.com", "display_name": "S",
              "password": "abc", "role": "user"},
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
    old = fresh.post("/auth/login",
                     data={"email": MEMBER_EMAIL, "password": "MemberPass123"},
                     follow_redirects=True)
    assert b"Welcome back" not in old.data
    new = fresh.post("/auth/login",
                     data={"email": MEMBER_EMAIL, "password": "BrandNewPass1"},
                     follow_redirects=True)
    assert b"Welcome back, Member!" in new.data


def test_admin_activity_and_backups_pages(admin_client):
    assert admin_client.get("/admin/activity").status_code == 200
    assert admin_client.get("/admin/backups").status_code == 200


def test_admin_can_run_a_backup(admin_client):
    """The 'Back Up Now' button: creates + verifies a backup and reports back."""
    response = admin_client.post("/admin/backups/run", follow_redirects=True)
    assert response.status_code == 200
    assert b"verified" in response.data.lower()


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
