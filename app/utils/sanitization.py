"""Centralized input sanitization utilities.

Rule 7: All free-text inputs must be sanitized before persisting to the DB.
This module provides the foundational function used across services.
"""
from typing import Any


def sanitizar_input(value: Any) -> Any:
    """Return a sanitized version of user-provided free-text input.

    - If value is a str: trims leading/trailing whitespace.
    - If value is None or not a str: returns as-is (no modification).

    This function is intentionally minimal for the foundation step.
    Future hardening (e.g., XSS neutralization) can be layered here
    without touching callers.
    """
    if isinstance(value, str):
        return value.strip()
    return value
