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

    # Column names match Master Plan §3.5 exactly (setting_key / setting_value)
    # so the v1 schema and the v2 MySQL schema are the same shape — one less
    # thing to reconcile during the migration.
    #
    # The key IS the primary key — natural, unique, and there's no point
    # in a surrogate id for a lookup table this small.
    setting_key = db.Column(db.String(80), primary_key=True)
    setting_value = db.Column(db.Text, nullable=False, default="", server_default="")

    def __repr__(self):
        return f"<SiteSetting {self.setting_key}>"
