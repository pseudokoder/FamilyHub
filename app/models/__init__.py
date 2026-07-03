"""The models package — the GEDCOM-7 genealogy core plus the app's own tables.

TEACHING NOTE: `db` itself is created in app/extensions.py (see the long note
there about the init_app pattern). We re-export it here so models can write
`from app.models import db`, and we import every model module below so
SQLAlchemy and Alembic *see* all the tables — a model that's never imported
is invisible to `flask db migrate`!

WP1 RE-FOUNDATION (Master Plan §3): these imports are the whole schema. The
genealogy core (individuals → families → events → sources → media → notes) is
the data model every "feature" is just a view of. `User`, `SiteSetting`, and
`AuditLog` are the application's own non-genealogy tables, carried forward from
the first build (the preserved auth + admin + security infrastructure).

v2 mapping: each class in this package becomes a Spring Boot @Entity, and
SQLAlchemy's query API becomes a Spring Data Repository interface.
"""

from app.extensions import db  # noqa: F401  (re-exported on purpose)

# --- Genealogy core (GEDCOM 7) -----------------------------------------------
# Order is just readability; SQLAlchemy resolves relationships by name, not by
# import order.
from app.models.individual import Individual, Name  # noqa: E402,F401
from app.models.family import Family, FamilyChild  # noqa: E402,F401
from app.models.place import Place  # noqa: E402,F401
from app.models.event import Event  # noqa: E402,F401
from app.models.source import Citation, Repository, Source  # noqa: E402,F401
from app.models.media import MediaLink, MediaObject  # noqa: E402,F401
from app.models.note import Note, NoteLink  # noqa: E402,F401

# --- Application layer (not GEDCOM — the website's own needs) -----------------
from app.models.role import Role  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.site_setting import SiteSetting  # noqa: E402,F401
from app.models.audit_log import AuditLog  # noqa: E402,F401
from app.models.historical_event import HistoricalEvent  # noqa: E402,F401
from app.models.suggestion import Suggestion  # noqa: E402,F401
from app.models.role_request import RoleRequest  # noqa: E402,F401

# A tidy public surface: `from app.models import *` (and humans reading this)
# get exactly the tables, nothing leaked from imports above.
__all__ = [
    "db",
    "Individual", "Name",
    "Family", "FamilyChild",
    "Place",
    "Event",
    "Repository", "Source", "Citation",
    "MediaObject", "MediaLink",
    "Note", "NoteLink",
    "Role", "User", "SiteSetting", "AuditLog", "HistoricalEvent",
    "Suggestion", "RoleRequest",
]
