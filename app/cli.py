"""Custom `flask` terminal commands for FamilyHub.

TEACHING NOTE: Flask lets us bolt our own subcommands onto its CLI, so admin
chores become one-liners you can run on the Lightsail server over SSH:

    flask init-db          -> create/upgrade the database schema
    flask create-admin bob -> create the first admin account (added in the
                              authentication chapter)

WHY a CLI instead of a "setup" web page? Two reasons:
  1. Security — there is no moment where the app is on the internet with an
     unauthenticated "create an admin" endpoint waiting to be found.
  2. Automation — deploy scripts and backups can call these commands
     non-interactively (D284 Software Engineering: repeatable processes
     beat manual checklists).

The v2 equivalent: Spring Boot `CommandLineRunner` beans or Spring Shell.
"""

import click
from flask_migrate import upgrade


def register_cli(app):
    """Attach our custom commands to the app.

    Called from the application factory — the same pattern as extensions:
    everything plugs into the app object that create_app() builds.
    """

    @app.cli.command("init-db")
    def init_db_command():
        """Create or upgrade the database to the latest schema.

        TEACHING NOTE: under the hood this runs every Alembic migration
        script in migrations/versions/ that hasn't been applied yet — the
        same as `flask db upgrade`. We wrap it in a friendlier name and make
        it the ONE blessed way to set up a database.

        Notice what we DON'T do: db.create_all(). That builds tables straight
        from the models and skips migration history entirely — fine for toy
        scripts, but then Alembic has no record of how the schema got there,
        and your dev/prod databases drift apart. Migrations are version
        control for your schema (D426 Data Management – Foundations covers
        schema design; D197 Version Control covers why history matters).
        """
        upgrade()
        click.echo("Database is up to date (all migrations applied).")
