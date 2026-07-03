"""WP3 admin: email verification + login lockout columns on users

Additive columns supporting Phase 2 security hardening (Master Plan §9):
  * email_verified_at   — when the current email address was verified (NULL = not
    yet). Set by the verification-link flow; cleared when the email changes.
  * failed_login_count  — consecutive failed sign-ins (reset on success).
  * locked_until        — account lockout timestamp once the settings-driven
    threshold is hit (NULL = not locked).

Revision ID: e7b5c9d3a1f2
Revises: d4a2c8e1f7b3
Create Date: 2026-07-03 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7b5c9d3a1f2'
down_revision = 'd4a2c8e1f7b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column(
            "failed_login_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_count")
        batch_op.drop_column("email_verified_at")
