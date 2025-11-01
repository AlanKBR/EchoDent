
from __future__ import annotations
from functools import wraps
from typing import Callable, Any
from flask import flash, redirect, url_for, current_app, abort
from flask_login import current_user
from app.models import RoleEnum


def debug_only(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator para rotas de desenvolvimento: só permite acesso se app.debug ou TESTING."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if not (current_app.debug or current_app.config.get("TESTING")):
            abort(404)
        return func(*args, **kwargs)
    return wrapper


def admin_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to restrict access to admins.

    - Requires authenticated user.
    - Requires current_user.role == RoleEnum.ADMIN
    - Otherwise, flashes and redirects to a safe page (patient list).
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # pragma: no cover - thin
        try:
            if not getattr(current_user, "is_authenticated", False):
                flash("Acesso restrito a administradores.", "error")
                return redirect(url_for("paciente_bp.lista"))
            if getattr(current_user, "role", None) != RoleEnum.ADMIN:
                flash("Acesso restrito a administradores.", "error")
                return redirect(url_for("paciente_bp.lista"))
        except Exception:
            # On any unexpected error in auth check, fail safe to redirect
            return redirect(url_for("paciente_bp.lista"))
        return func(*args, **kwargs)
    return wrapper


def dentista_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to restrict access to clinical staff (Dentist/Admin).

    - Requires authenticated user.
    - Allows RoleEnum.DENTISTA and RoleEnum.ADMIN.
    - Otherwise aborts with 403 Forbidden.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # pragma: no cover - thin
        try:
            if not getattr(current_user, "is_authenticated", False):
                abort(403)
            role = getattr(current_user, "role", None)
            if role not in (RoleEnum.DENTISTA, RoleEnum.ADMIN):
                abort(403)
        except Exception:
            abort(403)
        return func(*args, **kwargs)
    return wrapper
