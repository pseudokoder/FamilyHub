"""The main blueprint: just the home page.

The home page is the ONLY public page in the app, and it shows zero family
content — logged-out visitors see a welcome message and a Login button,
nothing else. Everything with family PII lives behind @login_required
(CLAUDE.md privacy rule).
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    # The template checks current_user.is_authenticated itself: a dashboard
    # of big buttons for family, a welcome + login button for everyone else.
    return render_template("index.html")
