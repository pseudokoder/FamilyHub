"""WP3 gaps: soft-delete, account↔person link, audit before/after, RBAC rename

Additive schema for the WP3 backend gaps (Master Plan v2.0.0 §3.5 sketches;
ADR-0001 write-control; ADR-0002 account↔person link). Everything here is
additive or a pure rename — no existing family data is dropped.

WHAT THIS MIGRATION DOES:
  1. users: add nullable ``individual_id`` FK (ADR-0002) + ``timezone``; migrate
     the ``role`` values to the renamed ladder (guest→viewer, user→contributor,
     power_user→curator; admin unchanged) and move the column default to
     'contributor'.
  2. Soft-delete (ADR-0001): add a nullable, indexed ``deleted_at`` to every
     user-editable table. NULL = live; a timestamp = soft-deleted.
  3. audit_log: rename target_type/target_id → subject_type/subject_id (the
     schema-wide polymorphic convention) and add ``before_json`` / ``after_json``
     snapshots for one-click revert.
  4. media_objects: add ``capture_date`` (+ sortable) — when the photo was taken,
     distinct from when it was uploaded.
  5. Create the ``historical_events`` almanac table (timeline backdrop).

TEACHING NOTE (why batch_alter_table): SQLite can't ALTER/rename/drop a column in
place — Alembic's ``batch_alter_table`` rebuilds the table for us, copying data
across. On MySQL (v2) these become real ALTERs; this code doesn't change.

Revision ID: c2f1a7b9d4e0
Revises: 8f1e6fa904a3
Create Date: 2026-07-03 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2f1a7b9d4e0'
down_revision = '8f1e6fa904a3'
branch_labels = None
depends_on = None


# Every user-editable table that gains a soft-delete column (Master Plan §3.5).
# Reference/join-of-reference tables (places, repositories) are excluded — they
# use ON DELETE SET NULL and are shared, not owned.
SOFT_DELETE_TABLES = [
    "individuals", "names",
    "families", "family_children",
    "events",
    "sources", "citations",
    "media_objects", "media_links",
    "notes", "note_links",
]


def upgrade():
    # 1. users: account↔person link + timezone + RBAC rename ------------------
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("individual_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("timezone", sa.String(length=50), nullable=True))
        # The role column's server default moves to the renamed 'contributor'.
        batch_op.alter_column(
            "role", existing_type=sa.String(length=20),
            existing_nullable=False, server_default="contributor",
        )
        batch_op.create_foreign_key(
            "fk_users_individual_id_individuals", "individuals",
            ["individual_id"], ["id"], ondelete="SET NULL",
        )

    # Data migration: rename existing role values onto the new ladder. Runs after
    # the column exists; 'admin' is unchanged so it needs no update.
    op.execute("UPDATE users SET role = 'viewer' WHERE role = 'guest'")
    op.execute("UPDATE users SET role = 'contributor' WHERE role = 'user'")
    op.execute("UPDATE users SET role = 'curator' WHERE role = 'power_user'")

    # 2. Soft-delete: deleted_at (+ index) on every user-editable table --------
    for table in SOFT_DELETE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
            batch_op.create_index(
                batch_op.f(f"ix_{table}_deleted_at"), ["deleted_at"], unique=False
            )

    # 3. audit_log: rename to subject_* + add before/after snapshots -----------
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.alter_column(
            "target_type", new_column_name="subject_type",
            existing_type=sa.String(length=50), existing_nullable=False,
        )
        batch_op.alter_column(
            "target_id", new_column_name="subject_id",
            existing_type=sa.Integer(), existing_nullable=True,
        )
        batch_op.add_column(sa.Column("before_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("after_json", sa.Text(), nullable=True))

    # 4. media_objects: capture_date (raw + sortable) --------------------------
    with op.batch_alter_table("media_objects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("capture_date", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("capture_date_sort", sa.String(length=20), nullable=True))

    # 5. historical_events almanac table ---------------------------------------
    op.create_table(
        "historical_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("date_sort", sa.String(length=20), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=10), nullable=False,
                  server_default="world"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_events")),
    )
    with op.batch_alter_table("historical_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_historical_events_year"), ["year"], unique=False)
        batch_op.create_index(
            "ix_historical_events_scope_year", ["scope", "year"], unique=False)


def downgrade():
    op.drop_table("historical_events")

    with op.batch_alter_table("media_objects", schema=None) as batch_op:
        batch_op.drop_column("capture_date_sort")
        batch_op.drop_column("capture_date")

    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_column("after_json")
        batch_op.drop_column("before_json")
        batch_op.alter_column(
            "subject_id", new_column_name="target_id",
            existing_type=sa.Integer(), existing_nullable=True,
        )
        batch_op.alter_column(
            "subject_type", new_column_name="target_type",
            existing_type=sa.String(length=50), existing_nullable=False,
        )

    for table in reversed(SOFT_DELETE_TABLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f"ix_{table}_deleted_at"))
            batch_op.drop_column("deleted_at")

    # Reverse the role rename (best-effort; 'admin' unchanged).
    op.execute("UPDATE users SET role = 'guest' WHERE role = 'viewer'")
    op.execute("UPDATE users SET role = 'user' WHERE role = 'contributor'")
    op.execute("UPDATE users SET role = 'power_user' WHERE role = 'curator'")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_individual_id_individuals", type_="foreignkey")
        batch_op.alter_column(
            "role", existing_type=sa.String(length=20),
            existing_nullable=False, server_default="user",
        )
        batch_op.drop_column("timezone")
        batch_op.drop_column("individual_id")
