"""GEDCOM export — turn the family wiki into a standard genealogy file.

WHY THIS EXISTS: GEDCOM (.ged) is the lingua franca of family trees —
Ancestry, FamilySearch, MyHeritage, and the open-source Gramps all import
it. The wiki already holds the raw material (names, birth/death dates,
bios, places), so one read-only export lets the family carry their tree
into "real" genealogy software without retyping a soul. It's the same
spirit as the JSON export (export_service): the data belongs to the
family, so give them a portable copy in the format their tools expect.

WHAT THIS DOES *NOT* DO (and why, honestly):
  - **No relationships.** GEDCOM's FAM records link parents/children/
    spouses, but v1 doesn't MODEL typed relationships — the wiki's
    [[Name]] links are freeform ("see also"), not "spouse of". Inventing
    relationships from untyped links would be guessing, and the timeline's
    partial-date rule taught us: honest "unknown" beats invented
    precision. So we export INDIviduals; the family draws the lines in
    their genealogy tool (or in v2, once relationships are a real table).
  - **No SEX field** — not tracked in v1.

GEDCOM 5.5.1 structure, minimally:
    0 HEAD ... 0 @I1@ INDI ... 0 TRLR
Every line is "LEVEL TAG value"; sub-facts nest by increasing level.

v2 mapping: a GedcomService; once relationships are modeled, FAM records
slot in alongside the INDI records this already produces.
"""

from app.models import FamilyMember

GEDCOM_MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]

# GEDCOM 5.5.1 caps a physical line at 255 bytes (level + tag + value).
# Long text is continued with CONC (same word, next line). We split well
# under the cap to leave room for the "N CONC " prefix.
_VALUE_CHARS = 200


def _date(value):
    """A Python date -> GEDCOM '12 MAR 1947'. We only store full dates,
    so there's no partial-date dance here (unlike the timeline)."""
    return f"{value.day} {GEDCOM_MONTHS[value.month - 1]} {value.year}"


def _split_name(full_name):
    """GEDCOM writes a name as 'Given /Surname/'. We only have one name
    string, so we use a documented heuristic: the last whitespace-separated
    word is the surname, the rest is the given name. Good for "Frank
    Leiter" and "Mary Jo Leiter"; for a single word ("Grandma") there's no
    surname and we emit just the given part. A guess, clearly marked as
    one — and a genealogist fixes names first thing anyway."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name, ""
    return " ".join(parts[:-1]), parts[-1]


def _emit_text(lines, level, tag, text):
    """Write 'level tag value', continuing onto CONT lines for embedded
    newlines and CONC lines when a single line would blow past GEDCOM's
    255-byte limit. This is the fiddly-but-correct part of the format."""
    paragraphs = (text or "").split("\n")
    first = True
    for paragraph in paragraphs:
        chunk, rest = paragraph[:_VALUE_CHARS], paragraph[_VALUE_CHARS:]
        if first:
            lines.append(f"{level} {tag} {chunk}".rstrip())
            first = False
        else:
            lines.append(f"{level + 1} CONT {chunk}".rstrip())
        while rest:
            chunk, rest = rest[:_VALUE_CHARS], rest[_VALUE_CHARS:]
            lines.append(f"{level + 1} CONC {chunk}")


def build_gedcom():
    """Return the whole family wiki as one GEDCOM 5.5.1 document (str)."""
    members = FamilyMember.query.order_by(FamilyMember.id).all()

    lines = [
        "0 HEAD",
        "1 SOUR FamilyHub",
        "2 VERS 1.0",
        "2 NAME FamilyHub",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
    ]

    for member in members:
        # @I1@, @I2@, ... — GEDCOM cross-reference ids. We use the DB id so
        # the same person keeps the same xref across re-exports.
        lines.append(f"0 @I{member.id}@ INDI")
        given, surname = _split_name(member.name)
        # With a surname, GEDCOM delimits it with slashes; without one,
        # emit just the given name (no empty "//").
        if surname:
            lines.append(f"1 NAME {given} /{surname}/")
        else:
            lines.append(f"1 NAME {given}")
        if member.birth_date:
            lines.append("1 BIRT")
            lines.append(f"2 DATE {_date(member.birth_date)}")
        if member.death_date:
            lines.append("1 DEAT")
            lines.append(f"2 DATE {_date(member.death_date)}")
        if member.location:
            lines.append("1 RESI")
            _emit_text(lines, 2, "PLAC", member.location)
        if member.bio:
            _emit_text(lines, 1, "NOTE", member.bio)

    lines.append("0 TRLR")
    # GEDCOM files conventionally use CRLF line endings.
    return "\r\n".join(lines) + "\r\n"
