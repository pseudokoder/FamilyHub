"""users email login, role, is_active (WP2 RBAC)

Reshape the `users` table to Master Plan §3.5 + the §10 role ladder:
  * email becomes the NOT NULL, indexed LOGIN key (was a nullable reset address)
  * a `role` string replaces the `is_admin` boolean (is_admin=1 -> 'admin', else 'user')
  * a new `is_active` switch
  * `username` is retired (email is the identifier now)
  * password_hash widened 128 -> 255 to match the §3.5 spec

TEACHING NOTE (why batch_alter_table): SQLite can't ALTER a column's nullability
or DROP a column in place — it has to rebuild the table. Alembic's
``batch_alter_table`` does exactly that rebuild for us, copying the data across,
which is why every change to an existing SQLite table goes through it (the lesson
from the WP1 naming-convention note). On MySQL in v2 the same ops are real
ALTERs; the migration code doesn't change.

Revision ID: 8f1e6fa904a3
Revises: 8da914c51520
Create Date: 2026-06-17 08:39:06.449477
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1e6fa904a3'
down_revision = '8da914c51520'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add the new columns WITH server defaults, so every existing row is
    #    instantly valid (no NULLs in a NOT NULL column).
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'role', sa.String(length=20), nullable=False, server_default='user'))
        batch_op.add_column(sa.Column(
            'is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))

    # 2. Data migration (runs while both is_admin AND role exist): map the old
    #    boolean onto the new ladder, and defensively give any account that
    #    somehow lacks an email a unique placeholder so the NOT NULL + UNIQUE
    #    rules below can be applied without failing.
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
    op.execute(
        "UPDATE users SET email = 'user' || id || '@example.invalid' "
        "WHERE email IS NULL OR email = ''"
    )

    # 3. Reshape: email is now the login key (NOT NULL + indexed), password_hash
    #    is widened, and the retired columns go. Dropping `username` also drops
    #    its index in the rebuild.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=255),
                              nullable=False)
        batch_op.alter_column('password_hash', existing_type=sa.String(length=128),
                              type_=sa.String(length=255), existing_nullable=False)
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=False)
        # Drop the username index EXPLICITLY: in a batch rebuild Alembic
        # otherwise reflects it and tries to recreate it on the new table —
        # which fails, because we're dropping the username column it indexes.
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.drop_column('is_admin')
        batch_op.drop_column('username')


def downgrade():
    # Best-effort reverse (no production data depends on it): restore username +
    # is_admin from the email/role, then drop the WP2 columns.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column(
            'is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.drop_index(batch_op.f('ix_users_email'))
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255),
                              type_=sa.String(length=128), existing_nullable=False)
        batch_op.alter_column('email', existing_type=sa.String(length=255),
                              nullable=True)

    op.execute("UPDATE users SET is_admin = 1 WHERE role = 'admin'")
    op.execute("UPDATE users SET username = email WHERE username IS NULL")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'],
                              unique=True)
        batch_op.alter_column('username', existing_type=sa.String(length=64),
                              nullable=False)
        batch_op.drop_column('is_active')
        batch_op.drop_column('role')
