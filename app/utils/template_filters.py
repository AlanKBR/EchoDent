from __future__ import annotations

from datetime import datetime
from typing import Optional


def format_datetime_br(dt_utc: Optional[datetime]) -> str:
    """Format a timezone-aware UTC datetime as dd/mm/YYYY HH:MM.

    - If dt_utc is None, return an empty string.
    - We don't convert timezones; we display the UTC timestamp recorded.
    """
    if dt_utc is None:
        return ""
    try:
        return dt_utc.strftime("%d/%m/%Y %H:%M")
    except Exception:
        # Fallback to safe string conversion if unexpected type
        return str(dt_utc)


def format_currency(value: object) -> str:
    """Format numeric value as Brazilian currency string.

    Examples:
    - 1234.5 -> "R$ 1.234,50"
    - None -> "R$ 0,00"
    """
    try:
        from decimal import Decimal

        if value is None:
            amt = Decimal("0")
        elif isinstance(value, Decimal):
            amt = value
        else:
            amt = Decimal(str(value))
        s = f"{amt:,.2f}"
        # Convert 1,234.56 -> 1.234,56
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {s}"
    except Exception:
        return f"R$ {value}"
