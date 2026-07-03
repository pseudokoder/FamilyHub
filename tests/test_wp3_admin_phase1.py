"""WP3 admin Phase 1 — config-as-data settings + the new tables."""

import pytest

from app.models import RoleRequest, Suggestion
from app.services import settings_service


def test_ensure_defaults_is_idempotent(app):
    first = settings_service.ensure_defaults()
    assert first == len(settings_service.DEFAULTS) > 0
    assert settings_service.ensure_defaults() == 0  # nothing to add second time


def test_typed_accessors_fall_back_to_defaults(app):
    # Before seeding, typed getters still return the DEFAULTS value.
    assert settings_service.get_int("min_password_length") == 8
    assert settings_service.get_bool("breach_check_enabled") is False
    settings_service.set_value("breach_check_enabled", "true")
    assert settings_service.get_bool("breach_check_enabled") is True


def test_security_config_shape(app):
    cfg = settings_service.security_config()
    assert set(cfg) == {"min_password_length", "breach_check_enabled",
                        "login_lockout_threshold", "session_timeout_days"}
    assert cfg["min_password_length"] == 8


def test_editable_settings_grouped_and_typed(app):
    editable = settings_service.editable_settings()
    assert set(editable) == set(settings_service.SETTING_GROUPS)
    assert isinstance(editable["security"]["min_password_length"], int)
    assert isinstance(editable["security"]["breach_check_enabled"], bool)


def test_update_settings_coerces_and_validates(app):
    settings_service.update_settings({
        "site_name": "The Hartwells", "min_password_length": "12",
        "breach_check_enabled": "true", "unknown_key": "ignored"})
    assert settings_service.get("site_name") == "The Hartwells"
    assert settings_service.get_int("min_password_length") == 12
    assert settings_service.get_bool("breach_check_enabled") is True
    # A too-short minimum is rejected.
    with pytest.raises(ValueError):
        settings_service.update_settings({"min_password_length": "3"})
    # Non-numeric int is rejected.
    with pytest.raises(ValueError):
        settings_service.update_settings({"session_timeout_days": "soon"})


def test_new_tables_roundtrip(app, member):
    from app.extensions import db
    s = Suggestion(author_user_id=member.id, topic="idea", body="Add a map view")
    r = RoleRequest(user_id=member.id, requested_role="curator")
    db.session.add_all([s, r])
    db.session.commit()
    assert Suggestion.query.count() == 1
    assert RoleRequest.query.one().status == "pending"
