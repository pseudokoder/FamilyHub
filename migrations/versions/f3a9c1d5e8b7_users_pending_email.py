"""Account self-service: pending_email column on users (FE-5)

The self-serve "change my email" flow (unlike the admin change-email dance)
must not apply the new address until its verification link is clicked — this
additive, nullable column holds the address in flight.

Revision ID: f3a9c1d5e8b7
Revises: e7b5c9d3a1f2
Create Date: 2026-07-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a9c1d5e8b7'
down_revision = 'e7b5c9d3a1f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pending_email", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("pending_email")
