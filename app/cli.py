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

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.option(
        "--display-name",
        default=None,
        help="Name shown to the family (defaults to the email).",
    )
    @click.option(
        "--password",
        prompt=True,              # ask interactively if not given as a flag...
        hide_input=True,          # ...without echoing it to the screen,
        confirmation_prompt=True, # ...and ask twice to catch typos.
        help="Password for the new admin (omit to be prompted securely).",
    )
    def create_admin_command(email, display_name, password):
        """Create an ADMIN account — the bootstrap step after init-db.

        Every other account is created by an admin inside the app
        (/admin/users). But the FIRST admin has to come from somewhere,
        and a terminal command is the safe somewhere: only a person with
        SSH access to the server (or sitting at this keyboard) can run it.
        """
        from app.models.role import Role
        from app.services import user_service

        try:
            user = user_service.create_user(
                email=email,
                display_name=display_name or email,
                password=password,
                role=Role.ADMIN,
            )
        except ValueError as err:
            # raise a ClickException so the command exits with status 1 —
            # scripts and deploy pipelines can detect the failure.
            raise click.ClickException(str(err))
        click.echo(f"Admin account '{user.email}' created. You can log in now.")

    @app.cli.command("backup")
    def backup_command():
        """Create, verify, and (if configured) upload a full backup.

        This is the command the nightly cron job runs on the Lightsail
        server — see DEVDIARY Chapter 8 for the crontab line. A backup that
        fails verification exits non-zero so cron's mail/monitoring notices.
        """
        from app.services import backup_service

        path = backup_service.create_backup()
        click.echo(f"Backup written: {path}")

        report = backup_service.verify_backup(path)
        if not report["ok"]:
            raise click.ClickException(
                "Backup FAILED verification: " + "; ".join(report["problems"])
            )
        click.echo(
            f"Verified: zip is sound, DB has {report['db_tables']} tables, "
            f"{report['file_count']} uploaded file(s) included."
        )

        uploaded, message = backup_service.upload_backup(path)
        click.echo(message)

    @app.cli.command("restore-backup")
    @click.argument("zip_path")
    @click.option("--yes", is_flag=True, help="Skip the confirmation prompt (for scripts).")
    def restore_backup_command(zip_path, yes):
        """DESTRUCTIVE: replace the database + uploads with a backup's contents.

        Deliberately CLI-only — restoring is rare, drastic, and should be a
        deliberate two-hands operation, never a web button. In production:
        stop gunicorn first, restore, start it again.
        """
        from app.services import backup_service

        if not yes:
            click.confirm(
                "This OVERWRITES the current database and uploaded files "
                "with the backup's contents. Continue?",
                abort=True,  # 'no' aborts the whole command safely
            )
        try:
            report = backup_service.restore_backup(zip_path)
        except (RuntimeError, OSError) as err:
            raise click.ClickException(str(err))
        click.echo(
            f"Restored. DB has {report['db_tables']} tables, "
            f"{report['file_count']} file(s) back in place. "
            "(The old DB was parked next to it as *.pre-restore.)"
        )

    @app.cli.command("export-data")
    def export_data_command():
        """Dump ALL data to a portable JSON export (the v2 migration format).

        This is CLAUDE.md's zero-data-loss guarantee: everything in the
        database plus a checksummed manifest of every uploaded file, in a
        format a future Java importer (or plain curiosity) can read.
        """
        from app.services import export_service

        out_dir, counts, file_count = export_service.export_all()
        click.echo(f"Export written to: {out_dir}")
        for name, count in counts.items():
            click.echo(f"  {name}: {count} row(s)")
        click.echo(f"  uploaded files in manifest: {file_count}")
        click.echo("Treat the export folder as sensitive — it's the whole archive.")

    @app.cli.command("seed")
    def seed_command():
        """Fill a FRESH database with realistic mock data (the Hartwell family).

        For development only — it lets Cowork (WP3) and Wes see the app full of
        believable three-generation data, and it doubles as a runnable proof
        that the GEDCOM-7 schema holds together (see seed.py). Run it once on an
        empty dev database, right after `flask db upgrade`.

        NOTE: full GEDCOM-7 *file* import/export (reading/writing .ged) is WP6 /
        a firm v2 deliverable — this command is mock data, not a GEDCOM importer.
        """
        from seed import seed_all, seed_users
        from app.services import historical_event_service, settings_service

        users = seed_users()
        counts = seed_all()
        # The timeline's almanac backdrop is reference data, not Hartwell data —
        # idempotent, so re-running seed never double-loads it.
        counts["historical_events"] = historical_event_service.seed_defaults()
        # Seed the admin/security/branding config defaults (idempotent).
        counts["site_settings"] = settings_service.ensure_defaults()
        click.echo(f"Seeded {len(users)} demo user(s) + mock data:")
        for name, count in counts.items():
            click.echo(f"  {name}: {count} row(s)")

    @app.cli.command("seed-historical")
    def seed_historical_command():
        """Load the bundled world/US almanac into the timeline (idempotent).

        Unlike `flask seed` (dev mock data), this is safe and INTENDED for
        production: the historical-events backdrop (Master Plan §4) is the same
        for every family, so run it once after `flask db upgrade` on a real
        server. It does nothing if the table is already populated.
        """
        from app.services import historical_event_service

        inserted = historical_event_service.seed_defaults()
        if inserted:
            click.echo(f"Loaded {inserted} historical event(s).")
        else:
            click.echo("Historical events already present — nothing to do.")

    @app.cli.command("seed-settings")
    def seed_settings_command():
        """Seed the admin/security/branding config defaults (idempotent).

        Prod-safe: run once after `flask db upgrade` so the Settings panel and the
        security baseline (min password length, lockout, session timeout…) have
        their default rows. Existing values are never overwritten.
        """
        from app.services import settings_service

        inserted = settings_service.ensure_defaults()
        click.echo(f"Seeded {inserted} setting default(s)."
                   if inserted else "Settings already seeded — nothing to do.")
