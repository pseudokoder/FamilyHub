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
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
bootstrap = Bootstrap5()

# When an anonymous visitor hits a @login_required page, send them to the
# login form (the "auth" blueprint's "login" view) with a friendly message —
# not a scary 401 error. Elderly-first means errors guide, never scold.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to see family pages."
login_manager.login_message_category = "warning"
