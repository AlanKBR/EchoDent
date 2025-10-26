from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import db
from sqlalchemy import delete
from app.models import Usuario, RoleEnum, CalendarEvent


@pytest.fixture()
def seed_dentists(app):
    """Create two active dentists on users bind."""
    with app.app_context():
        # Clean up any previously created test dentists to avoid
        # UNIQUE conflicts
        try:
            db.session.execute(
                delete(Usuario).where(Usuario.username.in_(["dent1", "dent2"]))
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        d1 = Usuario()
        d1.username = "dent1"
        d1.password_hash = "x"
        d1.role = RoleEnum.DENTISTA
        d1.nome_completo = "Dentista Um"
        d1.color = "#2563eb"

        d2 = Usuario()
        d2.username = "dent2"
        d2.password_hash = "x"
        d2.role = RoleEnum.DENTISTA
        d2.nome_completo = "Dentista Dois"
        d2.color = "#16a34a"

        db.session.add_all([d1, d2])
        db.session.commit()
        return d1.id, d2.id


def test_agenda_page_renders(client):
    resp = client.get("/agenda")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Key containers in the agenda page card
    assert "class=\"card agenda-card\"" in html or "agenda-card" in html
    assert "id=\"calendar\"" in html
    assert "id=\"miniCalendarFallback\"" in html
    assert "id=\"dentistsContainer\"" in html
    assert "id=\"filterNotice\"" in html
    # No inline CSS/JS indicators; theme override link placeholder is present
    assert "id=\"theme-override\"" in html


def _mk_iso(dt: datetime) -> str:
    # Return ISO with Z (UTC) to match API expectations
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture()
def seed_events(app, seed_dentists):
    """Create a small set of events in calendario bind.
    - ev1: assigned to d1, inside range
    - ev2: unassigned, inside range
    - ev3: assigned to d2, outside range
    """
    d1_id, d2_id = seed_dentists
    now = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    with app.app_context():
        ev1 = CalendarEvent()
        ev1.title = "Consulta Foo"
        ev1.start = now
        ev1.end = now + timedelta(hours=1)
        ev1.all_day = False
        ev1.dentista_id = d1_id
        ev1.color = "#2563eb"

        ev2 = CalendarEvent()
        ev2.title = "Retorno Bar"
        ev2.start = now + timedelta(days=1, hours=2)
        ev2.end = now + timedelta(days=1, hours=3)
        ev2.all_day = False
        ev2.dentista_id = None
        ev2.color = "#dc2626"

        ev3 = CalendarEvent()
        ev3.title = "Fora do Range"
        ev3.start = now + timedelta(days=60)
        ev3.end = now + timedelta(days=60, hours=2)
        ev3.all_day = False
        ev3.dentista_id = d2_id
        ev3.color = "#16a34a"
        db.session.add_all([ev1, ev2, ev3])
        db.session.commit()
        return {
            "d1": d1_id,
            "d2": d2_id,
            "ev1": ev1.id,
            "ev2": ev2.id,
            "ev3": ev3.id,
            "range_start": _mk_iso(now - timedelta(days=1)),
            "range_end": _mk_iso(now + timedelta(days=3)),
        }


def test_events_filtering_by_dentists_and_unassigned(client, seed_events):
    d1 = seed_events["d1"]
    start = seed_events["range_start"]
    end = seed_events["range_end"]

    # Only d1 (should include ev1 only)
    resp = client.get(
        f"/api/agenda/events?dentists={d1}&start={start}&end={end}"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    ids = {int(it["id"]) for it in data}
    assert seed_events["ev1"] in ids
    assert seed_events["ev2"] not in ids

    # No dentists + include_unassigned -> only unassigned (ev2)
    resp = client.get(
        f"/api/agenda/events?include_unassigned=1&start={start}&end={end}"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    ids = {int(it["id"]) for it in data}
    assert seed_events["ev2"] in ids
    assert seed_events["ev1"] not in ids

    # d1 + include_unassigned -> union (ev1, ev2)
    resp = client.get(
        "/api/agenda/events",
        query_string={
            "dentists": str(d1),
            "include_unassigned": "1",
            "start": start,
            "end": end,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    ids = {int(it["id"]) for it in data}
    assert seed_events["ev1"] in ids and seed_events["ev2"] in ids

    # Text search (q) filters by title/notes
    resp = client.get(
        f"/api/agenda/events?dentists={d1}&start={start}&end={end}&q=Foo"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    titles = {it["title"] for it in data}
    assert "Consulta Foo" in titles


def test_search_range_api(client, seed_events):
    d1 = seed_events["d1"]
    resp = client.get(
        f"/api/agenda/events/search_range?dentists={d1}&q=Foo"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data["count"] >= 1
    assert data["min"] is not None and data["max"] is not None


def test_holidays_year_and_refresh_without_token(client):
    # Initially returns empty for the given year
    r = client.get("/api/agenda/holidays/year?year=2025")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)

    # Refresh without token should error (400)
    r2 = client.post("/api/agenda/holidays/refresh", json={"year": 2025})
    assert r2.status_code == 400
    body = r2.get_json()
    assert body.get("status") == "error"


def test_dentists_api_lists_active_dentists(client, seed_dentists):
    r = client.get("/api/agenda/dentists")
    assert r.status_code == 200
    arr = r.get_json()
    assert isinstance(arr, list)
    # Should include two dentists created in fixture
    names = {it["nome"] for it in arr}
    assert {"Dentista Um", "Dentista Dois"}.issubset(names)
