"""All Flask extensions live here — created empty, wired up in the factory.

TEACHING NOTE: this solves the classic Flask chicken-and-egg problem.
Models need `db`. Routes need `login_manager`. But the `app` object doesn't
exist until create_app() runs. The fix is the **init_app pattern**:

  1. Create every extension HERE with no app:        db = SQLAlchemy()
  2. The factory binds them to the real app later:   db.init_app(app)

Any module can now `from app.extensions import db` with zero risk of a
circular import, because this file imports nothing from the rest of the app.

Who's who (and their Spring Boot v2 equivalents):
  db            — SQLAlchemy ORM: Python classes <-> SQL tables (Spring Data JPA)
  migrate       — Alembic schema migrations (Flyway)
  bcrypt        — password hashing (Spring Security's BCryptPasswordEncoder —
                  the SAME algorithm; v1 password hashes can be imported into
                  v2 unchanged. That's the zero-data-loss promise at work.)
  login_manager — session login state: who is this request? (Spring Security)
  csrf          — Cross-Site Request Forgery protection on every POST form
                  (Spring Security enables this by default, too)
  bootstrap     — Bootstrap 5 template helpers (closest v2 cousin: Angular
                  components, which replace server-rendered templates)
"""

from flask_bcrypt import Bcrypt
from flask_bootstrap import Bootstrap5
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData

# TEACHING NOTE — constraint NAMING CONVENTION. Databases give every index,
# foreign key, and unique rule an internal name. If we don't pick the names,
# each database invents its own — and then migrations can't talk about them
# ("rename WHICH constraint?"). This bit us for real: SQLite can't ALTER a
# table in place, so Alembic rebuilds it in "batch mode", and batch mode
# refuses to copy a constraint it can't name. The fix (straight from the
# Alembic docs) is to declare a convention once, here, so every constraint
# gets a predictable name like fk_photos_album_id_albums — on SQLite today
# and MySQL in v2. Deterministic names = portable migrations.
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
bootstrap = Bootstrap5()

# Rate limiter (D315): slows down password-guessing robots. No default
# limits — only the routes that opt in (the login form) are limited, keyed
# by visitor IP address. storage_uri="memory://" keeps counts in process
# memory: perfect for one gunicorn worker at family scale, and the v2 note
# is that a multi-server deployment would swap in Redis here — the
# decorator on the route wouldn't change at all.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

# When an anonymous visitor hits a @login_required page, send them to the
# login form (the "auth" blueprint's "login" view) with a friendly message —
# not a scary 401 error. Elderly-first means errors guide, never scold.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to see family pages."
login_manager.login_message_category = "warning"
