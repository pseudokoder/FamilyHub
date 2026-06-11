"""The models package — one file per database table (or tight family of tables).

TEACHING NOTE: `db` itself is created in app/extensions.py (see the long
note there about the init_app pattern). We re-export it here so models can
write `from app.models import db`, and we import every model module below so
SQLAlchemy and Alembic *see* all the tables — a model that's never imported
is invisible to `flask db migrate`!

v2 mapping: each class in this package becomes a Spring Boot @Entity, and
SQLAlchemy's query API becomes a Spring Data Repository interface.
"""

from app.extensions import db  # noqa: F401  (re-exported on purpose)

# Import models so SQLAlchemy "sees" them and migrations pick them up.
from app.models.family_member import FamilyMember  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
