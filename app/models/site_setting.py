"""SiteSetting — a tiny key/value table for admin-editable site text.

TEACHING NOTE: why a key/value table instead of one column per setting?
Settings come and go ("tagline" today, "welcome_message" next month), and
adding a COLUMN means a migration every time. Adding a ROW is free. The
trade-off: the database can't type-check values (everything's text) — fine
for a handful of display strings, wrong for real domain data. Knowing when
key/value is appropriate (config) and when it isn't (entities like Photo)
is a data-modeling judgment call (D426).

v2 mapping: a @Entity SiteSetting with a tiny SettingsService cache, or
Spring's @ConfigurationProperties for static config.
"""

from app.extensions import db


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    # The key IS the primary key — natural, unique, and there's no point
    # in a surrogate id for a lookup table this small.
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="", server_default="")

    def __repr__(self):
        return f"<SiteSetting {self.key}>"
