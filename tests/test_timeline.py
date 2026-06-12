"""Timeline tests: partial dates, ordering, the day-without-month rule."""

from app.models import TimelineEvent


def _add_event(client, title, year, month="0", day="", description=""):
    return client.post(
        "/timeline/new",
        data={"title": title, "year": str(year), "month": month, "day": day,
              "description": description},
        follow_redirects=True,
    )


def test_three_precisions_render_honestly(admin_client):
    _add_event(admin_client, "Came over from Germany", 1890)
    _add_event(admin_client, "House fire", 1962, month="3")
    _add_event(admin_client, "Grandpa born", 1947, month="6", day="12")

    page = admin_client.get("/timeline").data.decode()
    assert ">1890<" in page              # year only — no invented Jan 1
    assert "March 1962" in page
    assert "June 12, 1947" in page


def test_chronological_regardless_of_entry_order(admin_client):
    _add_event(admin_client, "Newest", 2001)
    _add_event(admin_client, "Oldest", 1890)
    _add_event(admin_client, "Middle", 1947)
    page = admin_client.get("/timeline").data.decode()
    assert page.index("Oldest") < page.index("Middle") < page.index("Newest")


def test_decade_headers(admin_client):
    _add_event(admin_client, "A", 1961)
    _add_event(admin_client, "B", 1968)  # same decade — header printed ONCE
    _add_event(admin_client, "C", 1975)
    page = admin_client.get("/timeline").data.decode()
    assert page.count("1960s") == 1
    assert page.count("1970s") == 1


def test_day_without_month_rejected(admin_client):
    response = _add_event(admin_client, "Bad date", 1980, month="0", day="15")
    assert b"pick the month too" in response.data
    assert TimelineEvent.query.count() == 0


def test_silly_year_rejected(admin_client):
    response = _add_event(admin_client, "Typo year", 19477)
    assert b"looks off" in response.data


def test_everyone_edits_creator_or_admin_deletes(admin_client, member_client):
    _add_event(admin_client, "Admins event", 1950)
    event_id = TimelineEvent.query.one().id

    # Any member may edit (collaborative, like the wiki)...
    response = member_client.post(
        f"/timeline/{event_id}/edit",
        data={"title": "Admins event, corrected", "year": "1951", "month": "0",
              "day": "", "description": ""},
        follow_redirects=True,
    )
    assert b"updated" in response.data

    # ...but only the creator or an admin may delete.
    assert member_client.post(f"/timeline/{event_id}/delete").status_code == 403
    response = admin_client.post(f"/timeline/{event_id}/delete", follow_redirects=True)
    assert b"removed from the timeline" in response.data
