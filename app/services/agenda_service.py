from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_to_utc(
    value: str | None, assume_all_day: bool = False
) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware UTC datetime.

    - Accepts 'YYYY-MM-DD' for all-day (interpreted at 00:00 UTC) when
      assume_all_day=True.
    - Accepts full ISO strings with timezone info; converts to UTC.
    - If input is naive (no tzinfo), assumes it is UTC and attaches tzinfo.
    """
    if value is None:
        raise ValueError("value is None")

    value = value.strip()
    if not value:
        raise ValueError("empty datetime value")

    # All-day shorthand date (YYYY-MM-DD)
    if assume_all_day and len(value) == 10 and value.count("-") == 2:
        # Interpret start of day in UTC
        dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt

    # General ISO parsing: fromisoformat handles offsets like +00:00
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        # Fallback: remove 'Z' if present and try again
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value[:-1])
        else:
            raise

    if dt.tzinfo is None:
        # Assume already UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt


essential_iso_format = "%Y-%m-%dT%H:%M:%S%z"


def format_dt_iso(dt: datetime | None) -> str | None:
    """Format a timezone-aware UTC datetime to ISO string with 'Z'.

    If dt is None, returns None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Attach UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # Produce compact ISO with 'Z'
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
