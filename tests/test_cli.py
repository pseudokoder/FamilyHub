"""Tests for the custom `flask` commands (app/cli.py).

These run the commands the way a deploy script or SSH session would — through
Flask's CLI runner — and assert on what they print and what they leave in the
database. They cover the operator-facing surface (create-admin, seed, backup,
export-data) that has no web route to exercise it.
"""

from app.extensions import db
from app.models import Individual, User


def test_create_admin_makes_an_admin(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=[
        "create-admin", "wes@example.com", "--display-name", "Wes",
        "--password", "Secret123",
    ])
    assert result.exit_code == 0
    assert "created" in result.output

    db.session.remove()  # see the row the command committed on its own connection
    user = User.query.filter_by(email="wes@example.com").one()
    assert user.is_admin is True
    assert user.role == "admin"


def test_create_admin_rejects_duplicate(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["create-admin", "dup@example.com", "--password", "Secret123"])
    again = runner.invoke(args=["create-admin", "dup@example.com", "--password", "Secret123"])
    # A ClickException exits non-zero so deploy pipelines notice the failure.
    assert again.exit_code != 0
    assert "already in use" in again.output


def test_seed_command_populates_the_database(app):
    result = app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    assert "Seeded" in result.output

    db.session.remove()
    assert Individual.query.count() == 9  # the three Hartwell generations


def test_export_data_command_writes_an_export(app, admin):
    result = app.test_cli_runner().invoke(args=["export-data"])
    assert result.exit_code == 0, result.output
    assert "Export written" in result.output
    assert "users: 1 row(s)" in result.output


def test_backup_command_creates_and_verifies(app, admin):
    result = app.test_cli_runner().invoke(args=["backup"])
    assert result.exit_code == 0, result.output
    assert "Backup written" in result.output
    assert "Verified" in result.output
    # No bucket configured locally — the command says so honestly, not errors.
    assert "No off-site bucket" in result.output
