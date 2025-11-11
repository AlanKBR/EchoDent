from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from flask import current_app

from .. import db
from ..models import Holiday

_CACHE_TTL_SECONDS = 3600  # 1 hour
_year_cache: dict[int, dict[str, Any]] = {}


def _now_ts() -> float:
    return time.time()


def _instance_token_path() -> str:
    try:
        base = current_app.instance_path
    except Exception:
        base = os.path.join(os.getcwd(), "instance")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "invertexto_token.txt")


def set_invertexto_token(token: str) -> None:
    path = _instance_token_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write(token.strip())


def clear_invertexto_token() -> None:
    path = _instance_token_path()
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def get_invertexto_token() -> str | None:
    # Prefer server config
    try:
        token = current_app.config.get("INVERTEXTO_API_TOKEN")
        if token:
            return str(token)
    except Exception:
        pass
    # Fallback to instance file
    path = _instance_token_path()
    try:
        with open(path, encoding="utf-8") as f:
            t = f.read().strip()
            return t or None
    except FileNotFoundError:
        return None


def _row_to_public(h: Holiday) -> dict[str, Any]:
    return {
        "date": h.date,
        "name": h.name,
        "type": h.type,
        "level": h.level,
        # state/source intentionally not exposed to client in UI needs,
        # but harmless if included. Keeping minimal here.
    }


def get_holidays_by_year(year: int) -> list[dict[str, Any]]:
    # Use tiny in-memory cache per process for the year
    ent = _year_cache.get(year)
    if ent and (_now_ts() - ent.get("ts", 0)) < _CACHE_TTL_SECONDS:
        return ent["data"]

    rows = (
        db.session.query(Holiday)
        .filter(Holiday.year == int(year))
        .order_by(Holiday.date.asc())
        .all()
    )
    data = [_row_to_public(r) for r in rows]
    _year_cache[year] = {"ts": _now_ts(), "data": data}
    return data


def refresh_holidays(year: int, state: str | None = None) -> dict[str, Any]:
    token = get_invertexto_token()
    if not token:
        return {"status": "error", "message": "Token não configurado"}

    # Lazy import to keep dependency optional when unused
    try:
        import httpx  # type: ignore
    except Exception:  # pragma: no cover
        return {"status": "error", "message": "Dependência httpx ausente"}

    y = int(year)
    base_url = f"https://api.invertexto.com/v1/holidays/{y}"
    params = {"token": token}
    if state:
        params["state"] = state.strip().upper()

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(base_url, params=params)
            if resp.status_code == 401 or resp.status_code == 403:
                return {"status": "error", "message": "Não autorizado"}
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:  # pragma: no cover
        return {"status": "error", "message": f"Falha na API: {e}"}

    # Normalize payload: expect list of {date, name, type, level}
    items: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for it in payload:
            try:
                d = str(it.get("date")).strip()
                nm = str(it.get("name") or "").strip() or "(sem nome)"
                tp = it.get("type") or None
                lv = it.get("level") or None
                items.append(
                    {
                        "date": d,
                        "name": nm,
                        "type": tp,
                        "level": lv,
                    }
                )
            except Exception:
                continue

    # UPSERT simplificado: apagar por (year, source)
    src = "invertexto"
    db.session.query(Holiday).filter(
        Holiday.year == y, Holiday.source == src
    ).delete(synchronize_session=False)

    now_utc = datetime.now(timezone.utc)
    to_add: list[Holiday] = []
    for it in items:
        h = Holiday()
        h.date = it["date"]
        h.name = it["name"]
        h.type = it.get("type")
        h.level = it.get("level")
        h.state = state.strip().upper() if state else None
        h.year = y
        h.source = src
        h.updated_at = now_utc
        to_add.append(h)

    if to_add:
        db.session.add_all(to_add)
    db.session.commit()

    # Invalidate cache for the year
    _year_cache.pop(y, None)
    return {"status": "success", "count": len(to_add)}


def clear_holiday_cache() -> None:
    """Clear in-memory holidays cache for all years."""
    _year_cache.clear()
