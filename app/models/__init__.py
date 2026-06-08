from flask_sqlalchemy import SQLAlchemy

# The single shared SQLAlchemy instance. Defined here (not bound to an app
# yet) so models can import it without causing circular imports. The factory
# calls db.init_app(app) to connect it to the real application.
db = SQLAlchemy()

# Import models so SQLAlchemy "sees" them and db.create_all() builds the tables.
from app.models.family_member import FamilyMember  # noqa: E402,F401
