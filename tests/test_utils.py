from __future__ import annotations

from datetime import datetime, timezone

from app.utils.template_filters import format_datetime_br


def test_format_datetime_br_happy_and_none():
    dt = datetime(2025, 10, 26, 13, 45, tzinfo=timezone.utc)
    assert format_datetime_br(dt) == "26/10/2025 13:45"
    assert format_datetime_br(None) == ""
