"""GEDCOM export tests: valid structure, correct field mapping, the
admin-only download, and the honest limitations (no relationships)."""

from datetime import date

from app.extensions import db
from app.models import FamilyMember
from app.services import gedcom_service


def _add(name, **kwargs):
    member = FamilyMember(name=name, **kwargs)
    db.session.add(member)
    db.session.commit()
    return member


def test_gedcom_has_header_and_trailer(app):
    with app.app_context():
        doc = gedcom_service.build_gedcom()
    assert doc.startswith("0 HEAD")
    assert "2 VERS 5.5.1" in doc
    assert doc.rstrip().endswith("0 TRLR")
    assert "\r\n" in doc  # GEDCOM uses CRLF


def test_individual_fields_map_correctly(app):
    with app.app_context():
        ruth = _add("Ruth Leiter", location="Pittsburgh, PA",
                    bio="Loved her garden.",
                    birth_date=date(1925, 3, 12),
                    death_date=date(2019, 11, 4))
        doc = gedcom_service.build_gedcom()

    assert f"0 @I{ruth.id}@ INDI" in doc
    assert "1 NAME Ruth /Leiter/" in doc       # given/surname heuristic
    assert "1 BIRT" in doc and "2 DATE 12 MAR 1925" in doc
    assert "1 DEAT" in doc and "2 DATE 4 NOV 2019" in doc
    assert "2 PLAC Pittsburgh, PA" in doc
    assert "1 NOTE Loved her garden." in doc


def test_single_word_name_has_no_surname(app):
    with app.app_context():
        _add("Grandma")
        doc = gedcom_service.build_gedcom()
    # No trailing "/Surname/" slashes when there's only one name word.
    assert "1 NAME Grandma" in doc
    assert "1 NAME Grandma /" not in doc


def test_long_bio_is_split_with_conc(app):
    with app.app_context():
        _add("Wordy Wilkins", bio="x" * 500)  # well over GEDCOM's line cap
        doc = gedcom_service.build_gedcom()
    assert "2 CONC " in doc, "long values continue onto CONC lines"


def test_multiline_bio_uses_cont(app):
    with app.app_context():
        _add("Multi Line", bio="First line.\nSecond line.")
        doc = gedcom_service.build_gedcom()
    assert "1 NOTE First line." in doc
    assert "2 CONT Second line." in doc


def test_download_route_is_admin_only_and_audited(admin_client, member_client):
    """A member is refused; the admin gets a .ged attachment, and the
    export leaves an audit row."""
    admin_client.post("/family/new",
                      data={"name": "Ruth Leiter", "location": "",
                            "bio": "", "birth_date": "1925-03-12",
                            "death_date": ""})

    assert member_client.get("/family/export.ged").status_code == 403

    response = admin_client.get("/family/export.ged")
    assert response.status_code == 200
    assert response.mimetype == "application/x-gedcom"
    assert "attachment" in response.headers["Content-Disposition"]
    assert b"@I" in response.data and b"Ruth /Leiter/" in response.data

    from app.models import AuditLog
    assert AuditLog.query.filter_by(action="export").count() == 1
