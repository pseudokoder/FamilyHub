"""WP3 admin Phase 2 — transactional email + security hardening (§9)."""

import hashlib

import pytest

from app.extensions import db, mail
from app.models import User
from app.services import security_service, settings_service, user_service
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


# --- Email verification -------------------------------------------------------

def test_email_verification_flow(app, member):
    assert member.email_verified is False
    token = user_service.generate_email_verify_token(member)
    confirmed = user_service.confirm_email_token(token)
    assert confirmed is not None
    assert db.session.get(User, member.id).email_verified is True

    # Changing the email un-verifies it, and the old token no longer matches.
    user_service.set_email(member, "moved@test.invalid")
    assert db.session.get(User, member.id).email_verified is False
    assert user_service.confirm_email_token(token) is None


def test_send_my_verification_email(member_client):
    with mail.record_messages() as outbox:
        resp = member_client.post("/api/me/verify-email")
    assert resp.get_json()["status"] == "sent"
    assert len(outbox) == 1
    assert "confirm" in outbox[0].subject.lower()


# --- Password baseline: length is settings-driven -----------------------------

def test_min_password_length_is_settings_driven(app):
    settings_service.set_value("min_password_length", "12")
    with pytest.raises(ValueError):
        user_service.create_user("shortpw@test.invalid", "Short", "only10char")
    # A long-enough one is accepted.
    user_service.create_user("okpw@test.invalid", "Fine", "thisIsLongEnough")


# --- Password baseline: HIBP breach check (k-anonymity, mocked) ---------------

def test_breach_check_blocks_known_password(app, monkeypatch):
    settings_service.set_value("breach_check_enabled", "true")
    pw = "hunter2breached"
    suffix = hashlib.sha1(pw.encode("utf-8")).hexdigest().upper()[5:]
    # Simulate HIBP returning our suffix among the range results.
    monkeypatch.setattr(security_service, "_fetch_hibp_range",
                        lambda prefix: f"{suffix}:1337\r\nABCDEF0123:2")
    assert security_service.is_breached(pw) is True
    with pytest.raises(ValueError):
        security_service.validate_password(pw)


def test_breach_check_allows_clean_password(app, monkeypatch):
    settings_service.set_value("breach_check_enabled", "true")
    monkeypatch.setattr(security_service, "_fetch_hibp_range",
                        lambda prefix: "0000000000000000000000000000000000000:9")
    security_service.validate_password("aPerfectlyFineLongPassword")  # no raise


def test_breach_check_fails_open_on_network_error(app, monkeypatch):
    def boom(prefix):
        raise OSError("network down")
    monkeypatch.setattr(security_service, "_fetch_hibp_range", boom)
    # An outage must not block anyone — availability wins for a nice-to-have check.
    assert security_service.is_breached("anything") is False


# --- Login lockout ------------------------------------------------------------

def test_account_locks_after_threshold(app, admin):
    settings_service.set_value("login_lockout_threshold", "3")
    for _ in range(3):
        assert user_service.authenticate(ADMIN_EMAIL, "wrong-password") is None
    locked = db.session.get(User, admin.id)
    assert locked.is_locked() is True
    # Even the CORRECT password is refused while locked.
    assert user_service.authenticate(ADMIN_EMAIL, ADMIN_PASSWORD) is None


def test_successful_login_resets_failure_count(app, admin):
    settings_service.set_value("login_lockout_threshold", "5")
    user_service.authenticate(ADMIN_EMAIL, "wrong")
    user_service.authenticate(ADMIN_EMAIL, "wrong")
    assert db.session.get(User, admin.id).failed_login_count == 2
    assert user_service.authenticate(ADMIN_EMAIL, ADMIN_PASSWORD) is not None
    assert db.session.get(User, admin.id).failed_login_count == 0
