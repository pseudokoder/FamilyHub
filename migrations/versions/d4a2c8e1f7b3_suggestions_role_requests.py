"""WP3 admin: suggestions inbox + role-change requests

Two additive application-layer tables (Master Plan §3.5 / §5). No genealogy data
is touched. site_settings needs no migration — it's key/value, so the new admin/
security/branding settings are just new ROWS (seeded by settings_service).

Revision ID: d4a2c8e1f7b3
Revises: c2f1a7b9d4e0
Create Date: 2026-07-03 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4a2c8e1f7b3'
down_revision = 'c2f1a7b9d4e0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("topic", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default="new"),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"],
            name=op.f("fk_suggestions_author_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestions")),
    )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_suggestions_status"), ["status"], unique=False)

    op.create_table(
        "role_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("requested_role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default="pending"),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_role_requests_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"], ["users.id"],
            name=op.f("fk_role_requests_decided_by_user_id_users"),
            ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_requests")),
    )
    with op.batch_alter_table("role_requests", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_role_requests_status"), ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("role_requests", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_role_requests_status"))
    op.drop_table("role_requests")
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_suggestions_status"))
    op.drop_table("suggestions")
